# 📊 Estrategias MACD - Gráficos Mensuales (365 días)

Esta carpeta contiene gráficos mensuales de backtesting para 6 estrategias MACD diferentes, divididas en 12 meses (1 año completo).

## 📁 Estructura

- **72 imágenes en total** (6 estrategias × 12 meses)
- Formato: `macd_{Estrategia}_mes_{Número}_{Año-Mes}.png`

## 🎯 Estrategias Incluidas

1. **MACD Básico (Sin Stop Loss)** - Estrategia MACD estándar sin gestión de riesgo
2. **MACD + Stop Loss Fijo (2.0%)** - MACD con stop loss fijo del 2%
3. **MACD + Trailing Stop (1.5%)** - MACD con trailing stop del 1.5%
4. **MACD + Take Profit (5.0%)** - MACD con take profit del 5%
5. **MACD + SL(2.0%) + TP(5.0%)** - MACD combinando stop loss y take profit
6. **MACD + ATR Stop (x2.0)** - MACD con stop basado en Average True Range

## 📊 Formato de los Gráficos

Cada gráfico muestra:
- **Panel Superior**: Precio de BTC/USD con señales de compra (▲ verde) y venta (▼ rojo)
- **Panel Inferior**: Evolución del portfolio durante ese mes

## 🚀 Cómo Generar

```bash
# Generar gráficos para todas las estrategias (365 días = 12 meses)
python3 masterMACD.py --backtest all 365

# Generar para una estrategia específica
python3 masterMACD.py --backtest 1 365  # Estrategia 1 = MACD Básico
```

## 📅 Período de Análisis

- **Duración**: 365 días (1 año completo)
- **División**: 12 gráficos mensuales por estrategia
- **Timeframe**: 1 hora (H1)

## 💡 Notas

- Los gráficos se generan automáticamente cuando se ejecuta backtesting con 365 días
- Cada mes muestra el período correspondiente del año completo
- El capital inicial es de $100,000 USD


