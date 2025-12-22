#!/usr/bin/env python3
"""
Script temporal para probar la conexión con Alpaca Paper Trading
"""

import os

# Configuración de API keys
api_key = "PK2DJUVWUTREY75RO4HWC4DKCN"
secret_key = None

# Intentar obtener secret_key de variable de entorno
if secret_key is None:
    secret_key = os.environ.get('ALPACA_SECRET_KEY')

# Verificar que tenemos ambas keys
if not api_key or not secret_key:
    print("❌ ERROR: Falta el Secret Key")
    print("Por favor, proporciona tu Secret Key de una de estas formas:")
    print("1. Configura la variable de entorno: export ALPACA_SECRET_KEY='tu_secret_key'")
    print("2. O edita este script y agrega: secret_key = 'tu_secret_key'")
    exit(1)

# Configuración de paper trading
paper = True

print("🔧 Configurando cliente de Alpaca para Paper Trading...")
print(f"API Key: {api_key[:10]}...")
print(f"Paper Trading: {paper}")

# Importar alpaca
try:
    from alpaca.trading.client import TradingClient
    print("✅ alpaca-py importado correctamente")
except ImportError as e:
    print(f"❌ Error al importar alpaca-py: {e}")
    exit(1)

# Crear cliente de trading
try:
    trade_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
    print("✅ Cliente de trading creado")
except Exception as e:
    print(f"❌ Error al crear cliente: {e}")
    exit(1)

# Verificar cuenta
try:
    print("\n📊 Verificando cuenta de Paper Trading...")
    acct = trade_client.get_account()
    print(f"✅ Conexión exitosa!")
    print(f"   Cuenta ID: {acct.account_number}")
    print(f"   Estado: {acct.status}")
    print(f"   Capital: ${float(acct.cash):,.2f}")
    print(f"   Capital de trading: ${float(acct.trading_blocked):,.2f}" if hasattr(acct, 'trading_blocked') else "")
    print(f"   Patrimonio: ${float(acct.equity):,.2f}")
    print(f"\n🎉 ¡Configuración completada! Puedes usar el notebook ahora.")
except Exception as e:
    print(f"❌ Error al verificar cuenta: {e}")
    print("   Verifica que tu API key y Secret key sean correctos para Paper Trading")
    exit(1)


