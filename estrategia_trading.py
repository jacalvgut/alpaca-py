#!/usr/bin/env python3
"""
Estrategia de Trading Automático para Crypto usando EMA Crossover
- Señal de COMPRA: EMA corta cruza por encima de EMA larga
- Señal de VENTA: EMA corta cruza por debajo de EMA larga
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

# Parámetros de la estrategia
SYMBOL = "BTC/USD"  # Puedes cambiar a ETH/USD, SOL/USD, etc.
EMA_SHORT = 9       # EMA corta (períodos)
EMA_LONG = 21       # EMA larga (períodos)
MIN_ORDER_VALUE = 10.0  # Valor mínimo de orden ($10 requerido por Alpaca)
# QTY se calculará dinámicamente basado en el precio actual

# ==================== FUNCIONES ====================

def obtener_datos(client, symbol, days=10, limit=200):
    """Obtiene datos históricos de crypto"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame(amount=1, unit=TimeFrameUnit.Hour),
        start=start_time,
        limit=limit
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    # Si hay múltiples símbolos, seleccionar el primero
    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df

def calcular_senales(df, ema_short=9, ema_long=21):
    """Calcula EMAs y genera señales de compra/venta"""
    # Calcular EMAs
    df['ema_short'] = ta.ema(df['close'], length=ema_short)
    df['ema_long'] = ta.ema(df['close'], length=ema_long)

    # Señal de COMPRA: EMA corta cruza por encima de EMA larga
    df['buy_signal'] = (df['ema_short'] > df['ema_long']) & \
                       (df['ema_short'].shift(1) <= df['ema_long'].shift(1))

    # Señal de VENTA: EMA corta cruza por debajo de EMA larga
    df['sell_signal'] = (df['ema_short'] < df['ema_long']) & \
                        (df['ema_short'].shift(1) >= df['ema_long'].shift(1))

    return df

def verificar_posicion(trade_client, symbol):
    """Verifica si hay una posición abierta"""
    symbol_for_position = symbol.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_for_position)
        return True, float(position.qty)
    except:
        return False, 0

def ejecutar_estrategia():
    """Ejecuta la estrategia de trading"""
    print("=" * 60)
    print(f"🚀 Ejecutando Estrategia EMA Crossover para {SYMBOL}")
    print("=" * 60)

    # Configurar clientes
    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

    # Verificar cuenta
    account = trade_client.get_account()
    print(f"\n💰 Efectivo disponible: ${float(account.cash):,.2f}")
    print(f"📈 Patrimonio: ${float(account.equity):,.2f}\n")

    # Obtener datos
    print("📊 Obteniendo datos históricos...")
    df = obtener_datos(crypto_client, SYMBOL)
    print(f"✅ {len(df)} barras obtenidas\n")

    # Calcular señales
    df = calcular_senales(df, EMA_SHORT, EMA_LONG)

    # Obtener última señal
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else None

    print(f"📊 Análisis de {SYMBOL}")
    print(f"💰 Precio actual: ${latest['close']:,.2f}")
    print(f"📈 EMA {EMA_SHORT}: ${latest['ema_short']:,.2f}")
    print(f"📉 EMA {EMA_LONG}: ${latest['ema_long']:,.2f}")

    # Verificar posición actual
    has_position, current_qty = verificar_posicion(trade_client, SYMBOL)

    if has_position:
        print(f"\n✅ Posición abierta: {current_qty} {SYMBOL}")
    else:
        print(f"\nℹ️ Sin posición abierta")

    # Calcular cantidad basada en precio actual (mínimo $10)
    current_price = latest['close']
    qty = max(MIN_ORDER_VALUE / current_price, QTY)  # Usar mínimo $10 o QTY, el que sea mayor
    qty = round(qty, 6)  # Redondear a 6 decimales

    # Lógica de trading
    print("\n" + "=" * 60)

    if latest['buy_signal'] and not has_position:
        # SEÑAL DE COMPRA
        print("🟢 SEÑAL DE COMPRA DETECTADA!")
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
            print(f"✅ Orden de compra ejecutada: {result.id}")
            print(f"   Estado: {result.status}")
            print(f"   💰 Tu portfolio se actualizará en Alpaca!")
            return result
        except Exception as e:
            print(f"❌ Error al comprar: {e}")
            return None

    elif latest['sell_signal'] and has_position:
        # SEÑAL DE VENTA
        print("🔴 SEÑAL DE VENTA DETECTADA!")
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
            print(f"✅ Orden de venta ejecutada: {result.id}")
            print(f"   Estado: {result.status}")
            return result
        except Exception as e:
            print(f"❌ Error al vender: {e}")
            return None
    else:
        # No hay señal nueva
        if latest['ema_short'] > latest['ema_long']:
            if has_position:
                print("⚪ Tendencia ALCISTA - Manteniendo posición")
            else:
                print("⚪ Tendencia ALCISTA - Esperando señal de compra")
        else:
            print("⚪ Tendencia BAJISTA - Esperando señal de compra")
        return None

    print("=" * 60)

def monitoreo_continuo(intervalo_horas=1):
    """Ejecuta la estrategia continuamente"""
    print("🔄 Iniciando monitoreo continuo...")
    print(f"   Intervalo: {intervalo_horas} hora(s)")
    print("   Presiona Ctrl+C para detener\n")

    while True:
        try:
            resultado = ejecutar_estrategia()
            if resultado:
                print(f"\n✅ Operación ejecutada a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            print(f"\n⏳ Esperando {intervalo_horas} hora(s) antes de la próxima revisión...\n")
            time.sleep(intervalo_horas * 3600)  # Convertir horas a segundos

        except KeyboardInterrupt:
            print("\n⏹️ Monitoreo detenido por el usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Reintentando en 1 minuto...\n")
            time.sleep(60)

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        # Modo monitoreo continuo
        intervalo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        monitoreo_continuo(intervalo)
    else:
        # Ejecución única
        ejecutar_estrategia()
        print("\n💡 Para monitoreo continuo, ejecuta:")
        print("   python3 estrategia_trading.py --monitor [horas]")

