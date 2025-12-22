# 🚀 Sistema de Trading con Alpaca - Guía Completa

Sistema completo de trading automatizado para crypto (BTC/USD) usando Alpaca Paper Trading con estrategias de backtesting y ejecución automática.

## 📋 Tabla de Contenidos

- [Configuración Inicial](#configuración-inicial)
- [Scripts Disponibles](#scripts-disponibles)
- [Backtesting de Estrategias](#backtesting-de-estrategias)
- [Ejecutar Estrategias Reales](#ejecutar-estrategias-reales)
- [Monitoreo Continuo](#monitoreo-continuo)
- [Ver Portfolio](#ver-portfolio)
- [Estructura de Archivos](#estructura-de-archivos)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Configuración Inicial

### 1. Credenciales de Alpaca

Las credenciales ya están configuradas en todos los scripts:
- **API Key**: `PKNO6ZAQMZJZEDK7ZEXPL7WXLX`
- **Secret Key**: `FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK`
- **Modo**: Paper Trading (dinero ficticio)

### 2. Instalar Dependencias

```bash
pip install alpaca-py pandas pandas-ta matplotlib numpy
```

O si tienes problemas con permisos:
```bash
pip install --break-system-packages alpaca-py pandas pandas-ta matplotlib numpy
```

### 3. Verificar Conexión

```bash
python3 test_connection.py
```

Deberías ver:
```
✅ Conexión exitosa con Paper Trading!
Cuenta: PA3GAZPWAGAY
Efectivo: $99,999.94
```

---

## 🎯 Script Maestro (Recomendado)

### `trading_master.py` - Todo en Uno ⭐

**Un solo script para todo: backtesting, ejecución real y monitoreo**

```bash
# Ver menú de ayuda
python3 trading_master.py

# Backtesting de TODAS las estrategias (default)
python3 trading_master.py --backtest all

# Backtesting de una estrategia específica
python3 trading_master.py --backtest 5  # MACD

# Ejecutar TODAS las estrategias en modo real (usa la mejor señal)
python3 trading_master.py --execute all

# Ejecutar estrategia específica en modo real
python3 trading_master.py --execute 5  # MACD

# Monitoreo continuo (todas las estrategias, cada hora)
python3 trading_master.py --monitor all 1

# Monitoreo continuo (estrategia específica, cada 2 horas)
python3 trading_master.py --monitor 5 2
```

**Estrategias disponibles:**
- `1` - EMA Crossover (9/21)
- `2` - EMA Crossover (5/13)
- `3` - SMA Crossover (9/21)
- `4` - SMA Crossover (5/13)
- `5` - MACD (12/26/9) ⭐ Mejor rendimiento
- `6` - Triple SMA (5/13/21)
- `all` - Todas las estrategias (default)

---

## 📊 Scripts Disponibles (Alternativos)

### Backtesting (Simulación)

#### 1. Probar Todas las Estrategias
```bash
python3 backtesting_estrategias.py
```

**Qué hace:**
- Prueba 7 estrategias diferentes
- Compara rentabilidad y win rate
- Genera gráficos en `backtest_results/`
- Muestra cuál es la mejor estrategia

**Estrategias incluidas:**
- **EMA Crossover** (9/21, 5/13, 12/26)
- **SMA Crossover** (9/21, 5/13, 12/26) ⭐ **Nuevo**
- **EMA + RSI**
- **SMA + RSI** ⭐ **Nuevo**
- **EMA + Volumen**
- **SMA + Volumen** ⭐ **Nuevo**
- **Triple SMA** (5/13/21) ⭐ **Nuevo**
- **MACD** (12/26/9) ⭐ **Mejor según backtesting**
- **Bollinger Bands**

**Resultados esperados:**
```
🏆 MEJOR ESTRATEGIA: MACD (12/26/9)
💰 Retorno: +X.XX%
📊 Win Rate: 44.4%
```

#### 2. Backtesting Básico (EMA Crossover)
```bash
python3 backtesting_btc.py
```

#### 3. Backtesting Day Trading
```bash
python3 backtesting_day_trading.py
```

---

### Ejecutar Estrategias Reales

#### 1. Mejor Estrategia (MACD)
```bash
python3 ejecutar_mejor_estrategia.py
```

Ejecuta la estrategia MACD que tuvo mejor rendimiento en backtesting.

#### 1b. Estrategia SMA Crossover
```bash
python3 ejecutar_estrategia_sma.py
```

Ejecuta estrategia usando Simple Moving Average (SMA) en lugar de EMA.

#### 2. Todas las Estrategias
```bash
python3 ejecutar_todas_estrategias.py
```

Analiza todas las estrategias y ejecuta la que tenga señal más fuerte.

#### 3. Day Trading
```bash
# Ejecutar una vez
python3 day_trading_btc.py

# Monitoreo continuo cada 5 minutos
python3 day_trading_btc.py --monitor 5
```

#### 4. Estrategia con Monitoreo
```bash
# Ejecutar una vez
python3 estrategia_real.py

# Monitoreo continuo cada hora
python3 estrategia_real.py --monitor 1
```

---

## 🔬 Backtesting de Estrategias

### Cómo Funciona

El backtesting simula operaciones históricas para evaluar la rentabilidad de una estrategia **sin riesgo**.

### Ejecutar Backtesting

```bash
python3 backtesting_estrategias.py
```

### Interpretar Resultados

**Métricas importantes:**
- **Retorno %**: Ganancia o pérdida porcentual
- **Win Rate**: Porcentaje de trades ganadores
- **Total Trades**: Número de operaciones
- **Ganancia promedio**: Ganancia promedio por trade

**Ejemplo de salida:**
```
🏆 MEJOR ESTRATEGIA: MACD (12/26/9)
💰 Retorno: +0.15% ($+1.51)
📊 Win Rate: 44.4%
📈 Trades: 36 (18 compras, 18 ventas)
💵 Ganancia promedio: $+0.08
✅ Trades ganadores: 8
❌ Trades perdedores: 10
```

### Gráficos Generados

Los gráficos se guardan automáticamente en `backtest_results/`:
- `backtest_EMA_Crossover_(9_21).png`
- `backtest_MACD_*.png`
- `backtest_day_trading.png`
- etc.

---

## 🚀 Ejecutar Estrategias Reales

### ⚠️ Importante

Las estrategias reales **ejecutan operaciones reales** en Paper Trading que actualizan tu portfolio en Alpaca.

### Opciones Disponibles

#### Opción 1: Mejor Estrategia (Recomendado)
```bash
python3 ejecutar_mejor_estrategia.py
```

Usa la estrategia MACD que tuvo mejor rendimiento.

#### Opción 2: Múltiples Estrategias
```bash
python3 ejecutar_todas_estrategias.py
```

Analiza todas y ejecuta la mejor señal.

#### Opción 3: Operación Manual
```bash
python3 ejecutar_operacion_real.py
```

Para hacer operaciones manuales de prueba.

### Qué Esperar

Cuando hay una señal:
```
🟢 SEÑAL DE COMPRA (MACD)
   MACD cruzó por encima de la señal
   Comprando 0.000114 BTC/USD (~$10.00)...

✅ ORDEN EJECUTADA:
   ID: abc123-def456-...
   Estado: OrderStatus.FILLED

💰 Tu portfolio en Alpaca se actualizará en unos segundos!
```

---

## 🔄 Monitoreo Continuo

### Configurar Monitoreo Automático

#### Monitoreo Cada Hora
```bash
python3 estrategia_real.py --monitor 1
```

#### Monitoreo Day Trading (Cada 5 minutos)
```bash
python3 day_trading_btc.py --monitor 5
```

### Detener Monitoreo

Presiona `Ctrl+C` en la terminal.

### Qué Hace el Monitoreo

1. Obtiene datos del mercado
2. Calcula señales de las estrategias
3. Ejecuta operaciones automáticamente si hay señal
4. Espera el intervalo configurado
5. Repite el proceso

---

## 💰 Ver Portfolio

### Ver Estado Actual
```bash
python3 ver_wallet.py
```

Muestra:
- Efectivo disponible
- Patrimonio total
- Posiciones abiertas
- Órdenes recientes

### Ver Operaciones Rápidas
```bash
python3 operar_btc.py
```

---

## 📁 Estructura de Archivos

```
alpaca-py/
├── README.md                          # Este archivo
├── backtest_results/                  # Gráficos de backtesting
│   ├── README.md
│   ├── backtest_EMA_Crossover_*.png
│   ├── backtest_MACD_*.png
│   └── backtest_day_trading.png
│
├── # Scripts de Backtesting
├── backtesting_estrategias.py        # Probar todas las estrategias
├── backtesting_btc.py                # Backtesting básico
├── backtesting_day_trading.py         # Backtesting day trading
│
├── # Scripts de Ejecución Real
├── ejecutar_mejor_estrategia.py       # Ejecutar MACD (mejor estrategia)
├── ejecutar_todas_estrategias.py     # Ejecutar todas las estrategias
├── ejecutar_operacion_real.py         # Operación manual
├── estrategia_real.py                 # Estrategia con monitoreo
├── day_trading_btc.py                # Day trading
│
├── # Utilidades
├── ver_wallet.py                      # Ver portfolio
├── operar_btc.py                      # Operaciones rápidas
├── test_connection.py                 # Verificar conexión
│
└── examples/
    └── crypto/
        ├── crypto-trading-basic.ipynb      # Notebook básico
        └── crypto-btc-usd-swing-trade.ipynb # Notebook swing trade
```

---

## 🎯 Flujo de Trabajo Recomendado

### 1. Probar Estrategias (Backtesting)
```bash
python3 backtesting_estrategias.py
```

### 2. Revisar Resultados
- Ver qué estrategia tiene mejor win rate
- Revisar gráficos en `backtest_results/`
- Analizar métricas de rentabilidad

### 3. Ejecutar Mejor Estrategia
```bash
python3 ejecutar_mejor_estrategia.py
```

### 4. Configurar Monitoreo (Opcional)
```bash
python3 estrategia_real.py --monitor 1
```

### 5. Monitorear Portfolio
```bash
python3 ver_wallet.py
```

---

## ⚙️ Personalizar Estrategias

### Modificar Parámetros

Edita los scripts y cambia:

```python
# En backtesting_estrategias.py o ejecutar_mejor_estrategia.py

SYMBOL = "BTC/USD"        # Cambiar a ETH/USD, SOL/USD, etc.
EMA_SHORT = 9             # Períodos EMA corta
EMA_LONG = 21             # Períodos EMA larga
MIN_ORDER_VALUE = 10.0    # Mínimo $10 (requerido por Alpaca)
DAYS_BACK = 30            # Días de datos históricos
```

### Crear Nueva Estrategia

1. Edita `backtesting_estrategias.py`
2. Agrega una nueva función:

```python
def mi_estrategia_personal(df):
    """Mi estrategia personalizada"""
    df = df.copy()
    # Tu lógica aquí
    df['buy_signal'] = ...  # Condiciones de compra
    df['sell_signal'] = ...  # Condiciones de venta
    return df, "Mi Estrategia Personal"
```

3. Agrégala a la lista de estrategias
4. Ejecuta backtesting para probarla

---

## 🐛 Troubleshooting

### Error: "unauthorized" o 401

**Problema**: Las credenciales no funcionan.

**Solución**:
1. Ve a https://app.alpaca.markets/paper/dashboard/overview
2. Regenera tus API keys
3. Actualiza las credenciales en los scripts:
   ```python
   API_KEY = "tu_nueva_key"
   SECRET_KEY = "tu_nuevo_secret"
   ```

### Error: "cost basis must be >= minimal amount of order 10"

**Problema**: La orden es menor a $10.

**Solución**: El script ya calcula automáticamente el mínimo. Si persiste, verifica que `MIN_ORDER_VALUE = 10.0`.

### Error: "ModuleNotFoundError"

**Problema**: Faltan dependencias.

**Solución**:
```bash
pip install --break-system-packages alpaca-py pandas pandas-ta matplotlib numpy
```

### Las imágenes no se generan

**Problema**: Error al generar gráficos.

**Solución**:
- Verifica que matplotlib esté instalado
- Los gráficos se guardan en `backtest_results/`
- Revisa permisos de escritura

### El portfolio no se actualiza

**Problema**: Las operaciones no aparecen en Alpaca.

**Solución**:
1. Verifica que las órdenes se ejecutaron: `python3 ver_wallet.py`
2. Refresca el dashboard de Alpaca
3. Espera unos segundos (puede haber delay)

---

## 📊 Estrategias Disponibles

### 1. EMA Crossover
- **Descripción**: Compra cuando EMA corta cruza por encima de EMA larga
- **Parámetros**: EMA_SHORT, EMA_LONG
- **Win Rate**: ~20-30%

### 1b. SMA Crossover ⭐ **NUEVO**
- **Descripción**: Compra cuando SMA corta cruza por encima de SMA larga
- **Parámetros**: SMA_SHORT, SMA_LONG
- **Win Rate**: ~21-28%
- **Diferencia con EMA**: SMA da igual peso a todos los períodos, EMA da más peso a precios recientes

### 2. MACD (Mejor Rendimiento)
- **Descripción**: Usa indicador MACD para señales
- **Parámetros**: Fast=12, Slow=26, Signal=9
- **Win Rate**: ~44.4% ⭐

### 3. EMA + RSI
- **Descripción**: EMA Crossover filtrado por RSI
- **Parámetros**: EMA + RSI (30/70)
- **Win Rate**: ~27%

### 4. Bollinger Bands
- **Descripción**: Compra en banda inferior, vende en superior
- **Parámetros**: Length=20, Std=2
- **Win Rate**: Variable

### 5. EMA + Volumen
- **Descripción**: EMA Crossover con confirmación de volumen
- **Parámetros**: EMA + Volumen threshold
- **Win Rate**: Variable

### 5b. SMA + Volumen ⭐ **NUEVO**
- **Descripción**: SMA Crossover con confirmación de volumen
- **Parámetros**: SMA + Volumen threshold
- **Win Rate**: ~40%

### 6. Triple SMA ⭐ **NUEVO**
- **Descripción**: Usa 3 SMAs (rápida, media, lenta) para confirmación
- **Parámetros**: SMA_FAST, SMA_MEDIUM, SMA_SLOW
- **Win Rate**: ~50% (muy conservadora, pocos trades)

---

## 📝 Notas Importantes

1. **Paper Trading**: Todas las operaciones son con dinero ficticio
2. **Mínimo de Orden**: $10 USD requerido por Alpaca
3. **Backtesting vs Real**:
   - Backtesting = Simulación (no actualiza portfolio)
   - Estrategias reales = Operaciones reales (actualiza portfolio)
4. **Monitoreo Continuo**: Usa con cuidado, puede ejecutar muchas operaciones
5. **Credenciales**: Nunca compartas tus API keys

---

## 🎓 Recursos Adicionales

- **Documentación Alpaca**: https://docs.alpaca.markets/
- **Dashboard Paper Trading**: https://app.alpaca.markets/paper/dashboard/overview
- **Notebooks de Ejemplo**: `examples/crypto/`

---

## ✅ Checklist de Uso

- [ ] Credenciales configuradas
- [ ] Dependencias instaladas
- [ ] Conexión verificada (`test_connection.py`)
- [ ] Backtesting ejecutado para encontrar mejor estrategia
- [ ] Estrategia real probada una vez
- [ ] Monitoreo configurado (opcional)
- [ ] Portfolio monitoreado regularmente

---

## 🆘 Soporte

Si tienes problemas:
1. Revisa la sección [Troubleshooting](#troubleshooting)
2. Verifica las credenciales
3. Ejecuta `test_connection.py` para diagnosticar
4. Revisa los logs de error en la terminal

---

**¡Buena suerte con tu trading! 🚀**
