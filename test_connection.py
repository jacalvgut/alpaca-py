#!/usr/bin/env python3
"""Test de conexión con Alpaca"""

from alpaca.trading.client import TradingClient

api_key = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
secret_key = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"

print("Probando conexión con Paper Trading...")
print(f"API Key: {api_key[:10]}...")
print(f"Paper: True\n")

try:
    # Intentar con paper=True
    client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
    account = client.get_account()
    print("✅ Conexión exitosa con Paper Trading!")
    print(f"Cuenta: {account.account_number}")
    print(f"Efectivo: ${float(account.cash):,.2f}")
except Exception as e:
    print(f"❌ Error con Paper Trading: {e}")
    print("\nProbando con Live Trading...")
    try:
        client = TradingClient(api_key=api_key, secret_key=secret_key, paper=False)
        account = client.get_account()
        print("✅ Conexión exitosa con Live Trading!")
        print(f"Cuenta: {account.account_number}")
    except Exception as e2:
        print(f"❌ Error con Live Trading: {e2}")
        print("\n⚠️  Verifica que las credenciales sean correctas y que sean para Paper Trading")

