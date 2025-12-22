#!/usr/bin/env python3
"""
Script para ver y operar con tu wallet de Alpaca Paper Trading
"""

import os
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest, QueryOrderStatus

# Configuración
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY') or "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"

if not SECRET_KEY:
    print("⚠️  ERROR: Necesitas configurar tu Secret Key")
    print("\nPara obtener tu Secret Key:")
    print("1. Ve a https://app.alpaca.markets/paper/dashboard/overview")
    print("2. En la sección 'API Keys', haz clic en 'Regenerate'")
    print("3. Copia el Secret Key que aparece (solo se muestra una vez)")
    print("\nLuego ejecuta:")
    print("export ALPACA_SECRET_KEY='tu_secret_key'")
    print("python3 ver_wallet.py")
    exit(1)

# Crear cliente de Paper Trading
print("🔌 Conectando a Alpaca Paper Trading...")
try:
    client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)
    print("✅ Conexión exitosa!\n")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    exit(1)

# Ver información de la cuenta
print("=" * 60)
print("💰 INFORMACIÓN DE TU WALLET")
print("=" * 60)
try:
    account = client.get_account()
    print(f"📊 Cuenta ID: {account.account_number}")
    print(f"💵 Efectivo disponible: ${float(account.cash):,.2f}")
    print(f"📈 Patrimonio total: ${float(account.equity):,.2f}")
    print(f"💼 Valor de posiciones: ${float(account.portfolio_value):,.2f}")
    if hasattr(account, 'day_trading_buying_power'):
        print(f"📉 Poder de compra day trading: ${float(account.day_trading_buying_power):,.2f}")
    print(f"✅ Estado: {account.status}")
    print(f"🔄 Trading bloqueado: {'Sí' if account.trading_blocked else 'No'}")
except Exception as e:
    print(f"❌ Error al obtener información de cuenta: {e}")
    exit(1)

# Ver posiciones abiertas
print("\n" + "=" * 60)
print("📊 POSICIONES ABIERTAS")
print("=" * 60)
try:
    positions = client.get_all_positions()
    if positions:
        for pos in positions:
            print(f"\n🔹 {pos.symbol}")
            print(f"   Cantidad: {pos.qty}")
            print(f"   Precio promedio: ${float(pos.avg_entry_price):,.2f}")
            print(f"   Precio actual: ${float(pos.current_price):,.2f}")
            print(f"   Valor de mercado: ${float(pos.market_value):,.2f}")
            print(f"   P/L no realizado: ${float(pos.unrealized_pl):,.2f}")
            print(f"   P/L %: {float(pos.unrealized_plpc) * 100:.2f}%")
    else:
        print("No tienes posiciones abiertas")
except Exception as e:
    print(f"❌ Error al obtener posiciones: {e}")

# Ver órdenes recientes
print("\n" + "=" * 60)
print("📋 ÓRDENES RECIENTES")
print("=" * 60)
try:
    orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL))
    if orders:
        for order in orders[:5]:  # Mostrar las últimas 5
            print(f"\n🔹 {order.symbol} - {order.side} {order.qty} @ ${order.limit_price if order.limit_price else 'Market'}")
            print(f"   Estado: {order.status}")
            print(f"   Tipo: {order.order_type}")
            print(f"   Fecha: {order.submitted_at}")
    else:
        print("No hay órdenes recientes")
except Exception as e:
    print(f"❌ Error al obtener órdenes: {e}")

print("\n" + "=" * 60)
print("✅ Consulta completada")
print("=" * 60)
print("\n💡 Para hacer operaciones, puedes usar el notebook:")
print("   jupyter notebook examples/crypto/crypto-trading-basic.ipynb")

