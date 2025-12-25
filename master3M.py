#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Estrategia 3M - Backtesting completo
Estrategia basada en: Estructura MentFX, Rangos, Zonas S&D, Pullbacks, Fractales, Stages, SMA

CORRECCIONES IMPLEMENTADAS:
- Variante Conservadora: Corregida para generar MENOS trades (validación Tipo 2 + múltiples confirmaciones)
- Variante Agresiva: Mejorada para capturar entradas tempranas (solo estructura básica)
"""

import os
import sys
# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sys
import time
import pandas as pd
# Configurar matplotlib para usar backend sin GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Importar módulos de la estrategia 3M
from estrategia_3m import aplicar_estrategia_3m_completa
from mentfx_structure import calcular_mentfx_structure
from backtesting_engine_3m import BacktestingEngine3M

# ==================== CONFIGURACIÓN ====================
SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0
MIN_ORDER_VALUE = 10.0
CAPITAL_PER_TRADE_PCT = 0.95

# ==================== ESTRATEGIAS 3M ====================

def estrategia_3m_completa(df):
    """
    Estrategia 3M Completa
    Incluye todos los componentes: Estructura, Rangos, Zonas S&D, Pullbacks, Fractales, Stages, SMA
    """
    df = df.copy()
    df = aplicar_estrategia_3m_completa(df, mostrar_progreso=True)
    return df, "Estrategia 3M Completa"

def estrategia_3m_conservadora(df):
    """
    Estrategia 3M Conservadora - CORREGIDA
    Requiere validaciones más estrictas: solo validación Tipo 2, múltiples confirmaciones
    
    CORRECCIÓN: La versión anterior tenía un error lógico que generaba MÁS señales.
    Ahora filtra correctamente para obtener señales de alta calidad solamente.
    """
    df = df.copy()
    df = aplicar_estrategia_3m_completa(df, mostrar_progreso=True)
    
    # Filtrar señales: solo validación Tipo 2 (más estricta)
    from estrategia_3m import validacion_tipo_2
    import numpy as np
    
    df_len = len(df)
    
    # Obtener arrays numpy para acceso rápido
    buy_signal_array = df.get('buy_signal', pd.Series([False] * df_len)).fillna(False).values
    sell_signal_array = df.get('sell_signal', pd.Series([False] * df_len)).fillna(False).values
    
    # Crear arrays para señales filtradas
    buy_signal_filtered = np.zeros(df_len, dtype=bool)
    sell_signal_filtered = np.zeros(df_len, dtype=bool)
    
    # Obtener índices de señales activas
    buy_indices = np.where(buy_signal_array)[0]
    sell_indices = np.where(sell_signal_array)[0]
    
    # Verificar validación Tipo 2 solo para señales activas (más estricta)
    # También requerir múltiples confirmaciones: estructura + stage + SMA
    market_structure = df['market_structure'].values
    stage_2 = df.get('stage_2', pd.Series([False] * df_len)).fillna(False).values
    stage_4 = df.get('stage_4', pd.Series([False] * df_len)).fillna(False).values
    sma_valid_alcista = df.get('sma_valid_alcista', pd.Series([False] * df_len)).fillna(False).values
    sma_valid_bajista = df.get('sma_valid_bajista', pd.Series([False] * df_len)).fillna(False).values
    
    for idx in buy_indices:
        # Requiere: validación Tipo 2 + estructura + stage + SMA
        if (validacion_tipo_2(df, idx) and 
            (market_structure[idx] == 'bullish' or stage_2[idx]) and
            sma_valid_alcista[idx]):
            buy_signal_filtered[idx] = True
    
    for idx in sell_indices:
        # Requiere: validación Tipo 2 + estructura + stage + SMA
        if (validacion_tipo_2(df, idx) and 
            (market_structure[idx] == 'bearish' or stage_4[idx]) and
            sma_valid_bajista[idx]):
            sell_signal_filtered[idx] = True
    
    # Asignar señales filtradas de vuelta al DataFrame
    df['buy_signal'] = buy_signal_filtered
    df['sell_signal'] = sell_signal_filtered
    
    return df, "Estrategia 3M Conservadora (Corregida)"

def estrategia_3m_agresiva(df):
    """
    Estrategia 3M Agresiva - MEJORADA
    Permite entradas tempranas: validación Tipo 1, menos confirmaciones requeridas
    
    MEJORA: Permite señales con solo estructura básica (no requiere stage ni SMA estricto)
    para capturar entradas más tempranas (CHoCH en lugar de solo BOS).
    """
    df = df.copy()
    df = aplicar_estrategia_3m_completa(df, mostrar_progreso=True)
    
    # Filtrar: solo validación Tipo 1 (más rápida) + estructura básica (menos estricta)
    from estrategia_3m import validacion_tipo_1
    import numpy as np
    
    df_len = len(df)
    
    # Obtener arrays numpy para acceso rápido
    buy_signal_array = df.get('buy_signal', pd.Series([False] * df_len)).fillna(False).values
    sell_signal_array = df.get('sell_signal', pd.Series([False] * df_len)).fillna(False).values
    
    # Crear arrays para señales filtradas
    buy_signal_filtered = np.zeros(df_len, dtype=bool)
    sell_signal_filtered = np.zeros(df_len, dtype=bool)
    
    # Obtener índices de señales activas
    buy_indices = np.where(buy_signal_array)[0]
    sell_indices = np.where(sell_signal_array)[0]
    
    # Para agresiva: solo requiere validación Tipo 1 + estructura básica (no stage ni SMA estricto)
    market_structure = df['market_structure'].values
    
    for idx in buy_indices:
        # Solo requiere: validación Tipo 1 + estructura alcista básica
        if validacion_tipo_1(df, idx) and market_structure[idx] == 'bullish':
            buy_signal_filtered[idx] = True
    
    for idx in sell_indices:
        # Solo requiere: validación Tipo 1 + estructura bajista básica
        if validacion_tipo_1(df, idx) and market_structure[idx] == 'bearish':
            sell_signal_filtered[idx] = True
    
    # Asignar señales filtradas de vuelta al DataFrame
    df['buy_signal'] = buy_signal_filtered
    df['sell_signal'] = sell_signal_filtered
    
    return df, "Estrategia 3M Agresiva (Mejorada)"

# Diccionario de estrategias
ESTRATEGIAS_3M = {
    '1': lambda d: estrategia_3m_completa(d),
    '2': lambda d: estrategia_3m_conservadora(d),
    '3': lambda d: estrategia_3m_agresiva(d),
    'all': 'all'
}

# ==================== FUNCIONES AUXILIARES ====================

def obtener_datos(client, symbol, days=30, timeframe="1Hour"):
    """Obtiene datos históricos"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    if timeframe == "1Hour":
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        expected_bars = days * 24
        limit = min(10000, max(2000, int(expected_bars * 1.2)))
    elif timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
        expected_bars = days * 24 * 12
        limit = min(10000, max(2000, int(expected_bars * 1.2)))
    else:
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        limit = min(10000, max(2000, int(days * 24 * 1.2)))

    request = CryptoBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=tf,
        start=start_time,
        limit=limit
    )

    bars = client.get_crypto_bars(request)
    df = bars.df

    if isinstance(df.index, pd.MultiIndex):
        df = df.loc[symbol]

    return df.sort_index()

