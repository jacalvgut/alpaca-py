# 🚀 Guía de Estrategias de Trading

## 📊 Estrategias Disponibles

### 1. Backtesting (Simulación)
Prueba estrategias sin riesgo:

```bash
# Probar todas las estrategias y comparar resultados
python3 backtesting_estrategias.py
```

**Estrategias incluidas:**
- EMA Crossover (9/21, 5/13, 12/26)
- EMA + RSI
- MACD (12/26/9) - ⭐ MEJOR según backtesting
- Bollinger Bands
- EMA + Volumen

### 2. Ejecutar Estrategias Reales

#### Opción A: Mejor Estrategia (MACD)
```bash
python3 ejecutar_mejor_estrategia.py
```
Ejecuta la estrategia MACD que tuvo mejor rendimiento en backtesting.

#### Opción B: Todas las Estrategias
```bash
python3 ejecutar_todas_estrategias.py
```
Analiza todas las estrategias y ejecuta la que tenga señal más fuerte.

#### Opción C: Day Trading
```bash
# Ejecutar una vez
python3 day_trading_btc.py

# Monitoreo continuo cada 5 minutos
python3 day_trading_btc.py --monitor 5
```

#### Opción D: Estrategia Real con Monitoreo
```bash
# Ejecutar una vez
python3 estrategia_real.py

# Monitoreo continuo cada hora
python3 estrategia_real.py --monitor 1
```

## 📈 Resultados del Backtesting

### Mejor Estrategia: MACD (12/26/9)
- ✅ Win Rate: 44.4%
- ✅ Retorno: +$1.51
- ✅ Trades: 36

### Comparación Completa:
1. MACD (12/26/9) - 44.4% win rate
2. EMA Crossover (5/13) - 30.8% win rate
3. EMA + RSI - 27.3% win rate
4. EMA Crossover (9/21) - 20.0% win rate

## 🔧 Personalizar Estrategias

### Crear tu propia estrategia:

1. Edita `backtesting_estrategias.py`
2. Agrega una nueva función:

```python
def mi_estrategia(df):
    df = df.copy()
    # Tu lógica aquí
    df['buy_signal'] = ...  # Condiciones de compra
    df['sell_signal'] = ...  # Condiciones de venta
    return df, "Mi Estrategia"
```

3. Agrégala a la lista de estrategias
4. Ejecuta el backtesting para probarla

## ⚙️ Configuración

### Ajustar parámetros:

**En los scripts, puedes modificar:**
- `SYMBOL`: "BTC/USD", "ETH/USD", etc.
- `INITIAL_CAPITAL`: Capital inicial para backtesting
- `MIN_ORDER_VALUE`: Mínimo $10 (requerido por Alpaca)
- `DAYS_BACK`: Período de datos históricos
- `TIMEFRAME`: "1Hour", "5Min", "15Min"

## 📊 Ver Resultados

### Ver tu portfolio:
```bash
python3 ver_wallet.py
```

### Ver gráficos generados:
Los backtests generan gráficos PNG que puedes abrir:
- `backtest_EMA_Crossover_(9_21).png`
- `backtest_MACD_*.png`
- etc.

## ⚠️ Notas Importantes

1. **Paper Trading**: Todas las operaciones son en modo Paper (dinero ficticio)
2. **Mínimo de orden**: $10 USD requerido por Alpaca
3. **Autenticación**: Si hay errores 401, verifica tus credenciales
4. **Backtesting vs Real**:
   - Backtesting = Simulación (no actualiza portfolio)
   - Estrategias reales = Operaciones reales (actualiza portfolio)

## 🎯 Próximos Pasos

1. ✅ Ejecutar backtesting para encontrar la mejor estrategia
2. ✅ Probar la estrategia en modo real
3. ✅ Ajustar parámetros según resultados
4. ✅ Configurar monitoreo continuo si la estrategia es rentable


