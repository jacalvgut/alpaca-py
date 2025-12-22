# 📊 Resultados de Backtesting - Estrategias MACD

Esta carpeta contiene los gráficos generados por las estrategias MACD con diferentes gestiones de riesgo.

## 📁 Archivos

Los gráficos se generan automáticamente cuando ejecutas:

```bash
python3 masterMACD.py --backtest all 365
```

## 🎯 Estrategias

1. **MACD Básico** - Sin gestión de riesgo
2. **MACD + Stop Loss Fijo** - Stop loss del 2%
3. **MACD + Trailing Stop** - Stop loss dinámico
4. **MACD + Take Profit** - Take profit del 5%
5. **MACD + SL + TP** - Stop loss y take profit combinados
6. **MACD + ATR Stop** - Stop loss basado en volatilidad

## 📊 Contenido de los Gráficos

Cada gráfico muestra:
- **Gráfico superior**: Precio de BTC/USD con señales de compra (▲ verde) y venta (▼ rojo)
- **Gráfico inferior**: Evolución del valor del portfolio en el tiempo


