#!/usr/bin/env python3
"""
Master All Strategies - Ejecuta y compara MACD y SMA strategies
Compara las mejores estrategias MACD y SMA en una gráfica inicial
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
MAX_DAYS = 1095  # 3 años

# ==================== FUNCIONES AUXILIARES ====================

def obtener_datos(client, symbol, days=30, timeframe="1Hour"):
    """Obtiene datos históricos con paginación para períodos largos"""
    now = datetime.now(ZoneInfo("America/New_York"))
    start_time = now - timedelta(days=days)

    if timeframe == "1Hour":
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        expected_bars = days * 24
    elif timeframe == "5Min":
        tf = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)
        expected_bars = days * 24 * 12  # 12 velas de 5 min por hora
    else:
        tf = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
        expected_bars = days * 24

    MAX_BARS_PER_REQUEST = 10000

    # Si necesitamos más de 10,000 barras, usar paginación
    if expected_bars > MAX_BARS_PER_REQUEST:
        print(f"  📊 Necesitamos ~{expected_bars:,} barras, usando paginación...")
        all_dfs = []
        current_start = start_time
        total_obtained = 0

        # Calcular cuántos días por request
        if timeframe == "5Min":
            days_per_request = MAX_BARS_PER_REQUEST / (24 * 12)  # ~34.7 días por request
        else:
            days_per_request = MAX_BARS_PER_REQUEST / 24  # ~416 días por request

        num_requests = int((days / days_per_request) + 1)
        print(f"  📦 Realizando ~{num_requests} solicitudes...")

        for i in range(num_requests):
            if current_start >= now:
                break

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
                    break

                all_dfs.append(df_batch)
                total_obtained += len(df_batch)

                # Actualizar start_time para la siguiente solicitud
                last_timestamp = df_batch.index[-1]
                if isinstance(last_timestamp, pd.Timestamp):
                    current_start = last_timestamp.to_pydatetime()
                else:
                    current_start = pd.to_datetime(last_timestamp).to_pydatetime()

                # Avanzar un poco para evitar solapamiento
                if timeframe == "5Min":
                    current_start += timedelta(minutes=5)
                else:
                    current_start += timedelta(hours=1)

                # Verificar si ya tenemos suficientes datos
                if total_obtained >= expected_bars * 0.95:  # 95% de los datos esperados
                    break

                if (i + 1) % 10 == 0:
                    print(f"    ✓ Solicitud {i+1}: {total_obtained:,} barras acumuladas...")

            except Exception as e:
                print(f"    ⚠️ Error en solicitud {i+1}: {e}")
                break

        # Combinar todos los datos
        if all_dfs:
            df = pd.concat(all_dfs).sort_index()
            # Eliminar duplicados
            df = df[~df.index.duplicated(keep='first')]
            print(f"  ✅ Total obtenido: {len(df):,} barras únicas (de ~{expected_bars:,} esperadas)")
        else:
            raise Exception("No se pudieron obtener datos")
    else:
        # Solicitud única si no necesitamos paginación
        request = CryptoBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=start_time,
            limit=min(MAX_BARS_PER_REQUEST, int(expected_bars * 1.2))
        )

        bars = client.get_crypto_bars(request)
        df = bars.df

        if isinstance(df.index, pd.MultiIndex):
            df = df.loc[symbol]

    return df.sort_index()

def generar_comparacion_inicial(macd_strategies_data, sma_strategies_data, df_original, days):
    """Genera una gráfica comparativa inicial con las mejores estrategias MACD y SMA"""
    try:
        os.makedirs('back_testresultsCOMPARISON', exist_ok=True)

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
            print("  ⚠️ No hay datos para comparar")
            return

        # Crear figura comparativa
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

        # Gráfico 1: Precio BTC/USD
        ax1.plot(df_original.index, df_original['close'],
                label='Precio BTC/USD', linewidth=2, color='black', alpha=0.9, zorder=1)

        # Gráfico 2: Comparar portfolios de las mejores estrategias
        colors_comparison = ['#FF6B35', '#004E89']  # Naranja para MACD, Azul para SMA

        if best_macd_data:
            portfolio_macd = pd.DataFrame(best_macd_data['results']['portfolio_values'])
            portfolio_macd['timestamp'] = pd.to_datetime(portfolio_macd['timestamp'])
            ax2.plot(portfolio_macd['timestamp'], portfolio_macd['portfolio_value'],
                    label=f"Mejor MACD: {best_macd_data['strategy_name']} (${best_macd_data['metrics']['total_return']:+.2f})",
                    linewidth=3, color=colors_comparison[0], alpha=0.8)

        if best_sma_data:
            portfolio_sma = pd.DataFrame(best_sma_data['results']['portfolio_values'])
            portfolio_sma['timestamp'] = pd.to_datetime(portfolio_sma['timestamp'])
            ax2.plot(portfolio_sma['timestamp'], portfolio_sma['portfolio_value'],
                    label=f"Mejor SMA: {best_sma_data['strategy_name']} (${best_sma_data['metrics']['total_return']:+.2f})",
                    linewidth=3, color=colors_comparison[1], alpha=0.8)

        ax2.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--',
                   label='Capital Inicial', alpha=0.8, linewidth=2)

        ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
        ax1.set_title(f'{SYMBOL} - COMPARACIÓN MEJORES ESTRATEGIAS MACD vs SMA ({days} días)',
                     fontsize=16, fontweight='bold', pad=20)
        ax1.legend(loc='best', fontsize=11, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')

        ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
        ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
        ax2.legend(loc='best', fontsize=11, framealpha=0.9)
        ax2.grid(True, alpha=0.3, linestyle='--')

        # Formatear fechas
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, days//30)))
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Guardar gráfica comparativa
        comparison_filename = os.path.join('back_testresultsCOMPARISON',
                                          f'comparison_BEST_MACD_vs_SMA_{days}dias.png')
        plt.savefig(comparison_filename, dpi=150, bbox_inches='tight')
        print(f"  ✅ Gráfica comparativa guardada: {comparison_filename}")
        plt.close()

    except Exception as e:
        print(f"  ⚠️ Error al generar gráfica comparativa: {e}")
        import traceback
        traceback.print_exc()

def generar_comparacion_pdf_detallada(macd_strategies_data, sma_strategies_data, df_original, days):
    """Genera un PDF con comparación detallada de las mejores estrategias MACD y SMA"""
    try:
        pdf_filename = os.path.join('back_testresultsCOMPARISON',
                                    f'comparison_MACD_vs_SMA_{days}dias.pdf')
        print(f"\n  📊 Generando PDF comparativo detallado...")

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
            print("  ⚠️ No hay datos para comparar")
            return

        colors_comparison = ['#FF6B35', '#004E89']  # Naranja para MACD, Azul para SMA

        with PdfPages(pdf_filename) as pdf:
            # ========== PÁGINA 1: COMPARACIÓN DE LAS MEJORES ESTRATEGIAS ==========
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), sharex=True)

            # Gráfico 1: Precio con señales de ambas mejores estrategias
            ax1.plot(df_original.index, df_original['close'],
                    label='Precio BTC/USD', linewidth=2, color='black', alpha=0.9, zorder=1)

            if best_macd_data:
                df_macd = best_macd_data['df']
                macd_name = best_macd_data['strategy_name']

                # Señales MACD
                buy_signals_macd = df_macd[df_macd.get('buy_signal', False)]
                if not buy_signals_macd.empty:
                    ax1.scatter(buy_signals_macd.index, buy_signals_macd['close'],
                               color=colors_comparison[0], marker='^', s=100,
                               label=f'{macd_name} - Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)

                sell_signals_macd = df_macd[df_macd.get('sell_signal', False)]
                if not sell_signals_macd.empty:
                    ax1.scatter(sell_signals_macd.index, sell_signals_macd['close'],
                               color=colors_comparison[0], marker='v', s=100,
                               label=f'{macd_name} - Venta',
                               zorder=5, edgecolors='darkred', linewidths=0.8, alpha=0.7)

            if best_sma_data:
                df_sma = best_sma_data['df']
                sma_name = best_sma_data['strategy_name']

                # Señales SMA
                buy_signals_sma = df_sma[df_sma.get('buy_signal', False)]
                if not buy_signals_sma.empty:
                    ax1.scatter(buy_signals_sma.index, buy_signals_sma['close'],
                               color=colors_comparison[1], marker='^', s=100,
                               label=f'{sma_name} - Compra',
                               zorder=5, edgecolors='darkgreen', linewidths=0.8, alpha=0.7)

                sell_signals_sma = df_sma[df_sma.get('sell_signal', False)]
                if not sell_signals_sma.empty:
                    ax1.scatter(sell_signals_sma.index, sell_signals_sma['close'],
                               color=colors_comparison[1], marker='v', s=100,
                               label=f'{sma_name} - Venta',
                               zorder=5, edgecolors='darkred', linewidths=0.8, alpha=0.7)

            ax1.set_ylabel('Precio (USD)', fontsize=13, fontweight='bold')
            title_str = f'{SYMBOL} - MEJORES ESTRATEGIAS MACD vs SMA ({days} días)'
            ax1.set_title(title_str, fontsize=16, fontweight='bold', pad=20)
            ax1.legend(loc='best', fontsize=10, framealpha=0.9, ncol=2)
            ax1.grid(True, alpha=0.3, linestyle='--')

            # Gráfico 2: Comparar portfolios
            if best_macd_data:
                portfolio_macd = pd.DataFrame(best_macd_data['results']['portfolio_values'])
                portfolio_macd['timestamp'] = pd.to_datetime(portfolio_macd['timestamp'])
                ax2.plot(portfolio_macd['timestamp'], portfolio_macd['portfolio_value'],
                        label=f"{best_macd_data['strategy_name']} (${best_macd_data['metrics']['total_return']:+.2f})",
                        linewidth=2.5, color=colors_comparison[0], alpha=0.8)

            if best_sma_data:
                portfolio_sma = pd.DataFrame(best_sma_data['results']['portfolio_values'])
                portfolio_sma['timestamp'] = pd.to_datetime(portfolio_sma['timestamp'])
                ax2.plot(portfolio_sma['timestamp'], portfolio_sma['portfolio_value'],
                        label=f"{best_sma_data['strategy_name']} (${best_sma_data['metrics']['total_return']:+.2f})",
                        linewidth=2.5, color=colors_comparison[1], alpha=0.8)

            ax2.axhline(y=INITIAL_CAPITAL, color='gray', linestyle='--',
                       label='Capital Inicial', alpha=0.8, linewidth=2)

            ax2.set_ylabel('Valor Portfolio (USD)', fontsize=13, fontweight='bold')
            ax2.set_xlabel('Fecha', fontsize=13, fontweight='bold')
            ax2.legend(loc='best', fontsize=11, framealpha=0.9)
            ax2.grid(True, alpha=0.3, linestyle='--')

            # Formatear fechas
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, days//30)))
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            pdf.savefig(fig, bbox_inches='tight', dpi=150)
            plt.close()

        print(f"  ✅ PDF comparativo generado: {pdf_filename}")

    except Exception as e:
        print(f"  ⚠️ Error al generar PDF comparativo: {e}")
        import traceback
        traceback.print_exc()

# ==================== FUNCIÓN PRINCIPAL ====================

def ejecutar_todas_estrategias(days=30, macd_strategies='all', sma_strategies='all'):
    """Ejecuta todas las estrategias MACD y SMA y compara resultados"""
    print("=" * 80)
    print("🚀 EJECUTANDO TODAS LAS ESTRATEGIAS - MACD y SMA")
    print("=" * 80)
    print(f"\n📊 Símbolo: {SYMBOL}")
    print(f"📅 Período: Últimos {days} días ({days/365:.2f} años)")
    print(f"💰 Capital inicial: ${INITIAL_CAPITAL:,.2f}\n")

    if days > MAX_DAYS:
        print(f"⚠️ Advertencia: {days} días excede el máximo recomendado ({MAX_DAYS} días = 3 años)")
        print(f"   Continuando de todas formas...\n")

    client = CryptoHistoricalDataClient()
    print("📥 Obteniendo datos históricos...")

    # Obtener datos para MACD (1 hora) y SMA (5 minutos)
    try:
        df_macd = obtener_datos(client, SYMBOL, days=days, timeframe="1Hour")
        expected_bars_macd = days * 24
        print(f"✅ MACD: {len(df_macd)} barras obtenidas (esperadas: ~{expected_bars_macd}, timeframe: 1 hora)\n")
    except Exception as e:
        print(f"❌ Error obteniendo datos MACD: {e}")
        return

    try:
        df_sma = obtener_datos(client, SYMBOL, days=days, timeframe="5Min")
        expected_bars_sma = days * 24 * 12
        print(f"✅ SMA: {len(df_sma)} barras obtenidas (esperadas: ~{expected_bars_sma}, timeframe: 5 minutos)\n")
    except Exception as e:
        print(f"❌ Error obteniendo datos SMA: {e}")
        df_sma = None

    # Ejecutar estrategias MACD
    print("=" * 80)
    print("📊 EJECUTANDO ESTRATEGIAS MACD")
    print("=" * 80)
    macd_results = []
    macd_strategies_data = []

    try:
        # Convertir estrategias a lista si es necesario
        if macd_strategies == 'all':
            macd_keys = [str(i) for i in range(1, 7)]
        else:
            macd_keys = macd_strategies.split(',') if isinstance(macd_strategies, str) else macd_strategies

        macd_estrategias_a_probar = {k: master_macd.ESTRATEGIAS_MACD[k]
                                     for k in macd_keys if k in master_macd.ESTRATEGIAS_MACD}

        for key, estrategia_func in macd_estrategias_a_probar.items():
            try:
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
                print(f"  ✅ {strategy_name}: {metrics['total_return_pct']:+.4f}% "
                      f"(${metrics['total_return']:+.2f}) | "
                      f"Win Rate: {metrics['win_rate']:.1f}% | "
                      f"Trades: {metrics['total_trades']}")
            except Exception as e:
                print(f"  ❌ Error en estrategia MACD {key}: {e}")
    except Exception as e:
        print(f"❌ Error ejecutando estrategias MACD: {e}")

    print()

    # Ejecutar estrategias SMA
    print("=" * 80)
    print("📊 EJECUTANDO ESTRATEGIAS SMA")
    print("=" * 80)
    sma_results = []
    sma_strategies_data = []

    try:
        # Convertir estrategias a lista si es necesario
        if sma_strategies == 'all':
            sma_keys = [str(i) for i in range(1, 10)]
        else:
            sma_keys = sma_strategies.split(',') if isinstance(sma_strategies, str) else sma_strategies

        sma_estrategias_a_probar = {k: master_sma.ESTRATEGIAS_SMA[k]
                                    for k in sma_keys if k in master_sma.ESTRATEGIAS_SMA}

        if df_sma is None:
            print("  ⚠️ No se pueden ejecutar estrategias SMA sin datos de 5 minutos")
        else:
            for key, estrategia_func in sma_estrategias_a_probar.items():
                try:
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
                    print(f"  ✅ {strategy_name}: {metrics['total_return_pct']:+.4f}% "
                          f"(${metrics['total_return']:+.2f}) | "
                          f"Win Rate: {metrics['win_rate']:.1f}% | "
                          f"Trades: {metrics['total_trades']}")
                except Exception as e:
                    print(f"  ❌ Error en estrategia SMA {key}: {e}")
                    import traceback
                    traceback.print_exc()
    except Exception as e:
        print(f"❌ Error ejecutando estrategias SMA: {e}")

    print()

    # Generar gráfica comparativa inicial (usar df_macd para el precio base)
    print("=" * 80)
    print("📊 GENERANDO COMPARACIÓN INICIAL")
    print("=" * 80)
    df_comparison = df_macd  # Usar datos de 1 hora para comparación
    generar_comparacion_inicial(macd_strategies_data, sma_strategies_data, df_comparison, days)
    generar_comparacion_pdf_detallada(macd_strategies_data, sma_strategies_data, df_comparison, days)

    # Generar gráficas completas para las mejores estrategias si es 3 años
    if days >= 1095:
        print("\n" + "=" * 80)
        print("📊 GENERANDO GRÁFICAS COMPLETAS PARA LAS MEJORES ESTRATEGIAS (3 AÑOS)")
        print("=" * 80)

        # Identificar mejores estrategias
        best_macd_key = None
        best_sma_key = None
        best_macd_data = None
        best_sma_data = None

        if macd_strategies_data:
            best_macd_data = max(macd_strategies_data,
                                key=lambda x: x['metrics']['total_return_pct'])
            best_macd_name = best_macd_data['strategy_name']
            print(f"  🏆 Mejor MACD identificado: {best_macd_name}")

            # Encontrar la key correspondiente comparando nombres con las estrategias ejecutadas
            # Buscar en macd_results que tiene la misma estructura
            for i, macd_result in enumerate(macd_results):
                if macd_result['strategy'] == best_macd_name:
                    # Obtener la key del índice en macd_keys
                    if i < len(macd_keys):
                        best_macd_key = macd_keys[i]
                        print(f"  ✅ Key encontrada: {best_macd_key}")
                        break

        if sma_strategies_data:
            best_sma_data = max(sma_strategies_data,
                               key=lambda x: x['metrics']['total_return_pct'])
            best_sma_name = best_sma_data['strategy_name']
            print(f"  🏆 Mejor SMA identificado: {best_sma_name}")

            # Encontrar la key correspondiente comparando nombres con las estrategias ejecutadas
            # Buscar en sma_results que tiene la misma estructura
            for i, sma_result in enumerate(sma_results):
                if sma_result['strategy'] == best_sma_name:
                    # Obtener la key del índice en sma_keys
                    if i < len(sma_keys):
                        best_sma_key = sma_keys[i]
                        print(f"  ✅ Key encontrada: {best_sma_key}")
                        break

        # Generar gráficas para mejor MACD con 3 años completos
        if best_macd_key and best_macd_data:
            try:
                print(f"\n📊 Generando gráficas completas para mejor MACD: {best_macd_data['strategy_name']}")
                print(f"   Key: {best_macd_key} | Período: {days} días (3 años)")
                # Usar los datos de 3 años ya obtenidos (1 hora)
                df_strategy, strategy_name = master_macd.ESTRATEGIAS_MACD[best_macd_key](df_macd.copy())
                results = master_macd.ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, CAPITAL_PER_TRADE_PCT)
                # Generar visualización con 365 días para PDFs mensuales
                master_macd.visualizar_estrategia(df_strategy, results, strategy_name, days=365, save_monthly=True, multiple_strategies=False)
                print(f"  ✅ Gráficas MACD generadas para {strategy_name}")
            except Exception as e:
                print(f"  ⚠️ Error generando gráficas MACD: {e}")
                import traceback
                traceback.print_exc()

        # Generar gráficas para mejor SMA con 3 años completos (5 minutos)
        if best_sma_key and best_sma_data and df_sma is not None:
            try:
                print(f"\n📊 Generando gráficas completas para mejor SMA: {best_sma_data['strategy_name']}")
                print(f"   Key: {best_sma_key} | Período: {days} días (3 años) | Timeframe: 5 minutos")
                # Usar los datos de 3 años ya obtenidos (5 minutos)
                df_strategy, strategy_name = master_sma.ESTRATEGIAS_SMA[best_sma_key](df_sma.copy())
                results = master_sma.ejecutar_backtest(df_strategy, INITIAL_CAPITAL, MIN_ORDER_VALUE, CAPITAL_PER_TRADE_PCT)
                # Generar visualización con 365 días para PDFs mensuales
                master_sma.visualizar_estrategia(df_strategy, results, strategy_name, days=365, save_monthly=True, multiple_strategies=False)
                print(f"  ✅ Gráficas SMA generadas para {strategy_name}")
            except Exception as e:
                print(f"  ⚠️ Error generando gráficas SMA: {e}")
                import traceback
                traceback.print_exc()

    # Ejecutar backtesting completo para generar PDFs individuales si es 365 días o más (pero menos de 3 años)
    elif days >= 365:
        print("\n" + "=" * 80)
        print(f"📊 GENERANDO PDFs INDIVIDUALES ({days} días)")
        print("=" * 80)

        # Ejecutar MACD completo (solo si hay estrategias seleccionadas)
        if macd_keys:
            try:
                print("\n📊 Generando PDFs MACD...")
                master_macd.backtesting(macd_keys, days=365)
            except Exception as e:
                print(f"  ⚠️ Error generando PDFs MACD: {e}")

        # Ejecutar SMA completo (solo si hay estrategias seleccionadas)
        if sma_keys:
            try:
                print("\n📊 Generando PDFs SMA...")
                master_sma.backtesting(sma_keys, days=365)
            except Exception as e:
                print(f"  ⚠️ Error generando PDFs SMA: {e}")

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

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Master All Strategies - Ejecuta MACD y SMA')
    parser.add_argument('--days', type=int, default=1095,
                       help='Número de días para backtesting (default: 1095 = 3 años)')
    parser.add_argument('--macd', type=str, default='all',
                       help='Estrategias MACD a ejecutar (1-6 o "all", default: all)')
    parser.add_argument('--sma', type=str, default='all',
                       help='Estrategias SMA a ejecutar (1-9 o "all", default: all)')

    args = parser.parse_args()

    ejecutar_todas_estrategias(
        days=args.days,
        macd_strategies=args.macd,
        sma_strategies=args.sma
    )

