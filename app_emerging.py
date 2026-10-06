import streamlit as st
import yfinance as yf
import json
import os
from datetime import datetime

# ==========================================
# CONFIGURACIÓN GENERAL Y PARÁMETROS BÁSICOS
# ==========================================
BITACORA_FILE = "bitacora_emerging.json"

# Rango de Capitalización para Empresas Emergentes
MARKET_CAP_MIN_USD = 500_000_000       # $500 Millones USD
MARKET_CAP_MAX_USD = 10_000_000_000    # $10,000 Millones USD ($10B)
VOLUMEN_MINIMO_DIARIO = 1_000_000      # 1M de acciones mínimo de liquidez

# Pool de Escaneo Emergente de Alto Crecimiento
CANDIDATAS_EMERGING = [
    "PLTR", "SOFI", "PATH", "RBLX", "U", "IONQ", "RGTI", "QUBT", "RKLB", "LUNR",
    "ASTS", "JOBY", "ACHR", "QS", "ENVX", "STEM", "RUN", "NOVA", "SEMR", "BBAI",
    "SOUND", "SOUN", "AUR", "SYM", "CFLT", "MDB", "SNOW", "NET", "S", "GTLB"
]

NUM_EMPRESAS_OBJETIVO = 5
STOP_LOSS_INDIVIDUAL_PCT = -3.5  # Umbral ajustado por volatilidad emergente (-3.5%)

# ==========================================
# MANEJO DE BITÁCORA Y ESTADO
# ==========================================
def cargar_bitacora():
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "capital_inicial": 10000.0,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "jornada_activa": False,
        "historial": []
    }

def guardar_bitacora(data):
    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ==========================================
# ALGORITMO DE SELECCIÓN Y ESCANEO
# ==========================================
def seleccionar_top_emergentes(n=5):
    resultados = []
    for ticker in CANDIDATAS_EMERGING:
        try:
            yt = yf.Ticker(ticker)
            
            # 1. Filtro de Capitalización
            mcap = yt.fast_info.get('marketCap', 0)
            if not (MARKET_CAP_MIN_USD <= mcap <= MARKET_CAP_MAX_USD):
                continue
                
            # 2. Filtro de Volumen Mínimo
            vol = yt.fast_info.get('lastVolume', 0)
            if vol < VOLUMEN_MINIMO_DIARIO:
                continue
                
            # 3. Momentum
            df = yt.history(period="2d")
            if len(df) >= 2:
                c_prev = df["Close"].iloc[-2]
                c_act = df["Close"].iloc[-1]
                var_pct = ((c_act - c_prev) / c_prev) * 100.0
                resultados.append((ticker, var_pct, c_act))
        except Exception:
            continue
            
    resultados.sort(key=lambda x: x[1], reverse=True)
    return resultados[:n]

# ==========================================
# INTERFAZ Y LÓGICA PRINCIPAL (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Emerging Growth Bot", layout="wide")
st.title("🌱 Emerging Growth Bot - High Momentum")

data = cargar_bitacora()

# Sidebar - Estado Financiero de la Cuenta
st.sidebar.header("Estado de la Cuenta")
capital_total = data["capital_inicial"] + data["ganancia_cerrada"]
st.sidebar.metric("Capital Actual (USD)", f"${capital_total:,.2f}")
st.sidebar.metric("Ganancia Realizada (USD)", f"${data['ganancia_cerrada']:,.2f}")

# Botones Tácticos de Control
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Abrir Jornada", use_container_width=True):
        if not data["jornada_activa"]:
            with st.spinner("Escaneando mercado emergente y validando volumen..."):
                seleccionadas = seleccionar_top_emergentes(NUM_EMPRESAS_OBJETIVO)
            if seleccionadas:
                monto_por_accion = capital_total / len(seleccionadas)
                posiciones = []
                for ticker, var, precio in seleccionadas:
                    posiciones.append({
                        "ticker": ticker,
                        "precio_entrada": precio,
                        "monto_invertido": monto_por_accion,
                        "variacion_inicial": var,
                        "activa": True
                    })
                data["posiciones"] = posiciones
                data["jornada_activa"] = True
                data["peak_flotante"] = 0.0
                guardar_bitacora(data)
                st.success(f"Jornada iniciada con {len(posiciones)} acciones emergentes.")
                st.rerun()
            else:
                st.warning("No se encontraron activos emergentes que cumplan los filtros de volumen y market cap.")
        else:
            st.info("La jornada ya se encuentra activa.")

