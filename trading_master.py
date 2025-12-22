#!/usr/bin/env python3
"""
Script Maestro de Trading - Todo en uno
Combina backtesting y ejecución real de estrategias
"""

import os
import sys
import time
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

# ==================== CONFIGURACIÓN ====================
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"
PAPER = True

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0
MIN_ORDER_VALUE = 10.0

# ==================== ESTRATEGIAS ====================

def estrategia_ema_crossover(df, short=9, long=21):
    """EMA Crossover"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=short)
    df['ema_long'] = ta.ema(df['close'], length=long)
    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & (df['ema_short'].shift(1) >= df['ema_long'].shift(1))
    return df, f"EMA ({short}/{long})"

def estrategia_sma_crossover(df, short=9, long=21):
    """SMA Crossover"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=short)
    df['sma_long'] = ta.sma(df['close'], length=long)
    df['buy_signal'] = (df['sma_short'] > df['sma_long']) & (df['sma_short'].shift(1) <= df['sma_long'].shift(1))
    df['sell_signal'] = (df['sma_short'] < df['sma_long']) & (df['sma_short'].shift(1) >= df['sma_long'].shift(1))
    return df, f"SMA ({short}/{long})"

def estrategia_macd(df):
    """MACD"""
    df = df.copy()
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['buy_signal'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
    return df, "MACD (12/26/9)"

def estrategia_sma_triple(df):
    """Triple SMA"""
    df = df.copy()
    df['sma_fast'] = ta.sma(df['close'], length=5)
    df['sma_medium'] = ta.sma(df['close'], length=13)
    df['sma_slow'] = ta.sma(df['close'], length=21)
    df['buy_signal'] = (df['sma_fast'] > df['sma_medium']) & (df['sma_medium'] > df['sma_slow']) & (df['sma_fast'].shift(1) <= df['sma_medium'].shift(1))
    df['sell_signal'] = (df['sma_fast'] < df['sma_medium']) & (df['sma_medium'] < df['sma_slow']) & (df['sma_fast'].shift(1) >= df['sma_medium'].shift(1))
    return df, "Triple SMA (5/13/21)"

# Diccionario de todas las estrategias disponibles
ESTRATEGIAS = {
    '1': lambda d: estrategia_ema_crossover(d, 9, 21),
    '2': lambda d: estrategia_ema_crossover(d, 5, 13),
    '3': lambda d: estrategia_sma_crossover(d, 9, 21),
    '4': lambda d: estrategia_sma_crossover(d, 5, 13),
    '5': lambda d: estrategia_macd(d),
    '6': lambda d: estrategia_sma_triple(d),
    'all': 'all'  # Todas las estrategias
}

# ==================== FUNCIONES AUXILIARES ====================

def obtener_datos(client, symbol, days=30, timeframe="1Hour"):
    """Obtiene datos históricos"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    if timeframe == "1Hour":
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        # Calcular límite necesario: días * 24 horas * margen de seguridad
        expected_bars = days * 24
        limit = min(10000, max(2000, int(expected_bars * 1.2)))  # Máximo 10,000, mínimo 2000, con 20% margen
    elif timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
        expected_bars = days * 24 * 12  # 12 barras de 5min por hora
        limit = min(10000, max(2000, int(expected_bars * 1.2)))
    else:
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        expected_bars = days * 24
        limit = min(10000, max(2000, int(expected_bars * 1.2)))

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=tf,
        start=start_time,
        limit=limit
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def ejecutar_backtest(df, initial_capital=100000, min_order_value=10.0):
    """Ejecuta backtest"""
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
            'price': row['close']
        })

        if row.get('buy_signal', False) and btc_held == 0:
            current_price = row['close']
            qty = round(min_order_value / current_price, 6)
            cost = qty * current_price

            if cash >= cost:
                cash -= cost
                btc_held = qty
                entry_price = current_price
                trades.append({'timestamp': idx, 'type': 'BUY', 'price': current_price, 'qty': qty})

        elif row.get('sell_signal', False) and btc_held > 0:
            current_price = row['close']
            revenue = btc_held * current_price
            cash += revenue
            profit = revenue - (btc_held * entry_price)
            trades.append({'timestamp': idx, 'type': 'SELL', 'price': current_price, 'profit': profit})
            btc_held = 0.0
            entry_price = 0.0

    final_value = cash + (btc_held * df.iloc[-1]['close'])

    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': final_value - initial_capital,
        'total_return_pct': ((final_value - initial_capital) / initial_capital) * 100,
        'trades': trades,
        'portfolio_values': portfolio_values
    }

def analizar_rentabilidad(results, strategy_name):
    """Analiza rentabilidad"""
    trades = results['trades']
    sell_trades = [t for t in trades if t['type'] == 'SELL']

    metrics = {
        'strategy': strategy_name,
        'total_return_pct': results['total_return_pct'],
        'total_return': results['total_return'],
        'total_trades': len(trades),
        'sell_trades': len(sell_trades),
    }

    if sell_trades:
        profits = [t['profit'] for t in sell_trades]
        metrics['win_rate'] = (len([p for p in profits if p > 0]) / len(sell_trades)) * 100
        metrics['avg_profit'] = sum(profits) / len(profits)
    else:
        metrics['win_rate'] = 0
        metrics['avg_profit'] = 0

    return metrics

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_pos = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        return True, float(position.qty)
    except:
        return False, 0

# ==================== FUNCIONES PRINCIPALES ====================

def backtesting(estrategias_seleccionadas, days=30):
    """Ejecuta backtesting de estrategias"""
    print("=" * 70)
    print("🔬 BACKTESTING DE ESTRATEGIAS")
    print("=" * 70)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"📅 Período: Últimos {days} días")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")

    client = CryptoHistoricalDataClient()
    print("📥 Obteniendo datos históricos...")
    try:
        df = obtener_datos(client, SYMBOL, days=days)
        expected_bars = days * 24
        print(f"✅ {len(df)} barras obtenidas (esperadas: ~{expected_bars} para timeframe 1 hora)\n")
    except Exception as e:
        print(f"⚠️ Error obteniendo datos: {e}")
        print("💡 Usando datos de ejemplo para demostración...")
        import numpy as np
        # Generar datos de ejemplo según días solicitados
        periods = min(days * 24, 10000)  # Máximo 10,000 barras
        dates = pd.date_range(end=datetime.now(ZoneInfo("America/New_York")), periods=periods, freq='H')
        prices = 87000 + np.cumsum(np.random.randn(periods) * 100)
        df = pd.DataFrame({
            'close': prices,
            'volume': np.random.randint(1000, 10000, periods)
        }, index=dates)
        print(f"✅ {len(df)} barras de ejemplo generadas\n")

    results_list = []

    if estrategias_seleccionadas == 'all':
        estrategias_a_probar = {k: v for k, v in ESTRATEGIAS.items() if k != 'all'}
    else:
        estrategias_a_probar = {k: ESTRATEGIAS[k] for k in estrategias_seleccionadas if k in ESTRATEGIAS}

    print(f"🚀 Probando {len(estrategias_a_probar)} estrategia(s)...\n")

    for key, estrategia_func in estrategias_a_probar.items():
        try:
            df_strategy, strategy_name = estrategia_func(df.copy())
            print(f"📊 {strategy_name}...", end=" ")

            results = ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE)
            metrics = analizar_rentabilidad(results, strategy_name)
            results_list.append(metrics)

            retorno_usd = metrics['total_return']
            print(f"Retorno: {metrics['total_return_pct']:+.4f}% (${retorno_usd:+.2f}) | "
                  f"Win Rate: {metrics['win_rate']:.1f}% | Trades: {metrics['total_trades']}")
        except Exception as e:
            print(f"❌ Error: {e}")

    if results_list:
        print("\n" + "=" * 70)
        print("📊 COMPARACIÓN")
        print("=" * 70)
        sorted_strategies = sorted(results_list, key=lambda x: x['total_return_pct'], reverse=True)

        for metrics in sorted_strategies:
            retorno_color = "🟢" if metrics['total_return_pct'] > 0 else "🔴"
            retorno_usd = metrics['total_return']
            print(f"{retorno_color} {metrics['strategy']:<25} "
                  f"{metrics['total_return_pct']:>8.4f}% (${retorno_usd:>10,.2f})  "
                  f"Win Rate: {metrics['win_rate']:>6.1f}%  Trades: {metrics['total_trades']:>4}")

        best = sorted_strategies[0]
        best_usd = best['total_return']
        print("\n🏆 MEJOR: {} ({:+.4f}%, ${:+,.2f} USD, Win Rate: {:.1f}%, {} trades en {} días)".format(
            best['strategy'], best['total_return_pct'], best_usd, best['win_rate'],
            best['total_trades'], days))

    print("=" * 70)

def ejecutar_real(estrategia_key):
    """Ejecuta estrategia en modo real"""
    print("=" * 70)
    print("🚀 EJECUTAR ESTRATEGIA (MODO REAL)")
    print("=" * 70)

    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient()

    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f} | Patrimonio: ${float(account.equity):,.2f}\n")

    print("📊 Obteniendo datos...")
    try:
        df = obtener_datos(crypto_client, SYMBOL, days=10)
        print(f"✅ {len(df)} barras obtenidas\n")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return

    # Ejecutar estrategia
    if estrategia_key == 'all':
        # Probar todas y usar la mejor señal
        senales = []
        for key, estrategia_func in {k: v for k, v in ESTRATEGIAS.items() if k != 'all'}.items():
            try:
                df_strategy, strategy_name = estrategia_func(df.copy())
                latest = df_strategy.iloc[-1]
                if latest.get('buy_signal', False):
                    senales.append(('BUY', strategy_name, latest))
                elif latest.get('sell_signal', False):
                    senales.append(('SELL', strategy_name, latest))
            except:
                pass

        if not senales:
            print("⚪ Ninguna estrategia tiene señal")
            return

        estrategia_key = list({k: v for k, v in ESTRATEGIAS.items() if k != 'all'}.keys())[0]
        print(f"🟢 Usando estrategia: {senales[0][1]}\n")

    try:
        df_strategy, strategy_name = ESTRATEGIAS[estrategia_key](df.copy())
    except:
        print(f"❌ Estrategia '{estrategia_key}' no válida")
        return

    latest = df_strategy.iloc[-1]
    has_position, current_qty = verificar_posicion(trade_client, SYMBOL)

    print(f"📊 {SYMBOL}: ${latest['close']:,.2f}")
    if has_position:
        print(f"✅ Posición: {current_qty} {SYMBOL}")
    else:
        print("ℹ️ Sin posición")

    qty = round(MIN_ORDER_VALUE / latest['close'], 6)

    print("\n" + "=" * 70)

    if latest.get('buy_signal', False) and not has_position:
        print(f"🟢 SEÑAL DE COMPRA - {strategy_name}")
        print(f"   Comprando {qty} {SYMBOL} (~${qty * latest['close']:,.2f})...")

        try:
            order = MarketOrderRequest(symbol=SYMBOL, qty=qty, side=OrderSide.BUY,
                                     type=OrderType.MARKET, time_in_force=TimeInForce.GTC)
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"💰 Portfolio actualizado en Alpaca!")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif latest.get('sell_signal', False) and has_position:
        print(f"🔴 SEÑAL DE VENTA - {strategy_name}")
        print(f"   Vendiendo {abs(current_qty)} {SYMBOL}...")

        try:
            order = MarketOrderRequest(symbol=SYMBOL, qty=abs(current_qty), side=OrderSide.SELL,
                                     type=OrderType.MARKET, time_in_force=TimeInForce.GTC)
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"💰 Portfolio actualizado en Alpaca!")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⚪ Sin señal en este momento")

    print("=" * 70)

def monitoreo_continuo(estrategia_key, intervalo_horas=1):
    """Monitoreo continuo"""
    print("🔄 MONITOREO CONTINUO")
    print(f"   Estrategia: {estrategia_key}")
    print(f"   Intervalo: {intervalo_horas} hora(s)")
    print("   Presiona Ctrl+C para detener\n")

    while True:
        try:
            ejecutar_real(estrategia_key)
            print(f"\n⏳ Esperando {intervalo_horas} hora(s)...\n")
            time.sleep(intervalo_horas * 3600)
        except KeyboardInterrupt:
            print("\n⏹️ Monitoreo detenido")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

# ==================== MENÚ PRINCIPAL ====================

def mostrar_menu():
    """Muestra menú de opciones"""
    print("\n" + "=" * 70)
    print("🚀 TRADING MASTER - Script Todo en Uno")
    print("=" * 70)
    print("\n📊 Estrategias disponibles:")
    print("   1. EMA Crossover (9/21)")
    print("   2. EMA Crossover (5/13)")
    print("   3. SMA Crossover (9/21)")
    print("   4. SMA Crossover (5/13)")
    print("   5. MACD (12/26/9)")
    print("   6. Triple SMA (5/13/21)")
    print("   all. Todas las estrategias")
    print("\n📅 Intervalos de tiempo disponibles:")
    print("   30   - Últimos 30 días (default)")
    print("   90   - Últimos 3 meses")
    print("   180  - Últimos 6 meses")
    print("   365  - Último año completo")
    print("   [número] - Cualquier cantidad de días")
    print("\n🔧 Modos:")
    print("   --backtest [estrategia] [días]  - Backtesting (default: all, 30 días)")
    print("   --execute [estrategia]          - Ejecutar real (default: all)")
    print("   --monitor [estrategia] [horas]  - Monitoreo continuo (default: all, 1h)")
    print("\n💡 Ejemplos:")
    print("   python3 trading_master.py --backtest all 30")
    print("   python3 trading_master.py --backtest 5 365    # MACD, 1 año")
    print("   python3 trading_master.py --backtest all 180  # Todas, 6 meses")
    print("   python3 trading_master.py --execute 5")
    print("   python3 trading_master.py --monitor 5 1")
    print("=" * 70)

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        mostrar_menu()
        sys.exit(0)

    modo = sys.argv[1]
    estrategia = sys.argv[2] if len(sys.argv) > 2 else 'all'

    if modo == '--backtest':
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        backtesting(estrategia, days)
    elif modo == '--execute':
        ejecutar_real(estrategia)
    elif modo == '--monitor':
        intervalo = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        monitoreo_continuo(estrategia, intervalo)
    else:
        print("❌ Modo no válido. Usa --backtest, --execute o --monitor")
        mostrar_menu()

