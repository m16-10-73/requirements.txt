import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import time
from datetime import datetime

st.set_page_config(
    page_title="App Valoris — Estrategia Conservadora Top 5", 
    page_icon="🛡️",
    layout="wide"
)

# Estilos CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .valoris-header {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        padding: 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .valoris-header h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        margin: 0;
    }
    .valoris-header p {
        color: #e0e0e0;
        margin-top: 5px;
        margin-bottom: 0;
        font-size: 0.95rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: bold;
        color: #1e3c72;
    }
    </style>
""", unsafe_allow_html=True)

# Autorefresco cada 30 segundos
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="auto_valoris")
except ImportError:
    pass

BITACORA_FILE = "bitacora_conservadora.json"

# Universo Fijo de 25 acciones consolidadas y de alta liquidez
UNIVERSO_VALORIS = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX", "INTC",
    "JPM", "BAC", "V", "MA", "DIS", "PFE", "XOM", "CVX", "KO", "PEP",
    "COST", "WMT", "NKE", "BA", "UNH"
]

NUM_EMPRESAS_VALORIS = 5
STOP_LOSS_INDIVIDUAL_PCT = -2.0  # Corte individual por seguridad al -2.0%

def cargar_bitacora():
    base_data = {
        "capital_inicial": 10000.0,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": []
    }
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, dict):
                    return contenido
        except Exception:
            pass
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(base_data, f, indent=4)
    return base_data

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def seleccionar_top_valoris(n=5):
    """Evalúa la variación del universo de 25 empresas conservadoras y toma el Top N."""
    rendimientos = []
    for ticker in UNIVERSO_VALORIS:
        try:
            df = yf.Ticker(ticker).history(period="2d")
            if len(df) >= 2:
                c_prev = df["Close"].iloc[-2]
                c_act = df["Close"].iloc[-1]
                var_pct = ((c_act - c_prev) / c_prev) * 100.0
            else:
                var_pct = 0.0
        except Exception:
            var_pct = 0.0
        rendimientos.append((ticker, var_pct))
    
    rendimientos.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in rendimientos[:n]]

data_bitacora = cargar_bitacora()

# Sidebar
st.sidebar.markdown("### 🛡️ **APP VALORIS**")
st.sidebar.markdown("*Estrategia Conservadora Top 5 & Piso Blindado*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider("Meta Diaria (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia Retroceso (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.markdown("""
    <div class="valoris-header">
        <h1>🛡️ APP VALORIS — TOP 5 CONSERVADORA</h1>
        <p>Estrategia Sobresegura | Stop Loss Individual (-2.0%) & Piso Blindado</p>
    </div>
""", unsafe_allow_html=True)

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
    pnl_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100.0 if precio_entrada > 0 else 0.0
    
    # --- STOP LOSS INDIVIDUAL (-2.0%) ---
    if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
        data_bitacora["ganancia_cerrada"] += pnl_usd
        data_bitacora["capital_inicial"] += pnl_usd
        
        hora_act = time.strftime('%H:%M:%S')
        msg = f"[{hora_act}] 🛡️ VALORIS STOP LOSS: Cierre en {ticker} a {pnl_pct:.2f}% (${pnl_usd:.2f} USD). Posición liquidada a caja."
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
            "PnL (%)": round(pnl_pct, 2)
        })

if hubo_cierre_individual:
    data_bitacora["posiciones"] = posiciones_restantes
    guardar_bitacora(data_bitacora)
    st.rerun()

capital_base = data_bitacora.get("capital_inicial", 10000.0)
ganancia_cerrada = data_bitacora.get("ganancia_cerrada", 0.0)

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

peak_previo = data_bitacora.get("peak_flotante", 0.0)
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

# --- PISO BLINDADO Y TRAILING STOP GLOBAL ---
umbral_calculado = peak_actual - trailing_tolerance_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    data_bitacora["ganancia_cerrada"] += total_flotante
    data_bitacora["capital_inicial"] += total_flotante
    data_bitacora["posiciones"] = []
    mensaje = f"[{time.strftime('%H:%M:%S')}] 🎯 VALORIS TRAILING STOP: Cierre ejecutado al {flotante_pct:.2f}%. Ganancia: ${total_flotante:,.2f} USD."
    data_bitacora["historial_alertas"].append(mensaje)
    data_bitacora["peak_flotante"] = 0.0
    guardar_bitacora(data_bitacora)
    st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base: ${capital_base:,.2f}")
col2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Peak: +{peak_actual:.2f}%")
col4.metric("Meta / Trailing (Piso)", f"Meta: {meta_diaria_pct:.1f}%", f"Umbral: +{umbral_salida:.2f}%")

st.markdown("---")

if data_bitacora.get("historial_alertas"):
    st.info("📜 **Última Alerta:** " + data_bitacora["historial_alertas"][-1])

# --- CONTROLES DE LA BARRA LATERAL ---

if st.sidebar.button("🚀 Abrir Jornada Valoris (Top 5)"):
    st.sidebar.info("Analizando el universo conservador de 25 empresas...")
    top_5 = seleccionar_top_valoris(n=NUM_EMPRESAS_VALORIS)
    monto_por_accion = capital_base / len(top_5)
    nuevas_pos = []
    for t in top_5:
        try:
            px = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
        except Exception:
            px = 100.0
        nuevas_pos.append({
            "ticker": t,
            "precio_entrada": round(px, 2),
            "acciones": round(monto_por_accion / px, 4)
        })
    data_bitacora["posiciones"] = nuevas_pos
    data_bitacora["peak_flotante"] = 0.0
    data_bitacora["historial_alertas"].append(
        f"[{time.strftime('%H:%M:%S')}] Jornada Valoris iniciada con Top 5: {', '.join(top_5)} ($2,000 USD/posición)."
    )
    guardar_bitacora(data_bitacora)
    st.sidebar.success(f"Posiciones abiertas: {', '.join(top_5)}")
    st.rerun()

if st.sidebar.button("🔴 Cierre Manual Valoris"):
    if data_bitacora.get("posiciones"):
        ganancia_del_dia = total_flotante
        nuevo_capital = data_bitacora["capital_inicial"] + ganancia_del_dia
        
        data_bitacora["capital_inicial"] = round(nuevo_capital, 2)
        data_bitacora["ganancia_cerrada"] = round(data_bitacora.get("ganancia_cerrada", 0.0) + ganancia_del_dia, 2)
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0
        
        hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alerta = f"[{hora_actual}] VALORIS CIERRE MANUAL: Utilidades aseguradas de ${ganancia_del_dia:.2f} USD."
        data_bitacora["historial_alertas"].append(alerta)
        
        guardar_bitacora(data_bitacora)
        st.sidebar.success("¡Utilidades aseguradas a caja líquida!")
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🟢 Posiciones en Curso — Valoris Top 5")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** Esperando inicio de jornada o liquidadas a caja.")
