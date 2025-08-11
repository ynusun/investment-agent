# strategies/sma_crossover.py

import pandas as pd

def compute_sma_crossover_signal(ohlcv, short_period=10, long_period=50):
    """
    SMA Crossover stratejisi.
    short_period: kısa dönem SMA periyodu
    long_period: uzun dönem SMA periyodu
    """
    df = pd.DataFrame(ohlcv)

    if not {"close"}.issubset(df.columns):
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]

    df["SMA_short"] = df["close"].rolling(window=short_period).mean()
    df["SMA_long"] = df["close"].rolling(window=long_period).mean()

    # Son iki satırı al (kesişim kontrolü için)
    last_two = df.tail(2)

    prev_short = last_two["SMA_short"].iloc[0]
    prev_long = last_two["SMA_long"].iloc[0]
    curr_short = last_two["SMA_short"].iloc[1]
    curr_long = last_two["SMA_long"].iloc[1]

    if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
        return "hold", None  # Veriler yetersiz

    # Al sinyali: kısa SMA uzun SMA'yı aşağıdan yukarı keserse
    if (prev_short < prev_long) and (curr_short > curr_long):
        return "buy", curr_short

    # Sat sinyali: kısa SMA uzun SMA'yı yukarıdan aşağı keserse
    elif (prev_short > prev_long) and (curr_short < curr_long):
        return "sell", curr_short

    else:
        return "hold", curr_short
