#!/usr/bin/env python3
"""
Implementación del indicador MentFX Structure
Identifica swing highs, swing lows y estructuras de mercado
Compatible con datos de Alpaca
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional

def identificar_swing_points(df: pd.DataFrame, 
                            lookback_left: int = 5, 
                            lookback_right: int = 5,
                            use_high_low: bool = True) -> pd.DataFrame:
    """
    Identifica swing highs y swing lows en los datos de precios.
    
    Un swing high es un punto máximo local donde:
    - El high es mayor que los 'lookback_left' highs anteriores
    - El high es mayor que los 'lookback_right' highs siguientes
    
    Un swing low es un punto mínimo local donde:
    - El low es menor que los 'lookback_left' lows anteriores
    - El low es menor que los 'lookback_right' lows siguientes
    
    Args:
        df: DataFrame con columnas 'high', 'low', 'close' (o solo 'close')
        lookback_left: Número de períodos a la izquierda para confirmar swing
        lookback_right: Número de períodos a la derecha para confirmar swing
        use_high_low: Si True, usa high/low. Si False, usa solo close
    
    Returns:
        DataFrame con columnas 'swing_high', 'swing_low', 'swing_high_price', 'swing_low_price'
    """
    df = df.copy()
    
    # Si no hay high/low, usar close para ambos
    if 'high' not in df.columns or 'low' not in df.columns:
        df['high'] = df['close']
        df['low'] = df['close']
    
    # Inicializar columnas
    df['swing_high'] = False
    df['swing_low'] = False
    df['swing_high_price'] = np.nan
    df['swing_low_price'] = np.nan
    
    # Identificar swing highs
    for i in range(lookback_left, len(df) - lookback_right):
        current_high = df.iloc[i]['high']
        
        # Verificar que es mayor que los períodos anteriores
        left_highs = df.iloc[i - lookback_left:i]['high']
        # Verificar que es mayor que los períodos siguientes
        right_highs = df.iloc[i + 1:i + lookback_right + 1]['high']
        
        if len(left_highs) > 0 and len(right_highs) > 0:
            if current_high > left_highs.max() and current_high > right_highs.max():
                df.iloc[i, df.columns.get_loc('swing_high')] = True
                df.iloc[i, df.columns.get_loc('swing_high_price')] = current_high
    
    # Identificar swing lows
    for i in range(lookback_left, len(df) - lookback_right):
        current_low = df.iloc[i]['low']
        
        # Verificar que es menor que los períodos anteriores
        left_lows = df.iloc[i - lookback_left:i]['low']
        # Verificar que es menor que los períodos siguientes
        right_lows = df.iloc[i + 1:i + lookback_right + 1]['low']
        
        if len(left_lows) > 0 and len(right_lows) > 0:
            if current_low < left_lows.min() and current_low < right_lows.min():
                df.iloc[i, df.columns.get_loc('swing_low')] = True
                df.iloc[i, df.columns.get_loc('swing_low_price')] = current_low
    
    return df

def identificar_estructura_mercado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifica la estructura del mercado basándose en swing highs y lows.
    
    Estructura Alcista (Bullish):
    - Higher Highs (HH): Swing highs cada vez más altos
    - Higher Lows (HL): Swing lows cada vez más altos
    
    Estructura Bajista (Bearish):
    - Lower Highs (LH): Swing highs cada vez más bajos
    - Lower Lows (LL): Swing lows cada vez más bajos
    
    Args:
        df: DataFrame con swing highs y lows identificados
    
    Returns:
        DataFrame con columnas adicionales:
        - 'market_structure': 'bullish', 'bearish', 'neutral'
        - 'structure_break': True cuando cambia la estructura
        - 'last_swing_high', 'last_swing_low'
    """
    df = df.copy()
    
    # Inicializar columnas
    df['market_structure'] = 'neutral'
    df['structure_break'] = False
    df['last_swing_high'] = np.nan
    df['last_swing_low'] = np.nan
    df['higher_high'] = False
    df['lower_low'] = False
    df['higher_low'] = False
    df['lower_high'] = False
    
    # Obtener todos los swing points
    swing_highs = df[df['swing_high'] == True].copy()
    swing_lows = df[df['swing_low'] == True].copy()
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return df
    
    # Analizar swing highs
    swing_high_prices = swing_highs['swing_high_price'].values
    swing_high_indices = swing_highs.index
    
    for i in range(1, len(swing_high_prices)):
        current_price = swing_high_prices[i]
        previous_price = swing_high_prices[i - 1]
        current_idx = swing_high_indices[i]
        
        if current_price > previous_price:
            df.loc[current_idx, 'higher_high'] = True
        elif current_price < previous_price:
            df.loc[current_idx, 'lower_high'] = True
    
    # Analizar swing lows
    swing_low_prices = swing_lows['swing_low_price'].values
    swing_low_indices = swing_lows.index
    
    for i in range(1, len(swing_low_prices)):
        current_price = swing_low_prices[i]
        previous_price = swing_low_prices[i - 1]
        current_idx = swing_low_indices[i]
        
        if current_price > previous_price:
            df.loc[current_idx, 'higher_low'] = True
        elif current_price < previous_price:
            df.loc[current_idx, 'lower_low'] = True
    
    # Determinar estructura de mercado
    last_structure = 'neutral'
    
    for idx in df.index:
        # Obtener últimos swing points hasta este punto
        swing_highs_until = swing_highs[swing_highs.index <= idx]
        swing_lows_until = swing_lows[swing_lows.index <= idx]
        
        if len(swing_highs_until) >= 2 and len(swing_lows_until) >= 2:
            # Últimos dos swing highs
            last_two_highs = swing_highs_until['swing_high_price'].tail(2).values
            # Últimos dos swing lows
            last_two_lows = swing_lows_until['swing_low_price'].tail(2).values
            
            # Determinar estructura
            if len(last_two_highs) == 2 and len(last_two_lows) == 2:
                hh = last_two_highs[1] > last_two_highs[0]  # Higher High
                hl = last_two_lows[1] > last_two_lows[0]   # Higher Low
                lh = last_two_highs[1] < last_two_highs[0]  # Lower High
                ll = last_two_lows[1] < last_two_lows[0]    # Lower Low
                
                if (hh and hl) or (hh and not ll):
                    structure = 'bullish'
                elif (lh and ll) or (ll and not hh):
                    structure = 'bearish'
                else:
                    structure = last_structure
                
                # Detectar cambio de estructura
                if structure != last_structure and last_structure != 'neutral':
                    df.loc[idx, 'structure_break'] = True
                
                df.loc[idx, 'market_structure'] = structure
                last_structure = structure
                
                # Guardar últimos swing points
                if len(swing_highs_until) > 0:
                    df.loc[idx, 'last_swing_high'] = swing_highs_until['swing_high_price'].iloc[-1]
                if len(swing_lows_until) > 0:
                    df.loc[idx, 'last_swing_low'] = swing_lows_until['swing_low_price'].iloc[-1]
    
    return df

