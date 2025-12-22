#!/usr/bin/env python3
"""
Backtesting de Estrategia EMA Crossover para BTC/USD
Simula operaciones históricas y muestra evolución del portfolio
"""

import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# ==================== CONFIGURACIÓN ====================
API_KEY = "PKIYRP5K7VVT72PNKVXLYVSQZR"
SECRET_KEY = "7u9Sfc4VUaiAmPBYiSzCGSZc9bjoQGNCHgY2Q2dZuRdc"

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0  # Capital inicial
EMA_SHORT = 9
EMA_LONG = 21
QTY = 0.001  # Cantidad por operación

# Parámetros de backtesting
DAYS_BACK = 30  # Días de datos históricos
TIMEFRAME = "1Hour"  # 1Hour, 5Min, 15Min

# ==================== FUNCIONES ====================

def obtener_datos_historicos(client, symbol, days=30, timeframe="1Hour"):
    """Obtiene datos históricos para backtesting"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    # Convertir timeframe string a TimeFrame
    if timeframe == "1Hour":
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
    elif timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
    elif timeframe == "15Min":
        tf = TimeFrame(amount=15, unit=TimeFrameUnit.Minute)
    else:
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=tf,
        start=start_time,
        limit=1000
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def calcular_senales(df, ema_short=9, ema_long=21):
    """Calcula señales de compra/venta"""
    df = df.copy()

    # Calcular EMAs
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)

    # Señales
    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & \
                       (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & \
                        (df['ema_short'].shift(1) >= df['ema_long'].shift(1))

    return df

def ejecutar_backtest(df, initial_capital=100000, qty=0.001):
    """Ejecuta el backtest"""
    capital = initial_capital
    cash = initial_capital
    btc_held = 0.0
    entry_price = 0.0

    # Registro de operaciones
    trades = []
    portfolio_values = []

    for idx, row in df.iterrows():
        # Calcular valor del portfolio en este momento
        portfolio_value = cash + (btc_held * row['close'])
        portfolio_values.append({
            'timestamp': idx,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'btc_value': btc_held * row['close'],
            'btc_held': btc_held,
            'price': row['close']
        })

        # Señal de compra
        if row['buy_signal'] and btc_held == 0:
            cost = qty * row['close']
            if cash >= cost:
                cash -= cost
                btc_held = qty
                entry_price = row['close']
                trades.append({
                    'timestamp': idx,
                    'type': 'BUY',
                    'price': row['close'],
                    'qty': qty,
                    'cost': cost,
                    'cash_after': cash,
                    'portfolio_value': portfolio_value
                })

        # Señal de venta
        elif row['sell_signal'] and btc_held > 0:
            revenue = btc_held * row['close']
            cash += revenue
            profit = revenue - (btc_held * entry_price)
            trades.append({
                'timestamp': idx,
                'type': 'SELL',
                'price': row['close'],
                'qty': btc_held,
                'revenue': revenue,
                'profit': profit,
                'profit_pct': (profit / (btc_held * entry_price)) * 100,
                'cash_after': cash,
                'portfolio_value': portfolio_value
            })
            btc_held = 0.0
            entry_price = 0.0

    # Valor final (incluyendo BTC si aún está en posición)
    final_value = cash + (btc_held * df.iloc[-1]['close'])

    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': final_value - initial_capital,
        'total_return_pct': ((final_value - initial_capital) / initial_capital) * 100,
        'trades': trades,
        'portfolio_values': portfolio_values,
        'final_btc_held': btc_held
    }

def visualizar_backtest(df, results):
    """Visualiza los resultados del backtest"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

        # Gráfico 1: Precio y señales
        ax1.plot(df.index, df['close'], label='Precio BTC/USD', linewidth=2, color='black')
        ax1.plot(df.index, df['ema_short'], label=f'EMA {EMA_SHORT}', linewidth=1.5, color='blue', alpha=0.7)
        ax1.plot(df.index, df['ema_long'], label=f'EMA {EMA_LONG}', linewidth=1.5, color='red', alpha=0.7)

        # Señales de compra
        buy_signals = df[df['buy_signal']]
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'],
                       color='green', marker='^', s=200, label='Compra', zorder=5)

        # Señales de venta
        sell_signals = df[df['sell_signal']]
        if not sell_signals.empty:
            ax1.scatter(sell_signals.index, sell_signals['close'],
                       color='red', marker='v', s=200, label='Venta', zorder=5)

        ax1.set_ylabel('Precio (USD)', fontsize=12)
        ax1.set_title(f'{SYMBOL} - Backtesting EMA Crossover Strategy', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Gráfico 2: Evolución del Portfolio
        portfolio_df = pd.DataFrame(results['portfolio_values'])
        ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                label='Valor del Portfolio', linewidth=2, color='green')
        ax2.axhline(y=results['initial_capital'], color='gray',
                   linestyle='--', label='Capital Inicial', alpha=0.7)
        ax2.fill_between(portfolio_df['timestamp'],
                         results['initial_capital'],
                         portfolio_df['portfolio_value'],
                         where=(portfolio_df['portfolio_value'] >= results['initial_capital']),
                         alpha=0.3, color='green', label='Ganancia')
        ax2.fill_between(portfolio_df['timestamp'],
                         results['initial_capital'],
                         portfolio_df['portfolio_value'],
                         where=(portfolio_df['portfolio_value'] < results['initial_capital']),
                         alpha=0.3, color='red', label='Pérdida')

        ax2.set_ylabel('Valor del Portfolio (USD)', fontsize=12)
        ax2.set_xlabel('Fecha', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Formatear fechas
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Guardar gráfico en carpeta backtest_results
        import os
        os.makedirs('backtest_results', exist_ok=True)
        filename = os.path.join('backtest_results', 'backtest_resultado.png')
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráfico guardado: {filename}")
        plt.show()

    except ImportError:
        print("⚠️ matplotlib no disponible para visualización")
    except Exception as e:
        print(f"⚠️ Error al generar gráfico: {e}")

def mostrar_resultados(results):
    """Muestra los resultados del backtest"""
    print("=" * 70)
    print("📊 RESULTADOS DEL BACKTEST")
    print("=" * 70)

    print(f"\n💰 Capital Inicial: ${results['initial_capital']:,.2f}")
    print(f"💰 Valor Final: ${results['final_value']:,.2f}")
    print(f"📈 Retorno Total: ${results['total_return']:+,.2f}")
    print(f"📊 Retorno %: {results['total_return_pct']:+.2f}%")

    # Estadísticas de trades
    trades = results['trades']
    if trades:
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']

        print(f"\n📋 Operaciones:")
        print(f"   Compras: {len(buy_trades)}")
        print(f"   Ventas: {len(sell_trades)}")
        print(f"   Total: {len(trades)}")

        if sell_trades:
            profits = [t['profit'] for t in sell_trades]
            avg_profit = sum(profits) / len(profits)
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]

            print(f"\n💵 Estadísticas de Trades:")
            print(f"   Ganancia promedio: ${avg_profit:+,.2f}")
            print(f"   Trades ganadores: {len(winning_trades)} ({len(winning_trades)/len(sell_trades)*100:.1f}%)")
            print(f"   Trades perdedores: {len(losing_trades)} ({len(losing_trades)/len(sell_trades)*100:.1f}%)")

            if winning_trades:
                print(f"   Mayor ganancia: ${max(winning_trades):+,.2f}")
            if losing_trades:
                print(f"   Mayor pérdida: ${min(losing_trades):+,.2f}")
    else:
        print("\n⚠️ No se ejecutaron operaciones en este período")

    if results['final_btc_held'] > 0:
        print(f"\n⚠️ Posición abierta al final: {results['final_btc_held']} BTC")

    print("=" * 70)

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🔬 BACKTESTING - Estrategia EMA Crossover")
    print("=" * 70)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"📅 Período: Últimos {DAYS_BACK} días")
    print(f"⏱️ Timeframe: {TIMEFRAME}")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")

    # Obtener datos
    print("📥 Obteniendo datos históricos...")
    client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)
    df = obtener_datos_historicos(client, SYMBOL, DAYS_BACK, TIMEFRAME)
    print(f"✅ {len(df)} barras obtenidas\n")

    # Calcular señales
    print("🔍 Calculando señales...")
    df = calcular_senales(df, EMA_SHORT, EMA_LONG)
    print("✅ Señales calculadas\n")

    # Ejecutar backtest
    print("🚀 Ejecutando backtest...")
    results = ejecutar_backtest(df, INITIAL_CAPITAL, QTY)
    print("✅ Backtest completado\n")

    # Mostrar resultados
    mostrar_resultados(results)

    # Visualizar
    print("\n📊 Generando visualización...")
    visualizar_backtest(df, results)

    print("\n💡 Para probar diferentes parámetros, edita el script")

