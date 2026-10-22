import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 1. PARÁMETROS DE PRUEBA (CONFIGURACIÓN)
# ==========================================
TICKERS = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'TXN']
START_DATE = '2024-01-01'
END_DATE = '2026-10-22'
INITIAL_CAPITAL = 10000.0
STOP_LOSS_PCT = -0.02  # -2.0% estricto
TAKE_PROFIT_PCT = 0.0135  # Meta Diaria 1.35%

def run_backtest():
    print(f"--- INICIANDO BACKTEST OFFLINE ({START_DATE} a {END_DATE}) ---")
    
    # Descargar datos históricos
    data = yf.download(TICKERS, start=START_DATE, end=END_DATE)
    
    capital = INITIAL_CAPITAL
    trades_log = []
    
    # Simulación iterativa por activo
    for ticker in TICKERS:
        df = data.xs(ticker, level=1, axis=1).dropna()
        in_position = False
        entry_price = 0.0
        
        for i in range(1, len(df)):
            date = df.index[i]
            prev_close = df['Close'].iloc[i-1]
            curr_open = df['Open'].iloc[i]
            curr_low = df['Low'].iloc[i]
            curr_high = df['High'].iloc[i]
            curr_close = df['Close'].iloc[i]
            
            # Condición de Entrada Simplificada (Momentum positivo del día previo)
            if not in_position and (curr_open > prev_close):
                in_position = True
                entry_price = curr_open
                position_size = (capital * 0.20) / entry_price # 20% del capital por activo
                continue
                
            # Monitoreo de Salida (Stop Loss vs Take Profit) dentro de la jornada
            if in_position:
                min_return = (curr_low - entry_price) / entry_price
                max_return = (curr_high - entry_price) / entry_price
                
                # 1. Chequeo de Stop Loss Individual
                if min_return <= STOP_LOSS_PCT:
                    exit_price = entry_price * (1 + STOP_LOSS_PCT)
                    pnl = (exit_price - entry_price) * position_size
                    capital += pnl
                    trades_log.append({
                        'Fecha': date.strftime('%Y-%m-%d'),
                        'Activo': ticker,
                        'Tipo': 'STOP LOSS',
                        'Precio Entrada': round(entry_price, 2),
                        'Precio Salida': round(exit_price, 2),
                        'PnL ($)': round(pnl, 2),
                        'Capital Acumulado': round(capital, 2)
                    })
                    in_position = False
                    
                # 2. Chequeo de Meta Diaria / Take Profit
                elif max_return >= TAKE_PROFIT_PCT:
                    exit_price = entry_price * (1 + TAKE_PROFIT_PCT)
                    pnl = (exit_price - entry_price) * position_size
                    capital += pnl
                    trades_log.append({
                        'Fecha': date.strftime('%Y-%m-%d'),
                        'Activo': ticker,
                        'Tipo': 'TAKE PROFIT',
                        'Precio Entrada': round(entry_price, 2),
                        'Precio Salida': round(exit_price, 2),
                        'PnL ($)': round(pnl, 2),
                        'Capital Acumulado': round(capital, 2)
                    })
                    in_position = False

    # ==========================================
    # 2. RESUMEN Y MÉTRICAS INSTITUCIONALES
    # ==========================================
    df_trades = pd.DataFrame(trades_log)
    win_trades = df_trades[df_trades['PnL ($)'] > 0]
    loss_trades = df_trades[df_trades['PnL ($)'] < 0]
    
    win_rate = (len(win_trades) / len(df_trades)) * 100 if len(df_trades) > 0 else 0
    total_pnl = capital - INITIAL_CAPITAL
    
    print("\n================ RESUMEN DE RESULTADOS ================")
    print(f"Capital Inicial:        ${INITIAL_CAPITAL:,.2f} USD")
    print(f"Capital Final:          ${capital:,.2f} USD")
    print(f"Rendimiento Total:      {((capital/INITIAL_CAPITAL)-1)*100:.2f}%")
    print(f"Total Operaciones:      {len(df_trades)}")
    print(f"Operaciones Ganadoras:  {len(win_trades)} ({win_rate:.1f}%)")
    print(f"Operaciones en Pérdida: {len(loss_trades)}")
    print("=======================================================\n")
    
    return df_trades

if __name__ == "__main__":
    log_operaciones = run_backtest()
    # Guardar bitácora aislada en CSV
    log_operaciones.to_csv("reporte_backtest_privado.csv", index=False)
    print(" Reporte guardado independientemente como 'reporte_backtest_privado.csv'")
