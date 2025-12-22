#!/usr/bin/env python3
"""
Master MACD - 6 Estrategias MACD con Diferentes Gestiones de Riesgo
Cada estrategia implementa un enfoque diferente de gestión de riesgo
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

# ==================== PARÁMETROS DE RIESGO ====================
STOP_LOSS_PCT = 0.02      # Stop loss del 2%
TAKE_PROFIT_PCT = 0.05    # Take profit del 5%
TRAILING_STOP_PCT = 0.015 # Trailing stop del 1.5%
ATR_MULTIPLIER = 2.0      # Multiplicador ATR para stop dinámico

# ==================== ESTRATEGIAS MACD ====================

def macd_basico(df, fast=12, slow=26, signal=9):
    """
    Estrategia 1: MACD Básico (Sin gestión de riesgo)
    - Solo señales de cruce MACD
    - No stop loss, no take profit
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    return df, "MACD Básico (Sin Stop Loss)"

def macd_stop_loss_fijo(df, fast=12, slow=26, signal=9, stop_loss_pct=0.02):
    """
    Estrategia 2: MACD con Stop Loss Fijo
    - Señales MACD normales
    - Stop loss fijo del X% desde precio de entrada
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # Calcular stop loss price para cada compra
    df['stop_loss_price'] = None
    entry_price = None
    for idx, row in df.iterrows():
        if row['buy_signal']:
            entry_price = row['close']
        elif entry_price and row['close'] <= entry_price * (1 - stop_loss_pct):
            # Stop loss activado
            df.loc[idx, 'sell_signal'] = True
            entry_price = None
        elif row['sell_signal']:
            entry_price = None

    return df, f"MACD + Stop Loss Fijo ({stop_loss_pct*100:.1f}%)"

def macd_trailing_stop(df, fast=12, slow=26, signal=9, trailing_pct=0.015):
    """
    Estrategia 3: MACD con Trailing Stop
    - Señales MACD normales
    - Stop loss que se mueve con el precio (trailing stop)
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # Trailing stop logic
    highest_price = None
    entry_price = None
    for idx, row in df.iterrows():
        if row['buy_signal']:
            entry_price = row['close']
            highest_price = row['close']
        elif entry_price:
            if row['close'] > highest_price:
                highest_price = row['close']
            # Si el precio baja más del trailing_pct desde el máximo
            if row['close'] <= highest_price * (1 - trailing_pct):
                df.loc[idx, 'sell_signal'] = True
                entry_price = None
                highest_price = None
        elif row['sell_signal']:
            entry_price = None
            highest_price = None

    return df, f"MACD + Trailing Stop ({trailing_pct*100:.1f}%)"

def macd_take_profit(df, fast=12, slow=26, signal=9, take_profit_pct=0.05):
    """
    Estrategia 4: MACD con Take Profit
    - Señales MACD normales
    - Take profit fijo del X%
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # Take profit logic
    entry_price = None
    for idx, row in df.iterrows():
        if row['buy_signal']:
            entry_price = row['close']
        elif entry_price and row['close'] >= entry_price * (1 + take_profit_pct):
            # Take profit activado
            df.loc[idx, 'sell_signal'] = True
            entry_price = None
        elif row['sell_signal']:
            entry_price = None

    return df, f"MACD + Take Profit ({take_profit_pct*100:.1f}%)"

def macd_stop_loss_take_profit(df, fast=12, slow=26, signal=9,
                                stop_loss_pct=0.02, take_profit_pct=0.05):
    """
    Estrategia 5: MACD con Stop Loss + Take Profit
    - Señales MACD normales
    - Stop loss y take profit simultáneos
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # Stop loss + Take profit logic
    entry_price = None
    for idx, row in df.iterrows():
        if row['buy_signal']:
            entry_price = row['close']
        elif entry_price:
            # Stop loss
            if row['close'] <= entry_price * (1 - stop_loss_pct):
                df.loc[idx, 'sell_signal'] = True
                entry_price = None
            # Take profit
            elif row['close'] >= entry_price * (1 + take_profit_pct):
                df.loc[idx, 'sell_signal'] = True
                entry_price = None
        elif row['sell_signal']:
            entry_price = None

    return df, f"MACD + SL({stop_loss_pct*100:.1f}%) + TP({take_profit_pct*100:.1f}%)"

