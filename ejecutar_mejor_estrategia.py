#!/usr/bin/env python3
"""
Ejecuta la MEJOR estrategia (MACD) en modo REAL
Actualiza tu portfolio en Alpaca con operaciones reales
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
MIN_ORDER_VALUE = 10.0  # Mínimo $10 por orden

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

def estrategia_macd(df):
    """Estrategia MACD - La mejor según backtesting"""
    df = df.copy()
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']

    # Compra: MACD cruza por encima de la señal
    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))

    # Venta: MACD cruza por debajo de la señal
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    return df

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_pos = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        return True, float(position.qty), float(position.current_price)
    except:
        return False, 0, 0

def ejecutar_estrategia_macd():
    """Ejecuta estrategia MACD en modo REAL"""
    print("=" * 70)
    print("🚀 EJECUTANDO ESTRATEGIA MACD (MODO REAL)")
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

    # Calcular señales MACD
    print("🔍 Calculando señales MACD...")
    df = estrategia_macd(df)
    latest = df.iloc[-1]

    print(f"\n📊 Análisis de {SYMBOL}:")
    print(f"   Precio actual: ${latest['close']:,.2f}")
    print(f"   MACD: {latest['macd']:.2f}")
    print(f"   Señal MACD: {latest['macd_signal']:.2f}")
    print(f"   Histograma: {latest['macd_hist']:.2f}")

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
        print("🟢 SEÑAL DE COMPRA (MACD)")
        print(f"   MACD cruzó por encima de la señal")
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
            print(f"   Refresca el dashboard para ver los cambios")
            return result
        except Exception as e:
            print(f"\n❌ Error al ejecutar orden: {e}")
            return None

    elif latest['sell_signal'] and has_position:
        print("🔴 SEÑAL DE VENTA (MACD)")
        print(f"   MACD cruzó por debajo de la señal")
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
        if latest['macd'] > latest['macd_signal']:
            print("⚪ Tendencia ALCISTA (MACD > Señal)")
            if has_position:
                print("   Manteniendo posición")
            else:
                print("   Esperando señal de compra más clara")
        else:
            print("⚪ Tendencia BAJISTA (MACD < Señal)")
            if has_position:
                print("   Considera vender si la señal se confirma")
            else:
                print("   Esperando señal de compra")
        return None

    print("=" * 70)

if __name__ == "__main__":
    resultado = ejecutar_estrategia_macd()

    if resultado:
        print("\n✅ Estrategia ejecutada exitosamente")
    else:
        print("\nℹ️ No se ejecutó ninguna operación (sin señal o ya en posición)")

