from datetime import datetime
import json
import os
import time
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Estrategia Eventos — Impulso por Noticias",
    page_icon="📰",
    layout="wide",
)

# Autorefresco nativo cada 30 segundos
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# Nombre exacto del archivo JSON de bitácora para Eventos
BITACORA_EVENTOS = "bitacora_eventos.json"

def cargar_bitacora_eventos():
    """Lee rigurosamente el archivo JSON físico asegurando la presencia del cierre de hoy (10,552.58) y sincronización de capital."""
    base_defaults = [
        {"Fecha": "28/10/2026", "Capital": 10000.00},
        {"Fecha": "29/10/2026", "Capital": 10247.23},
        {"Fecha": "30/10/2026", "Capital": 10590.01},
        {"Fecha": "02/11/2026", "Capital": 10555.68},
        {"Fecha": "03/11/2026", "Capital": 10552.58}
    ]
    
    if os.path.exists(BITACORA_EVENTOS):
        try:
            with open(BITACORA_EVENTOS, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, dict):
                    contenido.setdefault("ganancia_cerrada", 0.0)
                    contenido.setdefault("posiciones", [])
                    contenido.setdefault("peak_flotante", 0.0)
                    contenido.setdefault("historial_alertas", [])
                    contenido.setdefault("ultimo_cierre_automatico", "")
                    
                    historial = contenido.get("historial_rendimiento", [])
                    
                    # Limpiar entradas y asegurar puntos base históricos + hoy
                    historial_limpio = {}
                    for base in base_defaults:
                        historial_limpio[base["Fecha"]] = base["Capital"]
                        
                    for h in historial:
                        f_limpia = str(h.get("Fecha", "")).split(" ")[0]
                        if f_limpia:
                            historial_limpio[f_limpia] = float(h.get("Capital", 0.0))
                            
                    nuevo_historial = [{"Fecha": k, "Capital": v} for k, v in historial_limpio.items()]
                    contenido["historial_rendimiento"] = nuevo_historial

                    # Sincronización automática del capital inicial con el último cierre
                    if nuevo_historial:
                        try:
                            historial_ordenado = sorted(nuevo_historial, key=lambda x: datetime.strptime(x["Fecha"], "%d/%m/%Y"))
                            ultimo_registro = historial_ordenado[-1]
                            contenido["capital_inicial"] = float(ultimo_registro["Capital"])
                        except Exception:
                            contenido["capital_inicial"] = float(nuevo_historial[-1].get("Capital", 10552.58))
                    else:
                        contenido.setdefault("capital_inicial", 10552.58)

                    return contenido
        except Exception:
            pass

    base_data = {
        "capital_inicial": 10552.58,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": [],
        "ultimo_cierre_automatico": "",
        "historial_rendimiento": base_defaults,
    }
    with open(BITACORA_EVENTOS, "w", encoding="utf-8") as f:
        json.dump(base_data, f, indent=4, ensure_ascii=False)
    return base_data