with col2:
    if st.button("🔴 Cierre Manual", use_container_width=True):
        if data["jornada_activa"]:
            ganancia_jornada = 0.0
            for pos in data["posiciones"]:
                if pos.get("activa", True):
                    yt = yf.Ticker(pos["ticker"])
                    precio_actual = yt.fast_info.get('lastPrice', pos["precio_entrada"])
                    rendimiento = (precio_actual - pos["precio_entrada"]) / pos["precio_entrada"]
                    ganancia_jornada += pos["monto_invertido"] * rendimiento
                
            data["ganancia_cerrada"] += ganancia_jornada
            
            # Registrar en historial de la bitácora
            data["historial"].append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "resultado_usd": ganancia_jornada,
                "motivo": "Cierre Manual"
            })
            
            data["posiciones"] = []
            data["jornada_activa"] = False
            data["peak_flotante"] = 0.0
            guardar_bitacora(data)
            st.success(f"Jornada cerrada. Resultado: ${ganancia_jornada:,.2f} USD")
            st.rerun()
        else:
            st.info("No hay jornada activa para cerrar.")

st.divider()

# ==========================================
# MONITOREO Y EJECUCIÓN EN TIEMPO REAL
# ==========================================
if data["jornada_activa"] and data["posiciones"]:
    st.subheader("📊 Monitoreo de Portafolio en Tiempo Real")
    
    ganancia_flotante_total = 0.0
    posiciones_actualizadas = []
    
    for pos in data["posiciones"]:
        if not pos.get("activa", True):
            continue
            
        yt = yf.Ticker(pos["ticker"])
        precio_actual = yt.fast_info.get('lastPrice', pos["precio_entrada"])
        rendimiento_pct = ((precio_actual - pos["precio_entrada"]) / pos["precio_entrada"]) * 100.0
        ganancia_usd = pos["monto_invertido"] * (rendimiento_pct / 100.0)
        
        # Ejecución de Stop Loss Individual (-3.5%)
        if rendimiento_pct <= STOP_LOSS_INDIVIDUAL_PCT:
            st.error(f"⚠️ Stop Loss ejecutado para {pos['ticker']} ({rendimiento_pct:.2f}%). Posición cerrada.")
            pos["activa"] = False
            data["ganancia_cerrada"] += ganancia_usd
            data["historial"].append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ticker": pos["ticker"],
                "resultado_usd": ganancia_usd,
                "motivo": f"Stop Loss ({STOP_LOSS_INDIVIDUAL_PCT}%)"
            })
        else:
            ganancia_flotante_total += ganancia_usd
            posiciones_actualizadas.append(pos)
            
            col_t, col_p, col_r, col_u = st.columns(4)
            col_t.write(f"**{pos['ticker']}**")
            col_p.write(f"Entrada: ${pos['precio_entrada']:.2f} | Actual: ${precio_actual:.2f}")
            
            if rendimiento_pct >= 0:
                col_r.markdown(f":green[+{rendimiento_pct:.2f}%]")
                col_u.markdown(f":green[+${ganancia_usd:,.2f} USD]")
            else:
                col_r.markdown(f":red[{rendimiento_pct:.2f}%]")
                col_u.markdown(f":red[${ganancia_usd:,.2f} USD]")
                
    data["posiciones"] = posiciones_actualizadas
    
    # Gestión de Peak Flotante (Piso Blindado / Trailing Stop)
    if ganancia_flotante_total > data.get("peak_flotante", 0.0):
        data["peak_flotante"] = ganancia_flotante_total
        
    guardar_bitacora(data)
    
    st.divider()
    st.metric("Ganancia Flotante Total (USD)", f"${ganancia_flotante_total:,.2f}", delta=f"{ganancia_flotante_total:,.2f}")

else:
    st.info("Aguardando apertura de jornada...")
