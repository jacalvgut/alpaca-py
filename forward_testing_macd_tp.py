#!/usr/bin/env python3
"""
Forward Testing - MACD + Take Profit (5.0%)
Ejecuta la estrategia MACD + Take Profit en tiempo real usando Alpaca Paper Trading
Monitorea y ejecuta trades automáticamente
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
from alpaca.trading.models import Position

# ==================== CONFIGURACIÓN ====================
# Cargar desde variables de entorno o usar valores por defecto
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Si no están en variables de entorno, usar estas (actualiza con tus keys)
if not API_KEY:
    API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
if not SECRET_KEY:
    SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"

PAPER = True

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 1000.0  # Capital inicial
MIN_ORDER_VALUE = 10.0  # Mínimo requerido por Alpaca
CAPITAL_PER_TRADE_PCT = 0.95  # Usar 95% del capital disponible

# Parámetros de la estrategia MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
TAKE_PROFIT_PCT = 0.05  # 5.0% take profit

# Configuración de monitoreo
CHECK_INTERVAL_MINUTES = 15  # Verificar señales cada 15 minutos
TIMEFRAME = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)  # Velas de 1 hora

# ==================== FUNCIONES DE ESTRATEGIA ====================

def calcular_senales_macd_tp(df):
    """
    Calcula señales MACD + Take Profit (5.0%)
    Basado en masterMACD.py - macd_take_profit
    """
    df = df.copy()

    # Calcular MACD
    macd_data = ta.macd(df['close'], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    df['macd'] = macd_data[f'MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}']
    df['macd_signal'] = macd_data[f'MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}']
    df['macd_hist'] = macd_data[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}']

    # Señal de compra: MACD cruza por encima de la línea de señal
    df['buy_signal'] = (
        (df['macd'] > df['macd_signal']) &
        (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    )

    # Señal de venta: Take Profit (5%) o MACD cruza por debajo
    df['sell_signal'] = False  # Se calculará dinámicamente durante el trading

    return df

# ==================== FUNCIONES DE TRADING ====================

def obtener_datos_recientes(client, symbol, hours=100):
    """Obtiene datos históricos recientes para calcular señales"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(hours=hours)

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TIMEFRAME,
        start=start_time,
        limit=2000
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def obtener_posicion(trade_client, symbol):
    """Obtiene la posición actual en el símbolo"""
    try:
        position = trade_client.get_open_position(symbol)
        return True, float(position.qty), float(position.avg_entry_price)
    except Exception as e:
        if "position does not exist" in str(e).lower():
            return False, 0.0, 0.0
        raise

def obtener_cash_disponible(trade_client):
    """Obtiene el efectivo disponible en la cuenta"""
    account = trade_client.get_account()
    return float(account.cash)

def calcular_cantidad_a_comprar(cash_available, current_price):
    """Calcula la cantidad a comprar usando el porcentaje del capital"""
    trade_amount = max(MIN_ORDER_VALUE, cash_available * CAPITAL_PER_TRADE_PCT)
    trade_amount = min(trade_amount, cash_available)
    qty = round(trade_amount / current_price, 8)
    return qty, trade_amount

def ejecutar_compra(trade_client, symbol, qty):
    """Ejecuta una orden de compra de mercado"""
    try:
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        order = trade_client.submit_order(order_request)
        return True, order
    except Exception as e:
        return False, str(e)

def ejecutar_venta(trade_client, symbol, qty):
    """Ejecuta una orden de venta de mercado"""
    try:
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        order = trade_client.submit_order(order_request)
        return True, order
    except Exception as e:
        return False, str(e)

def verificar_take_profit(entry_price, current_price, take_profit_pct):
    """Verifica si se alcanzó el take profit"""
    if entry_price <= 0:
        return False
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    return profit_pct >= (take_profit_pct * 100)

