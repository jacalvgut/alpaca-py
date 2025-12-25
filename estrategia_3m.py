#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de funciones auxiliares para la Estrategia 3M
Implementa: Rangos, Zonas S&D, Pullbacks, Fractales, Stages, Validaciones
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Optional

def calcular_body_close(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el body close (cierre del cuerpo de la vela)
    Body = abs(close - open)
    Body close = close (si vela alcista) o open (si vela bajista)
    """
    df = df.copy()
    df['body'] = abs(df['close'] - df['open'])
    df['body_close'] = df['close']  # Usamos close como referencia principal
    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']
    return df

def identificar_rangos(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """
    Identifica rangos high/low basados en swing points
    Un rango high es el máximo swing high reciente
    Un rango low es el mínimo swing low reciente
    """
    df = df.copy()
    
    # Inicializar columnas
    df['range_high'] = np.nan
    df['range_low'] = np.nan
    df['current_range_high'] = np.nan
    df['current_range_low'] = np.nan
    
    # Obtener swing highs y lows si existen
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        return df
    
    swing_highs = df[df['swing_high'] == True]
    swing_lows = df[df['swing_low'] == True]
    
    current_high = None
    current_low = None
    
    for i in range(len(df)):
        # Actualizar range high si hay un nuevo swing high
        if df.iloc[i]['swing_high']:
            current_high = df.iloc[i]['swing_high_price']
        
        # Actualizar range low si hay un nuevo swing low
        if df.iloc[i]['swing_low']:
            current_low = df.iloc[i]['swing_low_price']
        
        if current_high is not None:
            df.iloc[i, df.columns.get_loc('current_range_high')] = current_high
        if current_low is not None:
            df.iloc[i, df.columns.get_loc('current_range_low')] = current_low
    
    return df

def detectar_breaks_estructura(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta breaks up/down de estructura basados en body close
    Break up: body close por encima del range high actual
    Break down: body close por debajo del range low actual
    """
    df = df.copy()
    
    if 'current_range_high' not in df.columns or 'current_range_low' not in df.columns:
        df = identificar_rangos(df)
    
    df['break_up'] = False
    df['break_down'] = False
    
    for i in range(1, len(df)):
        current_body_close = df.iloc[i]['body_close']
        prev_range_high = df.iloc[i-1]['current_range_high']
        prev_range_low = df.iloc[i-1]['current_range_low']
        
        # Break up: body close por encima del range high
        if pd.notna(prev_range_high) and current_body_close > prev_range_high:
            df.iloc[i, df.columns.get_loc('break_up')] = True
        
        # Break down: body close por debajo del range low
        if pd.notna(prev_range_low) and current_body_close < prev_range_low:
            df.iloc[i, df.columns.get_loc('break_down')] = True
    
    return df

def identificar_pullbacks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifica pullbacks alcistas y bajistas
    Pullback alcista: vela body close por debajo de la anterior
    Pullback bajista: vela body close por encima de la anterior
    """
    df = df.copy()
    
    df['pullback_alcista'] = False
    df['pullback_bajista'] = False
    
    for i in range(1, len(df)):
        current_body_close = df.iloc[i]['body_close']
        prev_body_close = df.iloc[i-1]['body_close']
        
        # Pullback alcista: body close por debajo de la anterior
        if current_body_close < prev_body_close:
            df.iloc[i, df.columns.get_loc('pullback_alcista')] = True
        
        # Pullback bajista: body close por encima de la anterior
        if current_body_close > prev_body_close:
            df.iloc[i, df.columns.get_loc('pullback_bajista')] = True
    
    return df

def identificar_zonas_sd(df: pd.DataFrame, lookback_zones: int = 50) -> pd.DataFrame:
    """
    Identifica zonas de oferta (Supply) y demanda (Demand) - VERSIÓN ULTRA OPTIMIZADA
    
    Zona de Demanda: Área que queda atrás cuando el precio sube
    Zona de Oferta: Área que queda atrás cuando el precio baja
    """
    df = df.copy()
    df_len = len(df)
    
    # Inicializar columnas con arrays numpy (mucho más rápido)
    df['zona_demanda_high'] = np.nan
    df['zona_demanda_low'] = np.nan
    df['zona_oferta_high'] = np.nan
    df['zona_oferta_low'] = np.nan
    df['zona_demanda_activa'] = False
    df['zona_oferta_activa'] = False
    
    # Obtener arrays numpy para acceso rápido
    high_array = df['high'].values
    low_array = df['low'].values
    close_array = df['close'].values
    
    zonas_demanda = []  # Lista de zonas no mitigadas
    zonas_oferta = []
    
    # Identificar movimientos significativos
    min_move_pct = 0.02  # Movimiento mínimo del 2% para considerar zona
    window_size = 5  # Ventana para detectar movimiento
    
    # Optimización: solo mantener las últimas N zonas no mitigadas
    max_zonas_activas = 20
    
    # Pre-calcular posiciones de columnas una sola vez
    col_demanda_high = df.columns.get_loc('zona_demanda_high')
    col_demanda_low = df.columns.get_loc('zona_demanda_low')
    col_demanda_activa = df.columns.get_loc('zona_demanda_activa')
    col_oferta_high = df.columns.get_loc('zona_oferta_high')
    col_oferta_low = df.columns.get_loc('zona_oferta_low')
    col_oferta_activa = df.columns.get_loc('zona_oferta_activa')
    
    # Preparar arrays para asignación masiva al final
    demanda_high_array = np.full(df_len, np.nan, dtype=float)
    demanda_low_array = np.full(df_len, np.nan, dtype=float)
    demanda_activa_array = np.zeros(df_len, dtype=bool)
    oferta_high_array = np.full(df_len, np.nan, dtype=float)
    oferta_low_array = np.full(df_len, np.nan, dtype=float)
    oferta_activa_array = np.zeros(df_len, dtype=bool)
    
    # Optimización: usar rolling window de numpy para detectar movimientos
    for i in range(window_size, df_len - window_size):
        current_price = close_array[i]
        
        # Detectar inicio de movimiento alcista (zona de demanda) - OPTIMIZADO
        future_window_high = np.max(high_array[i:i+window_size])
        current_low = low_array[i]
        move_pct = (future_window_high - current_low) / current_low if current_low > 0 else 0
        
        if move_pct > min_move_pct:
            # Crear zona de demanda desde la vela actual o anterior
            zone_start = max(0, i - 1)
            zone_high = max(np.max(high_array[zone_start:i+1]), high_array[i])
            zone_low = min(np.min(low_array[zone_start:i+1]), low_array[i])
            
            # Verificar si hay zona similar (optimizado: solo verificar últimas zonas)
            zona_similar = False
            # Solo verificar últimas 5 zonas para evitar bucle largo
            check_zones = zonas_demanda[-5:] if len(zonas_demanda) > 5 else zonas_demanda
            for zona_existente in check_zones:
                if (abs(zona_existente['high'] - zone_high) / zone_high < 0.01 and
                    abs(zona_existente['low'] - zone_low) / zone_low < 0.01):
                    zona_similar = True
                    break
            
            if not zona_similar:
                zonas_demanda.append({
                    'start_idx': zone_start,
                    'high': zone_high,
                    'low': zone_low,
                    'mitigated': False
                })
        
        # Detectar inicio de movimiento bajista (zona de oferta) - OPTIMIZADO
        future_window_low = np.min(low_array[i:i+window_size])
        current_high = high_array[i]
        move_pct = (current_high - future_window_low) / current_high if current_high > 0 else 0
        
        if move_pct > min_move_pct:
            # Crear zona de oferta desde la vela actual o anterior
            zone_start = max(0, i - 1)
            zone_high = max(np.max(high_array[zone_start:i+1]), high_array[i])
            zone_low = min(np.min(low_array[zone_start:i+1]), low_array[i])
            
            # Verificar si hay zona similar (optimizado: solo verificar últimas zonas)
            zona_similar = False
            # Solo verificar últimas 5 zonas para evitar bucle largo
            check_zones = zonas_oferta[-5:] if len(zonas_oferta) > 5 else zonas_oferta
            for zona_existente in check_zones:
                if (abs(zona_existente['high'] - zone_high) / zone_high < 0.01 and
                    abs(zona_existente['low'] - zone_low) / zone_low < 0.01):
                    zona_similar = True
                    break
            
            if not zona_similar:
                zonas_oferta.append({
                    'start_idx': zone_start,
                    'high': zone_high,
                    'low': zone_low,
                    'mitigated': False
                })
        
        # Verificar si zonas fueron mitigadas (optimizado: solo verificar zonas no mitigadas)
        for zona in zonas_demanda:
            if not zona['mitigated'] and current_price < zona['low']:
                zona['mitigated'] = True
        
        for zona in zonas_oferta:
            if not zona['mitigated'] and current_price > zona['high']:
                zona['mitigated'] = True
        
        # Obtener zonas no mitigadas (optimizado: usar list comprehension una sola vez)
        zonas_demanda_no_mitigadas = [z for z in zonas_demanda if not z['mitigated']]
        zonas_oferta_no_mitigadas = [z for z in zonas_oferta if not z['mitigated']]
        
        # Limitar a últimas N zonas
        if len(zonas_demanda_no_mitigadas) > max_zonas_activas:
            zonas_demanda_no_mitigadas = zonas_demanda_no_mitigadas[-max_zonas_activas:]
            # Actualizar lista original para mantener solo las relevantes
            zonas_demanda = [z for z in zonas_demanda if z in zonas_demanda_no_mitigadas or z['mitigated']]
        
        if len(zonas_oferta_no_mitigadas) > max_zonas_activas:
            zonas_oferta_no_mitigadas = zonas_oferta_no_mitigadas[-max_zonas_activas:]
            # Actualizar lista original para mantener solo las relevantes
            zonas_oferta = [z for z in zonas_oferta if z in zonas_oferta_no_mitigadas or z['mitigated']]
        
        # Asignar zona activa más reciente no mitigada a arrays (no a DataFrame todavía)
        if zonas_demanda_no_mitigadas:
            zona_activa = zonas_demanda_no_mitigadas[-1]  # La más reciente
            demanda_high_array[i] = zona_activa['high']
            demanda_low_array[i] = zona_activa['low']
            demanda_activa_array[i] = True
        
        if zonas_oferta_no_mitigadas:
            zona_activa = zonas_oferta_no_mitigadas[-1]  # La más reciente
            oferta_high_array[i] = zona_activa['high']
            oferta_low_array[i] = zona_activa['low']
            oferta_activa_array[i] = True
    
    # Asignación masiva al final (MUCHO más rápido que iloc dentro del bucle)
    df['zona_demanda_high'] = demanda_high_array
    df['zona_demanda_low'] = demanda_low_array
    df['zona_demanda_activa'] = demanda_activa_array
    df['zona_oferta_high'] = oferta_high_array
    df['zona_oferta_low'] = oferta_low_array
    df['zona_oferta_activa'] = oferta_activa_array
    
    return df

def identificar_fractales(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """
    Identifica fractales (puntos de giro)
    Fractal alcista: high mayor que los 'period' highs anteriores y siguientes
    Fractal bajista: low menor que los 'period' lows anteriores y siguientes
    """
    df = df.copy()
    
    df['fractal_alcista'] = False
    df['fractal_bajista'] = False
    
    for i in range(period, len(df) - period):
        current_high = df.iloc[i]['high']
        current_low = df.iloc[i]['low']
        
        # Fractal alcista
        left_highs = df.iloc[i-period:i]['high']
        right_highs = df.iloc[i+1:i+period+1]['high']
        
        if len(left_highs) > 0 and len(right_highs) > 0:
            if current_high > left_highs.max() and current_high > right_highs.max():
                df.iloc[i, df.columns.get_loc('fractal_alcista')] = True
        
        # Fractal bajista
        left_lows = df.iloc[i-period:i]['low']
        right_lows = df.iloc[i+1:i+period+1]['low']
        
        if len(left_lows) > 0 and len(right_lows) > 0:
            if current_low < left_lows.min() and current_low < right_lows.min():
                df.iloc[i, df.columns.get_loc('fractal_bajista')] = True
    
    return df

def calcular_sma(df: pd.DataFrame, periods: List[int] = [20, 50, 200]) -> pd.DataFrame:
    """
    Calcula Simple Moving Averages (SMA)
    """
    df = df.copy()
    
    for period in periods:
        df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
    
    return df

def validar_sma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida si los SMA están ordenados correctamente para bias alcista/bajista
    Bias alcista: precio > SMA20 > SMA50 > SMA200
    Bias bajista: precio < SMA20 < SMA50 < SMA200
    """
    df = df.copy()
    
    df['sma_valid_alcista'] = False
    df['sma_valid_bajista'] = False
    
    for i in range(200, len(df)):  # Necesitamos al menos 200 períodos para SMA200
        close = df.iloc[i]['close']
        sma20 = df.iloc[i]['sma_20']
        sma50 = df.iloc[i]['sma_50']
        sma200 = df.iloc[i]['sma_200']
        
        if pd.notna(sma20) and pd.notna(sma50) and pd.notna(sma200):
            # Validación alcista: precio y SMA ordenados
            if close > sma20 and sma20 > sma50 and sma50 > sma200:
                df.iloc[i, df.columns.get_loc('sma_valid_alcista')] = True
            
            # Validación bajista: precio y SMA ordenados inversamente
            if close < sma20 and sma20 < sma50 and sma50 < sma200:
                df.iloc[i, df.columns.get_loc('sma_valid_bajista')] = True
    
    return df

def identificar_stage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifica el Stage del mercado basándose en estructura y breaks
    Stage 2: Tendencia alcista (breaks up con pullbacks que no rompen estructura)
    Stage 4: Tendencia bajista (breaks down con pullbacks que no rompen estructura)
    Stage 1/3: Acumulación/Distribución (rango lateral)
    """
    df = df.copy()
    
    df['stage'] = 'neutral'
    df['stage_2'] = False  # Alcista
    df['stage_4'] = False  # Bajista
    
    breaks_up_count = 0
    breaks_down_count = 0
    last_break_up_idx = None
    last_break_down_idx = None
    
    for i in range(len(df)):
        if df.iloc[i]['break_up']:
            breaks_up_count += 1
            last_break_up_idx = i
        
        if df.iloc[i]['break_down']:
            breaks_down_count += 1
            last_break_down_idx = i
        
        # Determinar stage basado en estructura reciente
        if 'market_structure' in df.columns:
            structure = df.iloc[i]['market_structure']
            
            if structure == 'bullish' and breaks_up_count > breaks_down_count:
                df.iloc[i, df.columns.get_loc('stage')] = 'stage_2'
                df.iloc[i, df.columns.get_loc('stage_2')] = True
            elif structure == 'bearish' and breaks_down_count > breaks_up_count:
                df.iloc[i, df.columns.get_loc('stage')] = 'stage_4'
                df.iloc[i, df.columns.get_loc('stage_4')] = True
            else:
                df.iloc[i, df.columns.get_loc('stage')] = 'neutral'
    
    return df

def validacion_tipo_1(df: pd.DataFrame, idx: int) -> bool:
    """
    Validación Tipo 1: Confirmación inmediata después de tocar zona
    Requiere que después de tocar la zona, el precio confirme con movimiento en dirección esperada
    OPTIMIZADA: usa acceso directo a valores
    """
    if idx >= len(df) - 1:  # Necesitamos al menos idx+1 disponible
        return False
    
    # Acceso optimizado: obtener fila una sola vez
    row = df.iloc[idx]
    next_row = df.iloc[idx + 1]
    
    # Verificar si hay zona de demanda activa
    if row.get('zona_demanda_activa', False):
        zona_low = row.get('zona_demanda_low', np.nan)
        zona_high = row.get('zona_demanda_high', np.nan)
        current_price = row['close']
        
        # Precio debe estar dentro o cerca de la zona
        if pd.notna(zona_low) and pd.notna(zona_high):
            if zona_low <= current_price <= zona_high:
                # Verificar confirmación: siguiente vela debe subir
                next_close = next_row['close']
                if next_close > current_price:
                    return True
    
    # Verificar si hay zona de oferta activa
    if row.get('zona_oferta_activa', False):
        zona_low = row.get('zona_oferta_low', np.nan)
        zona_high = row.get('zona_oferta_high', np.nan)
        current_price = row['close']
        
        if pd.notna(zona_low) and pd.notna(zona_high):
            if zona_low <= current_price <= zona_high:
                # Verificar confirmación: siguiente vela debe bajar
                next_close = next_row['close']
                if next_close < current_price:
                    return True
    
    return False

def validacion_tipo_2(df: pd.DataFrame, idx: int) -> bool:
    """
    Validación Tipo 2: Confirmación con pullback y reacción
    Requiere pullback seguido de reacción en dirección esperada
    OPTIMIZADA: usa acceso directo a valores
    """
    if idx < 1 or idx >= len(df):
        return False
    
    # Acceso optimizado: obtener filas una sola vez
    row = df.iloc[idx]
    prev_row = df.iloc[idx - 1]
    
    # Verificar zona de demanda
    if row.get('zona_demanda_activa', False):
        # Debe haber pullback alcista seguido de reacción alcista
        if prev_row.get('pullback_alcista', False) and row['close'] > prev_row['close']:
            return True
    
    # Verificar zona de oferta
    if row.get('zona_oferta_activa', False):
        # Debe haber pullback bajista seguido de reacción bajista
        if prev_row.get('pullback_bajista', False) and row['close'] < prev_row['close']:
            return True
    
    return False

def aplicar_estrategia_3m_completa(df: pd.DataFrame, mostrar_progreso: bool = True) -> pd.DataFrame:
    """
    Aplica todos los componentes de la estrategia 3M - VERSIÓN OPTIMIZADA
    """
    from mentfx_structure import calcular_mentfx_structure
    import sys
    
    if mostrar_progreso:
        print("    🔄 Calculando estructura MentFX...", end=" ", flush=True)
    
    # Paso 1: Calcular estructura MentFX
    df = calcular_mentfx_structure(df, lookback_left=5, lookback_right=5, generar_senales=False)
    
    if mostrar_progreso:
        print("✅")
        print("    🔄 Calculando body close y rangos...", end=" ", flush=True)
    
    # Paso 2: Calcular body close
    df = calcular_body_close(df)
    
    # Paso 3: Identificar rangos
    df = identificar_rangos(df)
    
    # Paso 4: Detectar breaks de estructura
    df = detectar_breaks_estructura(df)
    
    # Paso 5: Identificar pullbacks
    df = identificar_pullbacks(df)
    
    if mostrar_progreso:
        print("✅")
        print("    🔄 Identificando zonas S&D (esto puede tardar)...", end=" ", flush=True)
    
    # Paso 6: Identificar zonas S&D (la parte más lenta)
    df = identificar_zonas_sd(df)
    
    if mostrar_progreso:
        print("✅")
        print("    🔄 Identificando fractales y calculando SMA...", end=" ", flush=True)
    
    # Paso 7: Identificar fractales
    df = identificar_fractales(df)
    
    # Paso 8: Calcular SMA
    df = calcular_sma(df, [20, 50, 200])
    
    # Paso 9: Validar SMA
    df = validar_sma(df)
    
    # Paso 10: Identificar stages
    df = identificar_stage(df)
    
    if mostrar_progreso:
        print("✅")
        print("    🔄 Generando señales de trading...", end=" ", flush=True)
    
    # Paso 11: Generar señales basadas en criterios de la estrategia
    df['buy_signal'] = False
    df['sell_signal'] = False
    
    # Optimización: usar arrays numpy para acceso más rápido
    total_rows = len(df)
    start_idx = 200  # Necesitamos SMA200
    
    if total_rows <= start_idx:
        if mostrar_progreso:
            print("⚠️ No hay suficientes datos (se necesitan al menos 200 períodos)")
        return df
    
    # Pre-calcular arrays para acceso rápido
    try:
        market_structure = df['market_structure'].values
        stage_2 = df.get('stage_2', pd.Series([False] * len(df))).fillna(False).values
        stage_4 = df.get('stage_4', pd.Series([False] * len(df))).fillna(False).values
        zona_demanda_activa = df.get('zona_demanda_activa', pd.Series([False] * len(df))).fillna(False).values
        zona_oferta_activa = df.get('zona_oferta_activa', pd.Series([False] * len(df))).fillna(False).values
        sma_valid_alcista = df.get('sma_valid_alcista', pd.Series([False] * len(df))).fillna(False).values
        sma_valid_bajista = df.get('sma_valid_bajista', pd.Series([False] * len(df))).fillna(False).values
        close_prices = df['close'].values
        
        # Pre-calcular arrays para validaciones (evitar accesos repetidos a df.iloc)
        zona_demanda_low = df.get('zona_demanda_low', pd.Series([np.nan] * len(df))).values
        zona_demanda_high = df.get('zona_demanda_high', pd.Series([np.nan] * len(df))).values
        zona_oferta_low = df.get('zona_oferta_low', pd.Series([np.nan] * len(df))).values
        zona_oferta_high = df.get('zona_oferta_high', pd.Series([np.nan] * len(df))).values
        pullback_alcista = df.get('pullback_alcista', pd.Series([False] * len(df))).fillna(False).values
        pullback_bajista = df.get('pullback_bajista', pd.Series([False] * len(df))).fillna(False).values
    except Exception as e:
        if mostrar_progreso:
            print(f"⚠️ Error al pre-calcular arrays: {e}")
        return df
    
    # Progreso cada 500 filas o cada 5%
    progress_interval = max(500, (total_rows - start_idx) // 20)
    buy_signals_idx = []
    sell_signals_idx = []
    
    # Calcular el rango real del bucle
    loop_end = total_rows - 1  # -1 para evitar problemas con idx+1
    total_iterations = loop_end - start_idx
    
    try:
        for i in range(start_idx, loop_end):
            # Mostrar progreso más frecuentemente cerca del final
            if mostrar_progreso:
                iteration_num = i - start_idx
                if (iteration_num % progress_interval == 0) or (iteration_num >= total_iterations - 100):
                    progress_pct = (iteration_num / total_iterations) * 100
                    print(f"\r    🔄 Generando señales de trading... {progress_pct:.1f}%", end="", flush=True)
            
            # Criterios para LONG (compra) - acceso rápido a arrays
            bias_alcista = (market_structure[i] == 'bullish' or stage_2[i])
            zona_demanda = zona_demanda_activa[i]
            sma_valid = sma_valid_alcista[i]
            
            # Solo verificar validación si los otros criterios se cumplen
            if bias_alcista and zona_demanda and sma_valid:
                # Validación optimizada usando arrays
                validacion = False
                
                # Validación Tipo 1: verificar siguiente vela
                if i < total_rows - 1:
                    if (pd.notna(zona_demanda_low[i]) and pd.notna(zona_demanda_high[i]) and
                        zona_demanda_low[i] <= close_prices[i] <= zona_demanda_high[i] and
                        close_prices[i + 1] > close_prices[i]):
                        validacion = True
                
                # Validación Tipo 2: verificar pullback anterior
                if not validacion and i >= 1:
                    if (pullback_alcista[i - 1] and close_prices[i] > close_prices[i - 1]):
                        validacion = True
                
                if validacion:
                    buy_signals_idx.append(i)
            
            # Criterios para SHORT (venta) - acceso rápido a arrays
            bias_bajista = (market_structure[i] == 'bearish' or stage_4[i])
            zona_oferta = zona_oferta_activa[i]
            sma_valid_b = sma_valid_bajista[i]
            
            # Solo verificar validación si los otros criterios se cumplen
            if bias_bajista and zona_oferta and sma_valid_b:
                # Validación optimizada usando arrays
                validacion_bajista = False
                
                # Validación Tipo 1: verificar siguiente vela
                if i < total_rows - 1:
                    if (pd.notna(zona_oferta_low[i]) and pd.notna(zona_oferta_high[i]) and
                        zona_oferta_low[i] <= close_prices[i] <= zona_oferta_high[i] and
                        close_prices[i + 1] < close_prices[i]):
                        validacion_bajista = True
                
                # Validación Tipo 2: verificar pullback anterior
                if not validacion_bajista and i >= 1:
                    if (pullback_bajista[i - 1] and close_prices[i] < close_prices[i - 1]):
                        validacion_bajista = True
                
                if validacion_bajista:
                    sell_signals_idx.append(i)
        
        # Mensaje de confirmación de que el bucle terminó
        if mostrar_progreso:
            print(f"\r    🔄 Generando señales de trading... 100.0% (bucle completado)", end="", flush=True)
            print()  # Nueva línea
        
        # Asignar señales usando método optimizado con arrays numpy
        if mostrar_progreso:
            num_signals = len(buy_signals_idx) + len(sell_signals_idx)
            print(f"    🔄 Asignando {num_signals} señales (DataFrame: {len(df)} filas)...", end=" ", flush=True)
            sys.stdout.flush()
        
        df_len = len(df)
        
        # Método optimizado: usar arrays numpy para asignación masiva (mucho más rápido)
        try:
            # Crear arrays booleanos inicializados en False
            buy_signals_array = np.zeros(df_len, dtype=bool)
            sell_signals_array = np.zeros(df_len, dtype=bool)
            
            # Validar y marcar señales de compra directamente en el array (OPTIMIZADO)
            if buy_signals_idx:
                # Convertir a numpy array primero (más rápido que list comprehension)
                buy_arr = np.array(buy_signals_idx, dtype=np.int64)
                # Filtrar índices válidos usando operaciones numpy vectorizadas (muy rápido)
                valid_buy = buy_arr[(buy_arr >= 0) & (buy_arr < df_len)]
                if len(valid_buy) > 0:
                    buy_signals_array[valid_buy] = True
            
            # Validar y marcar señales de venta directamente en el array (OPTIMIZADO)
            if sell_signals_idx:
                # Convertir a numpy array primero (más rápido que list comprehension)
                sell_arr = np.array(sell_signals_idx, dtype=np.int64)
                # Filtrar índices válidos usando operaciones numpy vectorizadas (muy rápido)
                valid_sell = sell_arr[(sell_arr >= 0) & (sell_arr < df_len)]
                if len(valid_sell) > 0:
                    sell_signals_array[valid_sell] = True
            
            # Asignar arrays completos al DataFrame de una sola vez (muy rápido)
            df['buy_signal'] = buy_signals_array
            df['sell_signal'] = sell_signals_array
            
            if mostrar_progreso:
                print(" ✅")
                print(f"       Señales: {len(buy_signals_idx)} compras, {len(sell_signals_idx)} ventas")
        
        except Exception as e:
            if mostrar_progreso:
                print(f"\n⚠️ Error: {str(e)[:60]}")
                print(f"    Usando método alternativo...", end=" ", flush=True)
            
            # Método alternativo: asignación directa con iloc (más lento pero seguro)
            try:
                # Obtener posición de columnas una sola vez
                buy_col_pos = df.columns.get_loc('buy_signal')
                sell_col_pos = df.columns.get_loc('sell_signal')
                
                if buy_signals_idx:
                    valid_buy = [idx for idx in buy_signals_idx if 0 <= idx < df_len]
                    # Asignar todos los índices de una vez usando iloc con lista
                    if valid_buy:
                        df.iloc[valid_buy, buy_col_pos] = True
                
                if sell_signals_idx:
                    valid_sell = [idx for idx in sell_signals_idx if 0 <= idx < df_len]
                    # Asignar todos los índices de una vez usando iloc con lista
                    if valid_sell:
                        df.iloc[valid_sell, sell_col_pos] = True
                
                if mostrar_progreso:
                    print("✅")
            except Exception as final_error:
                if mostrar_progreso:
                    print(f"❌ Error: {final_error}")
                # Asegurar que las columnas existan
                if 'buy_signal' not in df.columns:
                    df['buy_signal'] = False
                if 'sell_signal' not in df.columns:
                    df['sell_signal'] = False
    
    except Exception as e:
        if mostrar_progreso:
            print(f"\n⚠️ Error en generación de señales: {e}")
            import traceback
            traceback.print_exc()
    
    return df

