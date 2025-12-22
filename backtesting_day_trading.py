#!/usr/bin/env python3
"""
Backtesting de Day Trading para BTC/USD
Timeframes cortos (5 min, 15 min) para operaciones intradía
"""

import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# ==================== CONFIGURACIÓN DAY TRADING ====================
API_KEY = "PKIYRP5K7VVT72PNKVXLYVSQZR"
SECRET_KEY = "7u9Sfc4VUaiAmPBYiSzCGSZc9bjoQGNCHgY2Q2dZuRdc"

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0
EMA_SHORT = 5   # EMA muy corta para day trading
EMA_LONG = 13   # EMA corta para day trading
QTY = 0.001

# Parámetros
DAYS_BACK = 7   # Últimos 7 días para day trading
TIMEFRAME = "5Min"  # 5 minutos

def obtener_datos(client, symbol, days=7, timeframe="5Min"):
    """Obtiene datos para day trading"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    if timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
    elif timeframe == "15Min":
        tf = TimeFrame(amount=15, unit=TimeFrameUnit.Minute)
    else:
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=tf,
        start=start_time,
        limit=2000
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def calcular_senales_day_trading(df, ema_short=5, ema_long=13):
    """Señales optimizadas para day trading"""
    df = df.copy()

    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['volume_avg'] = df['volume'].rolling(window=20).mean()

    # Señales más estrictas para day trading
    df['buy_signal'] = (
        (df['ema_short'] > df['ema_long']) &
        (df['ema_short'].shift(1) <= df['ema_long'].shift(1)) &
        (df['rsi'] < 70) &
        (df['volume'] > df['volume_avg'] * 0.8)
    )

    df['sell_signal'] = (
        (df['ema_short'] < df['ema_long']) &
        (df['ema_short'].shift(1) >= df['ema_long'].shift(1)) &
        (df['rsi'] > 30)
    )

    return df

def ejecutar_backtest(df, initial_capital=100000, qty=0.001):
    """Backtest para day trading"""
    capital = initial_capital
    cash = initial_capital
    btc_held = 0.0
    entry_price = 0.0

    trades = []
    portfolio_values = []

    for idx, row in df.iterrows():
        portfolio_value = cash + (btc_held * row['close'])
        portfolio_values.append({
            'timestamp': idx,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'btc_value': btc_held * row['close'],
            'btc_held': btc_held,
            'price': row['close']
        })

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
                    'cost': cost
                })

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
                'profit_pct': (profit / (btc_held * entry_price)) * 100
            })
            btc_held = 0.0
            entry_price = 0.0

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
    """Visualiza resultados"""
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

        # Precio y señales
        ax1.plot(df.index, df['close'], label='Precio', linewidth=1.5, color='black')
        ax1.plot(df.index, df['ema_short'], label=f'EMA {EMA_SHORT}', linewidth=1, color='blue', alpha=0.7)
        ax1.plot(df.index, df['ema_long'], label=f'EMA {EMA_LONG}', linewidth=1, color='red', alpha=0.7)

        buy_signals = df[df['buy_signal']]
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'],
                       color='green', marker='^', s=100, label='Compra', zorder=5)

        sell_signals = df[df['sell_signal']]
        if not sell_signals.empty:
            ax1.scatter(sell_signals.index, sell_signals['close'],
                       color='red', marker='v', s=100, label='Venta', zorder=5)

        ax1.set_ylabel('Precio (USD)')
        ax1.set_title(f'{SYMBOL} - Day Trading Backtest ({TIMEFRAME})', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Portfolio
        portfolio_df = pd.DataFrame(results['portfolio_values'])
        ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                label='Valor Portfolio', linewidth=2, color='green')
        ax2.axhline(y=results['initial_capital'], color='gray',
                   linestyle='--', label='Capital Inicial', alpha=0.7)

        ax2.set_ylabel('Valor Portfolio (USD)')
        ax2.set_xlabel('Fecha')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.xticks(rotation=45)
        plt.tight_layout()
        # Guardar en carpeta backtest_results
        import os
        os.makedirs('backtest_results', exist_ok=True)
        filename = os.path.join('backtest_results', 'backtest_day_trading.png')
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"📊 Gráfico guardado: {filename}")
        plt.show()

    except Exception as e:
        print(f"⚠️ Error al generar gráfico: {e}")

def mostrar_resultados(results):
    """Muestra resultados"""
    print("=" * 70)
    print("📊 RESULTADOS DAY TRADING BACKTEST")
    print("=" * 70)

    print(f"\n💰 Capital Inicial: ${results['initial_capital']:,.2f}")
    print(f"💰 Valor Final: ${results['final_value']:,.2f}")
    print(f"📈 Retorno Total: ${results['total_return']:+,.2f}")
    print(f"📊 Retorno %: {results['total_return_pct']:+.2f}%")

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
            winning = [p for p in profits if p > 0]
            losing = [p for p in profits if p < 0]

            print(f"\n💵 Estadísticas:")
            print(f"   Ganancia promedio: ${avg_profit:+,.2f}")
            print(f"   Trades ganadores: {len(winning)} ({len(winning)/len(sell_trades)*100:.1f}%)")
            print(f"   Trades perdedores: {len(losing)} ({len(losing)/len(sell_trades)*100:.1f}%)")

            if winning:
                print(f"   Mayor ganancia: ${max(winning):+,.2f}")
            if losing:
                print(f"   Mayor pérdida: ${min(losing):+,.2f}")

    print("=" * 70)

if __name__ == "__main__":
    print("=" * 70)
    print("🔬 DAY TRADING BACKTEST - BTC/USD")
    print("=" * 70)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"📅 Período: Últimos {DAYS_BACK} días")
    print(f"⏱️ Timeframe: {TIMEFRAME}")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")

    print("📥 Obteniendo datos...")
    client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)
    df = obtener_datos(client, SYMBOL, DAYS_BACK, TIMEFRAME)
    print(f"✅ {len(df)} barras obtenidas\n")

    print("🔍 Calculando señales...")
    df = calcular_senales_day_trading(df, EMA_SHORT, EMA_LONG)
    print("✅ Señales calculadas\n")

    print("🚀 Ejecutando backtest...")
    results = ejecutar_backtest(df, INITIAL_CAPITAL, QTY)
    print("✅ Backtest completado\n")

    mostrar_resultados(results)

    print("\n📊 Generando visualización...")
    visualizar_backtest(df, results)

