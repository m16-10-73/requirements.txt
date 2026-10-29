import os
import json
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Estrategia Dinámica — Momentum & Tendencia",
    page_icon="📈",
    layout="wide",
)

# Estilos CSS
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .dynamic-header {
        background: linear-gradient(135deg, #FF512F, #DD2476);
        padding: 10px 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .dynamic-header h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    .dynamic-header p {
        color: #f0f0f0;
        margin-top: 3px;
        margin-bottom: 0;
        font-size: 0.82rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: bold;
        color: #11998e;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Autorefresco cada 30 segundos
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="auto_dynamic")
except ImportError:
    pass

# Nombre exacto del archivo JSON de bitácora (sin tildes para evitar errores en la nube)
BITACORA_FILE = "bitacora_dinamica.json"

CANDIDATAS_DINAMICO = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC"]
NUM_ACTIVOS = 3
STOP_LOSS_INDIVIDUAL_PCT = -0.75

def cargar_bitacora():
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, dict):
                    contenido.setdefault("capital_inicial", 10000.0)
                    contenido.setdefault("ganancia_cerrada", 0.0)
                    contenido.setdefault("posiciones", [])
                    contenido.setdefault("peak_flotante", 0.0)
                    contenido.setdefault("historial_alertas", [])
                    contenido.setdefault("historial_rendimiento", [])
                    return contenido
        except Exception:
            pass

    # Si no existe el archivo o falla la lectura, crea la estructura inicial
    base_data = {
        "capital_inicial": 10507.24,  # Tu capital real de partida
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": [],
        "historial_rendimiento": [{"Fecha": datetime.now().strftime("%d/%m/%Y"), "Capital": 10507.24}],
    }
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(base_data, f, indent=4, ensure_ascii=False)
    return base_data

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data_bitacora = cargar_bitacora()

# Sidebar
st.sidebar.markdown("### 📈 **BOT DINÁMICO**")
st.sidebar.markdown("*Momentum & Control de Riesgo*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider("Meta Diaria (%)", min_value=0.5, max_value=10.0, value=3.0, step=0.05)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia Retroceso (%)", min_value=0.05, max_value=5.0, value=0.5, step=0.05)

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
        precio_actual = float(df["Close"].iloc[-1]) if not df.empty else precio_entrada
    except Exception:
        precio_actual = precio_entrada

    pnl_usd = (precio_actual - precio_entrada) * acciones
    pnl_pct = (((precio_actual - precio_entrada) / precio_entrada) * 100.0) if precio_entrada > 0 else 0.0

    if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
        data_bitacora["ganancia_cerrada"] += pnl_usd
        msg = f"[{time.strftime('%H:%M:%S')}] 🛡️ STOP LOSS: Cierre en {ticker} a {pnl_pct:.2f}% (${pnl_usd:.2f} USD)."
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

capital_base = float(data_bitacora.get("capital_inicial", 10000.0))
ganancia_cerrada = float(data_bitacora.get("ganancia_cerrada", 0.0))

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

peak_previo = float(data_bitacora.get("peak_flotante", 0.0))
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

umbral_calculado = peak_actual - trailing_tolerance_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    data_bitacora["capital_inicial"] = nuevo_capital
    data_bitacora["ganancia_cerrada"] = 0.0
    data_bitacora["posiciones"] = []
    
    if "historial_rendimiento" not in data_bitacora:
        data_bitacora["historial_rendimiento"] = []
    data_bitacora["historial_rendimiento"].append({"Fecha": fecha_hoy, "Capital": nuevo_capital})

    data_bitacora["peak_flotante"] = 0.0
    guardar_bitacora(data_bitacora)
    st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base Acumulada: ${capital_base:,.2f}")
col2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Peak: +{peak_actual:.2f}%")
col4.metric("Meta / Umbral", f"Meta: {meta_diaria_pct:.2f}%", f"Umbral: +{umbral_salida:.2f}%")

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
        fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

        data_bitacora["capital_inicial"] = nuevo_capital
        data_bitacora["ganancia_cerrada"] = 0.0
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0

        if "historial_rendimiento" not in data_bitacora:
            data_bitacora["historial_rendimiento"] = []
        data_bitacora["historial_rendimiento"].append({"Fecha": fecha_hoy, "Capital": nuevo_capital})

        guardar_bitacora(data_bitacora)
        st.sidebar.success(f"¡Jornada cerrada! Capital acumulado actualizado a ${nuevo_capital:,.2f} USD")
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🟢 Posiciones en Curso")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.**")

st.markdown("---")
st.subheader("📈 Evolución Histórica del Capital Cuenta")
historial = data_bitacora.get("historial_rendimiento", [])
if historial:
    df_hist = pd.DataFrame(historial)
    if "Fecha" in df_hist.columns and "Capital" in df_hist.columns:
        df_hist = df_hist.set_index("Fecha")
        st.line_chart(df_hist)
    else:
        st.dataframe(df_hist, use_container_width=True)
else:
    st.info("Aún no hay registros históricos.")