def ejecutar_backtest(df, initial_capital=100000, min_order_value=10.0, capital_per_trade_pct=0.95):
    """
    Ejecuta backtest usando el motor profesional sin sesgos estadísticos.
    
    NOTA: capital_per_trade_pct se ignora ahora, se usa risk_per_trade_pct en su lugar.
    """
    # Crear motor de backtesting profesional
    engine = BacktestingEngine3M(
        initial_capital=initial_capital,
        maker_fee=0.001,  # 0.1% fee maker
        taker_fee=0.001,  # 0.1% fee taker (market orders)
        slippage_bps=5.0,  # 5 basis points (0.05%)
        risk_per_trade_pct=1.0,  # 1% de riesgo por trade (reemplaza capital_per_trade_pct)
        use_structural_stop=True,
        structural_stop_pct=2.0,  # Stop loss a 2% desde entrada
        max_bars_in_trade=None,  # Sin límite temporal por defecto
        signal_shift_bars=1,  # Desplazar señales 1 barra (elimina look-ahead bias)
        min_order_value=min_order_value
    )
    
    # Ejecutar backtest
    results = engine.run_backtest(df)
    
    # Convertir trades a formato compatible con código existente
    trades_compat = []
    for trade in results['trades']:
        if trade.exit_timestamp:
            trades_compat.append({
                'timestamp': trade.entry_timestamp,
                'type': 'BUY',
                'price': trade.entry_price,
                'qty': trade.quantity,
                'entry_price': trade.entry_price,
                'trade_amount': trade.quantity * trade.entry_price + trade.entry_commission
            })
            trades_compat.append({
                'timestamp': trade.exit_timestamp,
                'type': 'SELL',
                'price': trade.exit_price,
                'qty': trade.quantity,
                'exit_price': trade.exit_price,
                'entry_price': trade.entry_price,
                'profit': trade.pnl,
                'profit_pct': trade.pnl_pct
            })
    
    # Convertir equity_history a portfolio_values
    portfolio_values = [
        {
            'timestamp': e['timestamp'],
            'portfolio_value': e['equity'],
            'price': e['price']
        }
        for e in results['equity_history']
    ]
    
    return {
        'initial_capital': results['initial_capital'],
        'final_value': results['final_equity'],
        'total_return': results['total_return'],
        'total_return_pct': results['total_return_pct'],
        'trades': trades_compat,
        'trades_originales': results['trades'],  # Trades originales del motor para visualización
        'portfolio_values': portfolio_values,
        'metrics': results['metrics'],  # Métricas avanzadas
        'audit_results': results['audit_results']  # Resultados de auditoría
    }

