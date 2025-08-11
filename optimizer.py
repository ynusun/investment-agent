import pandas as pd
from strategies import run_strategy
from backtest_engine import backtest_strategy

strategies_to_test = [
    # RSI varyasyonları
    {"name": "RSI", "params": {"period": 14, "overbought": 70, "oversold": 30}},
    {"name": "RSI", "params": {"period": 7, "overbought": 65, "oversold": 25}},
    {"name": "RSI", "params": {"period": 7, "overbought": 65, "oversold": 30}},
    {"name": "RSI", "params": {"period": 7, "overbought": 65, "oversold": 35}},
    {"name": "RSI", "params": {"period": 14, "overbought": 70, "oversold": 30}},
    {"name": "RSI", "params": {"period": 21, "overbought": 75, "oversold": 35}},
    # SMA Crossover varyasyonları
    {"name": "SMA_Crossover", "params": {"short_period": 5, "long_period": 30}},
    {"name": "SMA_Crossover", "params": {"short_period": 10, "long_period": 50}},
    {"name": "SMA_Crossover", "params": {"short_period": 15, "long_period": 100}},
]

results = []

for strat in strategies_to_test:
    print(f"[OPT] Backtest çalıştırılıyor: {strat['name']}_{'_'.join([f'{k}{v}' for k,v in strat['params'].items()])}")
    try:
        df = run_strategy(strat["name"], **strat["params"])

        # Eğer veri yetersizse bu stratejiyi atla
        if df is None or df.empty:
            print("[SKIP] Veri yok, strateji atlandı.")
            continue

        profit = backtest_strategy(df)

        results.append({
            "strategy": strat["name"],
            "params": strat["params"],
            "profit": profit
        })

    except (IndexError, TypeError, ValueError) as e:
        print(f"[ERROR] Backtest sırasında hata: {e}")
        continue

# Sonuçları sıralayıp yazdır
results_df = pd.DataFrame(results)
if not results_df.empty:
    results_df = results_df.sort_values(by="profit", ascending=False)
    print("[OPT] Optimization tamamlandı. En iyi stratejiler:")
    print(results_df)
else:
    print("[OPT] Hiç başarılı strateji sonucu yok.")
