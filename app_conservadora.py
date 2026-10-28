from datetime import datetime
import json
import os
import time
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Estrategia Valoris — Dividendos & Value",
    page_icon="🛡️",
    layout="wide",
)

# --- CLASE BITÁCORA DINÁMICA INDEPENDIENTE PARA VALORIS ---
class BitacoraDinamica:
    def __init__(self, nombre_archivo, capital_inicial_default):
        self.archivo = nombre_archivo
        self.capital_default = capital_inicial_default
        self.estado = self.cargar_estado()

    def cargar_estado(self):
        if os.path.exists(self.archivo):
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "capital_inicial": self.capital_default,
            "ganancia_cerrada": 0.0,
            "posiciones": [],
            "peak_flotante": 0.0,
            "historial_rendimiento": [
                {
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Capital": self.capital_default,
                }
            ],
        }

    def actualizar_y_guardar(self, capital, ganancia, posiciones, peak, rendimiento):
        self.estado = {
            "capital_inicial": capital,
            "ganancia_cerrada": ganancia,
            "posiciones": posiciones,
            "peak_flotante": peak,
            "historial_rendimiento": rendimiento,
        }
        try:
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump(self.estado, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error al guardar la bitácora: {e}")

    def obtener(self, clave):
        return self.estado.get(clave, None)

# Instanciación exclusiva para Valoris
bitacora = BitacoraDinamica("bitacora_valoris.json", 10402.48)

# Estilos CSS
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .valoris-header {
        background: linear-gradient(135deg, #134E5E, #71B280);
        padding: 10px 15px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .valoris-header h1 {
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    .valoris-header p {
        color: #f0f0f0;
        margin-top: 3px;
        margin-bottom: 0;
        font-size: 0.82rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: bold;
        color: #134E5E;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Autorefresco cada 30 segundos
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="auto_valoris")
except ImportError:
    pass

MARKET_CAP_MINIMO_USD = 15_000_000_000

CANDIDATAS_VALORIS = [
    "JNJ", "PG", "KO", "PEP", "MRK", "ABBV", "PFE", "IBM", "CVX", "XOM",
    "VZ", "T", "MMM", "WMT", "MCD", "CSCO", "AMGN", "LOW", "UNH"
]

NUM_EMPRESAS_OBJETIVO = 4
STOP_LOSS_INDIVIDUAL_PCT = -0.75

# --- INICIALIZACIÓN DESDE LA BITÁCORA DINÁMICA ---
if "capital_inicial" not in st.session_state:
    st.session_state.capital_inicial = bitacora.obtener("capital_inicial")
if "ganancia_cerrada" not in st.session_state:
    st.session_state.ganancia_cerrada = bitacora.obtener("ganancia_cerrada")
if "posiciones" not in st.session_state:
    st.session_state.posiciones = bitacora.obtener("posiciones")
if "peak_flotante" not in st.session_state:
    st.session_state.peak_flotante = bitacora.obtener("peak_flotante")
if "historial_rendimiento" not in st.session_state:
    st.session_state.historial_rendimiento = bitacora.obtener("historial_rendimiento")

def seleccionar_top_valoris(n=4):
    resultados = []
    for ticker in CANDIDATAS_VALORIS:
        try:
            yt = yf.Ticker(ticker)
            mcap = yt.fast_info.get("marketCap", 0)
            if mcap < MARKET_CAP_MINIMO_USD:
                continue

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

# Sidebar
st.sidebar.markdown("### 🛡️ **BOT VALORIS**")
st.sidebar.markdown("*Estrategia de Dividendos & Valor Defensivo*")
st.sidebar.markdown("---")

meta_diaria_pct = st.sidebar.slider(
    "Meta Diaria (%)", min_value=0.3, max_value=8.0, value=3.50, step=0.05
)
trailing_tolerance_pct = st.sidebar.slider(
    "Tolerancia Retroceso (%)", min_value=0.05, max_value=5.0, value=0.60, step=0.05
)

st.markdown(
    """
    <div class="valoris-header">
        <h1>🛡️ BOT VALORIS — DIVIDENDOS & VALUE</h1>
        <p>Estabilidad, Activos Defensivos & Control de Riesgo</p>
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
    pnl_pct = (((precio_actual - precio_entrada) / precio_entrada) * 100.0) if precio_entrada > 0 else 0.0

    if pnl_pct <= STOP_LOSS_INDIVIDUAL_PCT:
        st.session_state.ganancia_cerrada += pnl_usd
        hora_act = time.strftime("%H:%M:%S")
        msg = f"[{hora_act}] 🛡️ STOP LOSS INDIVIDUAL: Cierre en {ticker} a {pnl_pct:.2f}% (${pnl_usd:.2f} USD). Posición liquidada a caja."
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
                "PnL (USD)": round(pnl_usd, 2),
                "PnL (%)": round(pnl_pct, 2),
            }
        )

if hubo_cierre_individual:
    st.session_state.posiciones = posiciones_restantes
    bitacora.actualizar_y_guardar(
        st.session_state.capital_inicial,
        st.session_state.ganancia_cerrada,
        st.session_state.posiciones,
        st.session_state.peak_flotante,
        st.session_state.historial_rendimiento
    )
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
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    st.session_state.capital_inicial = nuevo_capital
    st.session_state.ganancia_cerrada = 0.0
    st.session_state.posiciones = []
    st.session_state.peak_flotante = 0.0

    st.session_state.historial_rendimiento.append(
        {"Fecha": fecha_hoy, "Capital": nuevo_capital}
    )

    bitacora.actualizar_y_guardar(
        st.session_state.capital_inicial,
        st.session_state.ganancia_cerrada,
        st.session_state.posiciones,
        st.session_state.peak_flotante,
        st.session_state.historial_rendimiento
    )
    st.rerun()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base Acumulada: ${capital_base:,.2f}")
col2.metric("Ganancia Realizada", f"+${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"+${total_flotante:,.2f} USD", f"Peak: +{peak_actual:.2f}%")
col4.metric("Meta / Trailing (Piso)", f"Meta: {meta_diaria_pct:.2f}%", f"Umbral: +{umbral_salida:.2f}%")

st.markdown("---")

if st.sidebar.button("🚀 Abrir Jornada (Valoris)"):
    st.sidebar.info("Seleccionando activos defensivos...")
    top_val = seleccionar_top_valoris(n=NUM_EMPRESAS_OBJETIVO)

    if len(top_val) > 0:
        monto_por_accion = capital_base / len(top_val)
        nuevas_pos = []
        for t in top_val:
            try:
                px = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
            except Exception:
                px = 100.0
            nuevas_pos.append({
                "ticker": t,
                "precio_entrada": round(px, 2),
                "acciones": round(monto_por_accion / px, 4),
            })
        st.session_state.posiciones = nuevas_pos
        st.session_state.peak_flotante = 0.0
        bitacora.actualizar_y_guardar(
            st.session_state.capital_inicial,
            st.session_state.ganancia_cerrada,
            st.session_state.posiciones,
            st.session_state.peak_flotante,
            st.session_state.historial_rendimiento
        )
        st.sidebar.success(f"Posiciones abiertas: {', '.join(top_val)}")
        st.rerun()

if st.sidebar.button("🔴 Cierre Manual de Jornada"):
    if st.session_state.posiciones:
        ganancia_del_dia = total_flotante + ganancia_cerrada
        nuevo_capital = round(capital_base + ganancia_del_dia, 2)
        fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

        st.session_state.capital_inicial = nuevo_capital
        st.session_state.ganancia_cerrada = 0.0
        st.session_state.posiciones = []
        st.session_state.peak_flotante = 0.0

        st.session_state.historial_rendimiento.append(
            {"Fecha": fecha_hoy, "Capital": nuevo_capital}
        )

        bitacora.actualizar_y_guardar(
            st.session_state.capital_inicial,
            st.session_state.ganancia_cerrada,
            st.session_state.posiciones,
            st.session_state.peak_flotante,
            st.session_state.historial_rendimiento
        )
        st.sidebar.success(f"¡Jornada cerrada! Saldo base acumulado actualizado a ${nuevo_capital:,.2f} USD")
        st.rerun()
    else:
        st.sidebar.warning("No hay posiciones abiertas para cerrar.")

st.subheader("🛡️ Posiciones en Curso — Valoris & Dividendos")
if posiciones_procesadas:
    st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** Esperando inicio de jornada o liquidadas a caja.")

st.markdown("---")
st.subheader("📈 Evolución Histórica del Capital Cuenta")
historial = st.session_state.historial_rendimiento
if historial:
    df_hist = pd.DataFrame(historial)
    if "Fecha" in df_hist.columns and "Capital" in df_hist.columns:
        df_hist = df_hist.set_index("Fecha")
        st.line_chart(df_hist)
    else:
        st.dataframe(df_hist, use_container_width=True)
else:
    st.info("Aún no hay registros para mostrar la evolución.")