def analizar_rentabilidad(results, strategy_name):
    """
    Analiza la rentabilidad de los resultados usando métricas profesionales.
    Si hay métricas avanzadas disponibles, las usa; si no, calcula las básicas.
    """
    # Si hay métricas avanzadas del nuevo motor, usarlas
    if 'metrics' in results and results['metrics']:
        metrics = results['metrics']
        return {
            'strategy': strategy_name,
            'total_return': metrics['total_return'],
            'total_return_pct': metrics['total_return_pct'],
            'total_trades': metrics['total_trades'],
            'winning_trades': metrics['winning_trades'],
            'losing_trades': metrics['losing_trades'],
            'win_rate': metrics['win_rate'],
            'avg_profit': metrics['avg_profit'],
            'avg_loss': metrics['avg_loss'],
            'profit_factor': metrics['profit_factor'],
            'max_drawdown': metrics['max_drawdown'],
            'expectancy': metrics.get('expectancy', 0.0)
        }
    
    # Fallback: cálculo básico (compatibilidad con código antiguo)
    trades = results['trades']
    
    if not trades:
        return {
            'strategy': strategy_name,
            'total_return': 0,
            'total_return_pct': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'expectancy': 0.0
        }
    
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    
    if not sell_trades:
        return {
            'strategy': strategy_name,
            'total_return': results['total_return'],
            'total_return_pct': results['total_return_pct'],
            'total_trades': len(sell_trades),
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'expectancy': 0.0
        }
    
    profits = [t.get('profit', 0) for t in sell_trades]
    winning_trades = [p for p in profits if p > 0]
    losing_trades = [p for p in profits if p < 0]
    
    win_rate = (len(winning_trades) / len(sell_trades)) * 100 if sell_trades else 0
    avg_profit = sum(winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = abs(sum(losing_trades) / len(losing_trades)) if losing_trades else 0
    
    # CORREGIDO: Profit Factor = suma de beneficios / suma absoluta de pérdidas
    total_profits = sum(winning_trades)
    total_losses = abs(sum(losing_trades))
    profit_factor = (total_profits / total_losses) if total_losses > 0 else (float('inf') if total_profits > 0 else 0)
    
    # Calcular máximo drawdown
    portfolio_values = [pv['portfolio_value'] for pv in results['portfolio_values']]
    if portfolio_values:
        peak = portfolio_values[0]
        max_drawdown = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    else:
        max_drawdown = 0
    
    # Calcular expectancy
    win_rate_decimal = len(winning_trades) / len(sell_trades) if sell_trades else 0
    loss_rate_decimal = len(losing_trades) / len(sell_trades) if sell_trades else 0
    expectancy = (win_rate_decimal * avg_profit) - (loss_rate_decimal * avg_loss)
    
    return {
        'strategy': strategy_name,
        'total_return': results['total_return'],
        'total_return_pct': results['total_return_pct'],
        'total_trades': len(sell_trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'expectancy': expectancy
    }

def dibujar_estructura_3m(ax, df, mostrar_texto=True, tamaño_mensual=False, rango_visible=None):
    """Dibuja la estructura 3M completa: swing points, zonas S&D, SMA, breaks"""
    # Dibujar estructura MentFX básica (swing points)
    if 'swing_high' in df.columns and 'swing_low' in df.columns:
        swing_highs = df[df['swing_high'] == True].copy()
        swing_lows = df[df['swing_low'] == True].copy()
        
        if rango_visible is not None:
            min_idx, max_idx = rango_visible
            swing_highs = swing_highs[(swing_highs.index >= min_idx) & (swing_highs.index <= max_idx)]
            swing_lows = swing_lows[(swing_lows.index >= min_idx) & (swing_lows.index <= max_idx)]
        
        linewidth = 3 if tamaño_mensual else 2
        marker_size = 200 if tamaño_mensual else 150
        
        if len(swing_highs) > 1:
            swing_highs_sorted = swing_highs.sort_index()
            ax.plot(swing_highs_sorted.index, swing_highs_sorted['swing_high_price'],
                    color='red', linestyle='--', linewidth=linewidth, alpha=0.7, 
                    label='Estructura Highs', zorder=3)
        
        if len(swing_lows) > 1:
            swing_lows_sorted = swing_lows.sort_index()
            ax.plot(swing_lows_sorted.index, swing_lows_sorted['swing_low_price'],
                    color='blue', linestyle='--', linewidth=linewidth, alpha=0.7, 
                    label='Estructura Lows', zorder=3)
        
        if not swing_highs.empty:
            ax.scatter(swing_highs.index, swing_highs['swing_high_price'],
                       color='red', marker='v', s=marker_size, label='Swing High',
                       zorder=6, edgecolors='darkred', linewidths=2, alpha=0.9)
        
        if not swing_lows.empty:
            ax.scatter(swing_lows.index, swing_lows['swing_low_price'],
                       color='blue', marker='^', s=marker_size, label='Swing Low',
                       zorder=6, edgecolors='darkblue', linewidths=2, alpha=0.9)
    
    # Dibujar zonas S&D si existen
    if 'zona_demanda_activa' in df.columns:
        zonas_demanda = df[df['zona_demanda_activa'] == True]
        if not zonas_demanda.empty:
            zonas_unicas_demanda = {}
            for idx, row in zonas_demanda.iterrows():
                if pd.notna(row['zona_demanda_low']) and pd.notna(row['zona_demanda_high']):
                    zona_key = (round(row['zona_demanda_low'], 2), round(row['zona_demanda_high'], 2))
                    if zona_key not in zonas_unicas_demanda:
                        zonas_unicas_demanda[zona_key] = {
                            'low': row['zona_demanda_low'],
                            'high': row['zona_demanda_high']
                        }
            
            zonas_a_dibujar = list(zonas_unicas_demanda.values())[-5:]
            for i, zona in enumerate(zonas_a_dibujar):
                ax.axhspan(zona['low'], zona['high'], 
                          alpha=0.12, color='green', 
                          label='Zona Demanda' if i == 0 else '', zorder=1)
    
    if 'zona_oferta_activa' in df.columns:
        zonas_oferta = df[df['zona_oferta_activa'] == True]
        if not zonas_oferta.empty:
            zonas_unicas_oferta = {}
            for idx, row in zonas_oferta.iterrows():
                if pd.notna(row['zona_oferta_low']) and pd.notna(row['zona_oferta_high']):
                    zona_key = (round(row['zona_oferta_low'], 2), round(row['zona_oferta_high'], 2))
                    if zona_key not in zonas_unicas_oferta:
                        zonas_unicas_oferta[zona_key] = {
                            'low': row['zona_oferta_low'],
                            'high': row['zona_oferta_high']
                        }
            
            zonas_a_dibujar = list(zonas_unicas_oferta.values())[-5:]
            for i, zona in enumerate(zonas_a_dibujar):
                ax.axhspan(zona['low'], zona['high'], 
                          alpha=0.12, color='red', 
                          label='Zona Oferta' if i == 0 else '', zorder=1)
    
    # Dibujar SMA si existen
    if 'sma_20' in df.columns:
        ax.plot(df.index, df['sma_20'], label='SMA 20', linewidth=1, color='blue', alpha=0.6, linestyle='--')
    if 'sma_50' in df.columns:
        ax.plot(df.index, df['sma_50'], label='SMA 50', linewidth=1, color='orange', alpha=0.6, linestyle='--')
    if 'sma_200' in df.columns:
        ax.plot(df.index, df['sma_200'], label='SMA 200', linewidth=1.5, color='purple', alpha=0.7, linestyle='-')
    
    # Marcar breaks de estructura
    if 'break_up' in df.columns:
        breaks_up = df[df['break_up'] == True]
        if not breaks_up.empty:
            ax.scatter(breaks_up.index, breaks_up['close'], 
                      color='lime', marker='^', s=100, label='Break Up', 
                      zorder=8, alpha=0.8, edgecolors='green', linewidths=1)
    
    if 'break_down' in df.columns:
        breaks_down = df[df['break_down'] == True]
        if not breaks_down.empty:
            ax.scatter(breaks_down.index, breaks_down['close'], 
                      color='red', marker='v', s=100, label='Break Down', 
                      zorder=8, alpha=0.8, edgecolors='darkred', linewidths=1)
    
    # Mostrar estructura de mercado si está disponible
    if mostrar_texto and 'market_structure' in df.columns:
        latest_structure = df['market_structure'].iloc[-1]
        if latest_structure != 'neutral':
            color_structure = 'green' if latest_structure == 'bullish' else 'red'
            fontsize = 13 if tamaño_mensual else 11
            ax.text(0.98, 0.98, f'Estructura: {latest_structure.upper()}', 
                   transform=ax.transAxes, fontsize=fontsize, fontweight='bold',
                   color=color_structure, verticalalignment='top',
                   horizontalalignment='right', bbox=dict(boxstyle='round', 
                   facecolor='white', alpha=0.95, edgecolor=color_structure, linewidth=2.5))

def dibujar_candlesticks(ax, df, rango_visible=None):
    """
    Dibuja candlesticks (velas) normales en el gráfico.
    
    Args:
        ax: Axis de matplotlib
        df: DataFrame con OHLC data
        rango_visible: Tuple (min_idx, max_idx) para filtrar datos visibles
    """
    if rango_visible is not None:
        min_idx, max_idx = rango_visible
        df_plot = df[(df.index >= min_idx) & (df.index <= max_idx)].copy()
    else:
        df_plot = df.copy()
    
    if len(df_plot) == 0:
        return
    
    # Colores para velas alcistas y bajistas
    up_color = '#26a69a'  # Verde/azul para velas alcistas
    down_color = '#ef5350'  # Rojo para velas bajistas
    
    # Calcular ancho de vela basado en el número de barras visibles
    num_bars = len(df_plot)
    # Ancho en días (para fechas datetime)
    if num_bars > 0:
        # Calcular diferencia de tiempo promedio entre barras
        if len(df_plot.index) > 1:
            time_diff = (df_plot.index[-1] - df_plot.index[0]).total_seconds() / (num_bars - 1) if num_bars > 1 else 3600
            # Convertir a días y calcular ancho (aproximadamente 60% del espacio entre barras)
            bar_width_days = (time_diff / 86400) * 0.6
        else:
            bar_width_days = 0.01  # 1 hora por defecto
    else:
        bar_width_days = 0.01
    
    # Iterar sobre cada vela
    for idx, row in df_plot.iterrows():
        open_price = float(row['open'])
        close_price = float(row['close'])
        high_price = float(row['high'])
        low_price = float(row['low'])
        
        # Convertir timestamp a número para matplotlib
        if isinstance(idx, pd.Timestamp):
            x_pos = mdates.date2num(idx)
        else:
            x_pos = idx
        
        # Determinar color según si es alcista o bajista
        is_bullish = close_price >= open_price
        color = up_color if is_bullish else down_color
        
        # Calcular posición y tamaño del cuerpo
        body_bottom = min(open_price, close_price)
        body_top = max(open_price, close_price)
        body_height = body_top - body_bottom
        
        # Dibujar mecha superior (línea vertical desde el cuerpo hasta el high)
        if high_price > body_top:
            ax.plot([x_pos, x_pos], [body_top, high_price], 
                   color=color, linewidth=1.5, alpha=0.9, zorder=1, solid_capstyle='round')
        
        # Dibujar mecha inferior (línea vertical desde el cuerpo hasta el low)
        if low_price < body_bottom:
            ax.plot([x_pos, x_pos], [body_bottom, low_price], 
                   color=color, linewidth=1.5, alpha=0.9, zorder=1, solid_capstyle='round')
        
        # Dibujar cuerpo de la vela (rectángulo)
        if body_height > 0:
            # Cuerpo sólido con borde
            rect = Rectangle((x_pos - bar_width_days/2, body_bottom), 
                           bar_width_days, body_height, 
                           facecolor=color, edgecolor=color, 
                           alpha=0.95, linewidth=1.0, zorder=2)
            ax.add_patch(rect)
        else:
            # Vela doji (open == close) - línea horizontal más gruesa
            ax.plot([x_pos - bar_width_days/2, x_pos + bar_width_days/2], 
                   [close_price, close_price], 
                   color=color, linewidth=2.5, alpha=0.95, zorder=2)

def dibujar_estructura_mentfx_escalonada(ax, df, rango_visible=None):
    """
    Dibuja la estructura MentFX en formato escalonado con DOS líneas separadas:
    - Línea para swing highs (estructura de máximos)
    - Línea para swing lows (estructura de mínimos)
    
    Usa los swing points filtrados (structure_high/structure_low) para evitar cruces
    entre las líneas de estructura. Si no existen, usa los swing points originales.
    
    Args:
        ax: Axis de matplotlib
        df: DataFrame con swing highs y lows (o structure_high/structure_low si están disponibles)
        rango_visible: Tuple (min_idx, max_idx) para filtrar datos visibles
    """
    # Priorizar usar los swing points filtrados (structure_high/structure_low)
    # que evitan cruces, si están disponibles
    use_filtered = 'structure_high' in df.columns and 'structure_low' in df.columns
    
    if use_filtered:
        swing_highs_all = df[df['structure_high'] == True].copy().sort_index()
        swing_lows_all = df[df['structure_low'] == True].copy().sort_index()
        price_col_high = 'structure_high_price'
        price_col_low = 'structure_low_price'
    elif 'swing_high' in df.columns and 'swing_low' in df.columns:
        swing_highs_all = df[df['swing_high'] == True].copy().sort_index()
        swing_lows_all = df[df['swing_low'] == True].copy().sort_index()
        price_col_high = 'swing_high_price'
        price_col_low = 'swing_low_price'
    else:
        return
    
    if swing_highs_all.empty and swing_lows_all.empty:
        return
    
    # Determinar rango final para extender líneas
    if rango_visible is not None:
        min_idx, max_idx = rango_visible
    else:
        min_idx = df.index[0]
        max_idx = df.index[-1]
    
    # Colores para diferenciar las estructuras
    color_highs = '#1f77b4'  # Azul para estructura de máximos
    color_lows = '#d62728'   # Rojo para estructura de mínimos
    
    # ========== DIBUJAR ESTRUCTURA DE SWING HIGHS (MÁXIMOS) ==========
    if len(swing_highs_all) >= 2:
        swing_highs_list = []
        for idx, row in swing_highs_all.iterrows():
            swing_highs_list.append({
                'timestamp': idx,
                'price': row[price_col_high]
            })
        
        # Dibujar líneas escalonadas para swing highs
        for i in range(1, len(swing_highs_list)):
            prev_high = swing_highs_list[i-1]
            curr_high = swing_highs_list[i]
            
            # Línea horizontal desde el swing high anterior hasta el timestamp del actual
            ax.plot([prev_high['timestamp'], curr_high['timestamp']], 
                   [prev_high['price'], prev_high['price']], 
                   color=color_highs, linewidth=3, alpha=0.9, zorder=4, 
                   label='Estructura Highs' if i == 1 else '')
            
            # Línea vertical desde el precio anterior hasta el precio actual
            ax.plot([curr_high['timestamp'], curr_high['timestamp']], 
                   [prev_high['price'], curr_high['price']], 
                   color=color_highs, linewidth=3, alpha=0.9, zorder=4)
        
        # Extender línea horizontal final desde el último swing high hasta el final del rango
        if swing_highs_list:
            last_high = swing_highs_list[-1]
            # Solo extender si el último swing está antes del final del rango visible
            if last_high['timestamp'] < max_idx:
                ax.plot([last_high['timestamp'], max_idx], 
                       [last_high['price'], last_high['price']], 
                       color=color_highs, linewidth=3, alpha=0.9, zorder=4)
            
            # Extender línea inicial desde el inicio del rango hasta el primer swing high
            first_high = swing_highs_list[0]
            if first_high['timestamp'] > min_idx:
                ax.plot([min_idx, first_high['timestamp']], 
                       [first_high['price'], first_high['price']], 
                       color=color_highs, linewidth=3, alpha=0.9, zorder=4)
    
    # ========== DIBUJAR ESTRUCTURA DE SWING LOWS (MÍNIMOS) ==========
    if len(swing_lows_all) >= 2:
        swing_lows_list = []
        for idx, row in swing_lows_all.iterrows():
            swing_lows_list.append({
                'timestamp': idx,
                'price': row[price_col_low]
            })
        
        # Dibujar líneas escalonadas para swing lows
        for i in range(1, len(swing_lows_list)):
            prev_low = swing_lows_list[i-1]
            curr_low = swing_lows_list[i]
            
            # Línea horizontal desde el swing low anterior hasta el timestamp del actual
            ax.plot([prev_low['timestamp'], curr_low['timestamp']], 
                   [prev_low['price'], prev_low['price']], 
                   color=color_lows, linewidth=3, alpha=0.9, zorder=4, 
                   label='Estructura Lows' if i == 1 else '')
            
            # Línea vertical desde el precio anterior hasta el precio actual
            ax.plot([curr_low['timestamp'], curr_low['timestamp']], 
                   [prev_low['price'], curr_low['price']], 
                   color=color_lows, linewidth=3, alpha=0.9, zorder=4)
        
        # Extender línea horizontal final desde el último swing low hasta el final del rango
        if swing_lows_list:
            last_low = swing_lows_list[-1]
            # Solo extender si el último swing está antes del final del rango visible
            if last_low['timestamp'] < max_idx:
                ax.plot([last_low['timestamp'], max_idx], 
                       [last_low['price'], last_low['price']], 
                       color=color_lows, linewidth=3, alpha=0.9, zorder=4)
            
            # Extender línea inicial desde el inicio del rango hasta el primer swing low
            first_low = swing_lows_list[0]
            if first_low['timestamp'] > min_idx:
                ax.plot([min_idx, first_low['timestamp']], 
                       [first_low['price'], first_low['price']], 
                       color=color_lows, linewidth=3, alpha=0.9, zorder=4)

def dibujar_trade_info(ax, trade, df_trade_data):
    """
    Dibuja información del trade en el gráfico.
    
    Args:
        ax: Axis de matplotlib
        trade: Objeto Trade del backtesting engine
        df_trade_data: DataFrame con datos del período del trade
    """
    if not trade.exit_timestamp:
        return
    
    # Información del trade
    entry_price = trade.entry_price
    exit_price = trade.exit_price
    pnl = trade.pnl
    pnl_pct = trade.pnl_pct
    exit_reason = trade.exit_reason
    stop_loss = trade.stop_loss_price
    
    # Color según ganancia/pérdida
    color = 'green' if pnl >= 0 else 'red'
    
    # Marcar entrada
    ax.scatter([trade.entry_timestamp], [entry_price], 
              color='lime', marker='^', s=300, 
              edgecolors='darkgreen', linewidths=2, zorder=10,
              label='Entrada')
    
    # Marcar salida
    ax.scatter([trade.exit_timestamp], [exit_price], 
              color='orange', marker='v', s=300, 
              edgecolors='darkred', linewidths=2, zorder=10,
              label='Salida')
    
    # Línea conectando entrada y salida
    ax.plot([trade.entry_timestamp, trade.exit_timestamp], 
           [entry_price, exit_price], 
           color=color, linewidth=2, alpha=0.5, linestyle='--', zorder=9)
    
    # Dibujar stop loss si existe
    if stop_loss is not None:
        ax.axhline(y=stop_loss, color='red', linestyle=':', linewidth=2, 
                  alpha=0.7, label='Stop Loss', zorder=3)
    
    # Texto con información del trade
    info_text = f"PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)\n"
    info_text += f"Exit: {exit_reason}\n"
    if stop_loss:
        info_text += f"SL: ${stop_loss:.2f}"
    
    # Posicionar texto en la esquina superior izquierda
    ax.text(0.02, 0.98, info_text, 
           transform=ax.transAxes, fontsize=10, fontweight='bold',
           verticalalignment='top', horizontalalignment='left',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, 
                    edgecolor=color, linewidth=2))

def generar_pdf_consolidado(todas_las_estrategias, df_original):
    """Genera PDF consolidado con todas las estrategias"""
    try:
        os.makedirs('back_testresults3M', exist_ok=True)
        pdf_filename = os.path.join('back_testresults3M', 'strategy_3M_365_ALL_STRATEGIES.pdf')
        
        num_estrategias = len(todas_las_estrategias)
        df_original['month'] = df_original.index.to_period('M')
        months = sorted(df_original['month'].unique())[:12]
        
        print(f"  📄 Generando PDF consolidado: {pdf_filename}")
        
        # Colores para cada estrategia
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        
        with PdfPages(pdf_filename) as pdf:
            # ========== PÁGINA 1: COMPARACIÓN DE TODAS LAS ESTRATEGIAS ==========
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)
            
            # Gráfico 1: Precio BTC/USD con TODAS las señales de TODAS las estrategias superpuestas
            ax1.plot(df_original.index, df_original['close'],
                    label='Precio BTC/USD', linewidth=2, color='black', alpha=0.9, zorder=1)
            
            # Superponer TODAS las señales de compra y venta de TODAS las estrategias
            for idx, estrategia_data in enumerate(todas_las_estrategias):
                df_strategy = estrategia_data['df']
                strategy_name = estrategia_data['strategy_name']
                color = colors[idx % len(colors)]
                
                # Señales de compra
                buy_signals = df_strategy[df_strategy.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color=color, marker='^', s=100,
                               label=f'{strategy_name} - Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)
                
                # Señales de venta
                sell_signals = df_strategy[df_strategy.get('sell_signal', False)]
                if not sell_signals.empty:
                    ax1.scatter(sell_signals.index, sell_signals['close'],
                               color=color, marker='v', s=100,
                               label=f'{strategy_name} - Venta',
                               zorder=5, edgecolors='darkred', linewidths=0.8, alpha=0.7)
            
            ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
            ax1.set_title(f'{SYMBOL} - ESTRATEGIA 3M - COMPARACIÓN DE TODAS LAS ESTRATEGIAS (365 días)',
                         fontsize=16, fontweight='bold', pad=20)
            ax1.legend(loc='best', fontsize=9, framealpha=0.9, ncol=2)
            ax1.grid(True, alpha=0.3, linestyle='--')
            
            # Gráfico 2: Superponer TODOS los portfolios de TODAS las estrategias
            for idx, estrategia_data in enumerate(todas_las_estrategias):
                results = estrategia_data['results']
                strategy_name = estrategia_data['strategy_name']
                color = colors[idx % len(colors)]
                
                portfolio_df = pd.DataFrame(results['portfolio_values'])
                portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
                
                metrics = estrategia_data['metrics']
                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label=f'{strategy_name} (${metrics["total_return"]:+,.2f}, {metrics["total_return_pct"]:+.2f}%)',
                        linewidth=2.5, color=color, alpha=0.8)
            
            ax2.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--', 
                       label='Capital Inicial', alpha=0.8, linewidth=2)
            ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
            ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
            ax2.legend(loc='best', fontsize=10, framealpha=0.9)
            ax2.grid(True, alpha=0.3, linestyle='--')
            
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            pdf.savefig(fig, bbox_inches='tight', dpi=150)
            plt.close()
            
            # PÁGINAS 2 a N+1: Resumen completo por estrategia
            for estrategia_data in todas_las_estrategias:
                df_strategy = estrategia_data['df']
                results = estrategia_data['results']
                strategy_name = estrategia_data['strategy_name']
                
                portfolio_df = pd.DataFrame(results['portfolio_values'])
                portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
                
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)
                
                # Gráfico 1: Precio completo con estructura 3M
                ax1.plot(df_strategy.index, df_strategy['close'],
                        label='Precio BTC/USD', linewidth=1.5, color='black', alpha=0.9)
                
                # Dibujar estructura 3M completa
                dibujar_estructura_3m(ax1, df_strategy, mostrar_texto=True)
                
                # Señales de compra/venta
                buy_signals = df_strategy[df_strategy.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color='lime', marker='^', s=150, label='Compra',
                               zorder=9, edgecolors='darkgreen', linewidths=2, alpha=0.9)
                
                sell_signals = df_strategy[df_strategy.get('sell_signal', False)]
                if not sell_signals.empty:
                    ax1.scatter(sell_signals.index, sell_signals['close'],
                               color='orange', marker='v', s=150, label='Venta',
                               zorder=9, edgecolors='darkred', linewidths=2, alpha=0.9)
                
                ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
                ax1.set_title(f'{SYMBOL} - {strategy_name} - RESUMEN COMPLETO (365 días)',
                             fontsize=16, fontweight='bold', pad=20)
                ax1.legend(loc='best', fontsize=10, framealpha=0.9, ncol=3)
                ax1.grid(True, alpha=0.3, linestyle='--')
                
                # Gráfico 2: Evolución del Portfolio
                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label='Valor del Portfolio', linewidth=2.5, color='green')
                ax2.axhline(y=results['initial_capital'], color='gray',
                           linestyle='--', label='Capital Inicial', alpha=0.8, linewidth=2)
                
                ax2.fill_between(portfolio_df['timestamp'],
                                 results['initial_capital'],
                                 portfolio_df['portfolio_value'],
                                 where=(portfolio_df['portfolio_value'] >= results['initial_capital']),
                                 alpha=0.3, color='green', label='Ganancia')
                ax2.fill_between(portfolio_df['timestamp'],
                                 results['initial_capital'],
                                 portfolio_df['portfolio_value'],
                                 where=(portfolio_df['portfolio_value'] < results['initial_capital']),
                                 alpha=0.3, color='red', label='Pérdida')
                
                ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
                ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
                ax2.legend(loc='best', fontsize=11, framealpha=0.9)
                ax2.grid(True, alpha=0.3, linestyle='--')
                
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                
                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close()
            
            # PÁGINAS MENSUALES: Una página por estrategia por mes
            for month in months:
                month_str = str(month)
                month_df = df_original[df_original['month'] == month]
                
                if len(month_df) == 0:
                    continue
                
                for estrategia_data in todas_las_estrategias:
                    df_strategy = estrategia_data['df']
                    results = estrategia_data['results']
                    strategy_name = estrategia_data['strategy_name']
                    
                    month_strategy = df_strategy[df_strategy.index.isin(month_df.index)].copy()
                    month_portfolio = pd.DataFrame(results['portfolio_values'])
                    month_portfolio['timestamp'] = pd.to_datetime(month_portfolio['timestamp'])
                    month_portfolio = month_portfolio[month_portfolio['timestamp'].dt.to_period('M') == month]
                    
                    if len(month_strategy) == 0:
                        continue
                    
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
                    
                    # Gráfico 1: Precio mensual con estructura 3M
                    ax1.plot(month_strategy.index, month_strategy['close'],
                            label='Precio BTC/USD', linewidth=2, color='black')
                    
                    # Dibujar estructura 3M completa
                    min_idx = month_strategy.index.min()
                    max_idx = month_strategy.index.max()
                    dibujar_estructura_3m(ax1, df_strategy, mostrar_texto=True, 
                                         tamaño_mensual=True, 
                                         rango_visible=(min_idx, max_idx))
                    ax1.set_xlim(min_idx, max_idx)
                    
                    # Señales de compra/venta
                    buy_signals_month = month_strategy[month_strategy.get('buy_signal', False)]
                    if not buy_signals_month.empty:
                        ax1.scatter(buy_signals_month.index, buy_signals_month['close'],
                                   color='lime', marker='^', s=300, label='Compra',
                                   zorder=10, edgecolors='darkgreen', linewidths=2.5, alpha=0.9)
                    
                    sell_signals_month = month_strategy[month_strategy.get('sell_signal', False)]
                    if not sell_signals_month.empty:
                        ax1.scatter(sell_signals_month.index, sell_signals_month['close'],
                                   color='orange', marker='v', s=300, label='Venta',
                                   zorder=10, edgecolors='darkred', linewidths=2.5, alpha=0.9)
                    
                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    latest_structure = month_strategy['market_structure'].iloc[-1] if 'market_structure' in month_strategy.columns else 'neutral'
                    structure_text = f" - Estructura: {latest_structure.upper()}"
                    ax1.set_title(f'{SYMBOL} - {strategy_name} ({month_str}){structure_text}', 
                                fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=9, ncol=3)
                    ax1.grid(True, alpha=0.3)
                    
                    # Gráfico 2: Evolución del Portfolio mensual
                    if not month_portfolio.empty:
                        ax2.plot(month_portfolio['timestamp'],
                                month_portfolio['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)
                        
                        ax2.fill_between(month_portfolio['timestamp'],
                                         results['initial_capital'],
                                         month_portfolio['portfolio_value'],
                                         where=(month_portfolio['portfolio_value'] >= results['initial_capital']),
                                         alpha=0.3, color='green', label='Ganancia')
                        ax2.fill_between(month_portfolio['timestamp'],
                                         results['initial_capital'],
                                         month_portfolio['portfolio_value'],
                                         where=(month_portfolio['portfolio_value'] < results['initial_capital']),
                                         alpha=0.3, color='red', label='Pérdida')
                    
                    ax2.set_ylabel('Valor Portfolio (USD)', fontsize=12, fontweight='bold')
                    ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                    ax2.legend(loc='best', fontsize=10)
                    ax2.grid(True, alpha=0.3)
                    
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()
            
            # ========== PÁGINAS INDIVIDUALES POR TRADE ==========
            # Generar visualización individual para cada trade con candlesticks y estructura MentFX
            trades_pages = 0
            for estrategia_data in todas_las_estrategias:
                df_strategy = estrategia_data['df']
                results = estrategia_data['results']
                strategy_name = estrategia_data['strategy_name']
                
                # Obtener trades originales si están disponibles
                trades_originales = results.get('trades_originales', [])
                if not trades_originales:
                    continue
                
                # Filtrar solo trades completados
                trades_completados = [t for t in trades_originales if t.exit_timestamp is not None]
                
                for trade_idx, trade in enumerate(trades_completados):
                    try:
                        # Determinar rango de datos a mostrar (entrada - 50 barras antes, salida + 50 barras después)
                        # Buscar índice más cercano si no coincide exactamente
                        try:
                            entry_idx = df_strategy.index.get_loc(trade.entry_timestamp)
                            if isinstance(entry_idx, slice):
                                entry_idx = entry_idx.start if entry_idx.start is not None else entry_idx.stop
                        except (KeyError, TypeError):
                            # Si no está exactamente, buscar el más cercano
                            entry_idx = df_strategy.index.get_indexer([trade.entry_timestamp], method='nearest')[0]
                            if entry_idx < 0:
                                continue
                        
                        try:
                            exit_idx = df_strategy.index.get_loc(trade.exit_timestamp)
                            if isinstance(exit_idx, slice):
                                exit_idx = exit_idx.start if exit_idx.start is not None else exit_idx.stop
                        except (KeyError, TypeError):
                            # Si no está exactamente, buscar el más cercano
                            exit_idx = df_strategy.index.get_indexer([trade.exit_timestamp], method='nearest')[0]
                            if exit_idx < 0:
                                continue
                        
                        # Calcular índices con margen
                        start_idx = max(0, entry_idx - 50)
                        end_idx = min(len(df_strategy) - 1, exit_idx + 50)
                        
                        # Obtener datos del rango
                        trade_data = df_strategy.iloc[start_idx:end_idx+1].copy()
                        min_timestamp = trade_data.index[0]
                        max_timestamp = trade_data.index[-1]
                        
                        # Crear figura para el trade
                        fig, ax = plt.subplots(figsize=(20, 10))
                        
                        # Configurar el eje X para fechas ANTES de dibujar
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                        
                        # Determinar intervalo de fechas según la duración del trade
                        duration_hours = (max_timestamp - min_timestamp).total_seconds() / 3600
                        if duration_hours <= 24:
                            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
                        elif duration_hours <= 168:  # 1 semana
                            ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
                        else:
                            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                        
                        # Dibujar candlesticks PRIMERO (fondo)
                        dibujar_candlesticks(ax, trade_data, rango_visible=(min_timestamp, max_timestamp))
                        
                        # Dibujar estructura MentFX escalonada
                        dibujar_estructura_mentfx_escalonada(ax, df_strategy, rango_visible=(min_timestamp, max_timestamp))
                        
                        # Dibujar información del trade (sobre todo lo demás)
                        dibujar_trade_info(ax, trade, trade_data)
                        
                        # Configurar gráfico
                        ax.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                        ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                        ax.set_title(f'{SYMBOL} - {strategy_name} - Trade #{trade_idx+1} | '
                                   f'PnL: ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%) | '
                                   f'Exit: {trade.exit_reason}',
                                   fontsize=14, fontweight='bold', pad=20)
                        ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
                        ax.legend(loc='best', fontsize=10, framealpha=0.9)
                        
                        # Establecer límites del eje X
                        ax.set_xlim(min_timestamp, max_timestamp)
                        
                        # Ajustar límites del eje Y basados en los precios del rango visible
                        price_min = trade_data['low'].min()
                        price_max = trade_data['high'].max()
                        
                        # Añadir un margen del 5% arriba y abajo
                        price_range = price_max - price_min
                        margin = price_range * 0.05
                        
                        y_min = price_min - margin
                        y_max = price_max + margin
                        
                        # Asegurar que el stop loss (si existe) esté visible
                        if trade.stop_loss_price is not None:
                            y_min = min(y_min, trade.stop_loss_price * 0.995)
                            y_max = max(y_max, trade.stop_loss_price * 1.005)
                        
                        # Asegurar que entrada y salida estén visibles
                        y_min = min(y_min, trade.entry_price * 0.995, trade.exit_price * 0.995)
                        y_max = max(y_max, trade.entry_price * 1.005, trade.exit_price * 1.005)
                        
                        ax.set_ylim(y_min, y_max)
                        
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        
                        pdf.savefig(fig, bbox_inches='tight', dpi=150)
                        plt.close()
                        trades_pages += 1
                        
                    except Exception as e:
                        print(f"    ⚠️ Error generando visualización para trade {trade_idx+1}: {e}")
                        plt.close()
                        continue
        
        total_pages = 1 + num_estrategias + (num_estrategias * len(months)) + trades_pages
        print(f"  ✅ PDF consolidado generado: {pdf_filename}")
        print(f"     ({total_pages} páginas: 1 comparación + {num_estrategias} resúmenes + {num_estrategias * len(months)} mensuales + {trades_pages} trades individuales)")
        
        # Cerrar todas las figuras de matplotlib después de generar el PDF
        plt.close('all')
    
    except Exception as e:
        print(f"  ⚠️ Error al generar PDF consolidado: {e}")
        import traceback
        traceback.print_exc()
        # Asegurar que se cierren las figuras incluso si hay error
        plt.close('all')

def visualizar_estrategia(df, results, strategy_name, days=30, save_monthly=False, multiple_strategies=False):
    """Visualiza una estrategia 3M"""
    try:
        os.makedirs('back_testresults3M', exist_ok=True)
        
        if days == 365 and save_monthly:
            if multiple_strategies:
                safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('.', '').replace('%', 'pct').replace('+', '_')
                pdf_filename = os.path.join('back_testresults3M', f'strategy_3M_365_{safe_name}.pdf')
            else:
                pdf_filename = os.path.join('back_testresults3M', 'strategy_3M_365.pdf')
            
            print(f"  📊 Generando PDF con resumen completo + 12 gráficos mensuales...")
            
            portfolio_df = pd.DataFrame(results['portfolio_values'])
            portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
            
            df['month'] = df.index.to_period('M')
            portfolio_df['month'] = portfolio_df['timestamp'].dt.to_period('M')
            months = sorted(df['month'].unique())[:12]
            
            with PdfPages(pdf_filename) as pdf:
                # PÁGINA 1: Resumen completo
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)
                
                ax1.plot(df.index, df['close'], label='Precio BTC/USD',
                        linewidth=1.5, color='black', alpha=0.9)
                
                dibujar_estructura_3m(ax1, df, mostrar_texto=True)
                
                buy_signals = df[df.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color='lime', marker='^', s=150, label='Compra',
                               zorder=9, edgecolors='darkgreen', linewidths=2, alpha=0.9)
                
                sell_signals = df[df.get('sell_signal', False)]
                if not sell_signals.empty:
                    ax1.scatter(sell_signals.index, sell_signals['close'],
                               color='orange', marker='v', s=150, label='Venta',
                               zorder=9, edgecolors='darkred', linewidths=2, alpha=0.9)
                
                ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
                ax1.set_title(f'{SYMBOL} - {strategy_name} - RESUMEN COMPLETO (365 días)',
                             fontsize=16, fontweight='bold', pad=20)
                ax1.legend(loc='best', fontsize=10, framealpha=0.9, ncol=3)
                ax1.grid(True, alpha=0.3, linestyle='--')
                
                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label='Valor del Portfolio', linewidth=2.5, color='green')
                ax2.axhline(y=results['initial_capital'], color='gray',
                           linestyle='--', label='Capital Inicial', alpha=0.8, linewidth=2)
                
                ax2.fill_between(portfolio_df['timestamp'],
                                 results['initial_capital'],
                                 portfolio_df['portfolio_value'],
                                 where=(portfolio_df['portfolio_value'] >= results['initial_capital']),
                                 alpha=0.3, color='green', label='Ganancia')
                ax2.fill_between(portfolio_df['timestamp'],
                                 results['initial_capital'],
                                 portfolio_df['portfolio_value'],
                                 where=(portfolio_df['portfolio_value'] < results['initial_capital']),
                                 alpha=0.3, color='red', label='Pérdida')
                
                ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
                ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
                ax2.legend(loc='best', fontsize=11, framealpha=0.9)
                ax2.grid(True, alpha=0.3, linestyle='--')
                
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                
                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close()
                
                # PÁGINAS MENSUALES
                for month in months:
                    month_str = str(month)
                    month_df_filtered = df[df['month'] == month]
                    
                    if len(month_df_filtered) == 0:
                        continue
                    
                    month_portfolio = portfolio_df[portfolio_df['month'] == month]
                    
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
                    
                    ax1.plot(month_df_filtered.index, month_df_filtered['close'],
                            label='Precio BTC/USD', linewidth=2, color='black')
                    
                    min_idx = month_df_filtered.index.min()
                    max_idx = month_df_filtered.index.max()
                    dibujar_estructura_3m(ax1, df, mostrar_texto=True, tamaño_mensual=True,
                                         rango_visible=(min_idx, max_idx))
                    ax1.set_xlim(min_idx, max_idx)
                    
                    buy_signals_month = month_df_filtered[month_df_filtered.get('buy_signal', False)]
                    if not buy_signals_month.empty:
                        ax1.scatter(buy_signals_month.index, buy_signals_month['close'],
                                   color='lime', marker='^', s=300, label='Compra',
                                   zorder=10, edgecolors='darkgreen', linewidths=2.5, alpha=0.9)
                    
                    sell_signals_month = month_df_filtered[month_df_filtered.get('sell_signal', False)]
                    if not sell_signals_month.empty:
                        ax1.scatter(sell_signals_month.index, sell_signals_month['close'],
                                   color='orange', marker='v', s=300, label='Venta',
                                   zorder=10, edgecolors='darkred', linewidths=2.5, alpha=0.9)
                    
                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    latest_structure = month_df_filtered['market_structure'].iloc[-1] if 'market_structure' in month_df_filtered.columns else 'neutral'
                    structure_text = f" - Estructura: {latest_structure.upper()}"
                    ax1.set_title(f'{SYMBOL} - {strategy_name} ({month_str}){structure_text}',
                                fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=9, ncol=3)
                    ax1.grid(True, alpha=0.3)
                    
                    if not month_portfolio.empty:
                        ax2.plot(month_portfolio['timestamp'],
                                month_portfolio['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)
                        
                        ax2.fill_between(month_portfolio['timestamp'],
                                         results['initial_capital'],
                                         month_portfolio['portfolio_value'],
                                         where=(month_portfolio['portfolio_value'] >= results['initial_capital']),
                                         alpha=0.3, color='green', label='Ganancia')
                        ax2.fill_between(month_portfolio['timestamp'],
                                         results['initial_capital'],
                                         month_portfolio['portfolio_value'],
                                         where=(month_portfolio['portfolio_value'] < results['initial_capital']),
                                         alpha=0.3, color='red', label='Pérdida')
                    
                    ax2.set_ylabel('Valor Portfolio (USD)', fontsize=12, fontweight='bold')
                    ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                    ax2.legend(loc='best', fontsize=10)
                    ax2.grid(True, alpha=0.3)
                    
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()
                
                # ========== PÁGINAS INDIVIDUALES POR TRADE ==========
                # Generar visualización individual para cada trade con candlesticks y estructura MentFX
                trades_originales = results.get('trades_originales', [])
                if trades_originales:
                    trades_completados = [t for t in trades_originales if t.exit_timestamp is not None]
                    
                    for trade_idx, trade in enumerate(trades_completados):
                        try:
                            # Determinar rango de datos a mostrar (entrada - 50 barras antes, salida + 50 barras después)
                            # Buscar índice más cercano si no coincide exactamente
                            try:
                                entry_idx = df.index.get_loc(trade.entry_timestamp)
                                if isinstance(entry_idx, slice):
                                    entry_idx = entry_idx.start if entry_idx.start is not None else entry_idx.stop
                            except (KeyError, TypeError):
                                # Si no está exactamente, buscar el más cercano
                                entry_idx = df.index.get_indexer([trade.entry_timestamp], method='nearest')[0]
                                if entry_idx < 0:
                                    continue
                            
                            try:
                                exit_idx = df.index.get_loc(trade.exit_timestamp)
                                if isinstance(exit_idx, slice):
                                    exit_idx = exit_idx.start if exit_idx.start is not None else exit_idx.stop
                            except (KeyError, TypeError):
                                # Si no está exactamente, buscar el más cercano
                                exit_idx = df.index.get_indexer([trade.exit_timestamp], method='nearest')[0]
                                if exit_idx < 0:
                                    continue
                            
                            # Calcular índices con margen
                            start_idx = max(0, entry_idx - 50)
                            end_idx = min(len(df) - 1, exit_idx + 50)
                            
                            # Obtener datos del rango
                            trade_data = df.iloc[start_idx:end_idx+1].copy()
                            min_timestamp = trade_data.index[0]
                            max_timestamp = trade_data.index[-1]
                            
                            # Crear figura para el trade
                            fig, ax = plt.subplots(figsize=(20, 10))
                            
                            # Configurar el eje X para fechas ANTES de dibujar
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                            
                            # Determinar intervalo de fechas según la duración del trade
                            duration_hours = (max_timestamp - min_timestamp).total_seconds() / 3600
                            if duration_hours <= 24:
                                ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
                            elif duration_hours <= 168:  # 1 semana
                                ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
                            else:
                                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                            
                            # Dibujar candlesticks PRIMERO (fondo)
                            dibujar_candlesticks(ax, trade_data, rango_visible=(min_timestamp, max_timestamp))
                            
                            # Dibujar estructura MentFX escalonada
                            dibujar_estructura_mentfx_escalonada(ax, df, rango_visible=(min_timestamp, max_timestamp))
                            
                            # Dibujar información del trade (sobre todo lo demás)
                            dibujar_trade_info(ax, trade, trade_data)
                            
                            # Configurar gráfico
                            ax.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                            ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                            ax.set_title(f'{SYMBOL} - {strategy_name} - Trade #{trade_idx+1} | '
                                       f'PnL: ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%) | '
                                       f'Exit: {trade.exit_reason}',
                                       fontsize=14, fontweight='bold', pad=20)
                            ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
                            ax.legend(loc='best', fontsize=10, framealpha=0.9)
                            
                            # Establecer límites del eje X
                            ax.set_xlim(min_timestamp, max_timestamp)
                            
                            # Ajustar límites del eje Y basados en los precios del rango visible
                            price_min = trade_data['low'].min()
                            price_max = trade_data['high'].max()
                            
                            # Añadir un margen del 5% arriba y abajo
                            price_range = price_max - price_min
                            margin = price_range * 0.05
                            
                            y_min = price_min - margin
                            y_max = price_max + margin
                            
                            # Asegurar que el stop loss (si existe) esté visible
                            if trade.stop_loss_price is not None:
                                y_min = min(y_min, trade.stop_loss_price * 0.995)
                                y_max = max(y_max, trade.stop_loss_price * 1.005)
                            
                            # Asegurar que entrada y salida estén visibles
                            y_min = min(y_min, trade.entry_price * 0.995, trade.exit_price * 0.995)
                            y_max = max(y_max, trade.entry_price * 1.005, trade.exit_price * 1.005)
                            
                            ax.set_ylim(y_min, y_max)
                            
                            plt.xticks(rotation=45, ha='right')
                            plt.tight_layout()
                            
                            pdf.savefig(fig, bbox_inches='tight', dpi=150)
                            plt.close()
                            
                        except Exception as e:
                            print(f"    ⚠️ Error generando visualización para trade {trade_idx+1}: {e}")
                            plt.close()
                            continue
            
            print(f"  ✅ PDF generado: {pdf_filename}")
        
        # Cerrar todas las figuras de matplotlib para liberar memoria
        plt.close('all')
    
    except Exception as e:
        print(f"  ⚠️ Error al generar visualización: {e}")
        import traceback
        traceback.print_exc()
        # Asegurar que se cierren las figuras incluso si hay error
        plt.close('all')

def backtesting(estrategias_seleccionadas, days=30):
    """Función principal de backtesting - PROCESO ÚNICO QUE TERMINA AUTOMÁTICAMENTE"""
    try:
        print("=" * 70)
        print("ESTRATEGIA 3M - BACKTESTING")
        print("=" * 70)
        print(f"\n📊 Símbolo: {SYMBOL}")
        print(f"📅 Período: Últimos {days} días")
        print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")
        
        client = CryptoHistoricalDataClient()
        print("📥 Obteniendo datos históricos...")
        try:
            df = obtener_datos(client, SYMBOL, days=days)
            expected_bars = days * 24
            print(f"✅ {len(df)} barras obtenidas (esperadas: ~{expected_bars} para timeframe 1 hora)\n")
        except Exception as e:
            print(f"⚠️ Error obteniendo datos: {e}")
            print("=" * 70)
            print("❌ Backtesting cancelado por error")
            print("=" * 70)
            sys.exit(1)
        
        results_list = []
        
        if estrategias_seleccionadas == 'all':
            estrategias_a_probar = {k: v for k, v in ESTRATEGIAS_3M.items() if k != 'all'}
        else:
            estrategias_a_probar = {k: ESTRATEGIAS_3M[k] for k in estrategias_seleccionadas if k in ESTRATEGIAS_3M}
        
        num_estrategias = len(estrategias_a_probar)
        
        print(f"🚀 Probando {num_estrategias} estrategia(s) 3M...\n")
        
        todas_las_estrategias = []
        
        for key, estrategia_func in estrategias_a_probar.items():
            try:
                print(f"\n🔄 Procesando estrategia {key}...")
                start_time = time.time()
                
                df_strategy, strategy_name = estrategia_func(df.copy())
                
                elapsed_time = time.time() - start_time
                print(f"📊 {strategy_name} (completado en {elapsed_time:.1f}s)...", end=" ")
                
                results = ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, CAPITAL_PER_TRADE_PCT)
                metrics = analizar_rentabilidad(results, strategy_name)
                results_list.append(metrics)
                
                retorno_usd = metrics['total_return']
                print(f"Retorno: {metrics['total_return_pct']:+.4f}% (${retorno_usd:+.2f}) | "
                      f"Win Rate: {metrics['win_rate']:.1f}% | Trades: {metrics['total_trades']}")
                
                if days == 365:
                    todas_las_estrategias.append({
                        'df': df_strategy,
                        'results': results,
                        'strategy_name': strategy_name,
                        'metrics': metrics
                    })
                
                try:
                    save_monthly = (days == 365)
                    print(f"  📊 Generando visualización para {strategy_name}...")
                    visualizar_estrategia(df_strategy, results, strategy_name, days=days,
                                         save_monthly=save_monthly,
                                         multiple_strategies=(num_estrategias > 1))
                    print(f"  ✅ Visualización completada para {strategy_name}")
                except Exception as viz_error:
                    print(f"  ⚠️ Error al generar gráfico: {viz_error}")
                    import traceback
                    traceback.print_exc()
            except Exception as e:
                print(f"❌ Error en estrategia {key}: {e}")
                import traceback
                traceback.print_exc()
                # Continuar con la siguiente estrategia en lugar de detenerse
                continue
        
        if days == 365 and num_estrategias > 1 and len(todas_las_estrategias) > 1:
            try:
                generar_pdf_consolidado(todas_las_estrategias, df)
            except Exception as e:
                print(f"  ⚠️ Error al generar PDF consolidado: {e}")
        
        if results_list:
            print("\n" + "=" * 70)
            print("📊 COMPARACIÓN")
            print("=" * 70)
            sorted_strategies = sorted(results_list, key=lambda x: x['total_return_pct'], reverse=True)
            
            for metrics in sorted_strategies:
                retorno_color = "🟢" if metrics['total_return_pct'] > 0 else "🔴"
                retorno_usd = metrics['total_return']
                print(f"{retorno_color} {metrics['strategy']:<40} "
                      f"{metrics['total_return_pct']:>8.4f}% (${retorno_usd:>10,.2f})  "
                      f"Win Rate: {metrics['win_rate']:>6.1f}%  Trades: {metrics['total_trades']:>4}")
            
            best = sorted_strategies[0]
            best_usd = best['total_return']
            print("\n🏆 MEJOR: {} ({:+.4f}%, ${:+,.2f} USD, Win Rate: {:.1f}%, {} trades en {} días)".format(
                best['strategy'], best['total_return_pct'], best_usd, best['win_rate'],
                best['total_trades'], days))
    
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN BACKTESTING: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # SIEMPRE ejecutar limpieza, incluso si hay errores
        try:
            # Cerrar todas las figuras de matplotlib
            plt.close('all')
            
            # Forzar limpieza de recursos
            import gc
            gc.collect()
            
            print("=" * 70)
            print("✅ Backtesting completado - Proceso terminando")
            print("=" * 70)
        except:
            pass
    
    # FORZAR TERMINACIÓN DEL PROCESO - NUNCA DEBE CONTINUAR DESPUÉS DE AQUÍ
    sys.exit(0)

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 70)
        print("MASTER ESTRATEGIA 3M - Backtesting")
        print("=" * 70)
        print("\nEstrategias disponibles:")
        print("   1. Estrategia 3M Completa")
        print("   2. Estrategia 3M Conservadora (Corregida)")
        print("   3. Estrategia 3M Agresiva (Mejorada)")
        print("   all. Todas las estrategias")
        print("\nPeriodos disponibles:")
        print("   30   - Ultimos 30 dias")
        print("   90   - Ultimos 3 meses")
        print("   180  - Ultimos 6 meses")
        print("   365  - Ultimo ano completo (genera PDFs mensuales)")
        print("\nUso:")
        print("   python master3M.py --backtest [estrategia] [dias]")
        print("\nEjemplos:")
        print("   python master3M.py --backtest all 365")
        print("   python master3M.py --backtest 1 30")
        print("   python master3M.py --backtest 1 365    # Completa, 1 ano")
        print("=" * 70)
        sys.exit(0)
    
    modo = sys.argv[1]
    estrategia = sys.argv[2] if len(sys.argv) > 2 else 'all'
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    
    if modo == '--backtest':
        backtesting(estrategia, days)
        # El backtesting ya hace sys.exit(0), pero por si acaso:
        sys.exit(0)
    else:
        print("❌ Modo no válido. Usa --backtest")
        sys.exit(1)

