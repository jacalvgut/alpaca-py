#!/usr/bin/env python3
"""
Ejecuta una operación REAL para actualizar el portfolio
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest

# Configuración
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"
SYMBOL = "BTC/USD"

# Clientes
trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)
crypto_client = CryptoHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

print("=" * 70)
print("💰 ESTADO ACTUAL DEL PORTFOLIO")
print("=" * 70)

# Ver cuenta
account = trade_client.get_account()
print(f"\n💵 Efectivo disponible: ${float(account.cash):,.2f}")
print(f"📈 Patrimonio total: ${float(account.equity):,.2f}")
print(f"💼 Valor de posiciones: ${float(account.portfolio_value):,.2f}")

# Obtener precio actual
quote = crypto_client.get_crypto_latest_quote(CryptoLatestQuoteRequest(symbol_or_symbols=[SYMBOL]))
current_price = quote[SYMBOL].ask_price
print(f"\n📊 Precio actual de {SYMBOL}: ${current_price:,.2f}")

# Verificar posición actual
symbol_pos = SYMBOL.replace("/", "")
try:
    position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
    print(f"\n✅ Posición abierta:")
    print(f"   Cantidad: {position.qty}")
    print(f"   Precio promedio: ${float(position.avg_entry_price):,.2f}")
    print(f"   P/L: ${float(position.unrealized_pl):,.2f}")
    has_position = True
except:
    print(f"\nℹ️ Sin posición abierta en {SYMBOL}")
    has_position = False

print("\n" + "=" * 70)
print("🚀 EJECUTAR OPERACIÓN REAL")
print("=" * 70)

# Operación de prueba: comprar cantidad mínima ($10 mínimo requerido)
MIN_ORDER_VALUE = 10.0
QTY = MIN_ORDER_VALUE / current_price  # Calcular cantidad para $10
QTY = round(QTY, 6)  # Redondear a 6 decimales

print(f"\n🟢 Ejecutando compra de prueba de {QTY} {SYMBOL}")
print(f"   Costo aproximado: ${QTY * current_price:,.2f} (mínimo $10 requerido)")
print(f"   Esto actualizará tu portfolio en tiempo real\n")

# Ejecutar compra
try:
    order = MarketOrderRequest(
        symbol=SYMBOL,
        qty=QTY,
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        time_in_force=TimeInForce.GTC
    )

    result = trade_client.submit_order(order)
    print(f"✅ Orden ejecutada exitosamente!")
    print(f"   ID de orden: {result.id}")
    print(f"   Estado: {result.status}")
    print(f"   Cantidad: {result.qty}")
    print(f"   Símbolo: {result.symbol}")

    print("\n" + "=" * 70)
    print("📊 VERIFICANDO PORTFOLIO ACTUALIZADO")
    print("=" * 70)

    # Esperar un momento y verificar
    import time
    time.sleep(2)

    # Ver cuenta actualizada
    account_updated = trade_client.get_account()
    print(f"\n💵 Efectivo actualizado: ${float(account_updated.cash):,.2f}")
    print(f"📈 Patrimonio actualizado: ${float(account_updated.equity):,.2f}")

    # Ver posición
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        print(f"\n✅ Nueva posición:")
        print(f"   Cantidad: {position.qty}")
        print(f"   Precio promedio: ${float(position.avg_entry_price):,.2f}")
        print(f"   Precio actual: ${float(position.current_price):,.2f}")
        print(f"   P/L no realizado: ${float(position.unrealized_pl):,.2f}")
        print(f"   P/L %: {float(position.unrealized_plpc) * 100:.2f}%")
    except:
        print("\n⚠️ La posición aún no aparece (puede tardar unos segundos)")

    print("\n✅ ¡Tu portfolio en Alpaca debería actualizarse ahora!")
    print("   Refresca la página del dashboard para ver los cambios")

except Exception as e:
    print(f"\n❌ Error al ejecutar orden: {e}")
    print("\n💡 Verifica:")
    print("   1. Que tengas suficiente efectivo")
    print("   2. Que el mercado esté abierto")
    print("   3. Que las credenciales sean correctas")

print("\n" + "=" * 70)

