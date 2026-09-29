import json
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Terminal de Trading - Swing Robot",
    page_icon="⚡",
    layout="wide"
)

ARCHIVO_BITACORA = "bitacora_operACIONES.json" if False else "bitacora_operaciones.json"
CAPITAL_INICIAL = 10000.0

# --- FUNCIONES DE SOPORTE ---
def cargar_bitacora():
    try:
        with open(ARCHIVO_BITACORA, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_bitacora(datos):
    with open(ARCHIVO_BITACORA, "w") as f:
        json.dump(datos, f, indent=2)

def escanear_mercado_y_comprar():
    # Universo de activos para el escáner
    tickers = ["DIS", "PFE", "XOM", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
    operaciones = cargar_bitacora()
    activos_abiertos = [op["ticker"] for op in operaciones if op.get("estado") == "ABIERTA"]
    
    nuevas_compras = 0

    for ticker in tickers:
        if ticker in activos_abiertos:
            continue
        try:
            datos = yf.Ticker(ticker).history(period="1mo", interval="1h")
            if len(datos) < 50:
                continue

            precio = datos["Close"].iloc[-1]
            ema_20 = datos["Close"].ewm(span=20).mean().iloc[-1]
            
            # Criterio simplificado de oportunidad de compra
            if precio > ema_20:
                sl = precio * 0.985  # Stop Loss al -1.5%
                tp = precio * 1.03   # Take Profit al +3.0%
                
                # Riesgo del 5% sobre $10,000 = $500 USD
                riesgo_por_accion = precio - sl
                shares = int(500 / riesgo_por_accion) if riesgo_por_accion > 0 else 50

                nueva_op = {
                    "ticker": ticker,
                    "entry": float(precio),
                    "sl": float(sl),
                    "tp": float(tp),
                    "shares": shares,
                    "fecha_entrada": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "ABIERTA"
                }
                operaciones.append(nueva_op)
                nuevas_compras += 1
                if nuevas_compras >= 2: # Máximo 2 nuevas por escaneo
                    break
        except Exception:
            continue

    if nuevas_compras > 0:
        guardar_bitacora(operaciones)
    return nuevas_compras

# --- BARRA LATERAL (Escáner) ---
st.sidebar.title("⚡ Panel de Control")
st.sidebar.caption("Estrategia Swing Trading 1-3 días")

if st.sidebar.button("🔍 Escanear Mercado Ahora", use_container_width=True):
    with st.spinner("Buscando oportunidades en tiempo real..."):
        nuevas = escanear_mercado_y_comprar()
        if nuevas > 0:
            st.sidebar.success(f"¡Se ejecutaron {nuevas} nueva(s) operación(es)!")
            st.rerun()
        else:
            st.sidebar.info("No se encontraron nuevas oportunidades bajo el filtro actual.")

# --- ENCABEZADO Y RESUMEN ---
st.title("📈 Terminal de Inversión y Trading Algorítmico")

operaciones = cargar_bitacora()
df = pd.DataFrame(operaciones) if operaciones else pd.DataFrame()

df_abiertas = df[df["estado"] == "ABIERTA"].copy() if not df.empty and "estado" in df.columns else pd.DataFrame()
df_cerradas = df[df["estado"] != "ABIERTA"].copy() if not df.empty and "estado" in df.columns else pd.DataFrame()

pnl_flotante_total = 0.0
pnl_realizado_total = 0.0

if not df_cerradas.empty and "resultado_usd" in df_cerradas.columns:
    pnl_realizado_total = df_cerradas["resultado_usd"].sum()

if not df_abiertas.empty:
    precios, lucros, pcts = [], [], []
    for _, row in df_abiertas.iterrows():
        try:
            d = yf.Ticker(row["ticker"]).history(period="1d", interval="1m")
            p_act = d["Close"].iloc[-1] if not d.empty else row["entry"]
        except Exception:
            p_act = row["entry"]
        
        lucro = (p_act - row["entry"]) * row["shares"]
        pct = ((p_act - row["entry"]) / row["entry"]) * 100
        
        precios.append(p_act)
        lucros.append(lucro)
        pcts.append(pct)
        pnl_flotante_total += lucro

    df_abiertas["Precio Actual"] = precios
    df_abiertas["P&L ($)"] = lucros
    df_abiertas["P&L (%)"] = pcts

# CAPITAL Y RENDIMIENTO
capital_actual = CAPITAL_INICIAL + pnl_realizado_total + pnl_flotante_total
rendimiento_total_pct = ((capital_actual - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Capital de la Cuenta", f"${capital_actual:,.2f} USD", f"{rendimiento_total_pct:+.2f}%")
c2.metric("Posiciones Activas", len(df_abiertas))
c3.metric("Flotante Actual", f"${pnl_flotante_total:+.2f} USD")
c4.metric("Ganancia Realizada", f"${pnl_realizado_total:+.2f} USD")

st.divider()

# --- TABLA DE POSICIONES ---
st.subheader("🟢 Posiciones en Curso")
if df_abiertas.empty:
    st.info("No hay posiciones abiertas.")
else:
    vista = df_abiertas[["ticker", "entry", "Precio Actual", "sl", "tp", "shares", "P&L ($)", "P&L (%)"]].rename(
        columns={"ticker": "Activo", "entry": "Entrada", "sl": "Stop Loss", "tp": "Take Profit", "shares": "Acciones"}
    )
    st.dataframe(
        vista.style.format({
            "Entrada": "${:.2f}", "Precio Actual": "${:.2f}", 
            "Stop Loss": "${:.2f}", "Take Profit": "${:.2f}",
            "P&L ($)": "${:+.2f}", "P&L (%)": "{:+.2f}%"
        }),
        use_container_width=True
    )

    # --- GRÁFICO INTERACTIVO ---
    st.divider()
    st.subheader("📊 Análisis Técnico del Activo Seleccionado")
    
    activo_sel = st.selectbox("Selecciona un activo para ver su gráfico:", df_abiertas["ticker"].unique())
    
    if activo_sel:
        fila = df_abiertas[df_abiertas["ticker"] == activo_sel].iloc[0]
        
        # Obtener velas de Yahoo Finance
        df_hist = yf.Ticker(activo_sel).history(period="5d", interval="15m")
        
        fig = go.Figure(data=[go.Candlestick(
            x=df_hist.index,
            open=df_hist['Open'],
            high=df_hist['High'],
            low=df_hist['Low'],
            close=df_hist['Close'],
            name="Precio"
        )])
        
        # Líneas clave
        fig.add_hline(y=fila["entry"], line_dash="dash", line_color="green", annotation_text="Entrada")
        fig.add_hline(y=fila["tp"], line_dash="dash", line_color="blue", annotation_text="Take Profit")
        fig.add_hline(y=fila["sl"], line_dash="dash", line_color="red", annotation_text="Stop Loss")
        
        fig.update_layout(
            title=f"Gráfico Intradía {activo_sel} (Nivel Entrada: ${fila['entry']:.2f})",
            yaxis_title="Precio USD",
            xaxis_title="Fecha / Hora",
            template="plotly_dark",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
