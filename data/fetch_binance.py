import requests

def fetch_binance_ohlcv(symbol="BTC/USDT", interval="1h", limit=500):
    # Binance API, slash yerine bitişik format bekliyor
    symbol = symbol.replace("/", "")

    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    ohlcv = [
        {
            "timestamp": item[0],
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        }
        for item in data
    ]
    return ohlcv
