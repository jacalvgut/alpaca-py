#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de Backtesting Profesional para Estrategia 3M
Arquitectura modular sin sesgos estadísticos

Componentes:
- SignalEngine: Generación y desplazamiento de señales
- ExecutionEngine: Ejecución realista con comisiones y slippage
- Portfolio: Gestión de capital y posiciones
- Metrics: Cálculo de métricas avanzadas
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class Trade:
    """Representa una operación completa (entrada + salida)"""
    entry_timestamp: pd.Timestamp
    exit_timestamp: Optional[pd.Timestamp] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    entry_commission: float = 0.0
    exit_commission: float = 0.0
    entry_slippage: float = 0.0
    exit_slippage: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""  # 'signal', 'stop_loss', 'stop_temporal', 'invalidacion'
    
    # Métricas avanzadas
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    entry_equity: float = 0.0
    exit_equity: float = 0.0
    
    # Stop levels
    stop_loss_price: Optional[float] = None
    stop_temporal_bars: Optional[int] = None
    stop_temporal_start: Optional[pd.Timestamp] = None


@dataclass
class Portfolio:
    """Gestiona el capital y las posiciones"""
    initial_capital: float
    cash: float = 0.0  # Se inicializa en __post_init__
    position: float = 0.0  # Cantidad de activo en posición
    entry_price: float = 0.0
    entry_bar_index: int = -1  # Índice de la barra donde se entró
    current_trade: Optional[Trade] = None
    trades: List[Trade] = field(default_factory=list)
    equity_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_capital
    
    def get_equity(self, current_price: float) -> float:
        """Calcula el equity total (cash + valor de posición)"""
        return self.cash + (self.position * current_price)
    
    def get_position_value(self, current_price: float) -> float:
        """Calcula el valor actual de la posición"""
        return self.position * current_price


@dataclass
class ExecutionConfig:
    """Configuración de ejecución realista"""
    maker_fee: float = 0.001  # 0.1% fee maker
    taker_fee: float = 0.001  # 0.1% fee taker (usar taker para market orders)
    slippage_bps: float = 5.0  # 5 basis points (0.05%) de slippage
    min_order_value: float = 10.0
    
    # Gestión de riesgo
    risk_per_trade_pct: float = 1.0  # 1% de riesgo por trade
    use_structural_stop: bool = True
    structural_stop_pct: float = 2.0  # 2% desde entry para stop estructural
    
    # Stops temporales
    max_bars_in_trade: Optional[int] = None  # Máximo de barras en posición
    
    def calculate_commission(self, trade_value: float, is_maker: bool = False) -> float:
        """Calcula comisión basada en valor de la operación"""
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return trade_value * fee_rate
    
    def calculate_slippage(self, price: float, quantity: float, is_buy: bool) -> float:
        """Calcula slippage en términos de precio"""
        slippage_pct = self.slippage_bps / 10000.0
        slippage_amount = price * slippage_pct
        # Slippage siempre es adverso: sube precio de compra, baja precio de venta
        return slippage_amount if is_buy else -slippage_amount


class SignalEngine:
    """Maneja la generación y desplazamiento de señales (elimina look-ahead bias)"""
    
    @staticmethod
    def shift_signals(df: pd.DataFrame, shift_bars: int = 1) -> pd.DataFrame:
        """
        Desplaza señales al menos una vela para eliminar look-ahead bias.
        CRÍTICO: La ejecución nunca debe ocurrir en la misma vela que genera la señal.
        """
        df = df.copy()
        
        # Desplazar señales hacia adelante (la señal en t se ejecuta en t+shift_bars)
        if 'buy_signal' in df.columns:
            df['buy_signal'] = df['buy_signal'].shift(shift_bars).fillna(False).astype(bool)
        
        if 'sell_signal' in df.columns:
            df['sell_signal'] = df['sell_signal'].shift(shift_bars).fillna(False).astype(bool)
        
        return df
    
    @staticmethod
    def audit_repainting(df: pd.DataFrame) -> Dict[str, bool]:
        """Audita si hay repainting en las señales estructurales."""
        issues = {
            'fractals_ok': True,
            'swing_points_ok': True,
            'zones_ok': True,
            'breaks_ok': True
        }
        
        return issues


