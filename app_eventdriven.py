import time
from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# Importamos el motor de sentimiento
try:
    from news_engine import seleccionar_top_eventdriven
except ImportError:
    def seleccionar_top_eventdriven(n=5):
        return []

st.set_page_config(
    page_title="App Event-Driven — Estrategia de Sentimiento & Eventos",
    page_icon="📰",
    layout="wide",
)

# Estilos CSS con Encabezado Compacto para Celular
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .event-header {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        padding: 10px 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .event-header h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    .event-header p {
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

    st_autorefresh(interval=30000, limit=10000, key="auto_eventdriven")
except ImportError:
    pass

NUM_EMPRESAS = 5
STOP_LOSS_INDIVIDUAL_PCT = -0.75

# --- INICIALIZACIÓN DE ESTADO INTERNO (SIN JSON) ---
if "capital_inicial" not in st.session_state:
    st.session_state.capital_inicial = 10372.00
if "ganancia_cerrada" not in st.session_state:
    st.session_state.ganancia_cerrada = 0.0
if "posiciones" not in st.session_state:
    st.session_state.posiciones = []
if "peak_flotante" not in st.session_state:
    st.session_state.peak_flotante = 0.0
if "historial_alertas" not in st.session_state:
    st.session_state.historial_alertas = []
if "historial_capital" not in st.session_state:
    st.session_state.historial_capital = [
        {"Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "Capital": 10372.00}
    ]

# Sidebar
st.sidebar.markdown("### 📰 **APP EVENT-DRIVEN**")
st.sidebar.markdown("*Trading Basado en Noticias y Sentimiento*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider(
    "Meta Diaria (%)", min_value=0.5, max_value=10.0, value=5.35, step=0.05
)
trailing_tolerance_pct = st.sidebar.slider(
    "Tolerancia Retroceso (%)", min_value=0.05, max_value=5.0, value=0.75, step=0.05
)

st.markdown(
    """
    <div class="event-header">
        <h1>📰 APP EVENT-DRIVEN — NOTICIAS & SENTIMIENTO</h1>
        <p>Estrategia Basada en Eventos | Stop Loss & Piso Blindado</p>
    </div>
""",
    unsafe_allow_html=True,
)

posiciones = st.session_state.posiciones
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

    if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
        st.session_state.ganancia_cerrada += pnl_usd
        hora_act = time.strftime("%H:%M:%S")
        msg = f"[{hora_act}] 📰 EVENT-DRIVEN STOP LOSS: Cierre en {ticker} a {pnl_pct:.2f}% (${pnl_usd:.2f} USD)."
        st.session_state.historial_alertas.append(msg)
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
            "Sentimiento": pos.get("score_sentimiento", "N/A"),
        })

if hubo_cierre_individual:
    st.session_state.posiciones = posiciones_restantes
    st.rerun()

capital_base = float(st.session_state.capital_inicial)
ganancia_cerrada = float(st.session_state.ganancia_cerrada)

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

peak_previo = float(st.session_state.peak_flotante)
if flotante_pct > peak_previo:
    st.session_state.peak_flotante = flotante_pct
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

umbral_calculado = peak_actual - trailing_tolerance_pct
umbral_salida = max(umbral_calculado, meta_diaria_pct)

if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    nuevo_capital = round(capital_base + total_flotante + ganancia_cerrada, 2)
    st.session_state.capital_inicial = nuevo_capital
    st.session_state.ganancia_cerrada = 0.0
    st.session_state.posiciones = []

    st.session_state.historial_capital.append({
        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Capital": nuevo_capital,
    })

    mensaje = f"[{time.strftime('%H:%M:%S')}] 🎯 EVENT-DRIVEN TRAILING STOP: Cierre ejecutado al {flotante_pct:.2f}%. Nuevo Capital: ${nuevo_capital:,.2f} USD."
    st.session_state.historial_alertas.append(mensaje)
    st.session_state.peak_flotante = 0.0
    st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base: ${capital_base:,.2f}")
col2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Peak: +{peak_actual:.2f}%")
col4.metric("Meta / Trailing (Piso)", f"Meta: {meta_diaria_pct:.2f}%", f"Umbral: +{umbral_salida:.2f}%")

st.markdown("---")

if st.session_state.historial_alertas:
    st.info("📜 **Última Alerta:** " + st.session_state.historial_alertas[-1])

if st.sidebar.button("🚀 Escanear Eventos y Abrir Posiciones"):
    st.sidebar.info("Escaneando sentimiento de noticias en tiempo real...")
    candidatas = seleccionar_top_eventdriven(n=NUM_EMPRESAS)

    if candidatas:
        monto_por_accion = capital_base / len(candidatas)
        nuevas_pos = []
        tickers_abiertos = []

        for item in candidatas:
            t = item["ticker"]
            tickers_abiertos.append(t)
            try:
                px = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
            except Exception:
                px = 100.0

            nuevas_pos.append({
                "ticker": t,
                "precio_entrada": round(px, 2),
                "acciones": round(monto_por_accion / px, 4),
                "score_sentimiento": item["score_sentimiento"],
            })

        st.session_state.posiciones = nuevas_pos
        st.session_state.peak_flotante = 0.0
        st.session_state.historial_alertas.append(
            f"[{time.strftime('%H:%M:%S')}] Jornada Event-Driven iniciada con: {', '.join(tickers_abiertos)}."
        )
        st.sidebar.success(f"Posiciones abiertas por Eventos: {', '.join(tickers_abiertos)}")
        st.rerun()
    else:
        st.sidebar.warning("No se encontraron eventos con catalizador positivo suficiente.")

if st.sidebar.button("🔴 Cierre Manual Event-Driven"):
    if st.session_state.posiciones:
        ganancia_del_dia = total_flotante + ganancia_cerrada
        nuevo_capital = round(capital_base + ganancia_del_dia, 2)

        st.session_state.capital_inicial = nuevo_capital
        st.session_state.ganancia_cerrada = 0.0
        st.session_state.posiciones = []
        st.session_state.peak_flotante = 0.0

        st.session_state.historial_capital.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Capital": nuevo_capital,
        })

        hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alerta = f"[{hora_actual}] EVENT-DRIVEN CIERRE MANUAL: Saldo consolidado en ${nuevo_capital:,.2f} USD."
        st.session_state.historial_alertas.append(alerta)

        st.sidebar.success(f"¡Jornada cerrada! Saldo actualizado a ${nuevo_capital:,.2f} USD")
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🟢 Posiciones en Curso — Event-Driven Top 5")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** Presiona 'Escanear Eventos' para evaluar catalizadores de mercado.")

st.markdown("---")
st.subheader("📈 Evolución Diaria del Capital — Event-Driven")
historial_cap = st.session_state.historial_capital
if historial_cap:
    df_historial = pd.DataFrame(historial_cap)
    st.line_chart(df_historial.set_index("Fecha")["Capital"])
    with st.expander("Ver registro detallado de capital histórico"):
        st.dataframe(df_historial, use_container_width=True)
else:
    st.info("Aún no hay registros de cierres históricos para mostrar la evolución.")
