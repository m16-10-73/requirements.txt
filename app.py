import os
impoimport os
import json
import time
from datetime import datetime
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Estrategia Dinámica — Momentum & Tendencia",
    page_icon="📈",
    layout="wide",
)

# --- BITÁCORA DINÁMICA LOCAL ---
ARCHIVO_BITACORA = "bitacora_dinamica.json"
CAPITAL_BASE_DEFECTO = 10507.24

def cargar_o_crear_bitacora():
    if os.path.exists(ARCHIVO_BITACORA):
        try:
            with open(ARCHIVO_BITACORA, "r", encoding="utf-8") as f:
                datos = json.load(f)
                if "capital_inicial" in datos and datos["capital_inicial"] > 0:
                    return datos
        except Exception:
            pass
    return {
        "capital_inicial": CAPITAL_BASE_DEFECTO,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_rendimiento": [
            {
                "Fecha": datetime.now().strftime("%d/%m/%Y"),
                "Capital": CAPITAL_BASE_DEFECTO
            }
        ],
    }

def guardar_bitacora(capital, ganancia, posiciones, peak, rendimiento):
    estado = {
        "capital_inicial": capital,
        "ganancia_cerrada": ganancia,
        "posiciones": posiciones,
        "peak_flotante": peak,
        "historial_rendimiento": rendimiento,
    }
    try:
        with open(ARCHIVO_BITACORA, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error al guardar la bitácora: {e}")

# Carga inicial segura
estado_guardado = cargar_o_crear_bitacora()

if "capital_inicial" not in st.session_state:
    st.session_state.capital_inicial = estado_guardado["capital_inicial"]
if "ganancia_cerrada" not in st.session_state:
    st.session_state.ganancia_cerrada = estado_guardado["ganancia_cerrada"]
if "posiciones" not in st.session_state:
    st.session_state.posiciones = estado_guardado["posiciones"]
if "peak_flotante" not in st.session_state:
    st.session_state.peak_flotante = estado_guardado["peak_flotante"]
if "historial_rendimiento" not in st.session_state:
    st.session_state.historial_rendimiento = estado_guardado["historial_rendimiento"]

st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }
    .dinamico-header {
        background: linear-gradient(135deg, #1f4068, #162447);
        padding: 10px 15px;
        border-radius: 10px;
        color: white;
        margin-bottom: 15px;
    }
    .dinamico-header h1 { color: white; font-size: 1.25rem; margin: 0; }
    .dinamico-header p { color: #dcdcdc; font-size: 0.82rem; margin: 0; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: bold; color: #1f4068; }
    </style>
""",
    unsafe_allow_html=True,
)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="auto_dinamico")
except ImportError:
    pass

CANDIDATAS_DINAMICO = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC"]
NUM_ACTIVOS = 3
STOP_LOSS = -0.80

meta_diaria = st.sidebar.slider("Meta Diaria (%)", 0.3, 8.0, 3.0, 0.05, key="slider_meta_dinamico")
tolerancia = st.sidebar.slider("Tolerancia Retroceso (%)", 0.05, 5.0, 0.5, 0.05, key="slider_tol_dinamico")

st.markdown("""
    <div class="dinamico-header">
        <h1>📈 BOT DINÁMICO — MOMENTUM & TENDENCIA</h1>
        <p>Seguimiento de Activos Líquidos & Control de Riesgo</p>
    </div>
""", unsafe_allow_html=True)

posiciones = st.session_state.posiciones
total_flotante = 0.0
pos_procesadas = []
pos_restantes = []
cierre_individual = False

for pos in posiciones:
    ticker = pos.get("ticker")
    p_entrada = float(pos.get("precio_entrada", 0.0))
    acciones = float(pos.get("acciones", 0.0))
    try:
        df = yf.Ticker(ticker).history(period="1d")
        p_actual = float(df["Close"].iloc[-1]) if not df.empty else p_entrada
    except Exception:
        p_actual = p_entrada

    pnl_usd = (p_actual - p_entrada) * acciones
    pnl_pct = (((p_actual - p_entrada) / p_entrada) * 100.0) if p_entrada > 0 else 0.0

    if pnl_pct <= STOP_LOSS:
        st.session_state.ganancia_cerrada += pnl_usd
        cierre_individual = True
    else:
        total_flotante += pnl_usd
        pos_restantes.append(pos)
        pos_procesadas.append({
            "Activo": ticker, "Precio Entrada": round(p_entrada, 2),
            "Precio Actual": round(p_actual, 2), "Acciones": round(acciones, 4),
            "PnL (USD)": round(pnl_usd, 2), "PnL (%)": round(pnl_pct, 2)
        })

if cierre_individual:
    st.session_state.posiciones = pos_restantes
    guardar_bitacora(
        st.session_state.capital_inicial, st.session_state.ganancia_cerrada,
        st.session_state.posiciones, st.session_state.peak_flotante,
        st.session_state.historial_rendimiento
    )
    st.rerun()

capital_base = float(st.session_state.capital_inicial)
ganancia_cerrada = float(st.session_state.ganancia_cerrada)
flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

peak = max(float(st.session_state.peak_flotante), flotante_pct)
st.session_state.peak_flotante = peak
umbral_salida = max(peak - tolerancia, meta_diaria)

if peak >= meta_diaria and flotante_pct <= umbral_salida and len(pos_procesadas) > 0:
    nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
    st.session_state.capital_inicial = nuevo_capital
    st.session_state.ganancia_cerrada = 0.0
    st.session_state.posiciones = []
    st.session_state.peak_flotante = 0.0
    st.session_state.historial_rendimiento.append({"Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "Capital": nuevo_capital})
    guardar_bitacora(nuevo_capital, 0.0, [], 0.0, st.session_state.historial_rendimiento)
    st.rerun()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base: ${capital_base:,.2f}")
c2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}%")
c3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Peak: +{peak:.2f}%")
c4.metric("Meta / Umbral", f"Meta: {meta_diaria}%", f"Umbral: +{umbral_salida:.2f}%")

st.markdown("---")

if st.sidebar.button("🚀 Abrir Jornada", key="btn_abrir_dinamico"):
    seleccionados = CANDIDATAS_DINAMICO[:NUM_ACTIVOS]
    monto_part = capital_base / len(seleccionados)
    nuevas_pos = []
    for t in seleccionados:
        try:
            px = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
        except Exception:
            px = 100.0
        nuevas_pos.append({"ticker": t, "precio_entrada": round(px, 2), "acciones": round(monto_part / px, 4)})
    st.session_state.posiciones = nuevas_pos
    st.session_state.peak_flotante = 0.0
    guardar_bitacora(capital_base, ganancia_cerrada, nuevas_pos, 0.0, st.session_state.historial_rendimiento)
    st.rerun()

if st.sidebar.button("🔴 Cierre Manual", key="btn_cerrar_dinamico"):
    if st.session_state.posiciones:
        nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
        st.session_state.capital_inicial = nuevo_capital
        st.session_state.ganancia_cerrada = 0.0
        st.session_state.posiciones = []
        st.session_state.peak_flotante = 0.0
        st.session_state.historial_rendimiento.append({"Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "Capital": nuevo_capital})
        guardar_bitacora(nuevo_capital, 0.0, [], 0.0, st.session_state.historial_rendimiento)
        st.rerun()

st.subheader("Posiciones en Curso")
if pos_procesadas:
    st.dataframe(pd.DataFrame(pos_procesadas), use_container_width=True)
else:
    st.success("Sin posiciones abiertas.")

st.markdown("---")
st.subheader("Evolución del Capital")
hist = st.session_state.historial_rendimiento
if hist:
    st.line_chart(pd.DataFrame(hist).set_index("Fecha"))
