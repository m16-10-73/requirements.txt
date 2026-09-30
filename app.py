import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os

st.set_page_config(page_title="Terminal de Trading Algorítmico", layout="wide")

BITACORA_FILE = "bitacora_operaciones.json"

def cargar_bitacora():
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, list):
                    return {"capital_inicial": 10000.0, "posiciones": contenido, "peak_flotante": 0.0}
                elif isinstance(contenido, dict):
                    if "posiciones" not in contenido:
                        contenido["posiciones"] = []
                    if "capital_inicial" not in contenido:
                        contenido["capital_inicial"] = 10000.0
                    if "peak_flotante" not in contenido:
                        contenido["peak_flotante"] = 0.0
                    return contenido
        except Exception:
            pass
    return {"capital_inicial": 10000.0, "posiciones": [], "peak_flotante": 0.0}

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

data_bitacora = cargar_bitacora()

# MOSTRAR ESTRUCTURA EXACTA DEL JSON PARA DIAGNÓSTICO
st.sidebar.header("⚙️ Configuración del Bot")
meta_diaria_pct = st.sidebar.slider("Meta Diaria Objetivo (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia de Retroceso desde el Peak (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.title("📈 Terminal de Inversión y Trading Algorítmico")

posiciones = data_bitacora.get("posiciones", [])

# MOSTRAR EL PRIMER ELEMENTO DE LA BITÁCORA EN PANTALLA
if posiciones:
    st.info("🔍 **Diagnóstico de estructura JSON:**")
    st.json(posiciones[0])

total_flotante = 0.0
posiciones_procesadas = []

for pos in posiciones:
    ticker = pos.get("activo") or pos.get("ticker") or pos.get("symbol") or "N/A"
    
    # Intento de extracción de precio de entrada leyendo todas los nombres posibles
    precio_entrada = 0.0
    for k, v in pos.items():
        if any(palabra in k.lower() for palabra in ["entrada", "compra", "entry", "buy", "price", "precio"]):
            try:
                val = float(v)
                if val > 0:
                    precio_entrada = val
                    break
            except (ValueError, TypeError):
                pass
    
    acciones = float(pos.get("acciones") or pos.get("cantidad") or pos.get("shares") or 0.0)
    stop_loss = float(pos.get("stop_loss") or pos.get("sl") or 0.0)
    take_profit = float(pos.get("take_profit") or pos.get("tp") or 0.0)

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
        "Acciones": acciones,
        "Stop Loss": round(stop_loss, 2),
        "Take Profit": round(take_profit, 2),
        "PnL (USD)": round(pnl_usd, 2),
        "PnL (%)": round(pnl_pct, 2)
    })

capital_base = data_bitacora.get("capital_inicial", 10000.0)
flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0

peak_previo = data_bitacora.get("peak_flotante", 0.0)
if flotante_pct > peak_previo:
    data_bitacora["peak_flotante"] = flotante_pct
    guardar_bitacora(data_bitacora)
    peak_actual = flotante_pct
else:
    peak_actual = peak_previo

umbral_salida = peak_actual - trailing_tolerance_pct

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital de la Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"{flotante_pct:.2f}%")
col2.metric("Posiciones Activas", len(posiciones_procesadas))
col3.metric("Flotante Actual", f"${total_flotante:,.2f} USD", f"Peak del Día: +{peak_actual:.2f}%")
col4.metric("Meta Diaria Defendida", f"{meta_diaria_pct:.1f}%", f"Umbral Salida: +{umbral_salida:.2f}%")

st.markdown("---")

if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    st.error(f"🚨 **¡ALERTA DE TRAILING STOP ACTIVADA!** La cuenta alcanzó un peak de **+{peak_actual:.2f}%** y ha retrocedido más del **{trailing_tolerance_pct}%**. Es momento de tomar utilidades.")
    if st.button("🔒 CERRAR TODAS LAS POSICIONES Y ASEGURAR GANANCIAS"):
        data_bitacora["capital_inicial"] += total_flotante
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0
        guardar_bitacora(data_bitacora)
        st.success("✅ ¡Operaciones cerradas exitosamente! Ganancias consolidadas en caja.")
        st.rerun()

elif flotante_pct >= meta_diaria_pct and len(posiciones_procesadas) > 0:
    st.success(f"🎯 **¡META DIARIA CUMPLIDA!** Estás ganando un **+{flotante_pct:.2f}%** (Meta: {meta_diaria_pct}%). Puedes cerrar la jornada o dejar correr con el Trailing Stop activado.")
    if st.button("💰 Asegurar Ganancia Diaria Ahora"):
        data_bitacora["capital_inicial"] += total_flotante
        data_bitacora["posiciones"] = []
        data_bitacora["peak_flotante"] = 0.0
        guardar_bitacora(data_bitacora)
        st.success("✅ Ganancias aseguradas.")
        st.rerun()

if st.sidebar.button("🔄 Reiniciar Peak para Nuevo Día"):
    data_bitacora["peak_flotante"] = 0.0
    guardar_bitacora(data_bitacora)
    st.sidebar.success("Peak reseteado.")
    st.rerun()

st.subheader("🟢 Posiciones en Curso")
if posiciones_procesadas:
    df_pos = pd.DataFrame(posiciones_procesadas)
    st.dataframe(df_pos, use_container_width=True)
else:
    st.info("No hay posiciones abiertas actualmente. El escáner buscará nuevas entradas.")
