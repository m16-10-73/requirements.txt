import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import time

st.set_page_config(
    page_title="VALORIS — Crecimiento Patrimonial", 
    page_icon="🏛️",
    layout="wide"
)

# Estilos CSS personalizados para la identidad de marca VALORIS
st.markdown("""
    <style>
    /* Estilo del contenedor principal */
    .stApp {
        background-color: #f8f9fa;
    }
    /* Header principal de VALORIS */
    .valoris-header {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .valoris-header h1 {
        color: #f1c40f;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        margin: 0;
        letter-spacing: 1px;
    }
    .valoris-header p {
        color: #e0e0e0;
        margin-top: 5px;
        margin-bottom: 0;
        font-size: 0.95rem;
    }
    /* Estilizado de métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: bold;
        color: #1e3d59;
    }
    </style>
""", unsafe_allow_html=True)

# Autorefresco cada 30 segundos
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="auto_valoris")
except ImportError:
    pass

BITACORA_FILE = "bitacora_valoris.json"
TICKERS_FIJOS = ["DIS", "PFE", "XOM", "MSFT", "NVDA", "GOOGL"]

def cargar_bitacora():
    base_data = {
        "capital_inicial": 10216.01,
        "ganancia_cerrada": 216.01,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": [
            "[14:38:16] TRAILING STOP AUTOMÁTICO: Cierre ejecutado al 2.16% (Peak: +4.54%). Ganancia asegurada: $216.01 USD."
        ],
        "registro_cierre_bot": {
            "hora_salida": "14:38:16",
            "retorno_asegurado_pct": 2.16,
            "ganancia_usd": 216.01,
            "tickers": TICKERS_FIJOS
        }
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

data_bitacora = cargar_bitacora()

# Sidebar personalizada
st.sidebar.markdown("### 🏛️ **VALORIS**")
st.sidebar.markdown("*Gestión Patrimonial Institucional*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider("Meta Diaria (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia Retroceso (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

# Banner superior visual exclusivo para VALORIS
st.markdown("""
    <div class="valoris-header">
        <h1>🏛️ VALORIS</h1>
        <p>Estrategia Patrimonial Blue Chips | Piso Blindado & Trailing Stop Protegido</p>
    </div>
""", unsafe_allow_html=True)

posiciones = data_bitacora.get("posiciones", [])
total_flotante = 0.0
posiciones_procesadas = []

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
    pnl_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100 if precio_entrada > 0 else 0.0
    total_flotante += pnl_usd
    
    posiciones_procesadas.append({
        "Activo": ticker,
        "Precio Entrada": round(precio_entrada, 2),
        "Precio Actual": round(precio_actual, 2),
        "Acciones": round(acciones, 4),
        "PnL (USD)": round(pnl_usd, 2),
        "PnL (%)": round(pnl_pct, 2)
    })

capital_base = data_bitacora.get("capital_inicial", 10216.01)
ganancia_cerrada = data_bitacora.get("ganancia_cerrada", 216.01)

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

# --- PISO MÍNIMO GARANTIZADO ---
umbral_calculado = peak_actual - trailing_tolerance_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

# Cierre automático Trailing Stop con Piso Blindado
if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    data_bitacora["ganancia_cerrada"] += total_flotante
    data_bitacora["capital_inicial"] += total_flotante
    data_bitacora["posiciones"] = []
    mensaje = f"[{time.strftime('%H:%M:%S')}] VALORIS PROTECT: Cierre ejecutado al {flotante_pct:.2f}%. Ganancia: ${total_flotante:,.2f} USD."
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
    st.info("📜 **Última Acción VALORIS:** " + data_bitacora["historial_alertas"][-1])

if st.sidebar.button("🚀 Abrir Jornada VALORIS"):
    monto_por_accion = capital_base / len(TICKERS_FIJOS)
    nuevas_pos = []
    for t in TICKERS_FIJOS:
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
    # Limpia las alertas del día anterior para evitar falsos positivos
    data_bitacora["historial_alertas"] = [
        f"[{time.strftime('%H:%M:%S')}] Jornada VALORIS iniciada. Monitoreando mercado..."
    ]
    guardar_bitacora(data_bitacora)
    st.rerun()

if st.sidebar.button("🔴 Cierre Manual de Jornada"):
    if bitacora.get("posiciones"):
        # Calculamos el flotante actual
        ganancia_del_dia = bitacora.get("flotante_actual_usd", 0.0)
        nuevo_capital = bitacora["capital_inicial"] + ganancia_del_dia
        
        # Actualizamos la bitácora a caja líquida
        bitacora["capital_inicial"] = round(nuevo_capital, 2)
        bitacora["ganancia_cerrada"] = round(bitacora.get("ganancia_cerrada", 0.0) + ganancia_del_dia, 2)
        bitacora["posiciones"] = [] # Vacía la tabla
        bitacora["registro_cierre_bot"] = None
        
        # Guardamos en la lista de alertas
        hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alerta = f"[{hora_actual}] CIERRE MANUAL: Ganancia asegurada de ${ganancia_del_dia:.2f} USD."
        bitacora["historial_alertas"].append(alerta)
        
        guardar_bitacora(bitacora)
        st.sidebar.success("¡Utilidades aseguradas a caja líquida!")
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🟢 Posiciones en Curso — Estrategia VALORIS")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** Caja líquida bajo custodia.")
