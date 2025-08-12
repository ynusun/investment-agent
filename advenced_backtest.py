# advanced_backtest.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from data.fetch_binance import fetch_binance_ohlcv
from strategies.rsi_strategy import compute_rsi_signal
from strategies.sma_crossover import compute_sma_crossover_signal
from db import supabase, get_strategies
import json

class AdvancedBacktester:
    def __init__(self, initial_balance=10000, fee_rate=0.001, slippage=0.001):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.slippage = slippage
        
        # Performans metrikleri
        self.trades = []
        self.portfolio_values = []
        self.drawdowns = []
        
    def backtest_strategy(self, 
                         strategy: Dict[str, Any], 
                         symbol: str = "BTC/USDT", 
                         timeframe: str = "1h", 
                         lookback_days: int = 90) -> Dict[str, Any]:
        """Gelişmiş backtest gerçekleştir"""
        
        print(f"[BACKTEST] {strategy['name']} stratejisi test ediliyor...")
        print(f"[PARAMS] Symbol: {symbol}, Timeframe: {timeframe}, Days: {lookback_days}")
        
        # Veri çek
        ohlcv = fetch_binance_ohlcv(symbol, timeframe, limit=lookback_days*24)
        if not ohlcv or len(ohlcv) < 100:
            return {"error": "Yetersiz veri"}
        
        df = pd.DataFrame(ohlcv)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Backtest değişkenleri
        balance = self.initial_balance
        position = None  # None, 'long', 'short'
        position_size = 0
        entry_price = 0
        peak_balance = self.initial_balance
        
        # Performans tracking
        trades = []
        daily_returns = []
        portfolio_values = [self.initial_balance]
        
        strategy_params = strategy.get('parameters', {})
        
        # Her veri noktası için döngü
        for i in range(50, len(df)):  # İlk 50 veri teknik indikatörler için
            current_data = df.iloc[:i+1].to_dict(orient='records')
            current_price = df.iloc[i]['close']
            current_time = df.iloc[i]['timestamp']
            
            # Strateji sinyalini hesapla
            signal, indicator_value = self._get_strategy_signal(
                strategy['name'], current_data, strategy_params
            )
            
            # Trade execution logic
            if signal == "buy" and position is None:
                # Long pozisyon aç
                position = "long"
                position_size = (balance * 0.95) / current_price  # %95'ini kullan
                entry_price = current_price * (1 + self.slippage)  # Slippage ekle
                fee = position_size * entry_price * self.fee_rate
                balance -= fee
                
                trade_record = {
                    'entry_time': current_time,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'side': 'long',
                    'strategy': strategy['name'],
                    'indicator_value': indicator_value
                }
                
            elif signal == "sell" and position == "long":
                # Long pozisyonu kapat
                exit_price = current_price * (1 - self.slippage)
                fee = position_size * exit_price * self.fee_rate
                pnl = (exit_price - entry_price) * position_size - fee
                balance += pnl + (entry_price * position_size)
                
                # Trade'i kaydet
                trade_record.update({
                    'exit_time': current_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return_pct': (pnl / (entry_price * position_size)) * 100,
                    'hold_time': (current_time - trade_record['entry_time']).total_seconds() / 3600  # saat
                })
                trades.append(trade_record)
                
                position = None
                position_size = 0
                
            elif signal == "sell" and position is None:
                # Short pozisyon aç (eğer destekleniyorsa)
                position = "short"
                position_size = (balance * 0.95) / current_price
                entry_price = current_price * (1 - self.slippage)
                fee = position_size * entry_price * self.fee_rate
                balance -= fee
                
                trade_record = {
                    'entry_time': current_time,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'side': 'short',
                    'strategy': strategy['name'],
                    'indicator_value': indicator_value
                }
                
            elif signal == "buy" and position == "short":
                # Short pozisyonu kapat
                exit_price = current_price * (1 + self.slippage)
                fee = position_size * exit_price * self.fee_rate
                pnl = (entry_price - exit_price) * position_size - fee
                balance += pnl + (entry_price * position_size)
                
                trade_record.update({
                    'exit_time': current_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return_pct': (pnl / (entry_price * position_size)) * 100,
                    'hold_time': (current_time - trade_record['entry_time']).total_seconds() / 3600
                })
                trades.append(trade_record)
                
                position = None
                position_size = 0
            
            # Portfolio değerini hesapla
            if position == "long":
                portfolio_value = balance + (position_size * current_price)
            elif position == "short":
                portfolio_value = balance + (position_size * (2 * entry_price - current_price))
            else:
                portfolio_value = balance
                
            portfolio_values.append(portfolio_value)
            
            # Peak tracking (drawdown için)
            if portfolio_value > peak_balance:
                peak_balance = portfolio_value
        
        # Son pozisyonu kapat
        if position is not None:
            current_price = df.iloc[-1]['close']
            if position == "long":
                exit_price = current_price * (1 - self.slippage)
                pnl = (exit_price - entry_price) * position_size
                balance += pnl + (entry_price * position_size)
            elif position == "short":
                exit_price = current_price * (1 + self.slippage)
                pnl = (entry_price - exit_price) * position_size
                balance += pnl + (entry_price * position_size)
        
        # Performans metriklerini hesapla
        metrics = self._calculate_performance_metrics(trades, portfolio_values, df)
        
        # Sonuçları döndür
        result = {
            'strategy_id': strategy.get('id'),
            'strategy_name': strategy['name'],
            'symbol': symbol,
            'timeframe': timeframe,
            'start_date': df.iloc[50]['timestamp'].isoformat(),
            'end_date': df.iloc[-1]['timestamp'].isoformat(),
            'initial_balance': self.initial_balance,
            'final_balance': balance,
            'total_return': balance - self.initial_balance,
            'total_return_pct': ((balance - self.initial_balance) / self.initial_balance) * 100,
            'total_trades': len(trades),
            'parameters': strategy_params,
            **metrics
        }
        
        # Veritabanına kaydet
        self._save_backtest_result(result, trades)
        
        return result
    
    def _get_strategy_signal(self, strategy_name: str, data: List[Dict], params: Dict) -> tuple:
        """Strateji sinyalini al"""
        try:
            if "RSI" in strategy_name:
                return compute_rsi_signal(
                    data, 
                    rsi_period=params.get('rsi_period', 14)
                )
            elif "SMA" in strategy_name:
                return compute_sma_crossover_signal(
                    data,
                    short_period=params.get('short_period', 10),
                    long_period=params.get('long_period', 50)
                )
            else:
                return "hold", None
        except Exception as e:
            return "hold", None
    
    def _calculate_performance_metrics(self, trades: List[Dict], portfolio_values: List[float], df: pd.DataFrame) -> Dict:
        """Performans metriklerini hesapla"""
        if not trades:
            return {
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'avg_trade_pnl': 0,
                'avg_trade_return_pct': 0,
                'avg_hold_time_hours': 0,
                'volatility': 0,
                'calmar_ratio': 0
            }
        
        trade_pnls = [t['pnl'] for t in trades]
        trade_returns = [t['return_pct'] for t in trades]
        
        # Win rate
        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl <= 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown hesaplama
        peak = portfolio_values[0]
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = peak - value
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct
        
        # Returns için günlük değişimleri hesapla
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            daily_returns.append(daily_return)
        
        # Sharpe ratio (risk-free rate = 0 varsayım)
        if daily_returns:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0  # Yıllık
        else:
            sharpe_ratio = 0
            std_return = 0
        
        # Calmar ratio
        annual_return = ((portfolio_values[-1] / portfolio_values[0]) ** (252 / len(portfolio_values))) - 1
        calmar_ratio = annual_return / (max_drawdown_pct / 100) if max_drawdown_pct > 0 else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'avg_trade_pnl': np.mean(trade_pnls),
            'avg_trade_return_pct': np.mean(trade_returns),
            'avg_hold_time_hours': np.mean([t['hold_time'] for t in trades]),
            'volatility': std_return * np.sqrt(252),  # Yıllık volatilite
            'calmar_ratio': calmar_ratio,
            'total_fees': sum([abs(t['pnl']) * self.fee_rate for t in trades])
        }
    
    def _save_backtest_result(self, result: Dict, trades: List[Dict]):
        """Backtest sonucunu veritabanına kaydet"""
        try:
            # Ana result'ı kaydet
            backtest_data = {
                'strategy_id': result.get('strategy_id'),
                'symbol': result['symbol'],
                'start_date': result['start_date'],
                'end_date': result['end_date'],
                'initial_balance': result['initial_balance'],
                'final_balance': result['final_balance'],
                'total_return_pct': result['total_return_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown_pct'],
                'win_rate': result['win_rate'],
                'total_trades': result['total_trades'],
                'profit_factor': result['profit_factor'],
                'parameters': result['parameters'],
                'trade_log': trades
            }
            
            supabase.table("backtest_results").insert(backtest_data).execute()
            print(f"[BACKTEST] Sonuç veritabanına kaydedildi: {result['strategy_name']}")
            
        except Exception as e:
            print(f"[BACKTEST ERROR] Sonuç kaydedilemedi: {e}")
    
    def walk_forward_analysis(self, strategy: Dict, symbol: str = "BTC/USDT", 
                             train_days: int = 30, test_days: int = 7, 
                             total_periods: int = 12) -> Dict[str, Any]:
        """Walk-forward analizi gerçekleştir"""
        print(f"[WALK FORWARD] {strategy['name']} için analiz başlatılıyor...")
        
        results = []
        current_date = datetime.now()
        
        for period in range(total_periods):
            # Test dönemi
            test_end = current_date - timedelta(days=period * test_days)
            test_start = test_end - timedelta(days=test_days)
            
            # Training dönemi
            train_end = test_start
            train_start = train_end - timedelta(days=train_days)
            
            print(f"[WF Period {period+1}] Train: {train_start.date()} - {train_end.date()}, Test: {test_start.date()} - {test_end.date()}")
            
            # Training data ile optimize et (basit örnek)
            train_result = self.backtest_strategy(strategy, symbol, "1h", train_days)
            
            # Test data ile doğrula
            test_result = self.backtest_strategy(strategy, symbol, "1h", test_days)
            
            results.append({
                'period': period + 1,
                'train_return': train_result.get('total_return_pct', 0),
                'test_return': test_result.get('total_return_pct', 0),
                'train_sharpe': train_result.get('sharpe_ratio', 0),
                'test_sharpe': test_result.get('sharpe_ratio', 0),
                'train_max_dd': train_result.get('max_drawdown_pct', 0),
                'test_max_dd': test_result.get('max_drawdown_pct', 0)
            })
        
        # Sonuçları analiz et
        avg_test_return = np.mean([r['test_return'] for r in results])
        avg_test_sharpe = np.mean([r['test_sharpe'] for r in results])
        consistency = len([r for r in results if r['test_return'] > 0]) / len(results)
        
        return {
            'strategy_name': strategy['name'],
            'total_periods': total_periods,
            'avg_test_return': avg_test_return,
            'avg_test_sharpe': avg_test_sharpe,
            'consistency_score': consistency,
            'period_results': results
        }
    
    def monte_carlo_simulation(self, strategy: Dict, symbol: str = "BTC/USDT", 
                              simulations: int = 1000) -> Dict[str, Any]:
        """Monte Carlo simulasyonu"""
        print(f"[MONTE CARLO] {simulations} simulasyon çalıştırılıyor...")
        
        # Önce gerçek backtest yap
        base_result = self.backtest_strategy(strategy, symbol)
        if 'error' in base_result:
            return base_result
        
        # Veriyi al
        ohlcv = fetch_binance_ohlcv(symbol, "1h", limit=2000)
        df = pd.DataFrame(ohlcv)
        
        # Returns hesapla
        df['returns'] = df['close'].pct_change().dropna()
        daily_returns = df['returns'].dropna().values
        
        simulation_results = []
        
        for i in range(simulations):
            # Returns'ları shuffle et
            shuffled_returns = np.random.choice(daily_returns, size=len(daily_returns), replace=True)
            
            # Yeni fiyat serisi oluştur
            synthetic_prices = [df['close'].iloc[0]]
            for ret in shuffled_returns:
                new_price = synthetic_prices[-1] * (1 + ret)
                synthetic_prices.append(new_price)
            
            # Synthetic data ile backtest
            synthetic_ohlcv = []
            for j, price in enumerate(synthetic_prices[1:]):
                synthetic_ohlcv.append({
                    'timestamp': df['timestamp'].iloc[j] if j < len(df) else df['timestamp'].iloc[-1],
                    'open': synthetic_prices[j],
                    'high': max(synthetic_prices[j], price),
                    'low': min(synthetic_prices[j], price),
                    'close': price,
                    'volume': df['volume'].iloc[j] if j < len(df) else df['volume'].iloc[-1]
                })
            
            # Mini backtest
            sim_result = self._mini_backtest(strategy, synthetic_ohlcv)
            simulation_results.append(sim_result['total_return_pct'])
        
        # Sonuçları analiz et
        sorted_returns = sorted(simulation_results)
        
        return {
            'strategy_name': strategy['name'],
            'simulations': simulations,
            'mean_return': np.mean(simulation_results),
            'std_return': np.std(simulation_results),
            'var_95': np.percentile(sorted_returns, 5),  # %95 VaR
            'var_99': np.percentile(sorted_returns, 1),  # %99 VaR
            'max_return': max(simulation_results),
            'min_return': min(simulation_results),
            'positive_scenarios': len([r for r in simulation_results if r > 0]) / len(simulation_results),
            'actual_return': base_result['total_return_pct']
        }
    
    def _mini_backtest(self, strategy: Dict, ohlcv_data: List[Dict]) -> Dict:
        """Monte Carlo için hızlı backtest"""
        balance = self.initial_balance
        position = None
        entry_price = 0
        
        strategy_params = strategy.get('parameters', {})
        
        for i in range(50, len(ohlcv_data)):
            current_data = ohlcv_data[:i+1]
            current_price = ohlcv_data[i]['close']
            
            signal, _ = self._get_strategy_signal(strategy['name'], current_data, strategy_params)
            
            if signal == "buy" and position is None:
                position = "long"
                entry_price = current_price
            elif signal == "sell" and position == "long":
                balance += (current_price - entry_price) / entry_price * balance * 0.95
                position = None
        
        return {
            'final_balance': balance,
            'total_return_pct': ((balance - self.initial_balance) / self.initial_balance) * 100
        }

