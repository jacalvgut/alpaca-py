#!/usr/bin/env python3
"""
Ejecuta estrategia SMA Crossover en modo REAL
Simple Moving Average en lugar de Exponential Moving Average
"""

import pandas as pd
import pandas_ta as ta
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
SMA_SHORT = 9   # SMA corta
SMA_LONG = 21   # SMA larga
MIN_ORDER_VALUE = 10.0

def obtener_datos(client, symbol, days=10):
    """Obtiene datos históricos"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame(amount=1, unit=TimeFrameUnit.Hour),
        start=start_time,
        limit=200
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def calcular_senales_sma(df, sma_short=9, sma_long=21):
    """Calcula señales usando SMA"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=sma_short)
    df['sma_long'] = ta.sma(df['close'], length=sma_long)

    # Señal de COMPRA: SMA corta cruza por encima de SMA larga
    df['buy_signal'] = (df['sma_short'] > df['sma_long']) & \
                       (df['sma_short'].shift(1) <= df['sma_long'].shift(1))

    # Señal de VENTA: SMA corta cruza por debajo de SMA larga
    df['sell_signal'] = (df['sma_short'] < df['sma_long']) & \
                        (df['sma_short'].shift(1) >= df['sma_long'].shift(1))

    return df

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_pos = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        return True, float(position.qty), float(position.current_price)
    except:
        return False, 0, 0

def ejecutar_estrategia_sma():
    """Ejecuta estrategia SMA en modo REAL"""
    print("=" * 70)
    print(f"🚀 ESTRATEGIA SMA CROSSOVER ({SMA_SHORT}/{SMA_LONG}) - MODO REAL")
    print("=" * 70)

    # Clientes
    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient()

    # Ver cuenta
    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f}")
    print(f"📈 Patrimonio: ${float(account.equity):,.2f}\n")

    # Obtener datos
    print("📊 Obteniendo datos históricos...")
    try:
        df = obtener_datos(crypto_client, SYMBOL)
        print(f"✅ {len(df)} barras obtenidas\n")
    except Exception as e:
        print(f"⚠️ Error obteniendo datos: {e}")
        return None

    # Calcular señales SMA
    print("🔍 Calculando señales SMA...")
    df = calcular_senales_sma(df, SMA_SHORT, SMA_LONG)
    latest = df.iloc[-1]

    print(f"\n📊 Análisis de {SYMBOL}:")
    print(f"   Precio actual: ${latest['close']:,.2f}")
    print(f"   SMA {SMA_SHORT}: ${latest['sma_short']:,.2f}")
    print(f"   SMA {SMA_LONG}: ${latest['sma_long']:,.2f}")
    print(f"   Diferencia: ${latest['sma_short'] - latest['sma_long']:,.2f}")

    # Verificar posición
    has_position, current_qty, current_price = verificar_posicion(trade_client, SYMBOL)

    if has_position:
        pnl = ((current_price - latest['close']) / latest['close']) * 100
        print(f"\n✅ Posición abierta:")
        print(f"   Cantidad: {current_qty} {SYMBOL}")
        print(f"   Precio actual: ${current_price:,.2f}")
    else:
        print(f"\nℹ️ Sin posición abierta")

    # Calcular cantidad (mínimo $10)
    qty = round(MIN_ORDER_VALUE / latest['close'], 6)

    print("\n" + "=" * 70)

    # Ejecutar operación
    if latest['buy_signal'] and not has_position:
        print("🟢 SEÑAL DE COMPRA (SMA Crossover)")
        print(f"   SMA {SMA_SHORT} cruzó por encima de SMA {SMA_LONG}")
        print(f"   Comprando {qty} {SYMBOL} (~${qty * latest['close']:,.2f})...")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=qty,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"\n✅ ORDEN EJECUTADA:")
            print(f"   ID: {result.id}")
            print(f"   Estado: {result.status}")
            print(f"   Cantidad: {result.qty}")
            print(f"\n💰 Tu portfolio en Alpaca se actualizará en unos segundos!")
            return result
        except Exception as e:
            print(f"\n❌ Error al ejecutar orden: {e}")
            return None

    elif latest['sell_signal'] and has_position:
        print("🔴 SEÑAL DE VENTA (SMA Crossover)")
        print(f"   SMA {SMA_SHORT} cruzó por debajo de SMA {SMA_LONG}")
        print(f"   Vendiendo {abs(current_qty)} {SYMBOL}...")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=abs(current_qty),
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"\n✅ ORDEN EJECUTADA:")
            print(f"   ID: {result.id}")
            print(f"   Estado: {result.status}")
            print(f"\n💰 Tu portfolio en Alpaca se actualizará en unos segundos!")
            return result
        except Exception as e:
            print(f"\n❌ Error al ejecutar orden: {e}")
            return None
    else:
        if latest['sma_short'] > latest['sma_long']:
            print("⚪ Tendencia ALCISTA (SMA corta > SMA larga)")
            if has_position:
                print("   Manteniendo posición")
            else:
                print("   Esperando señal de compra más clara")
        else:
            print("⚪ Tendencia BAJISTA (SMA corta < SMA larga)")
            if has_position:
                print("   Considera vender si la señal se confirma")
            else:
                print("   Esperando señal de compra")
        return None

    print("=" * 70)

if __name__ == "__main__":
    resultado = ejecutar_estrategia_sma()

    if resultado:
        print("\n✅ Estrategia SMA ejecutada exitosamente")
    else:
        print("\nℹ️ No se ejecutó ninguna operación (sin señal o ya en posición)")