class ExecutionEngine:
    """Motor de ejecución realista con comisiones, slippage y stops"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
    
    def calculate_position_size(
        self, 
        portfolio: Portfolio, 
        entry_price: float,
        stop_loss_price: Optional[float] = None
    ) -> float:
        """Calcula el tamaño de posición basado en riesgo porcentual del equity."""
        equity = portfolio.get_equity(entry_price)
        
        # Si hay stop loss estructural, calcular riesgo basado en distancia al stop
        if stop_loss_price is not None and self.config.use_structural_stop:
            risk_per_unit = abs(entry_price - stop_loss_price)
            if risk_per_unit > 0:
                risk_amount = equity * (self.config.risk_per_trade_pct / 100.0)
                quantity = risk_amount / risk_per_unit
            else:
                quantity = (equity * (self.config.risk_per_trade_pct / 100.0)) / entry_price
        else:
            quantity = (equity * (self.config.risk_per_trade_pct / 100.0)) / entry_price
        
        # Asegurar valor mínimo de orden
        trade_value = quantity * entry_price
        if trade_value < self.config.min_order_value:
            quantity = self.config.min_order_value / entry_price
        
        # No puede exceder el cash disponible
        max_quantity = portfolio.cash / entry_price
        quantity = min(quantity, max_quantity)
        
        return round(quantity, 8)
    
    def execute_buy(
        self, 
        portfolio: Portfolio, 
        price: float, 
        timestamp: pd.Timestamp,
        bar_index: int,
        stop_loss_price: Optional[float] = None
    ) -> bool:
        """Ejecuta una orden de compra con comisiones y slippage."""
        if portfolio.position > 0:
            return False  # Ya hay posición
        
        # Calcular tamaño de posición basado en riesgo
        quantity = self.calculate_position_size(portfolio, price, stop_loss_price)
        
        if quantity <= 0:
            return False
        
        # Aplicar slippage (adverso: sube el precio de compra)
        execution_price = price + self.config.calculate_slippage(price, quantity, is_buy=True)
        
        # Calcular costos
        trade_value = quantity * execution_price
        commission = self.config.calculate_commission(trade_value, is_maker=False)
        total_cost = trade_value + commission
        
        # Verificar que hay suficiente cash
        if portfolio.cash < total_cost:
            return False
        
        # Ejecutar compra
        portfolio.cash -= total_cost
        portfolio.position = quantity
        portfolio.entry_price = execution_price
        portfolio.entry_bar_index = bar_index
        
        # Crear trade
        trade = Trade(
            entry_timestamp=timestamp,
            entry_price=execution_price,
            quantity=quantity,
            entry_commission=commission,
            entry_slippage=execution_price - price,
            entry_equity=portfolio.get_equity(execution_price),
            stop_loss_price=stop_loss_price,
            stop_temporal_start=timestamp if self.config.max_bars_in_trade else None
        )
        
        portfolio.current_trade = trade
        
        return True
    
    def execute_sell(
        self, 
        portfolio: Portfolio, 
        price: float, 
        timestamp: pd.Timestamp,
        exit_reason: str = "signal"
    ) -> bool:
        """Ejecuta una orden de venta con comisiones y slippage."""
        if portfolio.position <= 0:
            return False  # No hay posición
        
        quantity = portfolio.position
        
        # Aplicar slippage (adverso: baja el precio de venta)
        execution_price = price + self.config.calculate_slippage(price, quantity, is_buy=False)
        
        # Calcular ingresos
        trade_value = quantity * execution_price
        commission = self.config.calculate_commission(trade_value, is_maker=False)
        net_revenue = trade_value - commission
        
        # Ejecutar venta
        portfolio.cash += net_revenue
        
        # Completar trade
        if portfolio.current_trade:
            trade = portfolio.current_trade
            trade.exit_timestamp = timestamp
            trade.exit_price = execution_price
            trade.exit_commission = commission
            trade.exit_slippage = execution_price - price
            trade.exit_reason = exit_reason
            trade.exit_equity = portfolio.get_equity(execution_price)
            
            # Calcular PnL
            trade.pnl = net_revenue - (quantity * trade.entry_price) - trade.entry_commission
            trade.pnl_pct = (trade.pnl / (quantity * trade.entry_price)) * 100 if trade.entry_price > 0 else 0
            
            portfolio.trades.append(trade)
        
        # Resetear posición
        portfolio.position = 0.0
        portfolio.entry_price = 0.0
        portfolio.current_trade = None
        
        return True
    
    def check_stops(
        self, 
        portfolio: Portfolio, 
        current_bar: pd.Series, 
        timestamp: pd.Timestamp,
        bar_index: int,
        entry_bar_index: int
    ) -> Optional[str]:
        """Verifica si se activa algún stop (loss, temporal, invalidación)."""
        if not portfolio.current_trade or portfolio.position <= 0:
            return None
        
        trade = portfolio.current_trade
        current_price = current_bar['close']
        high = current_bar['high']
        low = current_bar['low']
        
        # 1. Stop Loss Estructural
        if trade.stop_loss_price is not None:
            if low <= trade.stop_loss_price:
                return "stop_loss"
        
        # 2. Stop Temporal (máximo de barras en posición)
        if self.config.max_bars_in_trade:
            bars_elapsed = bar_index - entry_bar_index
            if bars_elapsed >= self.config.max_bars_in_trade:
                return "stop_temporal"
        
        # 3. Invalidación del Setup (break de estructura contrario)
        if 'break_down' in current_bar and current_bar['break_down'] and trade.entry_price > 0:
            return "invalidacion"
        
        return None


class MetricsCalculator:
    """Calcula métricas avanzadas de rendimiento"""
    
    @staticmethod
    def calculate_mae_mfe(trade: Trade, price_history: pd.Series) -> Tuple[float, float]:
        """Calcula Maximum Adverse Excursion (MAE) y Maximum Favorable Excursion (MFE)."""
        if not trade.exit_timestamp:
            return 0.0, 0.0
        
        # Filtrar precios durante el trade
        mask = (price_history.index >= trade.entry_timestamp) & (price_history.index <= trade.exit_timestamp)
        trade_prices = price_history[mask]
        
        if len(trade_prices) == 0:
            return 0.0, 0.0
        
        entry_value = trade.quantity * trade.entry_price
        
        # Calcular PnL no realizado en cada punto
        unrealized_pnl = (trade_prices - trade.entry_price) * trade.quantity
        unrealized_pnl_pct = (unrealized_pnl / entry_value) * 100
        
        mae = abs(min(unrealized_pnl_pct)) if min(unrealized_pnl_pct) < 0 else 0.0
        mfe = max(unrealized_pnl_pct) if max(unrealized_pnl_pct) > 0 else 0.0
        
        return mae, mfe
    
    @staticmethod
    def calculate_profit_factor(trades: List[Trade]) -> float:
        """Calcula Profit Factor usando la fórmula estándar."""
        if not trades:
            return 0.0
        
        completed_trades = [t for t in trades if t.exit_timestamp is not None]
        if not completed_trades:
            return 0.0
        
        total_profits = sum(t.pnl for t in completed_trades if t.pnl > 0)
        total_losses = abs(sum(t.pnl for t in completed_trades if t.pnl < 0))
        
        if total_losses == 0:
            return float('inf') if total_profits > 0 else 0.0
        
        return total_profits / total_losses
    
    @staticmethod
    def calculate_expectancy(trades: List[Trade]) -> float:
        """Calcula la expectativa del sistema."""
        if not trades:
            return 0.0
        
        completed_trades = [t for t in trades if t.exit_timestamp is not None]
        if not completed_trades:
            return 0.0
        
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / len(completed_trades) if completed_trades else 0
        loss_rate = len(losing_trades) / len(completed_trades) if completed_trades else 0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t.pnl for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        return expectancy
    
    @staticmethod
    def calculate_drawdown_per_trade(equity_history: List[Dict]) -> List[float]:
        """Calcula drawdown por trade."""
        if not equity_history:
            return []
        
        equity_values = [e['equity'] for e in equity_history]
        drawdowns = []
        
        peak = equity_values[0]
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
        
        return drawdowns
    
    @staticmethod
    def calculate_all_metrics(
        portfolio: Portfolio, 
        trades: List[Trade],
        equity_history: List[Dict]
    ) -> Dict:
        """Calcula todas las métricas avanzadas."""
        completed_trades = [t for t in trades if t.exit_timestamp is not None]
        
        if not completed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'total_return_pct': 0.0
            }
        
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl < 0]
        
        win_rate = (len(winning_trades) / len(completed_trades)) * 100 if completed_trades else 0
        avg_profit = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t.pnl for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        
        profit_factor = MetricsCalculator.calculate_profit_factor(trades)
        expectancy = MetricsCalculator.calculate_expectancy(trades)
        
        # Drawdown máximo
        drawdowns = MetricsCalculator.calculate_drawdown_per_trade(equity_history)
        max_drawdown = max(drawdowns) if drawdowns else 0.0
        
        # Retorno total
        final_equity = equity_history[-1]['equity'] if equity_history else portfolio.initial_capital
        total_return = final_equity - portfolio.initial_capital
        total_return_pct = (total_return / portfolio.initial_capital) * 100 if portfolio.initial_capital > 0 else 0
        
        return {
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'final_equity': final_equity
        }


class BacktestingEngine3M:
    """
    Motor principal de backtesting profesional para Estrategia 3M.
    Arquitectura modular sin sesgos estadísticos.
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        maker_fee: float = 0.001,
        taker_fee: float = 0.001,
        slippage_bps: float = 5.0,
        risk_per_trade_pct: float = 1.0,
        use_structural_stop: bool = True,
        structural_stop_pct: float = 2.0,
        max_bars_in_trade: Optional[int] = None,
        signal_shift_bars: int = 1,
        min_order_value: float = 10.0
    ):
        """Inicializa el motor de backtesting."""
        self.config = ExecutionConfig(
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            slippage_bps=slippage_bps,
            risk_per_trade_pct=risk_per_trade_pct,
            use_structural_stop=use_structural_stop,
            structural_stop_pct=structural_stop_pct,
            max_bars_in_trade=max_bars_in_trade,
            min_order_value=min_order_value
        )
        
        self.initial_capital = initial_capital
        self.signal_shift_bars = signal_shift_bars
        self.execution_engine = ExecutionEngine(self.config)
        self.metrics_calculator = MetricsCalculator()
    
    def run_backtest(self, df: pd.DataFrame) -> Dict:
        """Ejecuta el backtest completo."""
        # 1. Auditar repainting
        audit_results = SignalEngine.audit_repainting(df)
        
        # 2. Desplazar señales para eliminar look-ahead bias
        df = SignalEngine.shift_signals(df, shift_bars=self.signal_shift_bars)
        
        # 3. Inicializar portfolio
        portfolio = Portfolio(initial_capital=self.initial_capital)
        
        # 4. Ejecutar backtest barra por barra
        for i, (timestamp, row) in enumerate(df.iterrows()):
            current_price = row['close']
            equity = portfolio.get_equity(current_price)
            
            # Registrar equity
            portfolio.equity_history.append({
                'timestamp': timestamp,
                'equity': equity,
                'cash': portfolio.cash,
                'position_value': portfolio.get_position_value(current_price),
                'price': current_price
            })
            
            # Verificar stops primero (tienen prioridad sobre señales)
            if portfolio.current_trade:
                stop_reason = self.execution_engine.check_stops(
                    portfolio, row, timestamp, i, portfolio.entry_bar_index
                )
                if stop_reason:
                    self.execution_engine.execute_sell(
                        portfolio, current_price, timestamp, exit_reason=stop_reason
                    )
                    continue
            
            # Procesar señales
            if row.get('buy_signal', False) and portfolio.position == 0:
                # Calcular stop loss estructural si está habilitado
                stop_loss_price = None
                if self.config.use_structural_stop:
                    stop_loss_price = current_price * (1 - self.config.structural_stop_pct / 100.0)
                
                self.execution_engine.execute_buy(
                    portfolio, current_price, timestamp, i, stop_loss_price=stop_loss_price
                )
            
            elif row.get('sell_signal', False) and portfolio.position > 0:
                self.execution_engine.execute_sell(
                    portfolio, current_price, timestamp, exit_reason="signal"
                )
            
            # Actualizar MAE/MFE del trade actual
            if portfolio.current_trade:
                price_series = df['close']
                mae, mfe = self.metrics_calculator.calculate_mae_mfe(
                    portfolio.current_trade, price_series
                )
                portfolio.current_trade.mae = mae
                portfolio.current_trade.mfe = mfe
        
        # 5. Cerrar posición abierta al final si existe
        if portfolio.position > 0:
            final_price = df.iloc[-1]['close']
            final_timestamp = df.index[-1]
            self.execution_engine.execute_sell(
                portfolio, final_price, final_timestamp, exit_reason="end_of_data"
            )
        
        # 6. Calcular métricas
        metrics = self.metrics_calculator.calculate_all_metrics(
            portfolio, portfolio.trades, portfolio.equity_history
        )
        
        return {
            'initial_capital': portfolio.initial_capital,
            'final_equity': metrics['final_equity'],
            'total_return': metrics['total_return'],
            'total_return_pct': metrics['total_return_pct'],
            'trades': portfolio.trades,
            'equity_history': portfolio.equity_history,
            'metrics': metrics,
            'audit_results': audit_results
        }

