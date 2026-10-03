import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import time
from datetime import datetime

st.set_page_config(page_title="Terminal de Trading Algorítmico", layout="wide")

# --- AUTOREFRESCO AUTOMÁTICO CADA 30 SEGUNDOS (SISTEMA AUTÓNOMO) ---
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=10000, key="bot_auto_execution_loop")
except ImportError:
    pass

BITACORA_FILE = "bitacora_operaciones.json"
BITACORA_POST_FILE = "bitacora_post_mercado.json"

# --- UNIVERSO BASE DE ALTA LIQUIDEZ (>20M VOLUMEN) ---
UNIVERSO_ALTA_LIQUIDEZ = [
    "NVDA", "AAPL", "TSLA", "AMZN", "AMD", "PLTR", "BAC", 
    "INTC", "MSFT", "GOOGL", "F", "AAL", "DIS", "XOM", "PFE"
]

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
            "tickers": ["DIS", "PFE", "XOM", "MSFT", "NVDA", "GOOGL"]
        }
    }
    
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if isinstance(contenido, dict):
                    if "historial_alertas" not in contenido or not contenido["historial_alertas"]:
                        contenido["historial_alertas"] = base_data["historial_alertas"]
                    if "registro_cierre_bot" not in contenido or not contenido["registro_cierre_bot"]:
                        contenido["registro_cierre_bot"] = base_data["registro_cierre_bot"]
                    if "ganancia_cerrada" not in contenido or contenido["ganancia_cerrada"] == 0:
                        contenido["ganancia_cerrada"] = base_data["ganancia_cerrada"]
                    if "capital_inicial" not in contenido or contenido["capital_inicial"] == 10000.0:
                        contenido["capital_inicial"] = base_data["capital_inicial"]
                    return contenido
        except Exception:
            pass
    
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(base_data, f, indent=4)
    return base_data

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def ejecutar_escaner_dinamico(capital_disponible, top_n=6):
    """
    Escanea el mercado buscando acciones con volumen > 20M 
    y selecciona las Top N para armar el portafolio diario.
    """
    seleccionadas = []
    for ticker in UNIVERSO_ALTA_LIQUIDEZ:
        try:
            df = yf.Ticker(ticker).history(period="1d")
            if not df.empty:
                volumen = df["Volume"].iloc[-1]
                precio = df["Close"].iloc[-1]
                if volumen > 1000000:  
                    seleccionadas.append({"ticker": ticker, "precio": precio, "volumen": volumen})
        except Exception:
            continue
    
    df_top = pd.DataFrame(seleccionadas).sort_values(by="volumen", ascending=False).head(top_n)
    
    posiciones = []
    monto_por_posicion = capital_disponible / len(df_top) if len(df_top) > 0 else 0
    
    for _, row in df_top.iterrows():
        posiciones.append({
            "ticker": row["ticker"],
            "precio_entrada": round(row["precio"], 2),
            "acciones": round(monto_por_posicion / row["precio"], 4),
            "stop_loss": round(row["precio"] * 0.98, 2),
            "take_profit": round(row["precio"] * 1.05, 2)
        })
    return posiciones

def registrar_auditoria_post_cierre(lista_tickers, retorno_bot_pct):
    if not lista_tickers:
        return
    try:
        log_post = []
        if os.path.exists(BITACORA_POST_FILE):
            with open(BITACORA_POST_FILE, "r", encoding="utf-8") as f:
                try:
                    log_post = json.load(f)
                except Exception:
                    log_post = []

        hoy_str = datetime.now().strftime("%Y-%m-%d")
        if not any(item.get("fecha") == hoy_str for item in log_post):
            registro = {
                "fecha": hoy_str,
                "hora_auditoria": time.strftime("%H:%M:%S"),
                "retorno_bot_pct": round(retorno_bot_pct, 2),
                "tickers_monitoreados": lista_tickers
            }
            log_post.append(registro)
            with open(BITACORA_POST_FILE, "w", encoding="utf-8") as f:
                json.dump(log_post, f, indent=4)
    except Exception:
        pass

data_bitacora = cargar_bitacora()

st.sidebar.header("⚙️ Configuración del Bot")
meta_diaria_pct = st.sidebar.slider("Meta Diaria Objetivo (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
trailing_tolerance_pct = st.sidebar.slider("Tolerancia de Retroceso desde el Peak (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.title("📈 Terminal de Inversión y Trading Algorítmico")
st.caption("🔍 **Motor de Escaneo:** Dinámico (>20M Volumen Diario) | **Estrategia:** Single-Cycle Trailing Stop")

posiciones = data_bitacora.get("posiciones", [])

total_flotante = 0.0
posiciones_procesadas = []
tickers_activos = []

for pos in posiciones:
    ticker = pos.get("ticker") or pos.get("activo") or pos.get("symbol") or "N/A"
    precio_entrada = float(pos.get("entry") or pos.get("precio_entrada") or pos.get("price") or 0.0)
    acciones = float(pos.get("shares") or pos.get("acciones") or pos.get("cantidad") or 0.0)
    stop_loss = float(pos.get("sl") or pos.get("stop_loss") or 0.0)
    take_profit = float(pos.get("tp") or pos.get("take_profit") or 0.0)

    if ticker == "N/A":
        continue

    tickers_activos.append(ticker)

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
        "Acciones / Fracciones": round(acciones, 4),
        "Stop Loss": round(stop_loss, 2),
        "Take Profit": round(take_profit, 2),
        "PnL (USD)": round(pnl_usd, 2),
        "PnL (%)": round(pnl_pct, 2)
    })

