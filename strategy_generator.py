# strategy_generator.py

from itertools import product
from db import get_strategy_by_name, create_strategy
import json

strategies_config = [
    {
        "name": "RSI",
        "description": "Relative Strength Index stratejisi",
        "parameters": {
            "rsi_period": [7, 14, 21],
            "overbought": [65, 70, 75],
            "oversold": [25, 30, 35]
        }
    },
    {
        "name": "SMA_Crossover",
        "description": "Kısa ve uzun SMA kesişim stratejisi",
        "parameters": {
            "short_period": [5, 10, 15],
            "long_period": [30, 50, 100]
        }
    }
]

def generate_variants(strategy):
    """Parametre kombinasyonlarını üretir"""
    keys = strategy["parameters"].keys()
    values = strategy["parameters"].values()
    for combo in product(*values):
        yield dict(zip(keys, combo))

def store_strategies():
    total_added = 0
    for strat in strategies_config:
        for params in generate_variants(strat):
            # Strateji ismini parametrelerle birlikte unique yapıyoruz
            variant_name = f"{strat['name']}_" + "_".join(f"{k}{v}" for k, v in params.items())

            # Aynı strateji zaten varsa eklemiyoruz
            if get_strategy_by_name(variant_name):
                print(f"[SKIP] {variant_name} zaten var.")
                continue

            # Supabase'e ekle
            create_strategy(
                name=variant_name,
                description=strat["description"],
                parameters=params
            )
            print(f"[ADD] {variant_name} eklendi.")
            total_added += 1

    print(f"[INFO] Toplam {total_added} yeni strateji eklendi.")

if __name__ == "__main__":
    store_strategies()
