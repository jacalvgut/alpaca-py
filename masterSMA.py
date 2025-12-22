#!/usr/bin/env python3
"""
Master SMA - 9 Estrategias SMA Crossover con diferentes períodos y modos
Basado en las estrategias encontradas en Project_VDRJ:
- SMA 7/20 (LONG, SHORT, MIXED)
- SMA 12/25 (LONG, SHORT, MIXED)
- SMA 20/50 (LONG, SHORT, MIXED)
"""

import os
import sys
import time
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

# ==================== CONFIGURACIÓN ====================
API_KEY = "PKNO6ZAQMZJZEDK7ZEXPL7WXLX"
SECRET_KEY = "FA3zirHrDfLgzXLMQGQswC3wsaLrMLUzBkSm2X78vqbK"
PAPER = True

SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 100000.0
MIN_ORDER_VALUE = 10.0

# ==================== ESTRATEGIAS SMA ====================

def sma_crossover_long(df, fast=7, slow=20):
    """
    Estrategia SMA Crossover LONG
    - Golden Cross: Fast SMA cruza por encima de Slow SMA
    - Confirmación: SMA 200 debe estar POR DEBAJO de ambas SMAs (tendencia alcista)
    - Para velas de 5 minutos, ajustar período de SMA 200
    """
    df = df.copy()

    # Determinar período de SMA 200 según el timeframe
    # Si hay muchas velas (5 min), usar SMA más corta; si hay pocas (1 hora), usar SMA 200
    num_bars = len(df)
    if num_bars > 10000:  # Probablemente 5 minutos
        sma_long_period = 288  # 288 velas de 5 min = 24 horas (1 día)
    else:  # Probablemente 1 hora
        sma_long_period = 200

    # Calcular SMAs
    df[f'sma_{fast}'] = ta.sma(df['close'], length=fast)
    df[f'sma_{slow}'] = ta.sma(df['close'], length=slow)
    df['sma_long'] = ta.sma(df['close'], length=sma_long_period)

    # Señal de compra: Golden Cross + SMA long debajo de ambas (o no disponible)
    df['buy_signal'] = (
        (df[f'sma_{fast}'] > df[f'sma_{slow}']) &  # Fast SMA por encima de Slow SMA
        (df[f'sma_{fast}'].shift(1) <= df[f'sma_{slow}'].shift(1)) &  # Crossover (anterior debajo)
        (df['sma_long'].notna()) &  # SMA long debe estar calculada
        (
            (df['sma_long'] < df[f'sma_{fast}']) |  # SMA long debajo de Fast SMA O
            (df['sma_long'] < df[f'sma_{slow}'])    # SMA long debajo de Slow SMA
        )
    )

    # Señal de venta: Death Cross (reversión)
    df['sell_signal'] = (
        (df[f'sma_{fast}'] < df[f'sma_{slow}']) &  # Fast SMA por debajo de Slow SMA
        (df[f'sma_{fast}'].shift(1) >= df[f'sma_{slow}'].shift(1))  # Crossover (anterior encima)
    )

    return df, f"SMA {fast}/{slow} Long"

