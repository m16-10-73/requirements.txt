import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuración de la interfaz web
st.set_page_config(page_title="Motor de Backtesting - Flota", layout="wide", page_icon="📊")

st.title("📊 Motor de Backtesting e Histórico de Estrategias")
st.caption("Herramienta privada de simulación e inspección cuantitativa para la flota.")

st.markdown("---")

# Panel lateral con parámetros de simulación
st.sidebar.header("⚙️ Parámetros de Simulación")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ USD)", value=10000.0, step=1000.0)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=-5.0, max_value=-0.5, value=-2.0, step=0.1) / 100.0
take_profit_pct = st.sidebar.slider("Meta / Take Profit (%)", min_value=0.5, max_value=5.0, value=1.35, step=0.05) / 100.0

tickers_input = st.sidebar.text_input("Activos", "NVDA, AAPL, TSLA, MSFT, TXN")
tickers = [t.strip().upper() for t in tickers_input.split(",")]

# Botón principal en pantalla
if st.button("▶️ Ejecutar Simulación Histórica", type="primary"):
    with st.spinner("Procesando datos históricos y ejecutando reglas de riesgo..."):
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

    st.success("¡Simulación completada!")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Capital Inicial", f"${capital_inicial:,.2f}")
    col2.metric("Capital Final", f"${capital:,.2f}")
    rendimiento = ((capital / capital_inicial) - 1) * 100
    col3.metric("Rendimiento", f"{rendimiento:.2f}%")
    col4.metric("Operaciones", len(trades_log))
    
    st.markdown("---")
    st.subheader("📋 Detalle de Operaciones")
    if trades_log:
        st.dataframe(pd.DataFrame(trades_log), use_container_width=True)
    else:
        st.info("No se registraron operaciones bajo los parámetros actuales.")
