#!/usr/bin/env python3
"""
Lista todos los gráficos de backtesting disponibles
"""

import os
from pathlib import Path

def listar_graficos():
    """Lista todos los gráficos en backtest_results"""
    results_dir = Path('backtest_results')

    if not results_dir.exists():
        print("❌ La carpeta backtest_results no existe")
        return

    print("=" * 70)
    print("📊 GRÁFICOS DE BACKTESTING DISPONIBLES")
    print("=" * 70)

    # Obtener todos los PNG
    png_files = list(results_dir.glob('*.png'))

    if not png_files:
        print("\n⚠️ No hay gráficos en backtest_results/")
        print("   Ejecuta: python3 backtesting_estrategias.py")
        return

    # Separar por tipo
    ema_files = [f for f in png_files if 'EMA' in f.name and 'SMA' not in f.name]
    sma_files = [f for f in png_files if 'SMA' in f.name]
    other_files = [f for f in png_files if 'EMA' not in f.name and 'SMA' not in f.name]

    print(f"\n📈 Total de gráficos: {len(png_files)}")
    print(f"   - EMA: {len(ema_files)}")
    print(f"   - SMA: {len(sma_files)} ⭐")
    print(f"   - Otros: {len(other_files)}")

    if sma_files:
        print("\n" + "=" * 70)
        print("📊 GRÁFICOS SMA (Simple Moving Average)")
        print("=" * 70)
        for i, file in enumerate(sorted(sma_files), 1):
            size_kb = file.stat().st_size / 1024
            print(f"{i}. {file.name}")
            print(f"   📁 {file}")
            print(f"   📏 Tamaño: {size_kb:.1f} KB")
            print()

    if ema_files:
        print("=" * 70)
        print("📊 GRÁFICOS EMA (Exponential Moving Average)")
        print("=" * 70)
        for i, file in enumerate(sorted(ema_files), 1):
            size_kb = file.stat().st_size / 1024
            print(f"{i}. {file.name} ({size_kb:.1f} KB)")

    if other_files:
        print("\n" + "=" * 70)
        print("📊 OTROS GRÁFICOS")
        print("=" * 70)
        for i, file in enumerate(sorted(other_files), 1):
            size_kb = file.stat().st_size / 1024
            print(f"{i}. {file.name} ({size_kb:.1f} KB)")

    print("\n" + "=" * 70)
    print("💡 Para abrir un gráfico en macOS:")
    print(f"   open backtest_results/{sma_files[0].name if sma_files else 'nombre_archivo.png'}")
    print("=" * 70)

if __name__ == "__main__":
    listar_graficos()