def sma_crossover_short(df, fast=7, slow=20):
    """
    Estrategia SMA Crossover SHORT
    - Death Cross: Fast SMA cruza por debajo de Slow SMA
    - Confirmación: SMA long debe estar POR ENCIMA de ambas SMAs (tendencia bajista)
    - Confirmación adicional: Al menos una SMA con pendiente negativa
    """
    df = df.copy()

    # Determinar período de SMA long según el timeframe
    num_bars = len(df)
    if num_bars > 10000:  # Probablemente 5 minutos
        sma_long_period = 288  # 288 velas de 5 min = 24 horas (1 día)
    else:  # Probablemente 1 hora
        sma_long_period = 200

    # Calcular SMAs
    df[f'sma_{fast}'] = ta.sma(df['close'], length=fast)
    df[f'sma_{slow}'] = ta.sma(df['close'], length=slow)
    df['sma_long'] = ta.sma(df['close'], length=sma_long_period)

    # Calcular pendiente (slope)
    df[f'sma_{fast}_slope'] = df[f'sma_{fast}'] - df[f'sma_{fast}'].shift(1)
    df[f'sma_{slow}_slope'] = df[f'sma_{slow}'] - df[f'sma_{slow}'].shift(1)

    # Señal de venta (SHORT): Death Cross + SMA long encima de ambas (o no disponible) + pendiente negativa
    df['sell_signal'] = (
        (df[f'sma_{fast}'] < df[f'sma_{slow}']) &  # Fast SMA por debajo de Slow SMA
        (df[f'sma_{fast}'].shift(1) >= df[f'sma_{slow}'].shift(1)) &  # Crossover (anterior encima)
        (df['sma_long'].notna()) &  # SMA long debe estar calculada
        (
            (df['sma_long'] > df[f'sma_{fast}']) |  # SMA long encima de Fast SMA O
            (df['sma_long'] > df[f'sma_{slow}'])     # SMA long encima de Slow SMA
        ) &
        ((df[f'sma_{fast}_slope'] < 0) | (df[f'sma_{slow}_slope'] < 0))  # Al menos una con pendiente negativa
    )

    # Señal de compra: Golden Cross (reversión)
    df['buy_signal'] = (
        (df[f'sma_{fast}'] > df[f'sma_{slow}']) &  # Fast SMA por encima de Slow SMA
        (df[f'sma_{fast}'].shift(1) <= df[f'sma_{slow}'].shift(1))  # Crossover (anterior debajo)
    )

    return df, f"SMA {fast}/{slow} Short"

def sma_crossover_mixed(df, fast=7, slow=20):
    """
    Estrategia SMA Crossover MIXED
    - Combina LONG y SHORT
    - LONG: Golden Cross + SMA long debajo
    - SHORT: Death Cross + SMA long encima + pendiente negativa
    """
    df = df.copy()

    # Determinar período de SMA long según el timeframe
    num_bars = len(df)
    if num_bars > 10000:  # Probablemente 5 minutos
        sma_long_period = 288  # 288 velas de 5 min = 24 horas (1 día)
    else:  # Probablemente 1 hora
        sma_long_period = 200

    # Calcular SMAs
    df[f'sma_{fast}'] = ta.sma(df['close'], length=fast)
    df[f'sma_{slow}'] = ta.sma(df['close'], length=slow)
    df['sma_long'] = ta.sma(df['close'], length=sma_long_period)

    # Calcular pendiente
    df[f'sma_{fast}_slope'] = df[f'sma_{fast}'] - df[f'sma_{fast}'].shift(1)
    df[f'sma_{slow}_slope'] = df[f'sma_{slow}'] - df[f'sma_{slow}'].shift(1)

    # Señal LONG: Golden Cross + SMA long debajo (condición menos restrictiva)
    df['buy_signal'] = (
        (df[f'sma_{fast}'] > df[f'sma_{slow}']) &
        (df[f'sma_{fast}'].shift(1) <= df[f'sma_{slow}'].shift(1)) &
        (df['sma_long'].notna()) &
        (
            (df['sma_long'] < df[f'sma_{fast}']) |  # SMA long debajo de Fast SMA O
            (df['sma_long'] < df[f'sma_{slow}'])     # SMA long debajo de Slow SMA
        )
    )

    # Señal SHORT: Death Cross + SMA long encima + pendiente negativa (condición menos restrictiva)
    df['sell_signal'] = (
        (df[f'sma_{fast}'] < df[f'sma_{slow}']) &
        (df[f'sma_{fast}'].shift(1) >= df[f'sma_{slow}'].shift(1)) &
        (df['sma_long'].notna()) &
        (
            (df['sma_long'] > df[f'sma_{fast}']) |  # SMA long encima de Fast SMA O
            (df['sma_long'] > df[f'sma_{slow}'])     # SMA long encima de Slow SMA
        ) &
        ((df[f'sma_{fast}_slope'] < 0) | (df[f'sma_{slow}_slope'] < 0))
    )

    return df, f"SMA {fast}/{slow} Mixed"

