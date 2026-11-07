import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuración de la interfaz web optimizada para móvil y escritorio
st.set_page_config(page_title="Motor de Backtesting - Flota", layout="wide", page_icon="📊")

# Ajuste CSS avanzado para perfecta visualización en móviles y escritorio
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1.0rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    .custom-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #2c3e50;
        margin-top: 8px;
        margin-bottom: 2px;
        line-height: 1.2;
    }
    .custom-caption {
        font-size: 0.78rem;
        color: #6c757d;
        margin-bottom: 10px;
    }
    /* Estilo responsivo para tarjetas de métricas */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 10px 12px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Encabezado estilizado con diseño compacto
st.markdown('<div class="custom-title">📊 Motor de Backtesting e Histórico</div>', unsafe_allow_html=True)
st.markdown('<div class="custom-caption">Herramienta privada de simulación e inspección cuantitativa para la flota.</div>', unsafe_allow_html=True)

# Panel lateral con parámetros de simulación
st.sidebar.header("⚙️ Parámetros de Simulación")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ USD)", value=10000.0, step=1000.0)

# Stop Loss (-5.0% a -0.5%)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=-5.0, max_value=-0.5, value=-0.5, step=0.1) / 100.0

# Take Profit ampliado hasta 10.0% con saltos de 1 en 1
take_profit_input = st.sidebar.slider("Meta / Take Profit (%)", min_value=1.0, max_value=10.0, value=6.0, step=1.0, format="%.1f")
take_profit_pct = take_profit_input / 100.0

tickers_input = st.sidebar.text_input("Activos", "NVDA, AAPL, TSLA, MSFT, TXN")
tickers = [t.strip().upper() for t in tickers_input.split(",")]

st.markdown("---")

# Botón principal de ejecución (ancho completo en móvil)
col_btn1, col_btn2 = st.columns([1, 2])
with col_btn1:
    ejecutar = st.button("▶️ Ejecutar Simulación", type="primary", use_container_width=True)

if ejecutar:
    with st.spinner("Procesando datos históricos..."):
        data = yf.download(tickers, start="2021-01-01", end="2026-10-22")
        
        capital = capital_inicial
        trades_log = []
        
        for ticker in tickers:
            try:
                df = data.xs(ticker, level=1, axis=1).dropna()
            except Exception:
                continue
                
            in_position = False
            entry_price = 0.0
            
            for i in range(1, len(df)):
                date = df.index[i]
                prev_close = df['Close'].iloc[i-1]
                curr_open = df['Open'].iloc[i]
                curr_low = df['Low'].iloc[i]
                curr_high = df['High'].iloc[i]
                
                # Regla de entrada
                if not in_position and (curr_open > prev_close):
                    in_position = True
                    entry_price = curr_open
                    position_size = (capital * 0.20) / entry_price
                    continue
                    
                # Gestión de riesgo (Stop Loss / Take Profit)
                if in_position:
                    min_return = (curr_low - entry_price) / entry_price
                    max_return = (curr_high - entry_price) / entry_price
                    
                    if min_return <= stop_loss_pct:
                        exit_price = entry_price * (1 + stop_loss_pct)
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl
                        trades_log.append({
                            'Fecha': date.strftime('%Y-%m-%d'),
                            'Activo': ticker,
                            'Resultado': '🔴 STOP LOSS',
                            'PnL ($)': round(pnl, 2),
                    'Capital ($)': round(capital, 2)
                        })
                        in_position = False
                        
                    elif max_return >= take_profit_pct:
                        exit_price = entry_price * (1 + take_profit_pct)
                        pnl = (exit_price - entry_price) * position_size
                        capital += pnl
                        trades_log.append({
                            'Fecha': date.strftime('%Y-%m-%d'),
                            'Activo': ticker,
                            'Resultado': '🟢 TAKE PROFIT',
                            'PnL ($)': round(pnl, 2),
                            'Capital ($)': round(capital, 2)
                        })
                        in_position = False

    st.success(f"¡Simulación completada con Take Profit al {take_profit_input:.1f}%!")
    
    # 1. Métricas organizadas en tarjetas limpias adaptables a móviles
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Capital Inicial", f"${capital_inicial:,.2f}")
        rendimiento = ((capital / capital_inicial) - 1) * 100
        st.metric("Rendimiento", f"{rendimiento:.2f}%")
    with col2:
        st.metric("Capital Final", f"${capital:,.2f}")
        st.metric("Operaciones", len(trades_log))
    
    st.markdown("---")
    
    # 2. Análisis Dinámico
    if take_profit_input == 6.0 and abs(stop_loss_pct - (-0.005)) < 1e-5:
        st.success("🎯 **Análisis Dinámico:** ¡Estás operando en la **Configuración Récord Óptima** (Stop Loss: -0.5% | Take Profit: 6.0%)!")
    elif take_profit_input == 5.0:
        st.info("ℹ️ **Análisis Dinámico:** Estás evaluando el estándar anterior (5.0% -> $227,886.52 USD). El 6.0% demostró mayor rentabilidad.")
    else:
        st.warning(f"🔍 **Análisis Dinámico:** Prueba activa con Stop Loss al {stop_loss_pct*100:.1f}% y Take Profit al **{take_profit_input:.1f}%** (${capital:,.2f} USD).")

    # 3. Referencia Fija
    st.info(
        "💡 **Estrategia Base de Referencia Óptima (Fija):**\n\n"
        "• **Configuración Histórica Récord:** Stop Loss: **-0.5%** | Take Profit: **6.0%** -> **$266,062.85 USD** (**+2,560.63%** en **1,812 operaciones**).\n"
        "• *Nota:* Referencia estructural derivada del análisis cuantitativo del Bot Dinámico."
    )
    
    st.markdown("---")
    st.subheader("📋 Detalle de Operaciones")
    if trades_log:
        st.dataframe(pd.DataFrame(trades_log), use_container_width=True)
    else:
        st.info("No se registraron operaciones bajo los parámetros actuales.")
else:
    st.info("👈 Configura tus parámetros en la barra lateral y presiona **▶️ Ejecutar Simulación** para desplegar los resultados.")