def guardar_bitacora_eventos(data):
    """Sobrescribe el archivo JSON con el estado actualizado."""
    with open(BITACORA_EVENTOS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def ejecutar_cierre_jornada_eventos(capital_final, origen="manual"):
    """Función blindada: guarda strictly la fecha en formato DD/MM/YYYY sin duplicados y actualiza el capital inicial."""
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    capital_redondeado = round(float(capital_final), 2)

    if os.path.exists(BITACORA_EVENTOS):
        try:
            with open(BITACORA_EVENTOS, "r", encoding="utf-8") as f:
                datos_actuales = json.load(f)
        except Exception:
            datos_actuales = {}
    else:
        datos_actuales = {}

    historial = datos_actuales.get("historial_rendimiento", [])
    
    # Filtrar cualquier registro previo de la misma fecha exacta para actualizarlo sin duplicar
    historial = [h for h in historial if str(h.get("Fecha", "")).split(" ")[0] != fecha_actual]
    historial.append({"Fecha": fecha_actual, "Capital": capital_redondeado})

    nuevo_estado = {
        "capital_inicial": capital_redondeado,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": datos_actuales.get("historial_alertas", []),
        "ultimo_cierre_automatico": fecha_actual if origen == "automatico" else datos_actuales.get("ultimo_cierre_automatico", ""),
        "historial_rendimiento": historial
    }

    with open(BITACORA_EVENTOS, "w", encoding="utf-8") as f:
        json.dump(nuevo_estado, f, indent=4, ensure_ascii=False)

data_bitacora = cargar_bitacora_eventos()

# Estilos CSS con margen superior ajustado a cero y contraste móvil
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .eventos-header {
        background: linear-gradient(135deg, #2C3E50, #4CA1AF);
        padding: 10px 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .eventos-header h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    .eventos-header p {
        color: #f0f0f0;
        margin-top: 3px;
        margin-bottom: 0;
        font-size: 0.82rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: bold;
        color: #2C3E50;
    }
    </style>
""",
    unsafe_allow_html=True,
)

CANDIDATAS_EVENTOS = [
    "SPY", "QQQ", "DIA", "IWM", "XLE", "XLF", "XLV", "XLI", "XLC", "XLU"
]

NUM_ACTIVOS_OBJETIVO = 3
STOP_LOSS_INDIVIDUAL_PCT = -1.00

def seleccionar_top_eventos(n=3):
    resultados = []
    for ticker in CANDIDATAS_EVENTOS:
        try:
            yt = yf.Ticker(ticker)
            df = yt.history(period="2d")
            if len(df) >= 2:
                c_prev = df["Close"].iloc[-2]
                c_act = df["Close"].iloc[-1]
                var_pct = ((c_act - c_prev) / c_prev) * 100.0
                resultados.append((ticker, var_pct))
        except Exception:
            continue

    resultados.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in resultados[:n]]

# Barra lateral
st.sidebar.markdown("### 📰 **BOT DE EVENTOS**")
st.sidebar.markdown("*Estrategia Basada en Reacción a Catalizadores*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider(
    "Meta Diaria (%)", min_value=0.3, max_value=8.0, value=3.00, step=0.05
)
tolerancia_retroceso_pct = st.sidebar.slider(
    "Tolerancia de Retroceso (%)", min_value=0.05, max_value=5.0, value=0.50, step=0.05
)

st.markdown(
    """
    <div class="eventos-header">
        <h1>📰 BOT DE EVENTOS — CATALIZADORES & FLUJO</h1>
        <p>Aprovechamiento de Volatilidad por Eventos Macroeconómicos</p>
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
        precio_actual = float(df["Close"].iloc[-1]) if not df.empty else precio_entrada
    except Exception:
        precio_actual = precio_entrada

    pnl_usd = (precio_actual - precio_entrada) * acciones
    pnl_pct = (((precio_actual - precio_entrada) / precio_entrada) * 100.0) if precio_entrada > 0 else 0.0

    if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
        data_bitacora["ganancia_cerrada"] += pnl_usd
        hora_act = time.strftime("%H:%M:%S")
        msg = f"[{hora_act}] 📰 CORTE DE PÉRDIDA: Cierre en {ticker} a {pnl_pct:.2f}% (${pnl_usd:.2f} USD)."
        data_bitacora.setdefault("historial_alertas", []).append(msg)
        hubo_cierre_individual = True
    else:
        total_flotante += pnl_usd
        posiciones_restantes.append(pos)
        posiciones_procesadas.append(
            {
                "Activo": ticker,
                "Precio Entrada": round(precio_entrada, 2),
                "Precio Actual": round(precio_actual, 2),
                "Acciones": round(acciones, 4),
                "Resultado (USD)": round(pnl_usd, 2),
                "Resultado (%)": round(pnl_pct, 2),
            }
        )

if hubo_cierre_individual:
    data_bitacora["posiciones"] = posiciones_restantes
    guardar_bitacora_eventos(data_bitacora)
    st.rerun()

capital_base = float(data_bitacora.get("capital_inicial", 10552.58))
ganancia_cerrada = float(data_bitacora.get("ganancia_cerrada", 0.0))

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

peak_previo = float(data_bitacora.get("peak_flotante", 0.0))
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora_eventos(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

umbral_calculado = peak_actual - tolerancia_retroceso_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

# Cierre automático por Trailing Stop Global
if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
    ejecutar_cierre_jornada_eventos(nuevo_capital, origen="automatico")
    st.rerun()

# Cierre automático por Horario (17:00 hrs)
hora_actual_str = datetime.now().strftime("%H:%M")
fecha_hoy_str = datetime.now().strftime("%d/%m/%Y")
ultimo_auto = data_bitacora.get("ultimo_cierre_automatico", "")

if hora_actual_str >= "17:00" and len(posiciones_procesadas) > 0 and ultimo_auto != fecha_hoy_str:
    nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
    ejecutar_cierre_jornada_eventos(nuevo_capital, origen="automatico")
    st.success(f"⏰ [Cierre Automático 17:00] Jornada cerrada. Capital acumulado: ${nuevo_capital:,.2f} USD")
    st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base Acumulada: ${capital_base:,.2f}")
col2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Punto Alto: +{peak_actual:.2f}%")
col4.metric("Meta / Umbral Salida", f"Meta: {meta_diaria_pct:.2f}%", f"Umbral: +{umbral_salida:.2f}%")

st.markdown("---")

if st.sidebar.button("🚀 Abrir Jornada (Eventos)"):
    st.sidebar.info("Evaluando catalizadores del mercado...")
    top_ev = seleccionar_top_eventos(n=NUM_ACTIVOS_OBJETIVO)

    if len(top_ev) > 0:
        monto_por_accion = capital_base / len(top_ev)
        nuevas_pos = []
        for t in top_ev:
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
        guardar_bitacora_eventos(data_bitacora)
        st.sidebar.success(f"Posiciones abiertas: {', '.join(top_ev)}")
        st.rerun()

if st.sidebar.button("🔴 Cierre Manual de Jornada"):
    if data_bitacora.get("posiciones"):
        ganancia_del_dia = total_flotante + ganancia_cerrada
        nuevo_capital = round(capital_base + ganancia_del_dia, 2)

        ejecutar_cierre_jornada_eventos(nuevo_capital, origen="manual")
        
        st.success(f"✅ **¡Cierre Manual Exitoso!** Capital acumulado actualizado a **${nuevo_capital:,.2f} USD** como base inicial para la siguiente sesión.")
        time.sleep(1.5)
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("📰 Posiciones en Curso — Bot de Eventos")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** Esperando catalizadores de mercado.")

st.markdown("---")
st.subheader("📋 Historial de Cierres Recientes (Últimos 14 días)")

historial = data_bitacora.get("historial_rendimiento", [])
if historial:
    df_hist = pd.DataFrame(historial)
    if "Fecha" in df_hist.columns and "Capital" in df_hist.columns:
        df_hist["Fecha_limpia"] = df_hist["Fecha"].astype(str).str.split(" ").str[0]
        df_hist["Fecha_obj"] = pd.to_datetime(df_hist["Fecha_limpia"], format="%d/%m/%Y", errors="coerce")
        
        df_hist = df_hist.sort_values(by="Fecha_obj", ascending=False).drop(columns=["Fecha_obj", "Fecha"]).rename(columns={"Fecha_limpia": "Fecha"})
        
        df_hist = df_hist[["Fecha", "Capital"]]
        df_hist["Capital"] = df_hist["Capital"].apply(lambda x: f"${float(x):,.2f} USD")
        st.dataframe(df_hist.head(14), use_container_width=True, hide_index=True)
    else:
        df_hist = pd.DataFrame(historial)
        st.dataframe(df_hist.tail(14), use_container_width=True)
else:
    st.info("Aún no hay registros para mostrar la evolución.")
    st.info("Aún no hay registros para mostrar la evolución.")
