#!/usr/bin/env python3
"""
Master All Historical - Ejecuta todas las estrategias MACD y SMA con TODOS los datos históricos de Bitcoin
Genera un PDF completo con comparación y todos los trades visibles
"""

import os
import sys
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Importar los módulos de estrategias
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Importar funciones de MACD y SMA
import importlib.util

# Cargar módulos dinámicamente
macd_module_path = os.path.join(os.path.dirname(__file__), 'masterMACD.py')
sma_module_path = os.path.join(os.path.dirname(__file__), 'masterSMA.py')

spec_macd = importlib.util.spec_from_file_location("masterMACD", macd_module_path)
spec_sma = importlib.util.spec_from_file_location("masterSMA", sma_module_path)

master_macd = importlib.util.module_from_spec(spec_macd)
master_sma = importlib.util.module_from_spec(spec_sma)

spec_macd.loader.exec_module(master_macd)
spec_sma.loader.exec_module(master_sma)

# ==================== CONFIGURACIÓN ====================
SYMBOL = "BTC/USD"
INITIAL_CAPITAL = 1000.0  # 1000 euros/dólares como capital inicial
MIN_ORDER_VALUE = 10.0  # Mínimo requerido por Alpaca
CAPITAL_PER_TRADE_PCT = 0.95  # Usar 95% del capital disponible por operación
MAX_BARS_PER_REQUEST = 10000

# Bitcoin empezó a tradearse alrededor de 2010, pero datos confiables desde ~2014
BITCOIN_START_DATE = datetime(2014, 1, 1, tzinfo=ZoneInfo("America/New_York"))

# ==================== FUNCIONES AUXILIARES ====================

def obtener_todos_los_datos(client, symbol, timeframe="1Hour", start_date=None):
    """Obtiene TODOS los datos históricos disponibles usando paginación"""
    now = datetime.now(ZoneInfo("America/New_York"))

    if start_date is None:
        start_date = BITCOIN_START_DATE

    print(f"  📅 Rango de fechas: {start_date.date()} a {now.date()}")

    if timeframe == "1Hour":
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
    elif timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
    else:
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)

    all_dfs = []
    current_start = start_date
    total_obtained = 0
    request_count = 0

    print(f"  📊 Obteniendo datos con paginación (máximo {MAX_BARS_PER_REQUEST} barras por solicitud)...")

    while current_start < now:
        request_count += 1

        request = CryptoBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=current_start,
            limit=MAX_BARS_PER_REQUEST
        )

        try:
            bars = client.get_crypto_bars(request)
            df_batch = bars.df

            if isinstance(df_batch.index, pd.MultiIndex):
                df_batch = df_batch.loc[symbol]

            if len(df_batch) == 0:
                print(f"    ✓ No hay más datos disponibles")
                break

            all_dfs.append(df_batch)
            total_obtained += len(df_batch)

            # Actualizar start_time para la siguiente solicitud
            last_timestamp = df_batch.index[-1]
            if isinstance(last_timestamp, pd.Timestamp):
                current_start = last_timestamp.to_pydatetime()
            else:
                current_start = pd.to_datetime(last_timestamp).to_pydatetime()

            # Avanzar para evitar solapamiento
            if timeframe == "5Min":
                current_start += timedelta(minutes=5)
            else:
                current_start += timedelta(hours=1)

            # Mostrar progreso cada 10 solicitudes
            if request_count % 10 == 0:
                print(f"    ✓ Solicitud {request_count}: {total_obtained:,} barras acumuladas... "
                      f"({current_start.date()})")

            # Pequeña pausa para evitar rate limiting
            if request_count % 50 == 0:
                time.sleep(1)

        except Exception as e:
            print(f"    ⚠️ Error en solicitud {request_count}: {e}")
            break

    # Combinar todos los datos
    if all_dfs:
        df = pd.concat(all_dfs).sort_index()
        # Eliminar duplicados
        df = df[~df.index.duplicated(keep='first')]
        print(f"  ✅ Total obtenido: {len(df):,} barras únicas desde {df.index[0].date()} hasta {df.index[-1].date()}")
        return df
    else:
        raise Exception("No se pudieron obtener datos")

