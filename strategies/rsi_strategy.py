import pandas as pd
import pandas_ta as ta

def compute_rsi_signal(ohlcv, rsi_period=14):
    df = pd.DataFrame(ohlcv)
    if not {"close"}.issubset(df.columns):
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]

    df["RSI"] = ta.rsi(df["close"], length=rsi_period)
    last_rsi = df["RSI"].iloc[-1]

    if last_rsi > 70:
        return "sell", last_rsi
    elif last_rsi < 30:
        return "buy", last_rsi
    else:
        return "hold", last_rsi
