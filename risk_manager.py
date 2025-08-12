# risk_manager.py

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from db import supabase

class RiskManager:
    def __init__(self, 
                 max_position_size_pct=0.10,  # Portföyün max %10'u bir pozisyonda
                 max_daily_loss_pct=0.05,     # Günlük max %5 kayıp
                 max_total_risk_pct=0.80,     # Toplam risk %80
                 min_cash_reserve=0.20):       # Min %20 nakit rezerv
        
        self.max_position_size_pct = max_position_size_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_total_risk_pct = max_total_risk_pct
        self.min_cash_reserve = min_cash_reserve
        
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        
    def reset_daily_limits(self):
        """Günlük limitleri sıfırla"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_loss = 0.0
            self.last_reset_date = current_date
            print(f"[RISK] Günlük limitler sıfırlandı - {current_date}")
    
    def get_current_portfolio_value(self) -> float:
        """Mevcut portföy değerini hesapla"""
        try:
            # Portfolio positions'ları al
            positions_result = supabase.table("portfolio_positions").select("*").execute()
            positions = positions_result.data
            
            total_value = 0.0
            
            for position in positions:
                if position['quantity'] > 0:
                    # Current price'ı al (gerçek uygulamada live price)
                    current_price = position['current_price'] or position['avg_price']
                    position_value = position['quantity'] * current_price
                    total_value += position_value
            
            # Nakit bakiyeyi ekle
            cash_result = supabase.table("portfolio_snapshots").select("cash_balance").order("created_at", desc=True).limit(1).execute()
            if cash_result.data:
                total_value += cash_result.data[0]['cash_balance']
            
            return total_value
            
        except Exception as e:
            print(f"[RISK ERROR] Portföy değeri hesaplanırken hata: {e}")
            return 10000.0  # Default değer
    
    def calculate_position_size(self, 
                              signal_strength: float, 
                              portfolio_value: float, 
                              asset_price: float) -> float:
        """Kelly Criterion ve risk limitlerine göre position size hesapla"""
        
        # Base position size (Kelly Criterion benzeri)
        base_size_pct = min(signal_strength * 0.1, self.max_position_size_pct)
        
        # Maksimum pozisyon büyüklüğünü kontrol et
        max_position_value = portfolio_value * self.max_position_size_pct
        max_quantity = max_position_value / asset_price
        
        # Signal strength'e göre ayarla
        suggested_quantity = (portfolio_value * base_size_pct) / asset_price
        
        return min(suggested_quantity, max_quantity)
    
    def check_risk_limits(self, 
                         signal: str, 
                         asset_symbol: str, 
                         quantity: float, 
                         price: float, 
                         confidence: float) -> Dict[str, Any]:
        """Tüm risk kontrollerini yap"""
        
        self.reset_daily_limits()
        
        risk_check = {
            "approved": True,
            "reasons": [],
            "warnings": [],
            "adjusted_quantity": quantity
        }
        
        portfolio_value = self.get_current_portfolio_value()
        position_value = quantity * price
        
        # 1. Pozisyon büyüklüğü kontrolü
        if position_value > (portfolio_value * self.max_position_size_pct):
            max_allowed = (portfolio_value * self.max_position_size_pct) / price
            risk_check["adjusted_quantity"] = max_allowed
            risk_check["warnings"].append(f"Pozisyon büyüklüğü ayarlandı: {quantity:.6f} → {max_allowed:.6f}")
        
        # 2. Günlük kayıp limiti kontrolü
        if self.daily_loss >= (portfolio_value * self.max_daily_loss_pct):
            risk_check["approved"] = False
            risk_check["reasons"].append(f"Günlük kayıp limiti aşıldı: {self.daily_loss:.2f}")
        
        # 3. Nakit rezerv kontrolü
        current_cash = self.get_current_cash_balance()
        if signal == "buy":
            remaining_cash = current_cash - position_value
            min_required_cash = portfolio_value * self.min_cash_reserve
            
            if remaining_cash < min_required_cash:
                risk_check["approved"] = False
                risk_check["reasons"].append(f"Nakit rezerv yetersiz. Gereken: {min_required_cash:.2f}, Kalan: {remaining_cash:.2f}")
        
        # 4. Confidence score kontrolü
        if confidence < 0.6:
            risk_check["approved"] = False
            risk_check["reasons"].append(f"Confidence score çok düşük: {confidence:.2f}")
        
        # 5. Toplam risk exposure kontrolü
        total_invested = portfolio_value - current_cash
        if signal == "buy":
            total_invested += position_value
            
        if total_invested > (portfolio_value * self.max_total_risk_pct):
            risk_check["approved"] = False
            risk_check["reasons"].append(f"Toplam risk limiti aşılıyor: {total_invested/portfolio_value:.1%}")
        
        # Log the decision
        self.log_risk_decision(asset_symbol, signal, quantity, price, risk_check)
        
        return risk_check
    
    def get_current_cash_balance(self) -> float:
        """Mevcut nakit bakiyeyi al"""
        try:
            result = supabase.table("portfolio_snapshots").select("cash_balance").order("created_at", desc=True).limit(1).execute()
            if result.data:
                return result.data[0]['cash_balance']
            return 1000.0  # Default başlangıç bakiyesi
        except:
            return 1000.0
    
    def update_daily_loss(self, loss_amount: float):
        """Günlük kaybı güncelle"""
        if loss_amount > 0:  # Sadece kayıpları say
            self.daily_loss += loss_amount
            print(f"[RISK] Günlük kayıp güncellendi: {self.daily_loss:.2f}")
    
    def log_risk_decision(self, asset_symbol: str, signal: str, quantity: float, 
                         price: float, decision: Dict[str, Any]):
        """Risk kararlarını logla"""
        log_data = {
            "asset_symbol": asset_symbol,
            "signal": signal,
            "quantity": quantity,
            "price": price,
            "approved": decision["approved"],
            "reasons": decision["reasons"],
            "warnings": decision["warnings"],
            "adjusted_quantity": decision["adjusted_quantity"],
            "created_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("risk_logs").insert(log_data).execute()
        except Exception as e:
            print(f"[RISK LOG ERROR] {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Risk durumu özeti"""
        portfolio_value = self.get_current_portfolio_value()
        cash_balance = self.get_current_cash_balance()
        
        return {
            "portfolio_value": portfolio_value,
            "cash_balance": cash_balance,
            "cash_ratio": cash_balance / portfolio_value,
            "daily_loss": self.daily_loss,
            "daily_loss_pct": self.daily_loss / portfolio_value,
            "remaining_daily_risk": (portfolio_value * self.max_daily_loss_pct) - self.daily_loss,
            "total_invested": portfolio_value - cash_balance,
            "investment_ratio": (portfolio_value - cash_balance) / portfolio_value
        }

# Risk manager singleton instance
risk_manager = RiskManager()