def generar_pdf_completo_con_todos_los_trades(macd_strategies_data, sma_strategies_data, days):
    """Genera un PDF completo con comparación y todos los trades visibles"""
    try:
        pdf_filename = os.path.join('back_testresultsCOMPARISON',
                                    'ALL_HISTORICAL_BEST_STRATEGIES_COMPLETE.pdf')
        print(f"\n  📊 Generando PDF completo con todos los trades...")

        # Encontrar mejores estrategias
        if macd_strategies_data:
            best_macd_data = max(macd_strategies_data,
                                key=lambda x: x['metrics']['total_return_pct'])
        else:
            best_macd_data = None

        if sma_strategies_data:
            best_sma_data = max(sma_strategies_data,
                               key=lambda x: x['metrics']['total_return_pct'])
        else:
            best_sma_data = None

        if not best_macd_data and not best_sma_data:
            print("  ⚠️ No hay datos para generar PDF")
            return

        colors_comparison = ['#FF6B35', '#004E89']  # Naranja para MACD, Azul para SMA

        with PdfPages(pdf_filename) as pdf:
            # ========== PÁGINA 1: COMPARACIÓN DE LAS MEJORES ESTRATEGIAS ==========
            print("  📄 Generando página 1: Comparación...")
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

            # Usar el dataframe más largo para el precio base
            if best_macd_data and best_sma_data:
                df_base = best_macd_data['df'] if len(best_macd_data['df']) > len(best_sma_data['df']) else best_sma_data['df']
            elif best_macd_data:
                df_base = best_macd_data['df']
            else:
                df_base = best_sma_data['df']

            # Gráfico 1: Precio BTC/USD
            ax1.plot(df_base.index, df_base['close'],
                    label='Precio BTC/USD', linewidth=1, color='black', alpha=0.9, zorder=1)

            # Gráfico 2: Comparar portfolios
            if best_macd_data:
                portfolio_macd = pd.DataFrame(best_macd_data['results']['portfolio_values'])
                portfolio_macd['timestamp'] = pd.to_datetime(portfolio_macd['timestamp'])
                ax2.plot(portfolio_macd['timestamp'], portfolio_macd['portfolio_value'],
                        label=f"{best_macd_data['strategy_name']} (${best_macd_data['metrics']['total_return']:+.2f})",
                        linewidth=2, color=colors_comparison[0], alpha=0.8)

            if best_sma_data:
                portfolio_sma = pd.DataFrame(best_sma_data['results']['portfolio_values'])
                portfolio_sma['timestamp'] = pd.to_datetime(portfolio_sma['timestamp'])
                ax2.plot(portfolio_sma['timestamp'], portfolio_sma['portfolio_value'],
                        label=f"{best_sma_data['strategy_name']} (${best_sma_data['metrics']['total_return']:+.2f})",
                        linewidth=2, color=colors_comparison[1], alpha=0.8)

            ax2.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--',
                       label='Capital Inicial', alpha=0.8, linewidth=2)

            ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
            ax1.set_title(f'{SYMBOL} - MEJORES ESTRATEGIAS MACD vs SMA (TODOS LOS DATOS HISTÓRICOS)',
                         fontsize=16, fontweight='bold', pad=20)
            ax1.legend(loc='best', fontsize=11, framealpha=0.9)
            ax1.grid(True, alpha=0.3, linestyle='--')

            ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
            ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
            ax2.legend(loc='best', fontsize=11, framealpha=0.9)
            ax2.grid(True, alpha=0.3, linestyle='--')

            # Formatear fechas
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.YearLocator())
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            pdf.savefig(fig, bbox_inches='tight', dpi=150)
            plt.close()

            # ========== PÁGINAS CON TODOS LOS TRADES: MEJOR MACD ==========
            if best_macd_data:
                print(f"  📄 Generando páginas con trades de {best_macd_data['strategy_name']}...")
                trades_macd = [t for t in best_macd_data['results']['trades'] if t.get('type') == 'SELL']
                df_macd = best_macd_data['df']
                results_macd = best_macd_data['results']

                # Dividir trades en grupos para mostrar en páginas (ej: 50 trades por página)
                trades_per_page = 50
                num_pages = (len(trades_macd) + trades_per_page - 1) // trades_per_page

                for page_num in range(num_pages):
                    start_idx = page_num * trades_per_page
                    end_idx = min((page_num + 1) * trades_per_page, len(trades_macd))
                    page_trades = trades_macd[start_idx:end_idx]

                    if not page_trades:
                        continue

                    # Encontrar rango de fechas para estos trades
                    trade_times = [pd.to_datetime(t['timestamp']) for t in page_trades]
                    min_time = min(trade_times)
                    max_time = max(trade_times)

                    # Agregar margen de tiempo antes y después (ajustar según timeframe)
                    # Para velas de 1 hora, usar más margen; para 5 minutos, menos
                    if len(df_macd) > 50000:  # Probablemente 5 minutos
                        time_margin = timedelta(days=2)
                    else:  # Probablemente 1 hora
                        time_margin = timedelta(days=7)
                    mask = (df_macd.index >= (min_time - time_margin)) & (df_macd.index <= (max_time + time_margin))
                    df_page = df_macd[mask]

                    if len(df_page) == 0:
                        continue

                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

                    # Gráfico 1: Precio con señales de estos trades
                    ax1.plot(df_page.index, df_page['close'],
                            label='Precio BTC/USD', linewidth=1.5, color='black', alpha=0.9)

                    # Señales de compra en este rango
                    buy_signals_page = df_page[df_page.get('buy_signal', False)]
                    if not buy_signals_page.empty:
                        ax1.scatter(buy_signals_page.index, buy_signals_page['close'],
                                   color='green', marker='^', s=150, label='Compra',
                                   zorder=5, edgecolors='darkgreen', linewidths=1, alpha=0.8)

                    # Señales de venta en este rango
                    sell_signals_page = df_page[df_page.get('sell_signal', False)]
                    if not sell_signals_page.empty:
                        ax1.scatter(sell_signals_page.index, sell_signals_page['close'],
                                   color='red', marker='v', s=150, label='Venta',
                                   zorder=5, edgecolors='darkred', linewidths=1, alpha=0.8)

                    # Marcar trades específicos de esta página con información detallada
                    for trade in page_trades:
                        trade_time = pd.to_datetime(trade['timestamp'])
                        trade_price = trade.get('exit_price', trade.get('price', 0))
                        profit = trade.get('profit', 0)
                        color = 'darkgreen' if profit > 0 else 'darkred'
                        marker_size = 400 if abs(profit) > 100 else 250
                        ax1.scatter(trade_time, trade_price,
                                   color=color, marker='*', s=marker_size,
                                   zorder=6, edgecolors='yellow', linewidths=1.5, alpha=0.9)
                        # Anotar profit en trades grandes
                        if abs(profit) > 50:
                            ax1.annotate(f'${profit:.0f}',
                                       xy=(trade_time, trade_price),
                                       xytext=(5, 10), textcoords='offset points',
                                       fontsize=8, color=color, fontweight='bold',
                                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    ax1.set_title(f'{best_macd_data["strategy_name"]} - Trades {start_idx+1}-{end_idx} de {len(trades_macd)}',
                                 fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=10)
                    ax1.grid(True, alpha=0.3)

                    # Gráfico 2: Portfolio en este rango
                    portfolio_df = pd.DataFrame(results_macd['portfolio_values'])
                    portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
                    mask_portfolio = (portfolio_df['timestamp'] >= (min_time - time_margin)) & \
                                   (portfolio_df['timestamp'] <= (max_time + time_margin))
                    portfolio_page = portfolio_df[mask_portfolio]

                    if not portfolio_page.empty:
                        ax2.plot(portfolio_page['timestamp'], portfolio_page['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results_macd['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)

                    ax2.set_ylabel('Valor Portfolio (USD)', fontsize=12, fontweight='bold')
                    ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                    ax2.legend(loc='best', fontsize=10)
                    ax2.grid(True, alpha=0.3)

                    # Formatear fechas
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()

                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()

                    if (page_num + 1) % 10 == 0:
                        print(f"    ✓ Página {page_num + 1}/{num_pages} generada...")

            # ========== PÁGINAS CON TODOS LOS TRADES: MEJOR SMA ==========
            if best_sma_data:
                print(f"  📄 Generando páginas con trades de {best_sma_data['strategy_name']}...")
                trades_sma = [t for t in best_sma_data['results']['trades'] if t.get('type') == 'SELL']
                df_sma = best_sma_data['df']
                results_sma = best_sma_data['results']

                # Dividir trades en grupos para mostrar en páginas
                trades_per_page = 50
                num_pages = (len(trades_sma) + trades_per_page - 1) // trades_per_page

                for page_num in range(num_pages):
                    start_idx = page_num * trades_per_page
                    end_idx = min((page_num + 1) * trades_per_page, len(trades_sma))
                    page_trades = trades_sma[start_idx:end_idx]

                    if not page_trades:
                        continue

                    # Encontrar rango de fechas para estos trades
                    trade_times = [pd.to_datetime(t['timestamp']) for t in page_trades]
                    min_time = min(trade_times)
                    max_time = max(trade_times)

                    # Agregar margen de tiempo (ajustar según timeframe)
                    if len(df_sma) > 50000:  # Probablemente 5 minutos
                        time_margin = timedelta(days=2)
                    else:  # Probablemente 1 hora
                        time_margin = timedelta(days=7)
                    mask = (df_sma.index >= (min_time - time_margin)) & (df_sma.index <= (max_time + time_margin))
                    df_page = df_sma[mask]

                    if len(df_page) == 0:
                        continue

                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

                    # Gráfico 1: Precio con señales
                    ax1.plot(df_page.index, df_page['close'],
                            label='Precio BTC/USD', linewidth=1.5, color='black', alpha=0.9)

                    # Señales de compra
                    buy_signals_page = df_page[df_page.get('buy_signal', False)]
                    if not buy_signals_page.empty:
                        ax1.scatter(buy_signals_page.index, buy_signals_page['close'],
                                   color='green', marker='^', s=150, label='Compra',
                                   zorder=5, edgecolors='darkgreen', linewidths=1, alpha=0.8)

                    # Señales de venta
                    sell_signals_page = df_page[df_page.get('sell_signal', False)]
                    if not sell_signals_page.empty:
                        ax1.scatter(sell_signals_page.index, sell_signals_page['close'],
                                   color='red', marker='v', s=150, label='Venta',
                                   zorder=5, edgecolors='darkred', linewidths=1, alpha=0.8)

                    # Marcar trades específicos con información detallada
                    for trade in page_trades:
                        trade_time = pd.to_datetime(trade['timestamp'])
                        trade_price = trade.get('exit_price', trade.get('price', 0))
                        profit = trade.get('profit', 0)
                        color = 'darkgreen' if profit > 0 else 'darkred'
                        marker_size = 400 if abs(profit) > 100 else 250
                        ax1.scatter(trade_time, trade_price,
                                   color=color, marker='*', s=marker_size,
                                   zorder=6, edgecolors='yellow', linewidths=1.5, alpha=0.9)
                        # Anotar profit en trades grandes
                        if abs(profit) > 50:
                            ax1.annotate(f'${profit:.0f}',
                                       xy=(trade_time, trade_price),
                                       xytext=(5, 10), textcoords='offset points',
                                       fontsize=8, color=color, fontweight='bold',
                                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

                    ax1.set_ylabel('Precio (USD)', fontsize=12, fontweight='bold')
                    ax1.set_title(f'{best_sma_data["strategy_name"]} - Trades {start_idx+1}-{end_idx} de {len(trades_sma)}',
                                 fontsize=14, fontweight='bold')
                    ax1.legend(loc='best', fontsize=10)
                    ax1.grid(True, alpha=0.3)

                    # Gráfico 2: Portfolio
                    portfolio_df = pd.DataFrame(results_sma['portfolio_values'])
                    portfolio_df['timestamp'] = pd.to_datetime(portfolio_df['timestamp'])
                    mask_portfolio = (portfolio_df['timestamp'] >= (min_time - time_margin)) & \
                                   (portfolio_df['timestamp'] <= (max_time + time_margin))
                    portfolio_page = portfolio_df[mask_portfolio]

                    if not portfolio_page.empty:
                        ax2.plot(portfolio_page['timestamp'], portfolio_page['portfolio_value'],
                                label='Valor del Portfolio', linewidth=2, color='green')
                        ax2.axhline(y=results_sma['initial_capital'], color='gray',
                                   linestyle='--', label='Capital Inicial', alpha=0.7, linewidth=1.5)

                    ax2.set_ylabel('Valor Portfolio (USD)', fontsize=12, fontweight='bold')
                    ax2.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                    ax2.legend(loc='best', fontsize=10)
                    ax2.grid(True, alpha=0.3)

                    # Formatear fechas
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()

                    pdf.savefig(fig, bbox_inches='tight', dpi=150)
                    plt.close()

                    if (page_num + 1) % 10 == 0:
                        print(f"    ✓ Página {page_num + 1}/{num_pages} generada...")

        total_pages = 1 + (len(trades_macd) + 49) // 50 + (len(trades_sma) + 49) // 50
        print(f"  ✅ PDF completo generado: {pdf_filename}")
        print(f"     Total: {total_pages} páginas (1 comparación + trades MACD + trades SMA)")

    except Exception as e:
        print(f"  ⚠️ Error al generar PDF completo: {e}")
        import traceback
        traceback.print_exc()

# ==================== FUNCIÓN PRINCIPAL ====================

def ejecutar_todas_estrategias_historicas():
    """Ejecuta todas las estrategias MACD y SMA con TODOS los datos históricos"""
    print("=" * 80)
    print("🚀 EJECUTANDO TODAS LAS ESTRATEGIAS - DATOS HISTÓRICOS COMPLETOS")
    print("=" * 80)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}")
    print(f"📈 Capital por operación: {CAPITAL_PER_TRADE_PCT*100:.0f}% del disponible (mínimo ${MIN_ORDER_VALUE})\n")

    client = CryptoHistoricalDataClient()

    # Obtener datos para MACD (1 hora)
    print("=" * 80)
    print("📥 OBTENIENDO DATOS HISTÓRICOS - MACD (1 hora)")
    print("=" * 80)
    try:
        df_macd = obtener_todos_los_datos(client, SYMBOL, timeframe="1Hour")
        print(f"✅ MACD: {len(df_macd):,} barras obtenidas\n")
    except Exception as e:
        print(f"❌ Error obteniendo datos MACD: {e}")
        return

    # Obtener datos para SMA (5 minutos)
    print("=" * 80)
    print("📥 OBTENIENDO DATOS HISTÓRICOS - SMA (5 minutos)")
    print("=" * 80)
    try:
        df_sma = obtener_todos_los_datos(client, SYMBOL, timeframe="5Min")
        print(f"✅ SMA: {len(df_sma):,} barras obtenidas\n")
    except Exception as e:
        print(f"❌ Error obteniendo datos SMA: {e}")
        df_sma = None

    # Ejecutar estrategias MACD
    print("=" * 80)
    print("📊 EJECUTANDO ESTRATEGIAS MACD")
    print("=" * 80)
    macd_results = []
    macd_strategies_data = []

    macd_keys = [str(i) for i in range(1, 7)]
    macd_estrategias_a_probar = {k: master_macd.ESTRATEGIAS_MACD[k]
                                 for k in macd_keys if k in master_macd.ESTRATEGIAS_MACD}

    for key, estrategia_func in macd_estrategias_a_probar.items():
        try:
            print(f"  🔬 Probando estrategia MACD {key}...", end=" ")
            df_strategy, strategy_name = estrategia_func(df_macd.copy())
            results = master_macd.ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, CAPITAL_PER_TRADE_PCT)
            metrics = master_macd.analizar_rentabilidad(results, strategy_name)
            macd_results.append(metrics)
            macd_strategies_data.append({
                'df': df_strategy,
                'results': results,
                'strategy_name': strategy_name,
                'metrics': metrics
            })
            print(f"✅ {strategy_name}: {metrics['total_return_pct']:+.4f}% "
                  f"(${metrics['total_return']:+.2f}) | "
                  f"Win Rate: {metrics['win_rate']:.1f}% | "
                  f"Trades: {metrics['total_trades']}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print()

    # Ejecutar estrategias SMA
    print("=" * 80)
    print("📊 EJECUTANDO ESTRATEGIAS SMA")
    print("=" * 80)
    sma_results = []
    sma_strategies_data = []

    if df_sma is not None:
        sma_keys = [str(i) for i in range(1, 10)]
        sma_estrategias_a_probar = {k: master_sma.ESTRATEGIAS_SMA[k]
                                    for k in sma_keys if k in master_sma.ESTRATEGIAS_SMA}

        for key, estrategia_func in sma_estrategias_a_probar.items():
            try:
                print(f"  🔬 Probando estrategia SMA {key}...", end=" ")
                df_strategy, strategy_name = estrategia_func(df_sma.copy())
                results = master_sma.ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, CAPITAL_PER_TRADE_PCT)
                metrics = master_sma.analizar_rentabilidad(results, strategy_name)
                sma_results.append(metrics)
                sma_strategies_data.append({
                    'df': df_strategy,
                    'results': results,
                    'strategy_name': strategy_name,
                    'metrics': metrics
                })
                print(f"✅ {strategy_name}: {metrics['total_return_pct']:+.4f}% "
                      f"(${metrics['total_return']:+.2f}) | "
                      f"Win Rate: {metrics['win_rate']:.1f}% | "
                      f"Trades: {metrics['total_trades']}")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("  ⚠️ No se pueden ejecutar estrategias SMA sin datos")

    print()

    # Generar PDF completo con todos los trades
    print("=" * 80)
    print("📊 GENERANDO PDF COMPLETO CON TODOS LOS TRADES")
    print("=" * 80)
    os.makedirs('back_testresultsCOMPARISON', exist_ok=True)
    generar_pdf_completo_con_todos_los_trades(macd_strategies_data, sma_strategies_data, None)

    # Resumen final
    print("\n" + "=" * 80)
    print("🏆 RESUMEN FINAL")
    print("=" * 80)

    if macd_results:
        best_macd = max(macd_results, key=lambda x: x['total_return_pct'])
        print(f"\n🥇 MEJOR MACD: {best_macd['strategy']}")
        print(f"   Retorno: {best_macd['total_return_pct']:+.4f}% (${best_macd['total_return']:+.2f})")
        print(f"   Win Rate: {best_macd['win_rate']:.1f}% | Trades: {best_macd['total_trades']}")

    if sma_results:
        best_sma = max(sma_results, key=lambda x: x['total_return_pct'])
        print(f"\n🥇 MEJOR SMA: {best_sma['strategy']}")
        print(f"   Retorno: {best_sma['total_return_pct']:+.4f}% (${best_sma['total_return']:+.2f})")
        print(f"   Win Rate: {best_sma['win_rate']:.1f}% | Trades: {best_sma['total_trades']}")

    if macd_results and sma_results:
        best_overall = max([best_macd, best_sma], key=lambda x: x['total_return_pct'])
        print(f"\n🏆 MEJOR ESTRATEGIA GENERAL: {best_overall['strategy']}")
        print(f"   Retorno: {best_overall['total_return_pct']:+.4f}% (${best_overall['total_return']:+.2f})")

    print("\n" + "=" * 80)
    print(f"📄 PDF generado: back_testresultsCOMPARISON/ALL_HISTORICAL_BEST_STRATEGIES_COMPLETE.pdf")
    print("=" * 80)

if __name__ == '__main__':
    ejecutar_todas_estrategias_historicas()

