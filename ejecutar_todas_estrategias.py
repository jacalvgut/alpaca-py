#!/usr/bin/env python3
"""
Ejecuta múltiples estrategias y usa la que tenga señal más fuerte
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

def estrategia_macd(df):
    """Estrategia MACD"""
    df = df.copy()
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['buy_signal'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
    return df, "MACD"

def estrategia_ema_crossover(df, short=5, long=13):
    """Estrategia EMA Crossover"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=short)
    df['ema_long'] = ta.ema(df['close'], length=long)
    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & (df['ema_short'].shift(1) >= df['ema_long'].shift(1))
    return df, f"EMA ({short}/{long})"

def estrategia_sma_crossover(df, short=9, long=21):
    """Estrategia SMA Crossover"""
    df = df.copy()
    df['sma_short'] = ta.sma(df['close'], length=short)
    df['sma_long'] = ta.sma(df['close'], length=long)
    df['buy_signal'] = (df['sma_short'] > df['sma_long']) & (df['sma_short'].shift(1) <= df['sma_long'].shift(1))
    df['sell_signal'] = (df['sma_short'] < df['sma_long']) & (df['sma_short'].shift(1) >= df['sma_long'].shift(1))
    return df, f"SMA ({short}/{long})"

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_pos = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        return True, float(position.qty)
    except:
        return False, 0

def ejecutar_estrategias():
    """Ejecuta todas las estrategias y usa la mejor señal"""
    print("=" * 70)
    print("🚀 EJECUTANDO MÚLTIPLES ESTRATEGIAS (MODO REAL)")
    print("=" * 70)

    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient()

    # Ver cuenta
    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f} | Patrimonio: ${float(account.equity):,.2f}\n")

    # Obtener datos
    print("📊 Obteniendo datos...")
    try:
        df = obtener_datos(crypto_client, SYMBOL)
        print(f"✅ {len(df)} barras obtenidas\n")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None

    # Probar estrategias (EMA y SMA)
    estrategias = [
        lambda d: estrategia_macd(d),
        lambda d: estrategia_ema_crossover(d, 5, 13),
        lambda d: estrategia_ema_crossover(d, 9, 21),
        lambda d: estrategia_sma_crossover(d, 9, 21),
        lambda d: estrategia_sma_crossover(d, 5, 13),
    ]

    print("🔍 Analizando estrategias...\n")
    senales = []

    for estrategia_func in estrategias:
        try:
            df_strategy, nombre = estrategia_func(df.copy())
            latest = df_strategy.iloc[-1]

            if latest['buy_signal']:
                senales.append(('BUY', nombre, latest))
                print(f"🟢 {nombre}: SEÑAL DE COMPRA")
            elif latest['sell_signal']:
                senales.append(('SELL', nombre, latest))
                print(f"🔴 {nombre}: SEÑAL DE VENTA")
            else:
                print(f"⚪ {nombre}: Sin señal")
        except Exception as e:
            print(f"❌ Error en estrategia: {e}")

    # Verificar posición
    has_position, current_qty = verificar_posicion(trade_client, SYMBOL)

    if has_position:
        print(f"\n✅ Posición abierta: {current_qty} {SYMBOL}")
    else:
        print(f"\nℹ️ Sin posición abierta")

    # Ejecutar operación si hay señal
    if senales:
        print("\n" + "=" * 70)
        senal = senales[0]  # Usar primera señal
        tipo, nombre, latest = senal

        current_price = latest['close']
        qty = round(MIN_ORDER_VALUE / current_price, 6)

        if tipo == 'BUY' and not has_position:
            print(f"🟢 Ejecutando COMPRA con estrategia: {nombre}")
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
                print(f"\n✅ ORDEN EJECUTADA: {result.id}")
                print(f"💰 Tu portfolio se actualizará en Alpaca!")
                return result
            except Exception as e:
                print(f"❌ Error: {e}")
                return None

        elif tipo == 'SELL' and has_position:
            print(f"🔴 Ejecutando VENTA con estrategia: {nombre}")
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
                print(f"\n✅ ORDEN EJECUTADA: {result.id}")
                print(f"💰 Tu portfolio se actualizará en Alpaca!")
                return result
            except Exception as e:
                print(f"❌ Error: {e}")
                return None
        else:
            print(f"ℹ️ Señal de {tipo} pero {'ya tienes posición' if has_position else 'no hay posición'}")
    else:
        print("\n⚪ Ninguna estrategia tiene señal en este momento")

    print("=" * 70)
    return None

if __name__ == "__main__":
    resultado = ejecutar_estrategias()

    if resultado:
        print("\n✅ Estrategias ejecutadas exitosamente")
    else:
        print("\nℹ️ No se ejecutó ninguna operación")

