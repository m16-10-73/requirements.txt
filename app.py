import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Terminal de Trading Algorítmico", layout="wide")

BITACORA_FILE = "bitacora_operaciones.json"

# --- FUNCIONES DE MEMORIA Y PERSISTENCIA ---
def cargar_bitacora():
    if os.path.exists(BITACORA_FILE):
        with open(BITACORA_FILE, "r") as f:
            return json.load(f)
    return {"capital_inicial": 10000.0, "posiciones": [], "peak_flotante": 0.0}

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data_bitacora = cargar_bitacora()

# Configuración en la Barra Lateral (Sidebar)
st.sidebar.header("⚙️ Configuración del Bot")
meta_diaria_pct = st.sidebar.slider("Meta Diaria Objetivo (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia de Retroceso desde el Peak (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.title("📈 Terminal de Inversión y Trading Algorítmico")

# --- OBTENCIÓN DE PRECIOS EN TIEMPO REAL ---
posiciones = data_bitacora.get("posiciones", [])
total_flotante = 0.0
posiciones_procesadas = []

for pos in posiciones:
    ticker = pos["activo"]
    precio_entrada = pos["entrada"]
    acciones = pos["acciones"]
    
    # Obtener precio actual
    df = yf.Ticker(ticker).history(period="1d")
    if not df.empty:
        precio_actual = df["Close"].iloc[-1]
    else:
        precio_actual = precio_entrada
        
    pnl_usd = (precio_actual - precio_entrada) * acciones
    pnl_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100
    
    total_flotante += pnl_usd
    
    pos_copy = pos.copy()
    pos_copy["precio_actual"] = round(precio_actual, 2)
    pos_copy["pnl_usd"] = round(pnl_usd, 2)
    pos_copy["pnl_pct"] = round(pnl_pct, 2)
    posiciones_procesadas.append(pos_copy)

# --- LÓGICA DE CONTROL DE PEAKS Y TRAILING STOP GLOBAL ---
capital_base = data_bitacora.get("capital_inicial", 10000.0)
flotante_pct = (total_flotante / capital_base) * 100

# Actualizar el pico más alto registrado en la sesión
peak_previo = data_bitacora.get("peak_flotante", 0.0)
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

# Calcular el umbral de disparo del Trailing Stop
umbral_salida = peak_actual - trailing_tolerance_pct

# --- TARJETAS DE MÉTRICAS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital de la Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"{flotante_pct:.2f}%")
col2.metric("Posiciones Activas", len(posiciones_procesadas))
col3.metric("Flotante Actual", f"${total_flotante:,.2f} USD", f"Peak del Día: +{peak_actual:.2f}%")
col4.metric("Meta Diaria Defendida", f"{meta_diaria_pct:.1f}%", f"Umbral Salida: +{umbral_salida:.2f}%")

st.markdown("---")

# --- ALERTAS INTELIGENTES DE EJECUCIÓN ---
if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones) > 0:
    st.error(f"🚨 **¡ALERTA DE TRAILING STOP ACTIVADA!** La cuenta alcanzó un peak de **+{peak_actual:.2f}%** y ha retrocedido más del **{trailing_tolerance_pct}%**. Es momento de tomar utilidades.")
    if st.button("🔒 CERRAR TODAS LAS POSICIONES Y ASEGURAR GANANCIAS"):
        # Lógica para liquidar y actualizar bitácora
        data_bitacora["capital_inicial"] += total_flotante
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0
        guardar_bitacora(data_bitacora)
        st.success("✅ ¡Operaciones cerradas exitosamente! Ganancias consolidadas en caja.")
        st.rerun()

elif flotante_pct >= meta_diaria_pct:
    st.success(f"🎯 **¡META DIARIA CUMPLIDA!** Estás ganando un **+{flotante_pct:.2f}%** (Meta: {meta_diaria_pct}%). Puedes cerrar la jornada o dejar correr con el Trailing Stop activado.")
    if st.button("💰 Asegurar Ganancia Diaria Ahora"):
        data_bitacora["capital_inicial"] += total_flotante
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0
        guardar_bitacora(data_bitacora)
        st.success("✅ Ganancias aseguradas.")
        st.rerun()

# Botón manual de reinicio de Peak al inicio del día
if st.sidebar.button("🔄 Reiniciar Peak para Nuevo Día"):
    data_bitacora["peak_flotante"] = 0.0
    guardar_bitacora(data_bitacora)
    st.sidebar.success("Peak reseteado.")
    st.rerun()

# --- TABLA DE POSICIONES EN CURSO ---
st.subheader("🟢 Posiciones en Curso")
if posiciones_procesadas:
    df_pos = pd.DataFrame(posiciones_procesadas)
    st.dataframe(df_pos[["activo", "entrada", "precio_actual", "stop_loss", "take_profit", "acciones", "pnl_usd", "pnl_pct"]], use_container_width=True)
else:
    st.info("No hay posiciones abiertas actualmente. El escáner buscará nuevas entradas.")