def mostrar_portfolio(trade_client, symbol):
    """Muestra el estado actual del portfolio"""
    try:
        account = trade_client.get_account()
        has_position, qty, entry_price = obtener_posicion(trade_client, symbol)

        # Obtener precio actual
        data_client = CryptoHistoricalDataClient()
        df = obtener_datos_recientes(data_client, symbol, hours=24)
        current_price = float(df['close'].iloc[-1])

        cash = float(account.cash)
        portfolio_value = float(account.portfolio_value)
        equity = float(account.equity)

        print("\n" + "=" * 70)
        print("💰 ESTADO DEL PORTFOLIO")
        print("=" * 70)
        print(f"💵 Efectivo disponible: ${cash:,.2f}")
        print(f"📊 Valor del portfolio: ${portfolio_value:,.2f}")
        print(f"💼 Equity: ${equity:,.2f}")
        print(f"📈 Precio actual {symbol}: ${current_price:,.2f}")

        if has_position:
            position_value = qty * current_price
            profit = position_value - (qty * entry_price)
            profit_pct = (profit / (qty * entry_price)) * 100 if entry_price > 0 else 0

            print(f"\n📦 POSICIÓN ABIERTA:")
            print(f"   Cantidad: {qty:.8f} {symbol.split('/')[0]}")
            print(f"   Precio de entrada: ${entry_price:,.2f}")
            print(f"   Valor actual: ${position_value:,.2f}")
            print(f"   {'🟢' if profit >= 0 else '🔴'} Ganancia/Pérdida: ${profit:+.2f} ({profit_pct:+.2f}%)")
            print(f"   Take Profit objetivo: ${entry_price * (1 + TAKE_PROFIT_PCT):,.2f} (+{TAKE_PROFIT_PCT*100:.1f}%)")

            # Verificar si se alcanzó el take profit
            if verificar_take_profit(entry_price, current_price, TAKE_PROFIT_PCT):
                print(f"   ✅ TAKE PROFIT ALCANZADO! ({profit_pct:.2f}%)")
        else:
            print(f"\n📭 Sin posición abierta en {symbol}")

        print("=" * 70)

    except Exception as e:
        print(f"⚠️ Error al obtener información del portfolio: {e}")

# ==================== FUNCIÓN PRINCIPAL ====================

