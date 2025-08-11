# backtest_engine.py

import pandas as pd
from db import get_strategies, insert_result
from data.fetch_binance import fetch_binance_ohlcv
from strategies.rsi_strategy import compute_rsi_signal
from strategies.sma_crossover import compute_sma_crossover_signal

FEE_RATE = 0.001  # %0.1 Binance spot fee

def backtest(strategy, symbol="BTC/USDT", interval="1h", initial_balance=1000):
    """Verilen stratejiyi geçmiş veride test eder"""
    params = strategy.get("parameters", {})
    ohlcv = fetch_binance_ohlcv(symbol, interval, limit=500)
    df = pd.DataFrame(ohlcv)

    balance = initial_balance
    position = None
    entry_price = 0
    trades = []

    for i in range(len(df)):
        window_data = df.iloc[:i+1].to_dict(orient="records")

        if "RSI" in strategy["name"]:
            signal, _ = compute_rsi_signal(window_data, rsi_period=params.get("rsi_period", 14))
        elif "SMA_Crossover" in strategy["name"]:
            signal, _ = compute_sma_crossover_signal(
                window_data,
                short_period=params.get("short_period", 10),
                long_period=params.get("long_period", 50)
            )
        else:
            continue

        price = df.iloc[i]["close"]

        # Long ve Short pozisyon yönetimi
        if signal == "buy" and position is None:
            position = "long"
            entry_price = price
        elif signal == "sell" and position == "long":
            profit = (price - entry_price) / entry_price * balance
            profit -= abs(profit) * FEE_RATE
            balance += profit
            trades.append(profit)
            position = None

        elif signal == "sell" and position is None:
            position = "short"
            entry_price = price
        elif signal == "buy" and position == "short":
            profit = (entry_price - price) / entry_price * balance
            profit -= abs(profit) * FEE_RATE
            balance += profit
            trades.append(profit)
            position = None

    total_profit = balance - initial_balance
    win_rate = sum(1 for p in trades if p > 0) / len(trades) if trades else 0

    return {
        "strategy_id": strategy["id"],
        "strategy": strategy["name"],
        "symbol": symbol,
        "profit_loss": total_profit,
        "win_rate": win_rate,
        "trades_count": len(trades)
    }

def run_backtests():
    strategies = get_strategies()
    all_results = []

    for strat in strategies:
        result = backtest(strat)
        all_results.append(result)

        print(f"[RESULT] {result['strategy']} | Profit: {result['profit_loss']:.2f} | Win%: {result['win_rate']*100:.1f}% | Trades: {result['trades_count']}")

        insert_result({
            "strategy_id": result["strategy_id"],
            "profit_loss": result["profit_loss"]
        })

    # En iyi 10 stratejiyi raporla
    sorted_results = sorted(all_results, key=lambda x: x["profit_loss"], reverse=True)[:10]
    print("\n=== TOP 10 STRATEJİ ===")
    for r in sorted_results:
        print(f"{r['strategy']} | Profit: {r['profit_loss']:.2f} | Win%: {r['win_rate']*100:.1f}%")

if __name__ == "__main__":
    run_backtests()
