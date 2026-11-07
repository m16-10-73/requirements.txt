import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuración de la interfaz web
st.set_page_config(page_title="Motor de Backtesting - Flota", layout="wide", page_icon="📊")

# Estilos CSS avanzados para mantener lectura compacta en móviles
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 1200px;
    }
    .main-header {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 14px 16px;
        border-radius: 10px;
        color: white;
        margin-bottom: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 0.75rem;
        margin: 3px 0 0 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Encabezado visual tipo plataforma
st.markdown(
    """
    <div class="main-header">
        <h1>📊 Motor de Backtesting e Histórico de Estrategias</h1>
        <p>Herramienta privada de simulación e inspección cuantitativa para la flota.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Panel lateral con parámetros de simulación
st.sidebar.header("⚙️ Parámetros de Simulación")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ USD)", value=10000.0, step=1000.0)

# Stop Loss (-5.0% a -0.5%)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=-5.0, max_value=-0.5, value=-0.5, step=0.1) / 100.0

# Take Profit ampliado hasta 10.0% con saltos de 1 en 1
take_profit_input = st.sidebar.slider("Meta / Take Profit (%)", min_value=1.0, max_value=10.0, value=6.0, step=1.0, format="%.1f")
take_profit_pct = take_profit_input / 100.0

# Fricción institucional estimada por volumen (0.03% por defecto o configurable)
tasa_friccion_comision = st.sidebar.slider("Fricción Comisión / Volumen (%)", min_value=0.01, max_value=0.10, value=0.03, step=0.01, format="%.2f") / 100.0

tickers_input = st.sidebar.text_input("Activos", "NVDA, AAPL, TSLA, MSFT, TXN")
tickers = [t.strip().upper() for t in tickers_input.split(",")]

# Botón principal de ejecución
ejecutar = st.button("▶️ Ejecutar Simulación Histórica", type="primary", use_container_width=True)

st.markdown("---")

if ejecutar:
    fecha_inicio = "2021-01-01"
    fecha_fin = "2026-10-22"
    
    with st.spinner("Procesando datos históricos y ejecutando reglas de riesgo..."):
        data = yf.download(tickers, start=fecha_inicio, end=fecha_fin)
        
        # -------------------------------------------------------------
        # SIMULACIÓN PRINCIPAL (Dinámica con los parámetros del usuario)
        # -------------------------------------------------------------
        capital = capital_inicial
        trades_log = []
        equity_curve = [capital_inicial]
        volumen_nocional_acumulado = 0.0
        
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
                
                if not in_position and (curr_open > prev_close):
                    in_position = True
                    entry_price = curr_open
                    position_size = (capital * 0.20) / entry_price
                    volumen_nocional_acumulado += (position_size * entry_price)
                    continue
                    
                if in_position:
                    min_return = (curr_low - entry_price) / entry_price
                    max_return = (curr_high - entry_price) / entry_price
                    
                    if min_return <= stop_loss_pct:
                        exit_price = entry_price * (1 + stop_loss_pct)
                        pnl = ((exit_price - entry_price) * position_size)
                        volumen_nocional_acumulado += (position_size * exit_price)
                        capital += pnl
                        equity_curve.append(capital)
                        trades_log.append({
                            'Fecha': date,
                            'Activo': ticker,
                            'Resultado': '🔴 STOP LOSS',
                            'PnL ($)': round(pnl, 2),
                            'Capital ($)': round(capital, 2)
                        })
                        in_position = False
                        
                    elif max_return >= take_profit_pct:
                        exit_price = entry_price * (1 + take_profit_pct)
                        pnl = ((exit_price - entry_price) * position_size)
                        volumen_nocional_acumulado += (position_size * exit_price)
                        capital += pnl
                        equity_curve.append(capital)
                        trades_log.append({
                            'Fecha': date,
                            'Activo': ticker,
                            'Resultado': '🟢 TAKE PROFIT',
                            'PnL ($)': round(pnl, 2),
                            'Capital ($)': round(capital, 2)
                        })
                        in_position = False

        # -------------------------------------------------------------
        # SIMULACIÓN BENCHMARK INDEPENDIENTE (Fija estricta al 6.0% TP / -0.5% SL)
        # -------------------------------------------------------------
        cap_bm = capital_inicial
        vol_bm = 0.0
        ops_bm = 0
        trades_bm_log = []
        
        for ticker in tickers:
            try:
                df_bm = data.xs(ticker, level=1, axis=1).dropna()
            except Exception:
                continue
                
            in_pos_bm = False
            ent_bm = 0.0
            
            for i in range(1, len(df_bm)):
                d_bm = df_bm.index[i]
                p_close = df_bm['Close'].iloc[i-1]
                c_open = df_bm['Open'].iloc[i]
                c_low = df_bm['Low'].iloc[i]
                c_high = df_bm['High'].iloc[i]
                
                if not in_pos_bm and (c_open > p_close):
                    in_pos_bm = True
                    ent_bm = c_open
                    pos_sz_bm = (cap_bm * 0.20) / ent_bm
                    vol_bm += (pos_sz_bm * ent_bm)
                    continue
                    
                if in_pos_bm:
                    min_r_bm = (c_low - ent_bm) / ent_bm
                    max_r_bm = (c_high - ent_bm) / ent_bm
                    
                    if min_r_bm <= -0.005:
                        exit_bm = ent_bm * (1 - 0.005)
                        pnl_bm = ((exit_bm - ent_bm) * pos_sz_bm)
                        vol_bm += (pos_sz_bm * exit_bm)
                        cap_bm += pnl_bm
                        ops_bm += 1
                        trades_bm_log.append({'Fecha': d_bm})
                        in_pos_bm = False
                        
                    elif max_r_bm >= 0.06:
                        exit_bm = ent_bm * (1 + 0.06)
                        pnl_bm = ((exit_bm - ent_bm) * pos_sz_bm)
                        vol_bm += (pos_sz_bm * exit_bm)
                        cap_bm += pnl_bm
                        ops_bm += 1
                        trades_bm_log.append({'Fecha': d_bm})
                        in_pos_bm = False

        comisiones_bm = vol_bm * tasa_friccion_comision
        cap_neto_bm = cap_bm - comisiones_bm
        rend_bm = ((cap_neto_bm / capital_inicial) - 1) * 100

    # Ordenar y formatear fechas del log principal
    df_trades = pd.DataFrame(trades_log)
    if not df_trades.empty:
        df_trades['Fecha'] = pd.to_datetime(df_trades['Fecha'])
        df_trades = df_trades.sort_values('Fecha').reset_index(drop=True)
        primera_fecha_real = df_trades['Fecha'].min().strftime('%d/%m/%Y')
        ultima_fecha_real = df_trades['Fecha'].max().strftime('%d/%m/%Y')
        df_trades['Fecha'] = df_trades['Fecha'].dt.strftime('%Y-%m-%d')
    else:
        primera_fecha_real = "N/A"
        ultima_fecha_real = "22/10/2026"

    # Detección automática también para el benchmark
    df_bm_log = pd.DataFrame(trades_bm_log)
    if not df_bm_log.empty:
        df_bm_log['Fecha'] = pd.to_datetime(df_bm_log['Fecha'])
        primera_fecha_bm = df_bm_log['Fecha'].min().strftime('%d/%m/%Y')
    else:
        primera_fecha_bm = primera_fecha_real

    # Cálculos estadísticos principales
    equity_series = pd.Series(equity_curve)
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    max_drawdown = drawdown.min() * 100

    num_operaciones = len(df_trades)
    capital_antes_comisiones = capital
    comisiones_totales = volumen_nocional_acumulado * tasa_friccion_comision
    capital_neto = capital_antes_comisiones - comisiones_totales
    
    indice_comisiones_pct = (comisiones_totales / capital_antes_comisiones) * 100 if capital_antes_comisiones > 0 else 0.0
    rendimiento = ((capital_neto / capital_inicial) - 1) * 100

    # 1. Recuadro superior del periodo sincronizado automáticamente con los datos reales
    st.info(f"📅 **Periodo de Simulación:** {primera_fecha_real} al {ultima_fecha_real}  |  *Take Profit:* **{take_profit_input:.1f}%**")
    
    # 2. Cuadrícula principal (2 columnas x 4 filas)
    st.markdown(f'<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 12px;"><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Capital Inicial</div><div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 2px; white-space: nowrap;">${capital_inicial:,.2f}</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Operaciones</div><div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 2px; white-space: nowrap;">{num_operaciones}</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Capital Antes de Comisiones</div><div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 2px; white-space: nowrap;">${capital_antes_comisiones:,.2f}</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Rendimiento Neto</div><div style="font-size: 0.95rem; font-weight: 700; color: #16a34a; margin-top: 2px; white-space: nowrap;">+{rendimiento:.2f}%</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Comisiones Totales</div><div style="font-size: 0.95rem; font-weight: 700; color: #dc2626; margin-top: 2px; white-space: nowrap;">${comisiones_totales:,.2f}</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Índice de Comisiones</div><div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 2px; white-space: nowrap;">{indice_comisiones_pct:.2f}% <span style="font-size: 0.65rem; color: #64748b;">(sobre capital bruto)</span></div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Capital Final (Neto)</div><div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 2px; white-space: nowrap;">${capital_neto:,.2f}</div></div><div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px;"><div style="font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Peor Baja (Max DD)</div><div style="font-size: 0.95rem; font-weight: 700; color: #dc2626; margin-top: 2px; white-space: nowrap;">{max_drawdown:.2f}%</div></div></div>', unsafe_allow_html=True)
    
    # 3. Glosa Metodológica de Comisiones
    st.markdown(
        f"📝 **Glosa Metodológica de Comisiones:** "
        f"Las *Comisiones Totales* (${comisiones_totales:,.2f} USD) se calculan aplicando una fricción institucional estándar de mercado del **{tasa_friccion_comision*100:.2f}%** sobre el **Volumen Nocional Acumulado** movilizado en las {num_operaciones} transacciones del periodo. "
        f"El *Índice de Comisiones* ({indice_comisiones_pct:.2f}%) expresa la proporción exacta que representa este costo operativo respecto al *Capital Antes de Comisiones*."
    )

    # 4. Benchmark Independiente (Sincronizado con la primera fecha real detectada)
    st.info(
        "💡 **Estrategia Base de Referencia Óptima (Benchmark Independiente al 6.0%):**\n\n"
        f"• **Configuración Histórica Fija ({primera_fecha_bm} - 22/10/2026):** Stop Loss: **-0.5%** | Take Profit: **6.0%** -> **${cap_bm:,.2f} USD** (**+{rend_bm:.2f}%** neto en **{ops_bm} operaciones** calculadas con la fricción actual)."
    )
    
    st.markdown("---")
    st.subheader("📋 Detalle de Operaciones")
    if not df_trades.empty:
        st.dataframe(df_trades, use_container_width=True)
    else:
        st.info("No se registraron operaciones bajo los parámetros actuales.")
else:
    st.info("👈 Configura tus parámetros en la barra lateral y presiona **▶️ Ejecutar Simulación Histórica** para desplegar los resultados.")
