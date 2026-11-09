from datetime import datetime
import json
import os
import time
import altair as alt
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Estrategia Dinámica — Momentum & Tendencia",
    page_icon="📈",
    layout="wide",
)

# Autorefresco nativo robusto cada 30 segundos
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# Estilos CSS forzados para modo claro en móviles y total visibilidad de encabezados
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }
    .stApp {
        background-color: #f8f9fa !important;
    }
    .dynamic-header {
        background: linear-gradient(135deg, #FF512F, #DD2476);
        padding: 12px 18px;
        border-radius: 10px;
        color: #ffffff !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .dynamic-header h1 {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    .dynamic-header p {
        color: #ffffff !important;
        margin-top: 3px;
        margin-bottom: 0;
        font-size: 0.82rem;
        opacity: 0.95;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: bold;
        color: #0d6efd !important;
    }
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricDelta"] {
        background-color: #e8f5e9 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
    [data-testid="stMetricDelta"] > div {
        color: #2e7d32 !important;
        font-weight: 600 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

BITACORA_FILE = "bitacora_dinamica.json"

CANDIDATAS_DINAMICO = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NFLX",
    "AMD",
    "INTC",
]
NUM_ACTIVOS = 3
STOP_LOSS_INDIVIDUAL_PCT = -0.75


def cargar_bitacora():
  """Lee rigurosamente el JSON físico respetando todo el histórico real sin frenarse en listas estáticas."""
  base_default_inicial = {"Fecha": "30/10/2026", "Capital": 10600.0}

  if os.path.exists(BITACORA_FILE):
    try:
      with open(BITACORA_FILE, "r", encoding="utf-8") as f:
        contenido = json.load(f)
        if isinstance(contenido, dict):
          contenido.setdefault("ganancia_cerrada", 0.0)
          contenido.setdefault("posiciones", [])
          contenido.setdefault("peak_flotante", 0.0)
          contenido.setdefault("historial_alertas", [])
          contenido.setdefault("ultimo_cierre_automatico", "")

          historial = contenido.get("historial_rendimiento", [])

          # Limpiar y parsear cada entrada del JSON real
          historial_limpio = {}
          for h in historial:
            f_limpia = str(h.get("Fecha", "")).split(" ")[0]
            cap_val = float(h.get("Capital", 0.0))
            if f_limpia and cap_val > 0:
              historial_limpio[f_limpia] = cap_val

          if not historial_limpio:
            historial_limpio[base_default_inicial["Fecha"]] = (
                base_default_inicial["Capital"]
            )

          # Reconstruir la lista ordenada cronológicamente
          lista_temporal = [
              {"Fecha": k, "Capital": v} for k, v in historial_limpio.items()
          ]
          try:
            lista_ordenada = sorted(
                lista_temporal,
                key=lambda x: datetime.strptime(x["Fecha"], "%d/%m/%Y"),
            )
          except Exception:
            lista_ordenada = lista_temporal

          contenido["historial_rendimiento"] = lista_ordenada

          # Sincronización automática del capital inicial con el último cierre del histórico real
          if lista_ordenada:
            contenido["capital_inicial"] = float(
                lista_ordenada[-1]["Capital"]
            )
          else:
            contenido["capital_inicial"] = 10600.0

          return contenido
    except Exception:
      pass

  # Si no existe el archivo, se crea con el punto base inicial
  base_data = {
      "capital_inicial": 10600.0,
      "ganancia_cerrada": 0.0,
      "posiciones": [],
      "peak_flotante": 0.0,
      "historial_alertas": [],
      "ultimo_cierre_automatico": "",
      "historial_rendimiento": [base_default_inicial],
  }
  with open(BITACORA_FILE, "w", encoding="utf-8") as f:
    json.dump(base_data, f, indent=4, ensure_ascii=False)
  return base_data


def guardar_bitacora(data):
  with open(BITACORA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)


def ejecutar_cierre_jornada(capital_final, origen="manual"):
  fecha_actual = datetime.now().strftime("%d/%m/%Y")
  capital_redondeado = round(float(capital_final), 2)

  if os.path.exists(BITACORA_FILE):
    try:
      with open(BITACORA_FILE, "r", encoding="utf-8") as f:
        datos_actuales = json.load(f)
    except Exception:
      datos_actuales = {}
  else:
    datos_actuales = {}

  historial = datos_actuales.get("historial_rendimiento", [])
  historial = [
      h
      for h in historial
      if str(h.get("Fecha", "")).split(" ")[0] != fecha_actual
  ]
  historial.append({"Fecha": fecha_actual, "Capital": capital_redondeado})

  try:
    historial = sorted(
        historial, key=lambda x: datetime.strptime(x["Fecha"], "%d/%m/%Y")
    )
  except Exception:
    pass

  nuevo_estado = {
      "capital_inicial": capital_redondeado,
      "ganancia_cerrada": 0.0,
      "posiciones": [],
      "peak_flotante": 0.0,
      "historial_alertas": datos_actuales.get("historial_alertas", []),
      "ultimo_cierre_automatico": (
          fecha_actual
          if origen == "automatico"
          else datos_actuales.get("ultimo_cierre_automatico", "")
      ),
      "historial_rendimiento": historial,
  }

  with open(BITACORA_FILE, "w", encoding="utf-8") as f:
    json.dump(nuevo_estado, f, indent=4, ensure_ascii=False)


data_bitacora = cargar_bitacora()

# Sidebar
st.sidebar.markdown("### 📈 **BOT DINÁMICO**")
st.sidebar.markdown("*Momentum & Control de Riesgo*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider(
    "Meta Diaria (%)", min_value=0.5, max_value=10.0, value=3.0, step=0.05
)
trailing_tolerance_pct = st.sidebar.slider(
    "Tolerancia Retroceso (%)", min_value=0.05, max_value=5.0, value=0.5, step=0.05
)

# Encabezado principal del Bot Dinámico
st.markdown(
    """
    <div class="dynamic-header">
        <h1>📈 BOT DINÁMICO — MOMENTUM & TENDENCIA</h1>
        <p>Estrategia de Impulso | Control de Riesgo & Acumulación Diaria</p>
    </div>
""",
    unsafe_allow_html=True,
)

posiciones = data_bitacora.get("posiciones", [])
total_flotante = 0.0
posiciones_procesadas = []
posiciones_restantes = []
hubo_cierre_individual = False

for pos in posiciones:
  ticker = pos.get("ticker")
  precio_entrada = float(pos.get("precio_entrada", 0.0))
  acciones = float(pos.get("acciones", 0.0))

  try:
    df = yf.Ticker(ticker).history(period="1d")
    precio_actual = (
        float(df["Close"].iloc[-1]) if not df.empty else precio_entrada
    )
  except Exception:
    precio_actual = precio_entrada

  pnl_usd = (precio_actual - precio_entrada) * acciones
  pnl_pct = (
      (((precio_actual - precio_entrada) / precio_entrada) * 100.0)
      if precio_entrada > 0
      else 0.0
  )

  if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
    data_bitacora["ganancia_cerrada"] += pnl_usd
    msg = (
        f"[{time.strftime('%H:%M:%S')}] 🛡️ STOP LOSS: Cierre en {ticker} a"
        f" {pnl_pct:.2f}% (${pnl_usd:.2f} USD)."
    )
    data_bitacora["historial_alertas"].append(msg)
    hubo_cierre_individual = True
  else:
    total_flotante += pnl_usd
    posiciones_restantes.append(pos)
    posiciones_procesadas.append({
        "Activo": ticker,
        "Precio Entrada": round(precio_entrada, 2),
        "Precio Actual": round(precio_actual, 2),
        "Acciones": round(acciones, 4),
        "PnL (USD)": round(pnl_usd, 2),
        "PnL (%)": round(pnl_pct, 2),
    })

if hubo_cierre_individual:
  data_bitacora["posiciones"] = posiciones_restantes
  guardar_bitacora(data_bitacora)
  st.rerun()

capital_base = float(data_bitacora.get("capital_inicial", 11229.17))
ganancia_cerrada = float(data_bitacora.get("ganancia_cerrada", 0.0))

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (
    (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0
)

peak_previo = float(data_bitacora.get("peak_flotante", 0.0))
if flotante_pct > peak_previo:
  data_bitacora["peak_flotante"] = flotante_pct
  guardar_bitacora(data_bitacora)
  peak_actual = flotante_pct
else:
  peak_actual = peak_previo

umbral_calculado = peak_actual - trailing_tolerance_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

# Cierre automático por Trailing Stop Global
if (
    peak_actual >= meta_diaria_pct
    and flotante_pct <= umbral_salida
    and len(posiciones_procesadas) > 0
):
  nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
  ejecutar_cierre_jornada(nuevo_capital, origen="automatico")
  st.rerun()

# Cierre automático por Horario (17:00 hrs)
hora_actual_str = datetime.now().strftime("%H:%M")
fecha_hoy_str = datetime.now().strftime("%d/%m/%Y")
ultimo_auto = data_bitacora.get("ultimo_cierre_automatico", "")

if (
    hora_actual_str >= "17:00"
    and len(posiciones_procesadas) > 0
    and ultimo_auto != fecha_hoy_str
):
  nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
  ejecutar_cierre_jornada(nuevo_capital, origen="automatico")
  st.success(
      "⏰ [Cierre Automático 17:00] Jornada cerrada. Capital acumulado:"
      f" ${nuevo_capital:,.2f} USD"
  )
  st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Capital Cuenta",
    f"${capital_base + total_flotante:,.2f} USD",
    f"Base Acumulada: ${capital_base:,.2f}",
)
col2.metric(
    "Ganancia Realizada",
    f"+${ganancia_total_dia:,.2f} USD",
    f"{ganancia_total_pct:.2f}% del Capital",
)
col3.metric(
    "Flotante Actual",
    f"+${total_flotante:,.2f} USD",
    f"Peak: +{peak_actual:.2f}%",
)
col4.metric(
    "Meta / Umbral",
    f"Meta: {meta_diaria_pct:.2f}%",
    f"Umbral: +{umbral_salida:.2f}%",
)

st.markdown("---")

if st.sidebar.button("🚀 Abrir Jornada"):
  st.sidebar.info("Seleccionando activos...")
  top_activos = CANDIDATAS_DINAMICO[:NUM_ACTIVOS]

  if len(top_activos) > 0:
    monto_por_accion = capital_base / len(top_activos)
    nuevas_pos = []
    for t in top_activos:
      try:
        px = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
      except Exception:
        px = 100.0
      nuevas_pos.append({
          "ticker": t,
          "precio_entrada": round(px, 2),
          "acciones": round(monto_por_accion / px, 4),
      })
    data_bitacora["posiciones"] = nuevas_pos
    data_bitacora["peak_flotante"] = 0.0
    guardar_bitacora(data_bitacora)
    st.sidebar.success(f"Posiciones abiertas: {', '.join(top_activos)}")
    st.rerun()

if st.sidebar.button("🔴 Cierre Manual de Jornada"):
  if data_bitacora.get("posiciones"):
    ganancia_del_dia = total_flotante + ganancia_cerrada
    nuevo_capital = round(capital_base + ganancia_del_dia, 2)

    ejecutar_cierre_jornada(nuevo_capital, origen="manual")

    st.success(
        "✅ **¡Cierre Manual Exitoso!** Capital acumulado actualizado a"
        f" **${nuevo_capital:,.2f} USD** como base inicial para la siguiente"
        " sesión."
    )
    time.sleep(1.5)
    st.rerun()
  else:
    st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🟢 Posiciones en Curso")
if posiciones_procesadas:
  st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
  st.success("✅ **Sin posiciones abiertas.**")

st.markdown("---")

# 📈 Gráfico de Evolución Histórica del Capital con Altair
historial = data_bitacora.get("historial_rendimiento", [])
if historial:
  df_chart = pd.DataFrame(historial)
  if "Fecha" in df_chart.columns and "Capital" in df_chart.columns:
    df_chart["Fecha_limpia"] = (
        df_chart["Fecha"].astype(str).str.split(" ").str[0]
    )
    df_chart["Fecha_obj"] = pd.to_datetime(
        df_chart["Fecha_limpia"], format="%d/%m/%Y", errors="coerce"
    )
    df_chart = df_chart.sort_values(by="Fecha_obj", ascending=True).reset_index(
        drop=True
    )

    st.subheader("📈 Evolución Histórica del Capital")

    chart = (
        alt.Chart(df_chart)
        .mark_line(point=True, strokeWidth=3, color="#0d6efd")
        .encode(
            x=alt.X(
                "Fecha_limpia:N",
                title="Fecha",
                sort=df_chart["Fecha_limpia"].tolist(),
            ),
            y=alt.Y(
                "Capital:Q",
                title="Capital (USD)",
                scale=alt.Scale(domain=[9000, 15000]),
            ),
            tooltip=["Fecha_limpia", alt.Tooltip("Capital:Q", format="$,.2f")],
        )
        .properties(height=320)
    )

    text = chart.mark_text(
        align="center", baseline="bottom", dy=-12, color="#333333", fontWeight="bold"
    ).encode(text=alt.Text("Capital:Q", format="$,.0f"))

    st.altair_chart(
        (chart + text).configure_view(stroke=None), use_container_width=True
    )

st.markdown("---")
st.subheader("📋 Historial de Cierres Recientes (Últimos 14 días)")

if historial:
  df_hist = pd.DataFrame(historial)
  if "Fecha" in df_hist.columns and "Capital" in df_hist.columns:
    df_hist["Fecha_limpia"] = (
        df_hist["Fecha"].astype(str).str.split(" ").str[0]
    )
    df_hist["Fecha_obj"] = pd.to_datetime(
        df_hist["Fecha_limpia"], format="%d/%m/%Y", errors="coerce"
    )
    df_hist = df_hist.sort_values(by="Fecha_obj", ascending=True).reset_index(
        drop=True
    )

    capital_inicial_base = (
        float(df_hist["Capital"].iloc[0]) if len(df_hist) > 0 else 10000.0
    )

    df_hist["Rent_Diaria_Pct"] = df_hist["Capital"].pct_change() * 100.0
    df_hist["Rent_Diaria_Pct"] = df_hist["Rent_Diaria_Pct"].fillna(0.0)
    df_hist["Rent_Acumulada_Pct"] = (
        (df_hist["Capital"] - capital_inicial_base) / capital_inicial_base
    ) * 100.0

    df_hist["Rent. Diaria"] = df_hist["Rent_Diaria_Pct"].apply(
        lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%"
    )
    df_hist["Rent. Acumulada"] = df_hist["Rent_Acumulada_Pct"].apply(
        lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%"
    )
    df_hist["Capital_USD"] = df_hist["Capital"].apply(
        lambda x: f"${float(x):,.2f} USD"
    )

    df_mostrar = df_hist.sort_values(by="Fecha_obj", ascending=False).copy()
    df_mostrar = df_mostrar[
        ["Fecha_limpia", "Capital_USD", "Rent. Diaria", "Rent. Acumulada"]
    ].rename(columns={"Fecha_limpia": "Fecha", "Capital_USD": "Capital"})

    st.dataframe(df_mostrar.head(14), use_container_width=True, hide_index=True)
  else:
    df_hist = pd.DataFrame(historial)
    st.dataframe(df_hist.tail(14), use_container_width=True)
else:
  st.info("Aún no hay registros históricos de cierre.")
