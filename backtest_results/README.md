# 📊 Resultados de Backtesting

Esta carpeta contiene los gráficos generados por los scripts de backtesting.

## 📁 Archivos Disponibles

### Estrategias EMA (Exponential Moving Average)
- `backtest_EMA_Crossover_(9_21).png`
- `backtest_EMA_Crossover_(5_13).png`
- `backtest_EMA_Crossover_(12_26).png`
- `backtest_EMA_+_RSI_(9_21,_RSI_30_70).png`
- `backtest_EMA_+_Volumen_(9_21,_vol_1.2).png`

### Estrategias SMA (Simple Moving Average) ⭐
- `backtest_SMA_Crossover_(9_21).png`
- `backtest_SMA_Crossover_(5_13).png`
- `backtest_SMA_Crossover_(12_26).png`
- `backtest_SMA_+_RSI_(9_21,_RSI_30_70).png`
- `backtest_SMA_+_Volumen_(9_21,_vol_1.2).png`
- `backtest_Triple_SMA_(5_13_21).png`

### Otras Estrategias
- `backtest_MACD_*.png` (si se genera)
- `backtest_Bollinger_Bands_*.png` (si se genera)
- `backtest_resultado.png` (backtesting básico)
- `backtest_day_trading.png` (day trading)

## 🔍 Cómo Ver los Gráficos

### En macOS:
```bash
open backtest_results/backtest_SMA_Crossover_(9_21).png
```

### Listar todos los gráficos SMA:
```bash
ls -lh backtest_results/*SMA*.png
```

### Ver todos los archivos:
```bash
ls -lh backtest_results/
```

## 📊 Generar Nuevos Gráficos

Ejecuta el backtesting para generar todos los gráficos:

```bash
python3 backtesting_estrategias.py
```

Todos los gráficos se guardan automáticamente en esta carpeta usando rutas relativas.

## 📈 Mejores Estrategias (según último backtesting)

1. **MACD (12/26/9)** - 44.4% win rate
2. **EMA Crossover (5/13)** - 30.8% win rate
3. **Triple SMA (5/13/21)** - 50.0% win rate (muy conservadora)

## 💡 Nota

Los gráficos se generan automáticamente cuando ejecutas `backtesting_estrategias.py`. Si no ves algún gráfico, ejecuta el script nuevamente.