def run_comprehensive_backtest(strategy_name: str = None):
    """Kapsamlı backtest çalıştır"""
    backtester = AdvancedBacktester()
    
    # Stratejileri al
    strategies = get_strategies()
    if strategy_name:
        strategies = [s for s in strategies if strategy_name.lower() in s['name'].lower()]
    
    all_results = []
    
    for strategy in strategies[:5]:  # İlk 5 stratejiyi test et
        print(f"\n{'='*60}")
        print(f"[COMPREHENSIVE] {strategy['name']} stratejisi test ediliyor...")
        
        # 1. Normal backtest
        normal_result = backtester.backtest_strategy(strategy)
        if 'error' not in normal_result:
            all_results.append(normal_result)
            
            # 2. Walk-forward analizi
            wf_result = backtester.walk_forward_analysis(strategy)
            print(f"[WF] Consistency Score: {wf_result['consistency_score']:.2f}")
            
            # 3. Monte Carlo (daha az simulasyon)
            mc_result = backtester.monte_carlo_simulation(strategy, simulations=100)
            print(f"[MC] VaR 95%: {mc_result['var_95']:.2f}%")
    
    # En iyi stratejileri listele
    if all_results:
        sorted_results = sorted(all_results, 
                              key=lambda x: x.get('sharpe_ratio', 0) * x.get('total_return_pct', 0), 
                              reverse=True)
        
        print(f"\n{'='*60}")
        print("[BEST STRATEGIES] Sharpe * Return sıralaması:")
        print(f"{'='*60}")
        
        for i, result in enumerate(sorted_results[:10]):
            print(f"{i+1:2d}. {result['strategy_name']:<20} | "
                  f"Return: {result['total_return_pct']:6.2f}% | "
                  f"Sharpe: {result['sharpe_ratio']:5.2f} | "
                  f"Win Rate: {result['win_rate']:5.2f} | "
                  f"Max DD: {result['max_drawdown_pct']:5.2f}%")

if __name__ == "__main__":
    run_comprehensive_backtest()