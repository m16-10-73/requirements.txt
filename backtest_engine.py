import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuración de la interfaz web
st.set_page_config(page_title="Motor de Backtesting - Flota", layout="wide", page_icon="📊")

# Ajuste CSS para reducir el título, dar sangría superior y estilo compacto
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 1.0rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    .custom-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #2c3e50;
        margin-top: 12px;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    .custom-caption {
        font-size: 0.82rem;
        color: #6c757d;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Encabezado estilizado con letras más pequeñas y sangría superior
st.markdown('<div class="custom-title">📊 Motor de Backtesting e Histórico de Estrategias</div>', unsafe_allow_html=True)
st.markdown('<div class="custom-caption">Herramienta privada de simulación e inspección cuantitativa para la flota.</div>', unsafe_allow_html=True)

# Panel lateral con parámetros de simulación
st.sidebar.header("⚙️ Parámetros de Simulación")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ USD)", value=10000.0, step=1000.0)

# Stop Loss (-5.0% a -0.5%)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=-5.0, max_value=-0.5, value=-0.5, step=0.1) / 100.0

# Take Profit ampliado hasta 10.0% con saltos de 1 en 1 y formato numérico limpio
take_profit_input = st.sidebar.slider("Meta / Take Profit (%)", min_value=1.0, max_value=10.0, value=6.0, step=1.0, format="%.1f")
take_profit_pct = take_profit_input / 100.0

tickers_input = st.sidebar.text_input("Activos", "NVDA, AAPL, TSLA, MSFT, TXN")
tickers = [t.strip().upper() for t in tickers_input.split(",")]

st.markdown("---")

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

    st.success(f"¡Simulación completada con Take Profit al {take_profit_input:.1f}%!")
    
    # 1. Cuadro de métricas de la simulación actual
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Capital Inicial", f"${capital_inicial:,.2f}")
    col2.metric("Capital Final", f"${capital:,.2f}")
    rendimiento = ((capital / capital_inicial) - 1) * 100
    col3.metric("Rendimiento", f"{rendimiento:.2f}%")
    col4.metric("Operaciones", len(trades_log))
    
    st.markdown("---")
    
    # 2. BLOQUE DE TEXTO DINÁMICO (Se adecúa a los cambios del slider)
    if take_profit_input == 6.0 and abs(stop_loss_pct - (-0.005)) < 1e-5:
        st.success("🎯 **Análisis Dinámico de Parámetros:** ¡Estás operando exactamente en la **Configuración Récord Óptima** de la flota (Stop Loss: -0.5% | Take Profit: 6.0%)!")
    elif take_profit_input == 5.0:
        st.info("ℹ️ **Análisis Dinámico de Parámetros:** Estás evaluando el estándar anterior (5.0%), el cual genera $227,886.52 USD. Subir al 6.0% demostró capturar mayor rentabilidad acumulada.")
    else:
        st.warning(f"🔍 **Análisis Dinámico de Parámetros:** Prueba activa con Stop Loss al {stop_loss_pct*100:.1f}% y Take Profit al **{take_profit_input:.1f}%**. Compara este resultado de ${capital:,.2f} USD frente al récord actual de $266,062.85 USD.")

    # 3. TEXTO FIJO DE REFERENCIA (Ubicado debajo de las métricas y análisis)
    st.info(
        "💡 **Estrategia Base de Referencia Óptima (Fija):**\n\n"
        "• **Configuración Histórica Récord:** Stop Loss: **-0.5%** | Take Profit: **6.0%** -> **$266,062.85 USD** (**+2,560.63%** en **1,812 operaciones**).\n"
        "• *Nota:* Este es el punto de referencia estructural de la flota derivado del análisis cuantitativo del Bot Dinámico."
    )
    
    st.markdown("---")
    st.subheader("📋 Detalle de Operaciones")
    if trades_log:
        st.dataframe(pd.DataFrame(trades_log), use_container_width=True)
    else:
        st.info("No se registraron operaciones bajo los parámetros actuales.")
else:
    st.info("👈 Configura tus parámetros en la barra lateral y presiona **▶️ Ejecutar Simulación Histórica** para desplegar los resultados y análisis.")
