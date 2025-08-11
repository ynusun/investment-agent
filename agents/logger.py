# agents/logger.py
import csv
import os
from datetime import datetime

LOG_FILE = "logs/decisions.csv"

os.makedirs("logs", exist_ok=True)

def log_decision(strategy, signal, price, notes=""):
    header = ["timestamp", "strategy", "signal", "price", "notes"]
    row = [datetime.now().isoformat(), strategy, signal, price, notes]
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row)
