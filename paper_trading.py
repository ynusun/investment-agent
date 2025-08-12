# paper_trading.py

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from db import supabase
from data.fetch_binance import fetch_binance_ohlcv
import time
import json

class PaperTradingEngine:
    def __init__(self, initial_balance=10000.0, fee_rate=0.001):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate  # %0.1 Binance spot fee
        
        # Initialize portfolio if not exists
        self.initialize_portfolio()
    
    def initialize_portfolio(self):
        """Portföyü başlat"""
        try:
            # Check if portfolio already exists
            result = supabase.table("portfolio_snapshots").select("*").order("created_at", desc=True).limit(1).execute()
            
            if not result.data:
                # Create initial portfolio
                initial_portfolio = {
                    "total_value": self.initial_balance,
                    "cash_balance": self.initial_balance,
                    "positions": {},
                    "created_at": datetime.now().isoformat()
                }
                
                supabase.table("portfolio_snapshots").insert(initial_portfolio).execute()
                print(f"[PAPER] Portföy başlatıldı: ${self.initial_balance}")
            else:
                print(f"[PAPER] Mevcut portföy bulundu: ${result.data[0]['total_value']}")
                
        except Exception as e:
            print(f"[PAPER ERROR] Portföy başlatılırken hata: {e}")
    
    def get_current_price(self, symbol: str) -> float:
        """Anlık fiyat al (Binance API'den)"""
        try:
            # Son fiyatı al
            ohlcv = fetch_binance_ohlcv(symbol, "1m", limit=1)
            if ohlcv:
                return ohlcv[-1]["close"]
        except Exception as e:
            print(f"[PAPER ERROR] Fiyat alınırken hata {symbol}: {e}")
        
        return 0.0
    
    def get_portfolio_positions(self) -> Dict[str, Any]:
        """Mevcut portföy pozisyonlarını al"""
        try:
            result = supabase.table("portfolio_positions").select("*").execute()
            positions = {}
            
            for pos in result.data:
                positions[pos['asset_symbol']] = {
                    'quantity': pos['quantity'],
                    'avg_price': pos['avg_price'],
                    'current_price': pos.get('current_price', pos['avg_price']),
                    'unrealized_pnl': pos.get('unrealized_pnl', 0)
                }
            
            return positions
            
        except Exception as e:
            print(f"[PAPER ERROR] Pozisyonlar alınırken hata: {e}")
            return {}
    
    def get_cash_balance(self) -> float:
        """Nakit bakiyeyi al"""
        try:
            result = supabase.table("portfolio_snapshots").select("cash_balance").order("created_at", desc=True).limit(1).execute()
            if result.data:
                return result.data[0]['cash_balance']
        except Exception as e:
            print(f"[PAPER ERROR] Nakit bakiyesi alınırken hata: {e}")
        
        return self.initial_balance
    
    def execute_paper_trade(self, 
                           asset_symbol: str, 
                           signal: str, 
                           quantity: float, 
                           strategy: str, 
                           confidence: float,
                           notes: str = "") -> Dict[str, Any]:
        """Paper trade işlemini gerçekleştir"""
        
        current_price = self.get_current_price(f"{asset_symbol}/USDT")
        if current_price <= 0:
            return {"success": False, "error": "Fiyat alınamadı"}
        
        cash_balance = self.get_cash_balance()
        positions = self.get_portfolio_positions()
        
        trade_id = str(uuid.uuid4())
        trade_value = quantity * current_price
        fee = trade_value * self.fee_rate
        
        trade_result = {
            "trade_id": trade_id,
            "success": False,
            "executed_quantity": 0,
            "executed_price": current_price,
            "fee": fee,
            "total_cost": 0,
            "new_cash_balance": cash_balance,
            "error": None
        }
        
        if signal.lower() == "buy":
            # BUY işlemi
            total_cost = trade_value + fee
            
            if cash_balance >= total_cost:
                # Yeterli nakit var
                new_cash_balance = cash_balance - total_cost
                
                # Pozisyonu güncelle veya oluştur
                if asset_symbol in positions:
                    # Mevcut pozisyon var - average down/up
                    old_quantity = positions[asset_symbol]['quantity']
                    old_avg_price = positions[asset_symbol]['avg_price']
                    
                    new_total_quantity = old_quantity + quantity
                    new_avg_price = ((old_quantity * old_avg_price) + (quantity * current_price)) / new_total_quantity
                    
                    self.update_position(asset_symbol, new_total_quantity, new_avg_price, current_price)
                else:
                    # Yeni pozisyon
                    self.create_position(asset_symbol, quantity, current_price)
                
                # Trade'i kaydet
                self.record_trade(trade_id, asset_symbol, "buy", quantity, current_price, fee, strategy, confidence, notes)
                
                # Cash balance'ı güncelle
                self.update_cash_balance(new_cash_balance)
                
                trade_result.update({
                    "success": True,
                    "executed_quantity": quantity,
                    "total_cost": total_cost,
                    "new_cash_balance": new_cash_balance
                })
                
                print(f"[PAPER BUY] {asset_symbol}: {quantity:.6f} @ ${current_price:.2f} | Fee: ${fee:.2f}")
                
            else:
                trade_result["error"] = f"Yetersiz bakiye. Gereken: ${total_cost:.2f}, Mevcut: ${cash_balance:.2f}"
        
        elif signal.lower() == "sell":
            # SELL işlemi
            if asset_symbol in positions and positions[asset_symbol]['quantity'] >= quantity:
                # Yeterli pozisyon var
                sell_value = trade_value - fee
                new_cash_balance = cash_balance + sell_value
                
                # Pozisyonu güncelle
                old_quantity = positions[asset_symbol]['quantity']
                new_quantity = old_quantity - quantity
                
                if new_quantity > 0:
                    # Kısmi satış
                    self.update_position(asset_symbol, new_quantity, positions[asset_symbol]['avg_price'], current_price)
                else:
                    # Tam satış
                    self.close_position(asset_symbol)
                
                # P&L hesapla
                avg_price = positions[asset_symbol]['avg_price']
                pnl = (current_price - avg_price) * quantity - fee
                
                # Trade'i kaydet
                self.record_trade(trade_id, asset_symbol, "sell", quantity, current_price, fee, strategy, confidence, notes, pnl)
                
                # Cash balance'ı güncelle
                self.update_cash_balance(new_cash_balance)
                
                trade_result.update({
                    "success": True,
                    "executed_quantity": quantity,
                    "total_cost": -sell_value,  # Negatif çünkü para girişi
                    "new_cash_balance": new_cash_balance,
                    "pnl": pnl
                })
                
                print(f"[PAPER SELL] {asset_symbol}: {quantity:.6f} @ ${current_price:.2f} | P&L: ${pnl:.2f}")
                
            else:
                available_qty = positions.get(asset_symbol, {}).get('quantity', 0)
                trade_result["error"] = f"Yetersiz pozisyon. İstenen: {quantity:.6f}, Mevcut: {available_qty:.6f}"
        
        else:
            trade_result["error"] = f"Geçersiz sinyal: {signal}"
        
        return trade_result
    
    def create_position(self, asset_symbol: str, quantity: float, avg_price: float):
        """Yeni pozisyon oluştur"""
        position_data = {
            "asset_symbol": asset_symbol,
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": avg_price,
            "unrealized_pnl": 0,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("portfolio_positions").insert(position_data).execute()
        except Exception as e:
            print(f"[PAPER ERROR] Pozisyon oluşturulamadı: {e}")
    
    def update_position(self, asset_symbol: str, quantity: float, avg_price: float, current_price: float):
        """Mevcut pozisyonu güncelle"""
        unrealized_pnl = (current_price - avg_price) * quantity
        
        update_data = {
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("portfolio_positions").update(update_data).eq("asset_symbol", asset_symbol).execute()
        except Exception as e:
            print(f"[PAPER ERROR] Pozisyon güncellenemedi: {e}")
    
    def close_position(self, asset_symbol: str):
        """Pozisyonu kapat"""
        try:
            supabase.table("portfolio_positions").delete().eq("asset_symbol", asset_symbol).execute()
        except Exception as e:
            print(f"[PAPER ERROR] Pozisyon kapatılamadı: {e}")
    
    def update_cash_balance(self, new_balance: float):
        """Nakit bakiyeyi güncelle"""
        portfolio_data = {
            "cash_balance": new_balance,
            "total_value": self.calculate_total_portfolio_value(),
            "positions": self.get_portfolio_positions(),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("portfolio_snapshots").insert(portfolio_data).execute()
        except Exception as e:
            print(f"[PAPER ERROR] Nakit bakiyesi güncellenemedi: {e}")
    
    def record_trade(self, trade_id: str, asset_symbol: str, side: str, quantity: float, 
                    price: float, fee: float, strategy: str, confidence: float, 
                    notes: str = "", pnl: float = 0):
        """Trade'i kaydet"""
        trade_data = {
            "id": trade_id,
            "asset_symbol": asset_symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "fee": fee,
            "strategy": strategy,
            "confidence_score": confidence,
            "realized_pnl": pnl,
            "notes": notes,
            "executed_at": datetime.now().isoformat(),
            "is_paper_trade": True
        }
        
        try:
            supabase.table("paper_trades").insert(trade_data).execute()
        except Exception as e:
            print(f"[PAPER ERROR] Trade kaydedilemedi: {e}")
    
    def calculate_total_portfolio_value(self) -> float:
        """Toplam portföy değerini hesapla"""
        cash_balance = self.get_cash_balance()
        positions = self.get_portfolio_positions()
        
        total_value = cash_balance
        
        for symbol, position in positions.items():
            current_price = self.get_current_price(f"{symbol}/USDT")
            if current_price > 0:
                position_value = position['quantity'] * current_price
                total_value += position_value
        
        return total_value
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Portföy özeti"""
        cash_balance = self.get_cash_balance()
        positions = self.get_portfolio_positions()
        total_value = self.calculate_total_portfolio_value()
        
        position_details = {}
        total_unrealized_pnl = 0
        
        for symbol, position in positions.items():
            current_price = self.get_current_price(f"{symbol}/USDT")
            if current_price > 0:
                position_value = position['quantity'] * current_price
                unrealized_pnl = (current_price - position['avg_price']) * position['quantity']
                total_unrealized_pnl += unrealized_pnl
                
                position_details[symbol] = {
                    'quantity': position['quantity'],
                    'avg_price': position['avg_price'],
                    'current_price': current_price,
                    'position_value': position_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': (unrealized_pnl / (position['avg_price'] * position['quantity'])) * 100
                }
        
        return {
            "total_value": total_value,
            "cash_balance": cash_balance,
            "invested_value": total_value - cash_balance,
            "initial_balance": self.initial_balance,
            "total_return": total_value - self.initial_balance,
            "total_return_pct": ((total_value - self.initial_balance) / self.initial_balance) * 100,
            "unrealized_pnl": total_unrealized_pnl,
            "cash_ratio": cash_balance / total_value,
            "positions": position_details
        }

# Global paper trading engine instance
paper_trader = PaperTradingEngine()