def macd_atr_stop(df, fast=12, slow=26, signal=9, atr_multiplier=2.0):
    """
    Estrategia 6: MACD con Stop Loss Basado en ATR (Volatilidad)
    - Señales MACD normales
    - Stop loss dinámico basado en volatilidad (ATR)
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']

    # Calcular ATR para stop dinámico
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    df['buy_signal'] = (df['macd'] > df['macd_signal']) & \
                       (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['sell_signal'] = (df['macd'] < df['macd_signal']) & \
                        (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # Stop loss basado en ATR
    entry_price = None
    entry_atr = None
    for idx, row in df.iterrows():
        if row['buy_signal']:
            entry_price = row['close']
            entry_atr = row['atr'] if pd.notna(row['atr']) else entry_price * 0.02
        elif entry_price and pd.notna(row['atr']):
            # Stop loss = precio entrada - (ATR * multiplicador)
            stop_price = entry_price - (entry_atr * atr_multiplier)
            if row['close'] <= stop_price:
                df.loc[idx, 'sell_signal'] = True
                entry_price = None
                entry_atr = None
        elif row['sell_signal']:
            entry_price = None
            entry_atr = None

    return df, f"MACD + ATR Stop (x{atr_multiplier})"

# Diccionario de estrategias
ESTRATEGIAS_MACD = {
    '1': lambda d: macd_basico(d),
    '2': lambda d: macd_stop_loss_fijo(d, stop_loss_pct=STOP_LOSS_PCT),
    '3': lambda d: macd_trailing_stop(d, trailing_pct=TRAILING_STOP_PCT),
    '4': lambda d: macd_take_profit(d, take_profit_pct=TAKE_PROFIT_PCT),
    '5': lambda d: macd_stop_loss_take_profit(d,
                                               stop_loss_pct=STOP_LOSS_PCT,
                                               take_profit_pct=TAKE_PROFIT_PCT),
    '6': lambda d: macd_atr_stop(d, atr_multiplier=ATR_MULTIPLIER),
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

        elif row.get('sell_signal', False) and btc_held > 0:
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
        'total_return_pct': ((final_value - initial_capital) / initial_capital) * 100,
        'trades': trades,
        'portfolio_values': portfolio_values
    }

def analizar_rentabilidad(results, strategy_name):
    """Analiza rentabilidad con métricas de riesgo"""
    trades = results['trades']
    sell_trades = [t for t in trades if t['type'] == 'SELL']

    metrics = {
        'strategy': strategy_name,
        'total_return_pct': results['total_return_pct'],
        'total_return': results['total_return'],
        'total_trades': len(trades),
        'sell_trades': len(sell_trades),
    }

    if sell_trades:
        profits = [t['profit'] for t in sell_trades]
        profit_pcts = [t.get('profit_pct', 0) for t in sell_trades]

        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        metrics['win_rate'] = (len(winning) / len(sell_trades)) * 100
        metrics['avg_profit'] = sum(profits) / len(profits)
        metrics['avg_win'] = sum(winning) / len(winning) if winning else 0
        metrics['avg_loss'] = sum(losing) / len(losing) if losing else 0
        metrics['max_profit'] = max(profits) if profits else 0
        metrics['max_loss'] = min(profits) if profits else 0
        metrics['profit_factor'] = abs(sum(winning) / sum(losing)) if losing else float('inf')

        # Risk metrics
        if winning and losing:
            metrics['risk_reward_ratio'] = abs(metrics['avg_win'] / metrics['avg_loss'])
        else:
            metrics['risk_reward_ratio'] = 0
    else:
        metrics.update({
            'win_rate': 0, 'avg_profit': 0, 'avg_win': 0, 'avg_loss': 0,
            'max_profit': 0, 'max_loss': 0, 'profit_factor': 0, 'risk_reward_ratio': 0
        })

    return metrics

def generar_pdf_consolidado(todas_las_estrategias, df_original):
    """Genera un PDF consolidado: Página 1 comparación, luego cada estrategia individual"""
    try:
        pdf_filename = os.path.join('back_testresultsMACD', 'strategy_MACD_365_ALL_STRATEGIES.pdf')
        print(f"\n  📊 Generando PDF consolidado...")

        # Preparar datos por meses
        df_original['month'] = df_original.index.to_period('M')
        months = sorted(df_original['month'].unique())[:12]
        num_estrategias = len(todas_las_estrategias)

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
            ax1.set_title(f'{SYMBOL} - COMPARACIÓN DE TODAS LAS ESTRATEGIAS MACD - RESUMEN COMPLETO (365 días)',
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

                # Gráfico 1: Precio completo con todas las señales de ESTA estrategia
                ax1.plot(df_strategy.index, df_strategy['close'],
                        label='Precio BTC/USD', linewidth=1.5, color='black', alpha=0.9)

                # Señales de compra (año completo) - ESTA estrategia
                buy_signals = df_strategy[df_strategy.get('buy_signal', False)]
                if not buy_signals.empty:
                    ax1.scatter(buy_signals.index, buy_signals['close'],
                               color='green', marker='^', s=80, label='Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)

                # Señales de venta (año completo) - ESTA estrategia
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

                # Gráfico 2: Evolución completa del Portfolio - ESTA estrategia
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
        print(f"  ✅ PDF consolidado generado: {pdf_filename}")
        print(f"     ({total_pages} páginas: 1 comparación + {num_estrategias} resúmenes + {num_estrategias * len(months)} mensuales)")

    except Exception as e:
        print(f"⚠️ Error al generar PDF consolidado: {e}")
        import traceback
        traceback.print_exc()

def visualizar_estrategia(df, results, strategy_name, days=30, save_monthly=False, multiple_strategies=False):
    """Visualiza una estrategia MACD"""
    try:
        os.makedirs('back_testresultsMACD', exist_ok=True)

        # Si es 365 días y se solicita guardado mensual, crear PDF con resumen completo + 12 meses
        if days == 365 and save_monthly:
            # Si hay múltiples estrategias, incluir nombre en el archivo; si es una sola, usar nombre simple
            if multiple_strategies:
                safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('.', '').replace('%', 'pct').replace('+', '_').replace(' ', '_')
                pdf_filename = os.path.join('back_testresultsMACD', f'strategy_MACD_365_{safe_name}.pdf')
            else:
                pdf_filename = os.path.join('back_testresultsMACD', 'strategy_MACD_365.pdf')

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
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Guardar en carpeta específica
        os.makedirs('back_testresultsMACD', exist_ok=True)
        safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('.', '').replace('%', 'pct').replace('+', '_')
        filename = os.path.join('back_testresultsMACD', f"macd_{safe_name}.png")
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"📊 Gráfico guardado: {filename}")
        plt.close()

    except Exception as e:
        print(f"⚠️ Error al generar gráfico: {e}")

# ==================== FUNCIONES PRINCIPALES ====================

def backtesting(estrategias_seleccionadas, days=30):
    """Ejecuta backtesting de estrategias MACD"""
    print("=" * 70)
    print("🔬 BACKTESTING - ESTRATEGIAS MACD CON GESTIÓN DE RIESGO")
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
        estrategias_a_probar = {k: v for k, v in ESTRATEGIAS_MACD.items() if k != 'all'}
    else:
        estrategias_a_probar = {k: ESTRATEGIAS_MACD[k] for k in estrategias_seleccionadas
                                if k in ESTRATEGIAS_MACD}

    # Detectar si hay múltiples estrategias
    num_estrategias = len(estrategias_a_probar)
    print(f"🚀 Probando {num_estrategias} estrategia(s) MACD...\n")

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
        print("📊 COMPARACIÓN DE ESTRATEGIAS MACD")
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

def ejecutar_real(estrategia_key):
    """Ejecuta estrategia MACD en modo real"""
    print("=" * 70)
    print("🚀 EJECUTAR ESTRATEGIA MACD (MODO REAL)")
    print("=" * 70)

    trade_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=PAPER)
    crypto_client = CryptoHistoricalDataClient()

    account = trade_client.get_account()
    print(f"\n💰 Efectivo: ${float(account.cash):,.2f} | Patrimonio: ${float(account.equity):,.2f}\n")

    print("📊 Obteniendo datos...")
    try:
        df = obtener_datos(crypto_client, SYMBOL, days=10)
        print(f"✅ {len(df)} barras obtenidas\n")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return

    try:
        df_strategy, strategy_name = ESTRATEGIAS_MACD[estrategia_key](df.copy())
    except:
        print(f"❌ Estrategia '{estrategia_key}' no válida")
        return

    latest = df_strategy.iloc[-1]

    # Verificar posición
    symbol_pos = SYMBOL.replace("/", "")
    try:
        position = trade_client.get_open_position(symbol_or_asset_id=symbol_pos)
        has_position = True
        current_qty = float(position.qty)
    except:
        has_position = False
        current_qty = 0

    print(f"📊 {SYMBOL}: ${latest['close']:,.2f}")
    print(f"📈 MACD: {latest['macd']:.2f}")
    print(f"📉 Señal: {latest['macd_signal']:.2f}")
    if has_position:
        print(f"✅ Posición: {current_qty} {SYMBOL}")
    else:
        print("ℹ️ Sin posición")

    qty = round(MIN_ORDER_VALUE / latest['close'], 6)

    print("\n" + "=" * 70)
    print(f"🎯 Estrategia: {strategy_name}")
    print("=" * 70)

    if latest.get('buy_signal', False) and not has_position:
        print(f"🟢 SEÑAL DE COMPRA")
        print(f"   Comprando {qty} {SYMBOL} (~${qty * latest['close']:,.2f})...")

        try:
            order = MarketOrderRequest(symbol=SYMBOL, qty=qty, side=OrderSide.BUY,
                                     type=OrderType.MARKET, time_in_force=TimeInForce.GTC)
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"💰 Portfolio actualizado en Alpaca!")
        except Exception as e:
            print(f"❌ Error: {e}")

    elif latest.get('sell_signal', False) and has_position:
        print(f"🔴 SEÑAL DE VENTA")
        print(f"   Vendiendo {abs(current_qty)} {SYMBOL}...")

        try:
            order = MarketOrderRequest(symbol=SYMBOL, qty=abs(current_qty), side=OrderSide.SELL,
                                     type=OrderType.MARKET, time_in_force=TimeInForce.GTC)
            result = trade_client.submit_order(order)
            print(f"✅ Orden ejecutada: {result.id}")
            print(f"💰 Portfolio actualizado en Alpaca!")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        if latest['macd'] > latest['macd_signal']:
            print("⚪ Tendencia ALCISTA (MACD > Señal)")
        else:
            print("⚪ Tendencia BAJISTA (MACD < Señal)")
        print("   Sin señal nueva en este momento")

    print("=" * 70)

def mostrar_menu():
    """Muestra menú de opciones"""
    print("\n" + "=" * 70)
    print("🎯 MASTER MACD - Estrategias MACD con Gestión de Riesgo")
    print("=" * 70)
    print("\n📊 Estrategias disponibles:")
    print("   1. MACD Básico (Sin Stop Loss)")
    print("   2. MACD + Stop Loss Fijo (2%)")
    print("   3. MACD + Trailing Stop (1.5%)")
    print("   4. MACD + Take Profit (5%)")
    print("   5. MACD + Stop Loss + Take Profit (2% / 5%)")
    print("   6. MACD + ATR Stop (Basado en volatilidad)")
    print("   all. Todas las estrategias")
    print("\n📅 Intervalos:")
    print("   30, 90, 180, 365 días")
    print("\n🔧 Modos:")
    print("   --backtest [estrategia] [días]  - Backtesting (default: all, 30)")
    print("   --execute [estrategia]          - Ejecutar real (default: 1)")
    print("\n💡 Ejemplos:")
    print("   python3 masterMACD.py --backtest all 365")
    print("   python3 masterMACD.py --backtest 5 180")
    print("   python3 masterMACD.py --execute 5")
    print("=" * 70)

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        mostrar_menu()
        sys.exit(0)

    modo = sys.argv[1]
    estrategia = sys.argv[2] if len(sys.argv) > 2 else ('all' if modo == '--backtest' else '1')

    if modo == '--backtest':
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        backtesting(estrategia, days)
    elif modo == '--execute':
        ejecutar_real(estrategia)
    else:
        print("❌ Modo no válido. Usa --backtest o --execute")
        mostrar_menu()

