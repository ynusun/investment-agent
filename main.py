from dotenv import load_dotenv
import os
from data.fetch_binance import fetch_binance_ohlcv
from strategies.rsi_strategy import compute_rsi_signal
from db import insert_signal, get_strategy_by_name
from send_signal import send_telegram_message
from strategies.sma_crossover import compute_sma_crossover_signal


load_dotenv()

def run_once():
    print("[DATA] Fiyatlar çekiliyor...")
    ohlcv = fetch_binance_ohlcv("BTC/USDT", "1h", limit=500)
    print(f"[DATA] Veri satırı: {len(ohlcv)}")

    # Strateji verisini çek
    strategy = get_strategy_by_name("RSI")
    if not strategy:
        print("[ERROR] RSI stratejisi bulunamadı, lütfen strategies tablosuna ekleyin.")
        return

    params = strategy.get("parameters", {})
    rsi_period = params.get("rsi_period", 14)  # default 14

    print(f"[STRAT] RSI hesaplanıyor... (period={rsi_period})")
    signal, rsi_value = compute_rsi_signal(ohlcv, rsi_period=rsi_period)
    print(f"[STRAT] Sinyal: {signal}  | RSI: {rsi_value}")

    confidence = 0.7  # Örnek confidence puanı

    last_price = ohlcv[-1]["close"]  # Son kapanış fiyatı

    signal_payload = {
    "symbol": "BTC",  # Büyük harfle, string olarak doğru verildiğinden emin ol
    "strategy": "RSI",
    "signal": signal,
    "price": last_price,
    "confidence_score": confidence,
    "rsi_value": rsi_value,
    "notes": "RSI sinyal testi"
}


    print("[DB] RSI Signal insert ediliyor...")
    insert_signal(signal_payload)

        # SMA Crossover sinyalini hesapla
    sma_signal, sma_value = compute_sma_crossover_signal(ohlcv)
    print(f"[STRAT] SMA Crossover sinyali: {sma_signal}  | SMA değeri: {sma_value}")

    sma_payload = {
        "symbol": "BTC",
        "strategy": "SMA_Crossover",
        "signal": sma_signal,
        "price": ohlcv[-1]["close"],  # son kapanış fiyatı
        "confidence_score": 0.6,      # örnek confidence
        "rsi_value": None,
        "notes": "SMA Crossover testi"
    }

    print("[DB] SMA signal insert ediliyor...")
    insert_signal(sma_payload)


   # Telegram mesajları
    print("[TG] RSI mesaj gönderiliyor...")
    send_telegram_message(f"BTC/USDT | Strateji: RSI\nSinyal: {signal}\nRSI: {rsi_value:.2f}")

    print("[TG] SMA mesaj gönderiliyor...")
    send_telegram_message(f"BTC/USDT | Strateji: SMA_Crossover\nSinyal: {sma_signal}\nSMA Değeri: {sma_value}")

if __name__ == "__main__":
    run_once()
