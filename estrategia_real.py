#!/usr/bin/env python3
"""
Estrategia de Trading REAL - Ejecuta operaciones que actualizan tu portfolio
Este script ejecuta la estrategia y HACE OPERACIONES REALES en Paper Trading
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

# ==================== CONFIGURACIÓN ====================
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"
PAPER = True

SYMBOL = "BTC/USD"
EMA_SHORT = 9
EMA_LONG = 21
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

    return df

def calcular_senales(df, ema_short=9, ema_long=21):
    """Calcula señales de trading"""
    df = df.copy()
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)
    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & \
                       (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & \
                        (df['ema_short'].shift(1) >= df['ema_long'].shift(1))
    return df

def verificar_posicion(trade_client, symbol):
    """Verifica posición actual"""
    symbol_pos = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        return True, float(position.qty)
    except:
        return False, 0

def ejecutar_estrategia_real():
    """Ejecuta la estrategia con operaciones REALES"""
    print("=" * 70)
    print("🚀 ESTRATEGIA REAL - Operaciones que actualizan tu portfolio")
    print("=" * 70)

    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

    # Ver cuenta
    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f} | Patrimonio: ${float(account.equity):,.2f}\n")

    # Obtener datos
    print("📊 Obteniendo datos...")
    df = obtener_datos(crypto_client, SYMBOL)
    print(f"✅ {len(df)} barras obtenidas\n")

    # Calcular señales
    df = calcular_senales(df, EMA_SHORT, EMA_LONG)
    latest = df.iloc[-1]

    print(f"📊 {SYMBOL}: ${latest['close']:,.2f}")
    print(f"📈 EMA {EMA_SHORT}: ${latest['ema_short']:,.2f}")
    print(f"📉 EMA {EMA_LONG}: ${latest['ema_long']:,.2f}")

    # Verificar posición
    has_position, current_qty = verificar_posicion(trade_client, SYMBOL)

    if has_position:
        print(f"\n✅ Posición abierta: {current_qty} {SYMBOL}")
    else:
        print(f"\nℹ️ Sin posición abierta")

    # Calcular cantidad (mínimo $10)
    current_price = latest['close']
    qty = round(MIN_ORDER_VALUE / current_price, 6)

    print("\n" + "=" * 70)

    # Ejecutar operación si hay señal
    if latest['buy_signal'] and not has_position:
        print("🟢 SEÑAL DE COMPRA - Ejecutando orden REAL...")
        print(f"   Comprando {qty} {SYMBOL} (~${qty * current_price:,.2f})")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=qty,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"   Estado: {result.status}")
            print(f"\n💰 Tu portfolio en Alpaca se actualizará en unos segundos!")
            print(f"   Refresca el dashboard para ver los cambios")
            return result
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    elif latest['sell_signal'] and has_position:
        print("🔴 SEÑAL DE VENTA - Ejecutando orden REAL...")
        print(f"   Vendiendo {abs(current_qty)} {SYMBOL}")

        try:
            order = MarketOrderRequest(
                symbol=SYMBOL,
                qty=abs(current_qty),
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"   Estado: {result.status}")
            print(f"\n💰 Tu portfolio en Alpaca se actualizará en unos segundos!")
            return result
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    else:
        if latest['ema_short'] > latest['ema_long']:
            print("⚪ Tendencia ALCISTA - Sin señal nueva")
        else:
            print("⚪ Tendencia BAJISTA - Esperando señal de compra")
        return None

    print("=" * 70)

def monitoreo_real(intervalo_horas=1):
    """Monitoreo continuo con operaciones REALES"""
    print("🔄 MONITOREO CONTINUO - Operaciones REALES")
    print(f"   Intervalo: {intervalo_horas} hora(s)")
    print("   ⚠️  Este script ejecutará operaciones REALES")
    print("   Presiona Ctrl+C para detener\n")

    while True:
        try:
            resultado = ejecutar_estrategia_real()
            if resultado:
                print(f"\n✅ Operación ejecutada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"⏳ Esperando {intervalo_horas} hora(s)...\n")
            time.sleep(intervalo_horas * 3600)

        except KeyboardInterrupt:
            print("\n⏹️ Monitoreo detenido")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        intervalo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        monitoreo_real(intervalo)
    else:
        ejecutar_estrategia_real()
        print("\n💡 Para monitoreo continuo:")
        print("   python3 estrategia_real.py --monitor [horas]")