def ejecutar_forward_testing():
    """Ejecuta el forward testing de la estrategia"""
    print("=" * 70)
    print("🚀 FORWARD TESTING - MACD + Take Profit (5.0%)")
    print("=" * 70)
    print(f"📊 Símbolo: {SYMBOL}")
    print(f"💰 Capital inicial aproximado: ${INITIAL_CAPITAL:,.2f}")
    print(f"⏰ Intervalo de verificación: {CHECK_INTERVAL_MINUTES} minutos")
    print(f"🎯 Take Profit: {TAKE_PROFIT_PCT*100:.1f}%")
    print("=" * 70)

    # Inicializar clientes
    try:
        trade_client = TradingClient(API_KEY, SECRET_KEY, paper=PAPER)
        data_client = CryptoHistoricalDataClient()

        # Verificar conexión
        account = trade_client.get_account()
        print(f"✅ Conectado a Alpaca Paper Trading")
        print(f"   Account ID: {account.account_number}")
        print(f"   Status: {account.status}")
        print()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    # Estado de la estrategia
    ultima_señal_compra = None
    ciclos = 0

    try:
        while True:
            ciclos += 1
            ahora = datetime.now(ZoneInfo("America/New_York"))
            print(f"\n{'='*70}")
            print(f"🔄 Ciclo #{ciclos} - {ahora.strftime('%Y-%m-%d %H:%M:%S')} ET")
            print(f"{'='*70}")

            # Obtener datos recientes
            try:
                df = obtener_datos_recientes(data_client, SYMBOL, hours=100)
                if len(df) < 50:
                    print("⚠️ Datos insuficientes, esperando más datos...")
                    time.sleep(CHECK_INTERVAL_MINUTES * 60)
                    continue

                # Calcular señales
                df = calcular_senales_macd_tp(df)
                ultimo_dato = df.iloc[-1]
                current_price = float(ultimo_dato['close'])

                # Verificar posición actual
                has_position, qty, entry_price = obtener_posicion(trade_client, SYMBOL)

                # Lógica de trading
                if has_position:
                    # Hay posición abierta - verificar Take Profit o señal de venta
                    print(f"📦 Posición abierta: {qty:.8f} @ ${entry_price:,.2f}")

                    # Verificar Take Profit
                    if verificar_take_profit(entry_price, current_price, TAKE_PROFIT_PCT):
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                        print(f"✅ TAKE PROFIT ALCANZADO! ({profit_pct:.2f}%)")
                        print(f"💰 Vendiendo posición...")

                        success, result = ejecutar_venta(trade_client, SYMBOL, qty)
                        if success:
                            print(f"✅ Orden de venta ejecutada: {result.id}")
                        else:
                            print(f"❌ Error al vender: {result}")
                    else:
                        # Verificar señal de venta MACD (MACD cruza por debajo)
                        if len(df) >= 2:
                            prev_row = df.iloc[-2]
                            if (prev_row['macd'] > prev_row['macd_signal'] and
                                ultimo_dato['macd'] <= ultimo_dato['macd_signal']):
                                print(f"📉 Señal de venta MACD detectada")
                                print(f"💰 Vendiendo posición...")

                                success, result = ejecutar_venta(trade_client, SYMBOL, qty)
                                if success:
                                    print(f"✅ Orden de venta ejecutada: {result.id}")
                                else:
                                    print(f"❌ Error al vender: {result}")
                            else:
                                profit_pct = ((current_price - entry_price) / entry_price) * 100
                                target_price = entry_price * (1 + TAKE_PROFIT_PCT)
                                print(f"⏳ Esperando Take Profit... (actual: {profit_pct:.2f}%, objetivo: {TAKE_PROFIT_PCT*100:.1f}%)")
                                print(f"   Precio objetivo: ${target_price:,.2f}, Actual: ${current_price:,.2f}")
                else:
                    # No hay posición - verificar señal de compra
                    if ultimo_dato['buy_signal']:
                        print(f"📈 Señal de compra MACD detectada!")

                        # Verificar que no acabamos de comprar (evitar señales duplicadas)
                        if ultima_señal_compra is None or (ahora - ultima_señal_compra).total_seconds() > 3600:
                            cash_available = obtener_cash_disponible(trade_client)

                            if cash_available >= MIN_ORDER_VALUE:
                                qty, trade_amount = calcular_cantidad_a_comprar(cash_available, current_price)
                                print(f"💰 Comprando {qty:.8f} {SYMBOL.split('/')[0]} por ~${trade_amount:,.2f}")

                                success, result = ejecutar_compra(trade_client, SYMBOL, qty)
                                if success:
                                    print(f"✅ Orden de compra ejecutada: {result.id}")
                                    ultima_señal_compra = ahora
                                else:
                                    print(f"❌ Error al comprar: {result}")
                            else:
                                print(f"⚠️ Efectivo insuficiente: ${cash_available:,.2f} < ${MIN_ORDER_VALUE}")
                        else:
                            print(f"⏭️ Señal de compra reciente, esperando...")
                    else:
                        print(f"⏳ Esperando señal de compra MACD...")
                        print(f"   MACD: {ultimo_dato['macd']:.2f}, Signal: {ultimo_dato['macd_signal']:.2f}")

                # Mostrar portfolio
                mostrar_portfolio(trade_client, SYMBOL)

            except Exception as e:
                print(f"❌ Error en ciclo: {e}")
                import traceback
                traceback.print_exc()

            # Esperar antes del próximo ciclo
            print(f"\n⏳ Esperando {CHECK_INTERVAL_MINUTES} minutos hasta el próximo ciclo...")
            print(f"   (Presiona Ctrl+C para detener)")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("🛑 FORWARD TESTING DETENIDO POR EL USUARIO")
        print("=" * 70)
        mostrar_portfolio(trade_client, SYMBOL)
        print("\n✅ Sesión finalizada")

if __name__ == '__main__':
    ejecutar_forward_testing()