def generar_senales_estructura(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera señales de compra/venta basadas en la estructura del mercado.
    
    Señales:
    - COMPRA: Estructura alcista + Higher High confirmado
    - VENTA: Estructura bajista + Lower Low confirmado
    - También puede usar breakouts de estructura
    
    Args:
        df: DataFrame con estructura de mercado identificada
    
    Returns:
        DataFrame con columnas 'buy_signal' y 'sell_signal'
    """
    df = df.copy()
    
    df['buy_signal'] = False
    df['sell_signal'] = False
    
    # Señal de compra: Estructura alcista + Higher High
    df['buy_signal'] = (
        (df['market_structure'] == 'bullish') &
        (df['higher_high'] == True)
    )
    
    # Señal de venta: Estructura bajista + Lower Low
    df['sell_signal'] = (
        (df['market_structure'] == 'bearish') &
        (df['lower_low'] == True)
    )
    
    # Alternativa: Señales en cambios de estructura
    # Compra cuando cambia de bearish a bullish
    df.loc[df['structure_break'] & (df['market_structure'] == 'bullish'), 'buy_signal'] = True
    
    # Venta cuando cambia de bullish a bearish
    df.loc[df['structure_break'] & (df['market_structure'] == 'bearish'), 'sell_signal'] = True
    
    return df

def filtrar_estructura_sin_cruces(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra los swing points para crear líneas de estructura que NO se crucen.
    
    En el indicador MentFX Structure, las líneas de estructura de máximos (swing highs)
    siempre deben estar por encima de las líneas de estructura de mínimos (swing lows).
    Esta función elimina swing points que causarían cruces en las líneas escalonadas.
    
    La lógica es construir las líneas de estructura de manera incremental, verificando
    que cada nuevo swing point mantenga la regla: estructura de highs > estructura de lows.
    
    Args:
        df: DataFrame con swing highs y lows identificados
    
    Returns:
        DataFrame con columnas adicionales 'structure_high' y 'structure_low' 
        que contienen solo los swing points válidos para las líneas de estructura
    """
    df = df.copy()
    
    # Inicializar columnas para estructura filtrada
    df['structure_high'] = False
    df['structure_low'] = False
    df['structure_high_price'] = np.nan
    df['structure_low_price'] = np.nan
    
    # Obtener todos los swing points ordenados por timestamp
    swing_highs = df[df['swing_high'] == True].copy().sort_index()
    swing_lows = df[df['swing_low'] == True].copy().sort_index()
    
    if swing_highs.empty or swing_lows.empty:
        # Si no hay suficientes swing points, usar los originales
        df['structure_high'] = df['swing_high']
        df['structure_low'] = df['swing_low']
        df['structure_high_price'] = df['swing_high_price']
        df['structure_low_price'] = df['swing_low_price']
        return df
    
    # Combinar y ordenar todos los swing points por timestamp
    all_swings = []
    for idx, row in swing_highs.iterrows():
        all_swings.append({
            'timestamp': idx,
            'type': 'high',
            'price': row['swing_high_price']
        })
    for idx, row in swing_lows.iterrows():
        all_swings.append({
            'timestamp': idx,
            'type': 'low',
            'price': row['swing_low_price']
        })
    
    # Ordenar por timestamp
    all_swings.sort(key=lambda x: x['timestamp'])
    
    if len(all_swings) < 2:
        # Usar originales si hay muy pocos puntos
        df['structure_high'] = df['swing_high']
        df['structure_low'] = df['swing_low']
        df['structure_high_price'] = df['swing_high_price']
        df['structure_low_price'] = df['swing_low_price']
        return df
    
    # Construir líneas de estructura incrementalmente
    # Mantener los niveles actuales de las líneas de estructura
    final_highs = []
    final_lows = []
    current_high_level = None  # Nivel actual de la línea de estructura de highs
    current_low_level = None   # Nivel actual de la línea de estructura de lows
    
    # Almacenar los últimos swing points aceptados para verificar cruces
    last_high_swing = None
    last_low_swing = None
    
    for swing in all_swings:
        if swing['type'] == 'high':
            # Para un swing high:
            # 1. Debe ser mayor que el nivel actual de la línea de lows (si existe)
            # 2. Verificar cruces con la línea de lows extendida horizontalmente
            
            # Si hay un nivel de lows actual y este high no es mayor, omitirlo
            if current_low_level is not None and swing['price'] <= current_low_level:
                continue
            
            # Verificar si este high causaría un cruce con la línea de lows extendida
            # La línea de lows se extiende horizontalmente desde el último swing low hasta este punto
            if last_low_swing is not None and swing['timestamp'] > last_low_swing['timestamp']:
                # Si el precio de este high es menor o igual al último low, causaría cruce
                if swing['price'] <= last_low_swing['price']:
                    continue
            
            # Aceptar este swing high
            final_highs.append(swing)
            current_high_level = swing['price']
            last_high_swing = swing
            
        else:  # swing['type'] == 'low'
            # Para un swing low:
            # 1. Debe ser menor que el nivel actual de la línea de highs (si existe)
            # 2. Verificar cruces con la línea de highs extendida horizontalmente
            
            # Si hay un nivel de highs actual y este low no es menor, omitirlo
            if current_high_level is not None and swing['price'] >= current_high_level:
                continue
            
            # Verificar si este low causaría un cruce con la línea de highs extendida
            # La línea de highs se extiende horizontalmente desde el último swing high hasta este punto
            if last_high_swing is not None and swing['timestamp'] > last_high_swing['timestamp']:
                # Si el precio de este low es mayor o igual al último high, causaría cruce
                if swing['price'] >= last_high_swing['price']:
                    continue
            
            # Aceptar este swing low
            final_lows.append(swing)
            current_low_level = swing['price']
            last_low_swing = swing
    
    # Asignar los swing points filtrados al DataFrame
    for swing in final_highs:
        df.loc[swing['timestamp'], 'structure_high'] = True
        df.loc[swing['timestamp'], 'structure_high_price'] = swing['price']
    
    for swing in final_lows:
        df.loc[swing['timestamp'], 'structure_low'] = True
        df.loc[swing['timestamp'], 'structure_low_price'] = swing['price']
    
    return df

def calcular_mentfx_structure(df: pd.DataFrame, 
                             lookback_left: int = 5,
                             lookback_right: int = 5,
                             generar_senales: bool = True) -> pd.DataFrame:
    """
    Función principal que calcula el indicador MentFX Structure completo.
    
    Esta es una implementación/replicación del indicador MentFX Structure original,
    que es un indicador de pago. La implementación aquí intenta replicar su funcionalidad
    basándose en documentación pública y definiciones comunes de estructura de mercado.
    
    NOTA: El indicador original MentFX Structure es propiedad de MentFX y requiere licencia.
    Esta implementación es una interpretación educativa/recreativa basada en conceptos
    públicos de análisis técnico y estructura de mercado.
    
    Args:
        df: DataFrame con columnas 'high', 'low', 'close' (o solo 'close')
        lookback_left: Períodos a la izquierda para confirmar swing
        lookback_right: Períodos a la derecha para confirmar swing
        generar_senales: Si True, genera señales de compra/venta
    
    Returns:
        DataFrame con todas las columnas del indicador
    """
    # Paso 1: Identificar swing points
    df = identificar_swing_points(df, lookback_left, lookback_right)
    
    # Paso 1.5: Filtrar swing points para evitar cruces en las líneas de estructura
    df = filtrar_estructura_sin_cruces(df)
    
    # Paso 2: Identificar estructura de mercado (usar swing points originales para análisis)
    df = identificar_estructura_mercado(df)
    
    # Paso 3: Generar señales (opcional)
    if generar_senales:
        df = generar_senales_estructura(df)
    
    return df

