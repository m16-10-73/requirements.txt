import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import time

st.set_page_config(page_title="Terminal de Trading Algorítmico", layout="wide")

# --- AUTOREFRESCO AUTOMÁTICO CADA 30 SEGUNDOS (SISTEMA AUTÓNOMO) ---
# Intenta usar la librería de autorefresco; si no está en requirements, no rompe el código
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="bot_auto_execution_loop")
except ImportError:
    pass

BITACORA_FILE = "bitacora_operaciones.json"

def cargar_bitacora():
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, list):
                    return {"capital_inicial": 10000.0, "posiciones": contenido, "peak_flotante": 0.0, "ganancia_cerrada": 0.0, "historial_alertas": []}
                elif isinstance(contenido, dict):
                    if "posiciones" not in contenido:
                        contenido["posiciones"] = []
                    if "capital_inicial" not in contenido:
                        contenido["capital_inicial"] = 10000.0
                    if "peak_flotante" not in contenido:
                        contenido["peak_flotante"] = 0.0
                    if "ganancia_cerrada" not in contenido:
                        contenido["ganancia_cerrada"] = 0.0
                    if "historial_alertas" not in contenido:
                        contenido["historial_alertas"] = []
                    return contenido
        except Exception:
            pass
    return {"capital_inicial": 10000.0, "posiciones": [], "peak_flotante": 0.0, "ganancia_cerrada": 0.0, "historial_alertas": []}

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

data_bitacora = cargar_bitacora()

st.sidebar.header("⚙️ Configuración del Bot")
meta_diaria_pct = st.sidebar.slider("Meta Diaria Objetivo (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia de Retroceso desde el Peak (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.title("📈 Terminal de Inversión y Trading Algorítmico")

posiciones = data_bitacora.get("posiciones", [])

total_flotante = 0.0
posiciones_procesadas = []

for pos in posiciones:
    ticker = pos.get("ticker") or pos.get("activo") or pos.get("symbol") or "N/A"
    
    precio_entrada = float(pos.get("entry") or pos.get("precio_entrada") or pos.get("price") or 0.0)
    acciones = float(pos.get("shares") or pos.get("acciones") or pos.get("cantidad") or 0.0)
    stop_loss = float(pos.get("sl") or pos.get("stop_loss") or 0.0)
    take_profit = float(pos.get("tp") or pos.get("take_profit") or 0.0)

    if ticker == "N/A":
        continue

    try:
        df = yf.Ticker(ticker).history(period="1d")
        if not df.empty:
            precio_actual = float(df["Close"].iloc[-1])
        else:
            precio_actual = precio_entrada
    except Exception:
        precio_actual = precio_entrada
        
    pnl_usd = (precio_actual - precio_entrada) * acciones if precio_entrada > 0 else 0.0
    pnl_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100 if precio_entrada > 0 else 0.0
    
    total_flotante += pnl_usd
    
    posiciones_procesadas.append({
        "Activo": ticker,
        "Precio Entrada": round(precio_entrada, 2),
        "Precio Actual": round(precio_actual, 2),
        "Acciones": int(acciones),
        "Stop Loss": round(stop_loss, 2),
        "Take Profit": round(take_profit, 2),
        "PnL (USD)": round(pnl_usd, 2),
        "PnL (%)": round(pnl_pct, 2)
    })

capital_base = data_bitacora.get("capital_inicial", 10000.0)
ganancia_cerrada = data_bitacora.get("ganancia_cerrada", 0.0)

flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
ganancia_total_dia = ganancia_cerrada + total_flotante
ganancia_total_pct = (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0

# --- LÓGICA DE REGISTRO DE HIGH-WATER MARK (PEAK) ---
peak_previo = data_bitacora.get("peak_flotante", 0.0)
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

umbral_salida = peak_actual - trailing_tolerance_pct

# --- EJECUCIÓN 100% AUTOMÁTICA EN EL SIMULADOR ---
# Si alcanzó la meta diaria y retrocedió más allá de la tolerancia, CIERRA SOLO
if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    # 1. Registrar ganancia y liquidar posiciones en la bitácora
    data_bitacora["ganancia_cerrada"] += total_flotante
    data_bitacora["capital_inicial"] += total_flotante
    data_bitacora["posiciones"] = []
    
    # Mensaje de auditoría
    timestamp_cierre = time.strftime("%H:%M:%S")
    mensaje_evento = f"[{timestamp_cierre}] TRAILING STOP AUTOMÁTICO: Cierre ejecutado al {flotante_pct:.2f}% (Peak: +{peak_actual:.2f}%). Ganancia asegurada: ${total_flotante:,.2f} USD."
    data_bitacora["historial_alertas"].append(mensaje_evento)
    data_bitacora["peak_flotante"] = 0.0
    
    guardar_bitacora(data_bitacora)
    st.rerun()

# --- INTERFAZ Y MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)

signo_flotante = "+" if total_flotante >= 0 else ""
signo_ganancia = "+" if ganancia_total_dia >= 0 else ""

col1.metric("Capital de la Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base: ${capital_base:,.2f}")
col2.metric("Ganancia Total Realizada", f"{signo_ganancia}${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"{signo_flotante}${total_flotante:,.2f} USD", f"Peak del Día: +{peak_actual:.2f}%")
col4.metric("Meta / Trailing Stop", f"Meta: {meta_diaria_pct:.1f}%", f"Umbral Salida: +{umbral_salida:.2f}%")

st.markdown("---")

# Notificaciones y registros en vivo
if data_bitacora.get("historial_alertas"):
    st.info("📜 **Última Acción Automática del Bot:** " + data_bitacora["historial_alertas"][-1])

if st.sidebar.button("🔄 Reiniciar Día / Nueva Jornada"):
    data_bitacora["peak_flotante"] = 0.0
    data_bitacora["ganancia_cerrada"] = 0.0
    data_bitacora["historial_alertas"] = []
    guardar_bitacora(data_bitacora)
    st.sidebar.success("Jornada reseteada.")
    st.rerun()

st.subheader("🟢 Posiciones en Curso")
if posiciones_procesadas:
    df_pos = pd.DataFrame(posiciones_procesadas)
    st.dataframe(df_pos, use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** El robot aseguró las utilidades y dejó la cuenta en caja líquida.")
