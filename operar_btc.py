#!/usr/bin/env python3
"""
Script rápido para operar BTC/USD manualmente
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

# Ver cuenta
account = trade_client.get_account()
print(f"💰 Efectivo disponible: ${float(account.cash):,.2f}")

# Obtener precio actual
quote = crypto_client.get_crypto_latest_quote(CryptoLatestQuoteRequest(symbol_or_symbols=[SYMBOL]))
current_price = quote[SYMBOL].ask_price
print(f"📊 Precio actual de {SYMBOL}: ${current_price:,.2f}")

# Verificar posición
symbol_pos = SYMBOL.replace("/", "")
try:
    position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
    print(f"\n✅ Posición abierta:")
    print(f"   Cantidad: {position.qty}")
    print(f"   Precio promedio: ${float(position.avg_entry_price):,.2f}")
    print(f"   P/L: ${float(position.unrealized_pl):,.2f} ({float(position.unrealized_plpc)*100:.2f}%)")
    has_position = True
except:
    print(f"\nℹ️ Sin posición abierta en {SYMBOL}")
    has_position = False

print("\n" + "="*60)
print("OPCIONES:")
print("="*60)
print("1. Comprar BTC/USD (orden de mercado)")
print("2. Vender BTC/USD (si tienes posición)")
print("3. Ver estado de la estrategia")
print("="*60)

# Ejemplo de compra (descomenta para usar)
# QTY = 0.001  # Ajusta la cantidad
# order = MarketOrderRequest(
#     symbol=SYMBOL,
#     qty=QTY,
#     side=OrderSide.BUY,
#     type=OrderType.MARKET,
#     time_in_force=TimeInForce.GTC
# )
# result = trade_client.submit_order(order)
# print(f"✅ Orden ejecutada: {result.id}")

print("\n💡 Para operar, edita este script y descomenta las líneas de orden")

