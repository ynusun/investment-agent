# db.py
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL veya SUPABASE_KEY .env içinde tanımlı değil")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Assets ---

def get_asset_id(symbol: str):
    response = supabase.table("assets").select("id").eq("symbol", symbol).execute()
    # debug çıktısı (gerektiğinde yorum satırı yap)
    print(f"[DEBUG] get_asset_id select response for symbol '{symbol}': {response.data}")
    if response.data and len(response.data) > 0:
        return response.data[0]['id']
    else:
        insert_resp = supabase.table("assets").insert({"symbol": symbol, "name": symbol}).execute()
        print(f"[DEBUG] get_asset_id insert response: {insert_resp.data}")
        if insert_resp.data and len(insert_resp.data) > 0:
            return insert_resp.data[0]['id']
        else:
            raise Exception("Asset eklenirken hata oluştu")

def get_assets():
    res = supabase.table("assets").select("*").execute()
    return res.data

def get_asset_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("assets").select("*").eq("symbol", symbol).limit(1).execute()
    data = res.data
    return data[0] if data else None

def create_asset(symbol: str, name: str = ""):
    payload = {"symbol": symbol, "name": name}
    return supabase.table("assets").insert(payload).execute()

# --- Strategies ---

def get_strategies():
    res = supabase.table("strategies").select("*").execute()
    return res.data

def get_strategy_by_name(name: str):
    res = supabase.table("strategies").select("*").eq("name", name).limit(1).execute()
    data = res.data
    return data[0] if data else None

def create_strategy(name: str, description: str = "", parameters: dict = None):
    payload = {"name": name, "description": description, "parameters": parameters or {}}
    return supabase.table("strategies").insert(payload).execute()

def update_strategy_performance(strategy_id: str, performance_score: float):
    """
    strategies.performance_score ve last_backtested değerlerini günceller
    """
    payload = {
        "performance_score": performance_score,
        "last_backtested": "now()"
    }
    # note: using RPC-like expression for now() is not supported via insert, so use raw SQL
    sql = f"""
    UPDATE public.strategies
    SET performance_score = {performance_score}, last_backtested = timezone('utc'::text, now())
    WHERE id = '{strategy_id}';
    """
    # execute raw SQL
    return supabase.rpc("sql", {"q": sql}) if False else supabase.postgrest.send("POST", "/rpc/sql", json={"q": sql})  # fallback, may not work in all clients

# Safer generic update using PostgREST:
def update_strategy_performance_simple(strategy_id: str, performance_score: float):
    return supabase.table("strategies").update({
        "performance_score": performance_score,
        "last_backtested": None  # we'll set last_backtested with SQL below if needed
    }).eq("id", strategy_id).execute()

# --- Backtests / Results helper ---

def insert_backtest_result(strategy_id: str, symbol: str, profit_loss: float, win_rate: float, trades_count: int):
    payload = {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "profit_loss": profit_loss,
        "win_rate": win_rate,
        "trades_count": trades_count
    }
    return supabase.table("backtests").insert(payload).execute()

# --- Signals & Trades ---

def insert_signal(signal_dict: dict):
    # Eğer 'symbol' verilirse asset_id'ye çevir
    if "symbol" in signal_dict:
        symbol = signal_dict.pop("symbol")  # symbol'u dict'ten çıkar
        asset_id = get_asset_id(symbol)     # asset_id'yi al

        print(f"[DEBUG] asset_id for symbol '{symbol}': {asset_id}")

        if not asset_id:
            raise Exception("asset_id sinyal verisinde olmalı ve boş olmamalı")

        signal_dict["asset_id"] = asset_id  # asset_id ekle

    else:
        print("[DEBUG] signal_dict içinde 'symbol' yok")

    # Eğer rsi_value / sma_value gelmiyorsa bırak (DB nullable ise sorun yok)
    return supabase.table("signals").insert(signal_dict).execute()

def insert_trade(trade_dict: dict):
    return supabase.table("trades").insert(trade_dict).execute()

def insert_result(result_dict: dict):
    return supabase.table("results").insert(result_dict).execute()