# Diccionario de estrategias
ESTRATEGIAS_SMA = {
    '1': lambda d: sma_crossover_long(d, fast=7, slow=20),
    '2': lambda d: sma_crossover_short(d, fast=7, slow=20),
    '3': lambda d: sma_crossover_mixed(d, fast=7, slow=20),
    '4': lambda d: sma_crossover_long(d, fast=12, slow=25),
    '5': lambda d: sma_crossover_short(d, fast=12, slow=25),
    '6': lambda d: sma_crossover_mixed(d, fast=12, slow=25),
    '7': lambda d: sma_crossover_long(d, fast=20, slow=50),
    '8': lambda d: sma_crossover_short(d, fast=20, slow=50),
    '9': lambda d: sma_crossover_mixed(d, fast=20, slow=50),
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
    Ejecuta backtest
    Args:
        initial_capital: Capital inicial
        min_order_value: Valor mínimo de orden (requerido por Alpaca)
        capital_per_trade_pct: Porcentaje del capital disponible a usar por operación (0.95 = 95%)
    """
    cash = initial_capital
    btc_held = 0.0
    entry_price = 0.0

    trades = []
    portfolio_values = []

    for idx, row in df.iterrows():
        portfolio_value = cash + (btc_held * row['close'])
        portfolio_values.append({
            'timestamp': idx,
            'portfolio_value': portfolio_value,
            'price': row['close']
        })

        # Señal de compra (LONG)
        if row.get('buy_signal', False) and btc_held == 0:
            current_price = row['close']

            # Usar un porcentaje del capital disponible (p.ej., 95%)
            # pero asegurarse de que sea al menos el mínimo requerido
            trade_amount = max(min_order_value, cash * capital_per_trade_pct)
            trade_amount = min(trade_amount, cash)  # No puede exceder el cash disponible

            qty = round(trade_amount / current_price, 8)
            cost = qty * current_price

            if cash >= cost and cost >= min_order_value:
                cash -= cost
                btc_held = qty
                entry_price = current_price
                trades.append({
                    'timestamp': idx,
                    'type': 'BUY',
                    'price': current_price,
                    'qty': qty,
                    'entry_price': current_price,
                    'trade_amount': cost
                })

        # Señal de venta (salida de LONG)
        elif row.get('sell_signal', False) and btc_held > 0:
            # Salida de posición LONG
            current_price = row['close']
            revenue = btc_held * current_price
            cash += revenue
            profit = revenue - (btc_held * entry_price)
            profit_pct = (profit / (btc_held * entry_price)) * 100 if entry_price > 0 else 0

            trades.append({
                'timestamp': idx,
                'type': 'SELL',
                'price': current_price,
                'qty': btc_held,
                'profit': profit,
                'profit_pct': profit_pct,
                'entry_price': entry_price
            })
            btc_held = 0.0
            entry_price = 0.0

    final_value = cash + (btc_held * df.iloc[-1]['close'])
    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': final_value - initial_capital,
        'trades': trades,
        'portfolio_values': portfolio_values
    }

def analizar_rentabilidad(results, strategy_name):
    """Analiza la rentabilidad de una estrategia"""
    trades = results['trades']
    sell_trades = [t for t in trades if t.get('type') == 'SELL']

    if not sell_trades:
        return {
            'strategy': strategy_name,
            'total_return': results['total_return'],
            'total_return_pct': (results['total_return'] / results['initial_capital']) * 100,
            'total_trades': 0,
            'sell_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'risk_reward_ratio': 0
        }

    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    losing_trades = [t for t in sell_trades if t.get('profit', 0) <= 0]

    total_profit = sum(t.get('profit', 0) for t in winning_trades)
    total_loss = abs(sum(t.get('profit', 0) for t in losing_trades))

    win_rate = (len(winning_trades) / len(sell_trades)) * 100 if sell_trades else 0
    if total_loss > 0:
        profit_factor = total_profit / total_loss
    elif total_profit > 0:
        profit_factor = float('inf')
    else:
        profit_factor = 0

    avg_win = total_profit / len(winning_trades) if winning_trades else 0
    avg_loss = total_loss / len(losing_trades) if losing_trades else 0
    risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    return {
        'strategy': strategy_name,
        'total_return': results['total_return'],
        'total_return_pct': (results['total_return'] / results['initial_capital']) * 100,
        'total_trades': len(sell_trades),
        'sell_trades': len(sell_trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'risk_reward_ratio': risk_reward_ratio,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades)
    }

def generar_pdf_consolidado(todas_las_estrategias, df_original):
    """Genera un PDF consolidado: Página 1 comparación, luego cada estrategia individual"""
    try:
        pdf_filename = os.path.join('back_testresultsSMA', 'strategy_SMA_365_ALL_STRATEGIES.pdf')
        print(f"\n  📊 Generando PDF consolidado...")

        # Preparar datos por meses
        df_original['month'] = df_original.index.to_period('M')
        months = sorted(df_original['month'].unique())[:12]
        num_estrategias = len(todas_las_estrategias)

        # Colores para cada estrategia
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']

        with PdfPages(pdf_filename) as pdf:
            # ========== PÁGINA 1: COMPARACIÓN DE TODAS LAS ESTRATEGIAS SUPERPUESTAS ==========
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

            # Gráfico 2: Superponer TODOS los portfolios de TODAS las estrategias
            for idx, estrategia_data in enumerate(todas_las_estrategias):
                results = estrategia_data['results']
                strategy_name = estrategia_data['strategy_name']
                color = colors[idx % len(colors)]

                portfolio_df = pd.DataFrame(results['portfolio_values'])
                portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])

                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label=f'{strategy_name} (${results["total_return"]:+.2f})',
                        linewidth=2.5, color=color, alpha=0.8)

            ax2.axhline(y=todas_las_estrategias[0]['results']['initial_capital'],
                       color='gray', linestyle='--',
                       label='Capital Inicial', alpha=0.8, linewidth=2)

            ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
            ax1.set_title(f'{SYMBOL} - COMPARACIÓN DE TODAS LAS ESTRATEGIAS SMA - RESUMEN COMPLETO (365 días)',
                         fontsize=16, fontweight='bold', pad=20)
            ax1.legend(loc='best', fontsize=9, framealpha=0.9, ncol=2)
            ax1.grid(True, alpha=0.3, linestyle='--')

            ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
            ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
            ax2.legend(loc='best', fontsize=10, framealpha=0.9, ncol=2)
            ax2.grid(True, alpha=0.3, linestyle='--')

            # Formatear fechas
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            pdf.savefig(fig, bbox_inches='tight', dpi=150)
            plt.close()

            # ========== PÁGINAS 2 a N+1: RESUMEN COMPLETO - UNA ESTRATEGIA POR PÁGINA ==========
            for estrategia_data in todas_las_estrategias:
                df_strategy = estrategia_data['df']
                results = estrategia_data['results']
                strategy_name = estrategia_data['strategy_name']

                # Preparar datos del portfolio
                portfolio_df = pd.DataFrame(results['portfolio_values'])
                portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])

                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

                # Gráfico 1: Precio completo con señales de ESTA estrategia
                ax1.plot(df_strategy.index, df_strategy['close'],
                        label='Precio BTC/USD', linewidth=1.5, color='black', alpha=0.9)

                # Señales de compra (año completo)
                buy_signals = df_strategy[df_strategy.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color='green', marker='^', s=80, label='Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)

                # Señales de venta (año completo)
                sell_signals = df_strategy[df_strategy.get('sell_signal', False)]
                if not sell_signals.empty:
                    ax1.scatter(sell_signals.index, sell_signals['close'],
                               color='red', marker='v', s=80, label='Venta',
                               zorder=5, edgecolors='darkred', linewidths=0.8, alpha=0.7)

                ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
                ax1.set_title(f'{SYMBOL} - {strategy_name} - RESUMEN COMPLETO (365 días)',
                             fontsize=16, fontweight='bold', pad=20)
                ax1.legend(loc='best', fontsize=11, framealpha=0.9)
                ax1.grid(True, alpha=0.3, linestyle='--')

                # Gráfico 2: Evolución completa del Portfolio
                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label='Valor del Portfolio', linewidth=2.5, color='green')
                ax2.axhline(y=results['initial_capital'], color='gray',
                           linestyle='--', label='Capital Inicial', alpha=0.8, linewidth=2)

                # Rellenar áreas de ganancia/pérdida
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

                # Formatear fechas
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()

                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close()

            # ========== PÁGINAS MENSUALES: UNA PÁGINA POR ESTRATEGIA POR MES ==========
            for month in months:
                month_str = str(month)

                for estrategia_data in todas_las_estrategias:
                    df_strategy = estrategia_data['df']
                    results = estrategia_data['results']
                    strategy_name = estrategia_data['strategy_name']

                    # Dividir por meses
                    df_strategy['month'] = df_strategy.index.to_period('M')
                    month_df = df_strategy[df_strategy['month'] == month]

                    portfolio_df = pd.DataFrame(results['portfolio_values'])
                    portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
                    portfolio_df['month'] = portfolio_df['timestamp'].dt.to_period('M')
                    month_portfolio = portfolio_df[portfolio_df['month'] == month]

                    if len(month_df) == 0:
                        continue

                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

                    # Gráfico 1: Precio mensual y señales
                    ax1.plot(month_df.index, month_df['close'],
                            label='Precio BTC/USD', linewidth=2, color='black')

                    # Señales de compra
                    buy_signals_month = month_df[month_df.get('buy_signal', False)]
                    if not buy_signals_month.empty:
                        ax1.scatter(buy_signals_month.index, buy_signals_month['close'],
                                   color='green', marker='^', s=200, label='Compra',
                                   zorder=5, edgecolors='darkgreen', linewidths=1.5)

                    # Señales de venta
                    sell_signals_month = month_df[month_df.get('sell_signal', False)]
                    if not sell_signals_month.empty:
                        ax1.scatter(sell_signals_month.index, sell_signals_month['close'],
                                   color='red', marker='v', s=200, label='Venta',
                                   zorder=5, edgecolors='darkred', linewidths=1.5)

                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    ax1.set_title(f'{SYMBOL} - {strategy_name} ({month_str})',
                                 fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=10)
                    ax1.grid(True, alpha=0.3)

                    # Gráfico 2: Evolución del Portfolio mensual
                    if not month_portfolio.empty:
                        ax2.plot(month_portfolio['timestamp'],
                                month_portfolio['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)

                        # Rellenar áreas
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

                    # Formatear fechas
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()

                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()

        total_pages = 1 + num_estrategias + (num_estrategias * len(months))
        print(f"  ✅ PDF consolidado generado: {pdf_filename} ({total_pages} páginas: 1 comparación + {num_estrategias} resúmenes + {num_estrategias * len(months)} páginas mensuales)")

    except Exception as e:
        print(f"⚠️ Error al generar PDF consolidado: {e}")
        import traceback
        traceback.print_exc()

def visualizar_estrategia(df, results, strategy_name, days=30, save_monthly=False, multiple_strategies=False):
    """Visualiza una estrategia SMA"""
    try:
        os.makedirs('back_testresultsSMA', exist_ok=True)

        # Si es 365 días y se solicita guardado mensual, crear PDF con resumen completo + 12 meses
        if days == 365 and save_monthly:
            # Si hay múltiples estrategias, incluir nombre en el archivo; si es una sola, usar nombre simple
            if multiple_strategies:
                safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('.', '').replace('%', 'pct').replace('+', '_').replace(' ', '_')
                pdf_filename = os.path.join('back_testresultsSMA', f'strategy_SMA_365_{safe_name}.pdf')
            else:
                pdf_filename = os.path.join('back_testresultsSMA', 'strategy_SMA_365.pdf')

            print(f"  📊 Generando PDF con resumen completo + 12 gráficos mensuales...")

            # Preparar datos del portfolio
            portfolio_df = pd.DataFrame(results['portfolio_values'])
            portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])

            # Dividir datos por meses para las páginas mensuales
            df['month'] = df.index.to_period('M')
            portfolio_df['month'] = portfolio_df['timestamp'].dt.to_period('M')
            months = sorted(df['month'].unique())[:12]

            with PdfPages(pdf_filename) as pdf:
                # ========== PÁGINA 1: RESUMEN COMPLETO (TODO EL AÑO) ==========
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

                # Gráfico 1: Precio completo con todas las señales
                ax1.plot(df.index, df['close'], label='Precio BTC/USD',
                        linewidth=1.5, color='black', alpha=0.9)

                # Señales de compra (año completo)
                buy_signals = df[df.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color='green', marker='^', s=80, label='Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)

                # Señales de venta (año completo)
                sell_signals = df[df.get('sell_signal', False)]
                if not sell_signals.empty:
                    ax1.scatter(sell_signals.index, sell_signals['close'],
                               color='red', marker='v', s=80, label='Venta',
                               zorder=5, edgecolors='darkred', linewidths=0.8, alpha=0.7)

                ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
                ax1.set_title(f'{SYMBOL} - {strategy_name} - RESUMEN COMPLETO (365 días)',
                             fontsize=16, fontweight='bold', pad=20)
                ax1.legend(loc='best', fontsize=11, framealpha=0.9)
                ax1.grid(True, alpha=0.3, linestyle='--')

                # Gráfico 2: Evolución completa del Portfolio
                ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                        label='Valor del Portfolio', linewidth=2.5, color='green')
                ax2.axhline(y=results['initial_capital'], color='gray',
                           linestyle='--', label='Capital Inicial', alpha=0.8, linewidth=2)

                # Rellenar áreas de ganancia/pérdida
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

                # Formatear fechas para el resumen completo
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()

                pdf.savefig(fig, bbox_inches='tight', dpi=150)
                plt.close()

                # ========== PÁGINAS 2-13: GRÁFICOS MENSUALES ==========
                for i, month in enumerate(months, 1):
                    month_str = str(month)
                    month_df = df[df['month'] == month]
                    month_portfolio = portfolio_df[portfolio_df['month'] == month]

                    if len(month_df) == 0:
                        continue

                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

                    # Gráfico 1: Precio mensual y señales
                    ax1.plot(month_df.index, month_df['close'],
                            label='Precio BTC/USD', linewidth=2, color='black')

                    # Señales de compra
                    buy_signals_month = month_df[month_df.get('buy_signal', False)]
                    if not buy_signals_month.empty:
                        ax1.scatter(buy_signals_month.index, buy_signals_month['close'],
                                   color='green', marker='^', s=200, label='Compra',
                                   zorder=5, edgecolors='darkgreen', linewidths=1.5)

                    # Señales de venta
                    sell_signals_month = month_df[month_df.get('sell_signal', False)]
                    if not sell_signals_month.empty:
                        ax1.scatter(sell_signals_month.index, sell_signals_month['close'],
                                   color='red', marker='v', s=200, label='Venta',
                                   zorder=5, edgecolors='darkred', linewidths=1.5)

                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    ax1.set_title(f'{SYMBOL} - {strategy_name} ({month_str})',
                                 fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=10)
                    ax1.grid(True, alpha=0.3)

                    # Gráfico 2: Evolución del Portfolio mensual
                    if not month_portfolio.empty:
                        ax2.plot(month_portfolio['timestamp'],
                                month_portfolio['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)

                        # Rellenar áreas
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

                    # Formatear fechas
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()

                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()

            print(f"  ✅ PDF generado: {pdf_filename} (13 páginas: 1 resumen completo + 12 mensuales)")
            return

        # Gráfico completo (no mensual)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

        # Gráfico 1: Precio y señales
        ax1.plot(df.index, df['close'], label='Precio BTC/USD', linewidth=2, color='black')

        # Señales de compra
        buy_signals = df[df.get('buy_signal', False)]
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'],
                       color='green', marker='^', s=200, label='Compra',
                       zorder=5, edgecolors='darkgreen', linewidths=1.5, alpha=0.8)

        # Señales de venta
        sell_signals = df[df.get('sell_signal', False)]
        if not sell_signals.empty:
            ax1.scatter(sell_signals.index, sell_signals['close'],
                       color='red', marker='v', s=200, label='Venta',
                       zorder=5, edgecolors='darkred', linewidths=1.5, alpha=0.8)

        ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
        ax1.set_title(f'{SYMBOL} - {strategy_name}', fontsize=14, fontweight='bold')
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Gráfico 2: Evolución del Portfolio
        portfolio_df = pd.DataFrame(results['portfolio_values'])
        ax2.plot(portfolio_df['timestamp'], portfolio_df['portfolio_value'],
                label='Valor del Portfolio', linewidth=2, color='green')
        ax2.axhline(y=results['initial_capital'], color='gray',
                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)

        # Rellenar áreas de ganancia/pérdida
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

        ax2.set_ylabel('Valor Portfolio (USD)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)

        # Formatear fechas
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Guardar en carpeta específica
        os.makedirs('back_testresultsSMA', exist_ok=True)
        safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('.', '').replace('%', 'pct').replace('+', '_')
        filename = os.path.join('back_testresultsSMA', f"sma_{safe_name}.png")
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"📊 Gráfico guardado: {filename}")
        plt.close()

    except Exception as e:
        print(f"⚠️ Error al generar gráfico: {e}")

# ==================== FUNCIONES PRINCIPALES ====================

def backtesting(estrategias_seleccionadas, days=30):
    """Ejecuta backtesting de estrategias SMA"""
    print("=" * 70)
    print("🔬 BACKTESTING - ESTRATEGIAS SMA CROSSOVER")
    print("=" * 70)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"📅 Período: Últimos {days} días")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")

    client = CryptoHistoricalDataClient()
    print("📥 Obteniendo datos históricos...")
    try:
        df = obtener_datos(client, SYMBOL, days=days)
        expected_bars = days * 24
        print(f"✅ {len(df)} barras obtenidas (esperadas: ~{expected_bars})\n")
    except Exception as e:
        print(f"⚠️ Error obteniendo datos: {e}")
        print("💡 Usando datos de ejemplo...")
        import numpy as np
        periods = min(days * 24, 10000)
        dates = pd.date_range(end=datetime.now(ZoneInfo("America/New_York")),
                             periods=periods, freq='H')
        prices = 87000 + np.cumsum(np.random.randn(periods) * 100)
        highs = prices * (1 + abs(np.random.randn(periods) * 0.002))
        lows = prices * (1 - abs(np.random.randn(periods) * 0.002))
        df = pd.DataFrame({
            'close': prices,
            'high': highs,
            'low': lows,
            'volume': np.random.randint(1000, 10000, periods)
        }, index=dates)
        print(f"✅ {len(df)} barras de ejemplo generadas\n")

    results_list = []

    if estrategias_seleccionadas == 'all':
        estrategias_a_probar = {k: v for k, v in ESTRATEGIAS_SMA.items() if k != 'all'}
    else:
        estrategias_a_probar = {k: ESTRATEGIAS_SMA[k] for k in estrategias_seleccionadas
                                if k in ESTRATEGIAS_SMA}

    # Detectar si hay múltiples estrategias
    num_estrategias = len(estrategias_a_probar)
    print(f"🚀 Probando {num_estrategias} estrategia(s) SMA...\n")

    # Guardar datos de todas las estrategias para PDF consolidado
    todas_las_estrategias = []

    for key, estrategia_func in estrategias_a_probar.items():
        try:
            df_strategy, strategy_name = estrategia_func(df.copy())
            print(f"📊 {strategy_name}...", end=" ")

            results = ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, 0.95)
            metrics = analizar_rentabilidad(results, strategy_name)
            results_list.append(metrics)

            retorno_usd = metrics['total_return']
            print(f"Retorno: {metrics['total_return_pct']:+.4f}% (${retorno_usd:+.2f}) | "
                  f"Win Rate: {metrics['win_rate']:.1f}% | Trades: {metrics['total_trades']}")

            # Guardar datos para PDF consolidado
            if days == 365:
                todas_las_estrategias.append({
                    'df': df_strategy,
                    'results': results,
                    'strategy_name': strategy_name,
                    'metrics': metrics
                })

            # Generar gráfico para cada estrategia
            try:
                # Si es 365 días, generar gráficos mensuales
                save_monthly = (days == 365)
                visualizar_estrategia(df_strategy, results, strategy_name, days=days,
                                     save_monthly=save_monthly,
                                     multiple_strategies=(num_estrategias > 1))
            except Exception as viz_error:
                print(f"  ⚠️ Error al generar gráfico: {viz_error}")
        except Exception as e:
            print(f"❌ Error: {e}")

    # Generar PDF consolidado si hay múltiples estrategias y es 365 días
    if days == 365 and num_estrategias > 1 and len(todas_las_estrategias) > 1:
        try:
            generar_pdf_consolidado(todas_las_estrategias, df)
        except Exception as e:
            print(f"  ⚠️ Error al generar PDF consolidado: {e}")

    if results_list:
        print("\n" + "=" * 70)
        print("📊 COMPARACIÓN DE ESTRATEGIAS SMA")
        print("=" * 70)
        sorted_strategies = sorted(results_list, key=lambda x: x['total_return_pct'], reverse=True)

        print(f"\n{'Estrategia':<35} {'Retorno %':<12} {'Win Rate':<10} {'Profit Factor':<12} {'Trades':<8}")
        print("-" * 70)

        for metrics in sorted_strategies:
            retorno_color = "🟢" if metrics['total_return_pct'] > 0 else "🔴"
            pf = metrics['profit_factor'] if metrics['profit_factor'] != float('inf') else 999.99
            print(f"{retorno_color} {metrics['strategy']:<33} "
                  f"{metrics['total_return_pct']:>8.4f}%  "
                  f"{metrics['win_rate']:>6.1f}%    "
                  f"{pf:>8.2f}      "
                  f"{metrics['total_trades']:>6}")

        best = sorted_strategies[0]
        best_usd = best['total_return']
        print("\n" + "=" * 70)
        print(f"🏆 MEJOR ESTRATEGIA: {best['strategy']}")
        print("=" * 70)
        print(f"💰 Retorno: {best['total_return_pct']:+.4f}% (${best_usd:+,.2f} USD)")
        print(f"📊 Win Rate: {best['win_rate']:.1f}%")
        print(f"📈 Total Trades: {best['total_trades']} ({best['sell_trades']} ventas)")
        print(f"💵 Profit Factor: {best['profit_factor']:.2f}" if best['profit_factor'] != float('inf') else "💵 Profit Factor: ∞")
        if best.get('risk_reward_ratio', 0) > 0:
            print(f"⚖️  Risk/Reward Ratio: {best['risk_reward_ratio']:.2f}")
        print(f"📅 Período: {days} días")
        print("=" * 70)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Master SMA - Backtesting de Estrategias SMA Crossover')
    parser.add_argument('--backtest', nargs='+', required=True,
                       help='Estrategias a probar (1-9 o "all")')
    parser.add_argument('days', type=int, nargs='?', default=30,
                       help='Número de días para backtesting (default: 30)')

    args = parser.parse_args()

    estrategias = args.backtest[0] if len(args.backtest) == 1 else 'all'
    if estrategias == 'all':
        estrategias = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    else:
        estrategias = estrategias.split(',') if ',' in estrategias else [estrategias]

    days = args.days if len(args.backtest) == 1 else int(args.backtest[1]) if len(args.backtest) > 1 else 30

    backtesting(estrategias, days)

