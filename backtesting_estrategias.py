#!/usr/bin/env python3
"""
Sistema de Backtesting para Probar Diferentes Estrategias
Evalúa la rentabilidad de diferentes estrategias de trading
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
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0
MIN_ORDER_VALUE = 10.0

# ==================== ESTRATEGIAS ====================

def estrategia_ema_crossover(df, ema_short=9, ema_long=21):
    """Estrategia 1: EMA Crossover básico"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)

    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & \
                       (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & \
                        (df['ema_short'].shift(1) >= df['ema_long'].shift(1))

    return df, "EMA Crossover ({}/{})".format(ema_short, ema_long)

def estrategia_sma_crossover(df, sma_short=9, sma_long=21):
    """Estrategia 1b: SMA Crossover básico"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=sma_short)
    df['sma_long'] = ta.sma(df['close'], length=sma_long)

    df['buy_signal'] = (df['sma_short'] > df['sma_long']) & \
                       (df['sma_short'].shift(1) <= df['sma_long'].shift(1))
    df['sell_signal'] = (df['sma_short'] < df['sma_long']) & \
                        (df['sma_short'].shift(1) >= df['sma_long'].shift(1))

    return df, "SMA Crossover ({}/{})".format(sma_short, sma_long)

def estrategia_ema_rsi(df, ema_short=9, ema_long=21, rsi_oversold=30, rsi_overbought=70):
    """Estrategia 2: EMA Crossover + RSI (más conservadora)"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)
    df['rsi'] = ta.rsi(df['close'], length=14)

    # Compra: EMA crossover + RSI no sobrecomprado
    df['buy_signal'] = (
        (df['ema_short'] > df['ema_long']) &
        (df['ema_short'].shift(1) <= df['ema_long'].shift(1)) &
        (df['rsi'] < rsi_overbought)
    )

    # Venta: EMA crossover + RSI no sobrevendido
    df['sell_signal'] = (
        (df['ema_short'] < df['ema_long']) &
        (df['ema_short'].shift(1) >= df['ema_long'].shift(1)) &
        (df['rsi'] > rsi_oversold)
    )

    return df, "EMA + RSI ({}/{}, RSI {}/{})".format(ema_short, ema_long, rsi_oversold, rsi_overbought)

def estrategia_sma_rsi(df, sma_short=9, sma_long=21, rsi_oversold=30, rsi_overbought=70):
    """Estrategia 2b: SMA Crossover + RSI"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=sma_short)
    df['sma_long'] = ta.sma(df['close'], length=sma_long)
    df['rsi'] = ta.rsi(df['close'], length=14)

    # Compra: SMA crossover + RSI no sobrecomprado
    df['buy_signal'] = (
        (df['sma_short'] > df['sma_long']) &
        (df['sma_short'].shift(1) <= df['sma_long'].shift(1)) &
        (df['rsi'] < rsi_overbought)
    )

    # Venta: SMA crossover + RSI no sobrevendido
    df['sell_signal'] = (
        (df['sma_short'] < df['sma_long']) &
        (df['sma_short'].shift(1) >= df['sma_long'].shift(1)) &
        (df['rsi'] > rsi_oversold)
    )

    return df, "SMA + RSI ({}/{}, RSI {}/{})".format(sma_short, sma_long, rsi_oversold, rsi_overbought)

def estrategia_macd(df, fast=12, slow=26, signal=9):
    """Estrategia 3: MACD Crossover"""
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']

    # Compra: MACD cruza por encima de la señal
    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))

    # Venta: MACD cruza por debajo de la señal
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    return df, "MACD ({}/{}/{})".format(fast, slow, signal)

def estrategia_bollinger_bands(df, length=20, std=2):
    """Estrategia 4: Bollinger Bands"""
    df = df.copy()
    bb = ta.bbands(df['close'], length=length, std=std)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_middle'] = bb['BBM_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['rsi'] = ta.rsi(df['close'], length=14)

    # Compra: Precio toca banda inferior + RSI < 30
    df['buy_signal'] = (df['close'] <= df['bb_lower']) & (df['rsi'] < 30)

    # Venta: Precio toca banda superior + RSI > 70
    df['sell_signal'] = (df['close'] >= df['bb_upper']) & (df['rsi'] > 70)

    return df, "Bollinger Bands ({} std)".format(std)

def estrategia_ema_volumen(df, ema_short=9, ema_long=21, volume_threshold=1.2):
    """Estrategia 5: EMA + Confirmación de Volumen"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)
    df['volume_avg'] = df['volume'].rolling(window=20).mean()

    # Compra: EMA crossover + volumen alto
    df['buy_signal'] = (
        (df['ema_short'] > df['ema_long']) &
        (df['ema_short'].shift(1) <= df['ema_long'].shift(1)) &
        (df['volume'] > df['volume_avg'] * volume_threshold)
    )

    # Venta: EMA crossover
    df['sell_signal'] = (
        (df['ema_short'] < df['ema_long']) &
        (df['ema_short'].shift(1) >= df['ema_long'].shift(1))
    )

    return df, "EMA + Volumen ({}/{}, vol {})".format(ema_short, ema_long, volume_threshold)

def estrategia_sma_volumen(df, sma_short=9, sma_long=21, volume_threshold=1.2):
    """Estrategia 5b: SMA + Confirmación de Volumen"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=sma_short)
    df['sma_long'] = ta.sma(df['close'], length=sma_long)
    df['volume_avg'] = df['volume'].rolling(window=20).mean()

    # Compra: SMA crossover + volumen alto
    df['buy_signal'] = (
        (df['sma_short'] > df['sma_long']) &
        (df['sma_short'].shift(1) <= df['sma_long'].shift(1)) &
        (df['volume'] > df['volume_avg'] * volume_threshold)
    )

    # Venta: SMA crossover
    df['sell_signal'] = (
        (df['sma_short'] < df['sma_long']) &
        (df['sma_short'].shift(1) >= df['sma_long'].shift(1))
    )

    return df, "SMA + Volumen ({}/{}, vol {})".format(sma_short, sma_long, volume_threshold)

def estrategia_sma_triple(df, sma_fast=5, sma_medium=13, sma_slow=21):
    """Estrategia 6: Triple SMA Crossover"""
    df = df.copy()
    df['sma_fast'] = ta.sma(df['close'], length=sma_fast)
    df['sma_medium'] = ta.sma(df['close'], length=sma_medium)
    df['sma_slow'] = ta.sma(df['close'], length=sma_slow)

    # Compra: SMA rápida cruza por encima de ambas
    df['buy_signal'] = (
        (df['sma_fast'] > df['sma_medium']) &
        (df['sma_medium'] > df['sma_slow']) &
        (df['sma_fast'].shift(1) <= df['sma_medium'].shift(1))
    )

    # Venta: SMA rápida cruza por debajo de ambas
    df['sell_signal'] = (
        (df['sma_fast'] < df['sma_medium']) &
        (df['sma_medium'] < df['sma_slow']) &
        (df['sma_fast'].shift(1) >= df['sma_medium'].shift(1))
    )

    return df, "Triple SMA ({}/{}/{})".format(sma_fast, sma_medium, sma_slow)

# ==================== BACKTESTING ====================

def obtener_datos(client, symbol, days=30, timeframe="1Hour"):
    """Obtiene datos históricos"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

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
        limit=2000
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def ejecutar_backtest(df, initial_capital=100000, min_order_value=10.0):
    """Ejecuta backtest con cualquier estrategia"""
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
            'price': row['close']
        })

        # Señal de compra
        if row.get('buy_signal', False) and btc_held == 0:
            current_price = row['close']
            qty = round(min_order_value / current_price, 6)
            cost = qty * current_price

            if cash >= cost:
                cash -= cost
                btc_held = qty
                entry_price = current_price
                trades.append({
                    'timestamp': idx,
                    'type': 'BUY',
                    'price': current_price,
                    'qty': qty,
                    'cost': cost
                })

        # Señal de venta
        elif row.get('sell_signal', False) and btc_held > 0:
            current_price = row['close']
            revenue = btc_held * current_price
            cash += revenue
            profit = revenue - (btc_held * entry_price)
            profit_pct = (profit / (btc_held * entry_price)) * 100 if entry_price > 0 else 0

            trades.append({
                'timestamp': idx,
                'type': 'SELL',
                'price': current_price,
                'qty': btc_held,
                'revenue': revenue,
                'profit': profit,
                'profit_pct': profit_pct
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

def analizar_rentabilidad(results, strategy_name):
    """Analiza la rentabilidad de una estrategia"""
    trades = results['trades']
    sell_trades = [t for t in trades if t['type'] == 'SELL']

    metrics = {
        'strategy': strategy_name,
        'initial_capital': results['initial_capital'],
        'final_value': results['final_value'],
        'total_return': results['total_return'],
        'total_return_pct': results['total_return_pct'],
        'total_trades': len(trades),
        'buy_trades': len([t for t in trades if t['type'] == 'BUY']),
        'sell_trades': len(sell_trades),
    }

    if sell_trades:
        profits = [t['profit'] for t in sell_trades]
        profit_pcts = [t['profit_pct'] for t in sell_trades]

        metrics.update({
            'winning_trades': len([p for p in profits if p > 0]),
            'losing_trades': len([p for p in profits if p < 0]),
            'win_rate': (len([p for p in profits if p > 0]) / len(sell_trades)) * 100 if sell_trades else 0,
            'avg_profit': sum(profits) / len(profits),
            'avg_profit_pct': sum(profit_pcts) / len(profit_pcts),
            'max_profit': max(profits) if profits else 0,
            'max_loss': min(profits) if profits else 0,
            'total_profit': sum([p for p in profits if p > 0]),
            'total_loss': sum([p for p in profits if p < 0]),
        })
    else:
        metrics.update({
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_profit_pct': 0,
            'max_profit': 0,
            'max_loss': 0,
            'total_profit': 0,
            'total_loss': 0,
        })

    return metrics

def comparar_estrategias(strategies_results):
    """Compara múltiples estrategias"""
    print("\n" + "=" * 100)
    print("📊 COMPARACIÓN DE ESTRATEGIAS")
    print("=" * 100)

    # Ordenar por retorno
    sorted_strategies = sorted(strategies_results, key=lambda x: x['total_return_pct'], reverse=True)

    print(f"\n{'Estrategia':<30} {'Retorno %':<12} {'Retorno $':<15} {'Win Rate':<12} {'Trades':<10}")
    print("-" * 100)

    for metrics in sorted_strategies:
        retorno_color = "🟢" if metrics['total_return_pct'] > 0 else "🔴"
        print(f"{metrics['strategy']:<30} {retorno_color} {metrics['total_return_pct']:>8.2f}%  "
              f"${metrics['total_return']:>12,.2f}  {metrics['win_rate']:>8.1f}%  {metrics['total_trades']:>6}")

    # Mejor estrategia
    best = sorted_strategies[0]
    print("\n" + "=" * 100)
    print(f"🏆 MEJOR ESTRATEGIA: {best['strategy']}")
    print("=" * 100)
    print(f"💰 Retorno: {best['total_return_pct']:+.2f}% (${best['total_return']:+,.2f})")
    print(f"📊 Win Rate: {best['win_rate']:.1f}%")
    print(f"📈 Trades: {best['total_trades']} ({best['buy_trades']} compras, {best['sell_trades']} ventas)")
    print(f"💵 Ganancia promedio: ${best['avg_profit']:+,.2f}")
    if best['winning_trades'] > 0:
        print(f"✅ Trades ganadores: {best['winning_trades']}")
    if best['losing_trades'] > 0:
        print(f"❌ Trades perdedores: {best['losing_trades']}")
    print("=" * 100)

def visualizar_estrategia(df, results, strategy_name):
    """Visualiza una estrategia"""
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

        # Precio y señales
        ax1.plot(df.index, df['close'], label='Precio', linewidth=1.5, color='black')

        buy_signals = df[df.get('buy_signal', False)]
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'],
                       color='green', marker='^', s=100, label='Compra', zorder=5)

        sell_signals = df[df.get('sell_signal', False)]
        if not sell_signals.empty:
            ax1.scatter(sell_signals.index, sell_signals['close'],
                       color='red', marker='v', s=100, label='Venta', zorder=5)

        ax1.set_ylabel('Precio (USD)')
        ax1.set_title(f'{SYMBOL} - {strategy_name}', fontsize=14, fontweight='bold')
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
        filename = os.path.join('backtest_results', f"backtest_{strategy_name.replace(' ', '_').replace('/', '_')}.png")
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"📊 Gráfico guardado: {filename}")
        plt.close()

    except Exception as e:
        print(f"⚠️ Error al generar gráfico: {e}")

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    print("=" * 100)
    print("🔬 BACKTESTING DE MÚLTIPLES ESTRATEGIAS")
    print("=" * 100)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}")
    print(f"📅 Período: Últimos 30 días\n")

    # Obtener datos
    print("📥 Obteniendo datos históricos...")
    try:
        # Intentar con autenticación
        client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)
        df = obtener_datos(client, SYMBOL, days=30, timeframe="1Hour")
        print(f"✅ {len(df)} barras obtenidas\n")
    except Exception as e:
        print(f"⚠️ Error con API de datos: {e}")
        print("💡 Intentando sin autenticación (datos públicos)...")
        try:
            # Intentar sin autenticación para datos históricos
            client = CryptoHistoricalDataClient()
            df = obtener_datos(client, SYMBOL, days=30, timeframe="1Hour")
            print(f"✅ {len(df)} barras obtenidas (sin autenticación)\n")
        except Exception as e2:
            print(f"❌ No se pudieron obtener datos: {e2}")
            print("\n💡 Usando datos de ejemplo para demostración...")
            # Crear datos de ejemplo
            import numpy as np
            dates = pd.date_range(end=datetime.now(ZoneInfo("America/New_York")), periods=720, freq='H')
            base_price = 87000
            prices = base_price + np.cumsum(np.random.randn(720) * 100)
            df = pd.DataFrame({
                'open': prices * (1 + np.random.randn(720) * 0.001),
                'high': prices * (1 + abs(np.random.randn(720) * 0.002)),
                'low': prices * (1 - abs(np.random.randn(720) * 0.002)),
                'close': prices,
                'volume': np.random.randint(1000, 10000, 720)
            }, index=dates)
            print(f"✅ {len(df)} barras de ejemplo generadas\n")

    # Definir estrategias a probar (EMA y SMA)
    estrategias = [
        # EMA Strategies
        lambda d: estrategia_ema_crossover(d, 9, 21),
        lambda d: estrategia_ema_crossover(d, 5, 13),
        lambda d: estrategia_ema_crossover(d, 12, 26),
        lambda d: estrategia_ema_rsi(d, 9, 21),
        lambda d: estrategia_ema_volumen(d, 9, 21),
        # SMA Strategies
        lambda d: estrategia_sma_crossover(d, 9, 21),
        lambda d: estrategia_sma_crossover(d, 5, 13),
        lambda d: estrategia_sma_crossover(d, 12, 26),
        lambda d: estrategia_sma_rsi(d, 9, 21),
        lambda d: estrategia_sma_volumen(d, 9, 21),
        lambda d: estrategia_sma_triple(d, 5, 13, 21),
        # Other Strategies
        lambda d: estrategia_macd(d),
        lambda d: estrategia_bollinger_bands(d),
    ]

    print("🚀 Probando estrategias...\n")
    results_list = []

    for i, estrategia_func in enumerate(estrategias, 1):
        try:
            df_strategy, strategy_name = estrategia_func(df.copy())
            print(f"[{i}/{len(estrategias)}] Probando: {strategy_name}...")

            results = ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE)
            metrics = analizar_rentabilidad(results, strategy_name)
            results_list.append(metrics)

            print(f"    Retorno: {metrics['total_return_pct']:+.2f}% | "
                  f"Win Rate: {metrics['win_rate']:.1f}% | "
                  f"Trades: {metrics['total_trades']}")

            # Visualizar todas las estrategias (incluyendo SMA)
            try:
                visualizar_estrategia(df_strategy, results, strategy_name)
            except Exception as viz_error:
                print(f"    ⚠️ Error al generar gráfico: {viz_error}")

        except Exception as e:
            print(f"    ❌ Error: {e}")

    # Comparar resultados
    comparar_estrategias(results_list)

    print("\n💡 Para probar tus propias estrategias, edita el script y agrega nuevas funciones")

