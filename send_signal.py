import requests
import os

def send_telegram_message(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[TG] BOT_TOKEN veya CHAT_ID eksik! Mesaj gönderilmedi.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"[TG] Cevap: {result}")
    except Exception as e:
        print(f"[TG] Hata: {e}")
