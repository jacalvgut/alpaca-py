#!/usr/bin/env python3
"""
Day Trading Strategy para BTC/USD
- Timeframes cortos (5 min, 15 min)
- Operaciones intradía
- Señales más frecuentes
"""

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_ta as ta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

# ==================== CONFIGURACIÓN DAY TRADING ====================
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"
PAPER = True

# Parámetros para day trading (timeframes más cortos)
SYMBOL = "BTC/USD"
TIMEFRAME_MINUTES = 5  # 5 minutos para day trading
EMA_SHORT = 5          # EMA muy corta para day trading
EMA_LONG = 13          # EMA corta para day trading
MIN_ORDER_VALUE = 10.0  # Valor mínimo de orden ($10 requerido)
QTY_BASE = 0.001       # Cantidad base (se ajustará al mínimo $10)
STOP_LOSS_PCT = 0.02   # Stop loss del 2%
TAKE_PROFIT_PCT = 0.015  # Take profit del 1.5%

# ==================== FUNCIONES ====================

def obtener_datos_day_trading(client, symbol, minutes=5, periods=100):
    """Obtiene datos para day trading con timeframe corto"""
    now = datetime.now(ZoneInfo("America/New_York"))
    # Para day trading, necesitamos datos de las últimas horas
    start_time = now - timedelta(hours=24)  # Últimas 24 horas

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame(amount=minutes, unit=TimeFrameUnit.Minute),
        start=start_time,
        limit=periods
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df

def calcular_senales_day_trading(df, ema_short=5, ema_long=13):
    """Calcula señales optimizadas para day trading"""
    # Calcular EMAs
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)

    # RSI para confirmación (evitar señales en mercados laterales)
    df['rsi'] = ta.rsi(df['close'], length=14)

    # Volumen promedio para confirmación
    df['volume_avg'] = df['volume'].rolling(window=20).mean()

    # Señal de COMPRA: EMA crossover + RSI no sobrecomprado + volumen alto
    df['buy_signal'] = (
        (df['ema_short'] > df['ema_long']) &
        (df['ema_short'].shift(1) <= df['ema_long'].shift(1)) &
        (df['rsi'] < 70) &  # No sobrecomprado
        (df['volume'] > df['volume_avg'] * 0.8)  # Volumen decente
    )

    # Señal de VENTA: EMA crossover + RSI no sobrevendido
    df['sell_signal'] = (
        (df['ema_short'] < df['ema_long']) &
        (df['ema_short'].shift(1) >= df['ema_long'].shift(1)) &
        (df['rsi'] > 30)  # No sobrevendido
    )

    return df

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_for_position = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_for_position)
        return True, float(position.qty), float(position.avg_entry_price), float(position.current_price)
    except:
        return False, 0, 0, 0

def ejecutar_day_trading():
    """Ejecuta estrategia de day trading"""
    print("=" * 70)
    print(f"📈 DAY TRADING - {SYMBOL} (Timeframe: {TIMEFRAME_MINUTES} minutos)")
    print("=" * 70)

    # Configurar clientes
    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

    # Verificar cuenta
    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f} | Patrimonio: ${float(account.equity):,.2f}\n")

    # Obtener datos
    print(f"📊 Obteniendo datos de {TIMEFRAME_MINUTES} minutos...")
    df = obtener_datos_day_trading(crypto_client, SYMBOL, TIMEFRAME_MINUTES)
    print(f"✅ {len(df)} barras obtenidas\n")

    # Calcular señales
    df = calcular_senales_day_trading(df, EMA_SHORT, EMA_LONG)

    # Última barra
    latest = df.iloc[-1]

    print(f"📊 Análisis de {SYMBOL}")
    print(f"💰 Precio: ${latest['close']:,.2f}")
    print(f"📈 EMA {EMA_SHORT}: ${latest['ema_short']:,.2f}")
    print(f"📉 EMA {EMA_LONG}: ${latest['ema_long']:,.2f}")
    print(f"📊 RSI: {latest['rsi']:.2f}")
    print(f"📦 Volumen: {latest['volume']:,.0f}")

    # Verificar posición
    has_position, qty, entry_price, current_price = verificar_posicion(trade_client, SYMBOL)

    if has_position:
        pnl = (current_price - entry_price) / entry_price * 100
        print(f"\n✅ Posición abierta: {qty} {SYMBOL}")
        print(f"   Entrada: ${entry_price:,.2f} | Actual: ${current_price:,.2f}")
        print(f"   P/L: {pnl:+.2f}%")

        # Verificar stop loss / take profit
        if pnl <= -STOP_LOSS_PCT * 100:
            print(f"\n🛑 STOP LOSS activado ({pnl:.2f}%)")
        elif pnl >= TAKE_PROFIT_PCT * 100:
            print(f"\n🎯 TAKE PROFIT activado ({pnl:.2f}%)")
    else:
        print(f"\nℹ️ Sin posición abierta")

    # Lógica de trading
    print("\n" + "=" * 70)

    # Calcular cantidad (mínimo $10)
    current_price = latest['close']
    qty = max(MIN_ORDER_VALUE / current_price, QTY_BASE)
    qty = round(qty, 6)

    if latest['buy_signal'] and not has_position:
        print("🟢 SEÑAL DE COMPRA (DAY TRADING)")
        print(f"   Comprando {qty} {SYMBOL} (~${qty * current_price:,.2f})...")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=qty,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id} | Estado: {result.status}")
            return result
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    elif latest['sell_signal'] and has_position:
        print("🔴 SEÑAL DE VENTA (DAY TRADING)")
        print(f"   Vendiendo {abs(qty)} {SYMBOL}...")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=abs(qty),
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id} | Estado: {result.status}")
            return result
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    else:
        if latest['ema_short'] > latest['ema_long']:
            print("⚪ Tendencia ALCISTA - Esperando señal de compra")
        else:
            print("⚪ Tendencia BAJISTA - Esperando señal de compra")
        return None

    print("=" * 70)

def monitoreo_day_trading(intervalo_minutos=5):
    """Monitoreo continuo para day trading"""
    print("🔄 DAY TRADING - Monitoreo continuo")
    print(f"   Intervalo: {intervalo_minutos} minutos")
    print("   Presiona Ctrl+C para detener\n")

    while True:
        try:
            resultado = ejecutar_day_trading()
            if resultado:
                print(f"\n✅ Operación ejecutada: {datetime.now().strftime('%H:%M:%S')}\n")

            print(f"⏳ Esperando {intervalo_minutos} minutos...\n")
            time.sleep(intervalo_minutos * 60)

        except KeyboardInterrupt:
            print("\n⏹️ Monitoreo detenido")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        intervalo = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        monitoreo_day_trading(intervalo)
    else:
        ejecutar_day_trading()
        print("\n💡 Para monitoreo continuo:")
        print("   python3 day_trading_btc.py --monitor [minutos]")