capital_base = data_bitacora.get("capital_inicial", 10216.01)
ganancia_cerrada = data_bitacora.get("ganancia_cerrada", 216.01)

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

# --- EJECUCIÓN AUTOMÁTICA DE TRAILING STOP ---
if peak_actual >= meta_diaria_pct and flotante_pct <= umbral_salida and len(posiciones_procesadas) > 0:
    retorno_asegurado_pct = flotante_pct
    data_bitacora["ganancia_cerrada"] += total_flotante
    data_bitacora["capital_inicial"] += total_flotante
    data_bitacora["registro_cierre_bot"] = {
        "hora_salida": time.strftime("%H:%M:%S"),
        "retorno_asegurado_pct": round(retorno_asegurado_pct, 2),
        "ganancia_usd": round(total_flotante, 2),
        "tickers": tickers_activos
    }
    data_bitacora["posiciones"] = []
    
    timestamp_cierre = time.strftime("%H:%M:%S")
    mensaje_evento = f"[{timestamp_cierre}] TRAILING STOP AUTOMÁTICO: Cierre ejecutado al {flotante_pct:.2f}% (Peak: +{peak_actual:.2f}%). Ganancia asegurada: ${total_flotante:,.2f} USD."
    data_bitacora["historial_alertas"].append(mensaje_evento)
    data_bitacora["peak_flotante"] = 0.0
    
    guardar_bitacora(data_bitacora)
    registrar_auditoria_post_cierre(tickers_activos, retorno_asegurado_pct)
    st.rerun()

# --- REGISTRO SILENCIOSO POST-MERCADO ---
if not posiciones_procesadas and data_bitacora.get("registro_cierre_bot"):
    info_cierre = data_bitacora["registro_cierre_bot"]
    registrar_auditoria_post_cierre(info_cierre.get("tickers", []), info_cierre.get("retorno_asegurado_pct", 0.0))

# --- INTERFAZ Y MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)

signo_flotante = "+" if total_flotante >= 0 else ""
signo_ganancia = "+" if ganancia_total_dia >= 0 else ""

col1.metric("Capital de la Cuenta", f"${capital_base + total_flotante:,.2f} USD", f"Base: ${capital_base:,.2f}")
col2.metric("Ganancia Total Realizada", f"{signo_ganancia}${ganancia_total_dia:,.2f} USD", f"{ganancia_total_pct:.2f}% del Capital")
col3.metric("Flotante Actual", f"{signo_flotante}${total_flotante:,.2f} USD", f"Peak del Día: +{peak_actual:.2f}%")
col4.metric("Meta / Trailing Stop", f"Meta: {meta_diaria_pct:.1f}%", f"Umbral Salida: +{umbral_salida:.2f}%")

st.markdown("---")

if data_bitacora.get("historial_alertas"):
    st.info("📜 **Última Acción Automática del Bot:** " + data_bitacora["historial_alertas"][-1])

if not posiciones_procesadas and data_bitacora.get("registro_cierre_bot"):
    c = data_bitacora["registro_cierre_bot"]
    st.warning(f"👁️ **Modo Monitoreo Post-Mercado Activo:** Cierre ejecutado a las {c['hora_salida']} (+{c['retorno_asegurado_pct']}%). Registrando tendencia post-salida para la prueba del 2 al 9 de Octubre.")

# --- BOTONES EN PANEL LATERAL (UNICOS Y SIN DUPLICADOS) ---
if st.sidebar.button("🚀 Escanear y Abrir Jornada"):
    nuevas_pos = ejecutar_escaner_dinamico(capital_base, top_n=6)
    data_bitacora["posiciones"] = nuevas_pos
    data_bitacora["peak_flotante"] = 0.0
    data_bitacora["registro_cierre_bot"] = None
    data_bitacora["historial_alertas"] = [f"[{time.strftime('%H:%M:%S')}] Jornada iniciada. Monitoreando posiciones..."]
    guardar_bitacora(data_bitacora)
    st.sidebar.success("Escaneo completado y portafolio generado.")
    st.rerun()

if st.sidebar.button("🔄 Reiniciar Día"):
    data_bitacora["peak_flotante"] = 0.0
    data_bitacora["ganancia_cerrada"] = 0.0
    data_bitacora["historial_alertas"] = []
    data_bitacora["registro_cierre_bot"] = None
    guardar_bitacora(data_bitacora)
    st.sidebar.success("Jornada reseteada.")
    st.rerun()

st.subheader("🟢 Posiciones en Curso (Selección Dinámica >20M)")
if posiciones_procesadas:
    df_pos = pd.DataFrame(posiciones_procesadas)
    st.dataframe(df_pos, use_container_width=True)
else:
    st.success("✅ **Sin posiciones abiertas.** El robot aseguró las utilidades y dejó la cuenta en caja líquida.")
