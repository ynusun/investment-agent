# main_updated.py

from dotenv import load_dotenv
import os
from data.fetch_binance import fetch_binance_ohlcv
from strategies.rsi_strategy import compute_rsi_signal
from strategies.sma_crossover import compute_sma_crossover_signal
from db import insert_signal, get_strategy_by_name
from send_signal import send_telegram_message
from risk_manager import risk_manager
from paper_trading import paper_trader
import json
from datetime import datetime
import time

load_dotenv()

def run_strategy_analysis(symbol="BTC/USDT", limit=500):
    """Tek bir symbol için tüm stratejileri çalıştır"""
    print(f"\n{'='*50}")
    print(f"[ANALYSIS] {symbol} analizi başlatılıyor...")
    print(f"{'='*50}")
    
    # Fiyat verilerini çek
    print("[DATA] Fiyatlar çekiliyor...")
    ohlcv = fetch_binance_ohlcv(symbol, "1h", limit=limit)
    print(f"[DATA] {len(ohlcv)} veri noktası alındı")
    
    if not ohlcv or len(ohlcv) < 50:
        print("[ERROR] Yetersiz veri!")
        return
    
    last_price = ohlcv[-1]["close"]
    asset_symbol = symbol.split("/")[0]  # BTC/USDT -> BTC
    
    strategies_results = []
    
    # 1. RSI Stratejisi
    print(f"\n[STRATEGY] RSI analizi...")
    rsi_strategy = get_strategy_by_name("RSI")
    if rsi_strategy:
        params = rsi_strategy.get("parameters", {})
        rsi_period = params.get("rsi_period", 14)
        
        rsi_signal, rsi_value = compute_rsi_signal(ohlcv, rsi_period=rsi_period)
        
        # Confidence hesapla (RSI'nin ekstrem değerlere yakınlığına göre)
        if rsi_value > 70:
            confidence = min((rsi_value - 70) / 10, 1.0)  # 70-80 arası normalize
        elif rsi_value < 30:
            confidence = min((30 - rsi_value) / 10, 1.0)  # 30-20 arası normalize
        else:
            confidence = 0.3  # Hold sinyali için düşük confidence
        
        strategies_results.append({
            'name': 'RSI',
            'signal': rsi_signal,
            'confidence': confidence,
            'value': rsi_value,
            'notes': f"RSI: {rsi_value:.2f} (period: {rsi_period})"
        })
        
        print(f"[RSI] Sinyal: {rsi_signal} | Değer: {rsi_value:.2f} | Güven: {confidence:.2f}")
    
    # 2. SMA Crossover Stratejisi
    print(f"[STRATEGY] SMA Crossover analizi...")
    sma_strategy = get_strategy_by_name("SMA_Crossover")
    if sma_strategy:
        params = sma_strategy.get("parameters", {})
        short_period = params.get("short_period", 10)
        long_period = params.get("long_period", 50)
        
        sma_signal, sma_value = compute_sma_crossover_signal(
            ohlcv, short_period=short_period, long_period=long_period
        )
        
        # SMA confidence (fiyatın SMA'lardan uzaklığına göre)
        if sma_signal in ['buy', 'sell'] and sma_value:
            price_sma_diff = abs(last_price - sma_value) / last_price
            confidence = min(price_sma_diff * 10, 0.9)  # Fark ne kadar büyükse confidence o kadar yüksek
        else:
            confidence = 0.4
        
        strategies_results.append({
            'name': 'SMA_Crossover',
            'signal': sma_signal,
            'confidence': confidence,
            'value': sma_value,
            'notes': f"SMA: {sma_value:.2f} (periods: {short_period}/{long_period})"
        })
        
        print(f"[SMA] Sinyal: {sma_signal} | Değer: {sma_value:.2f} | Güven: {confidence:.2f}")
    
    # 3. En güvenilir sinyali seç (en yüksek confidence)
    print(f"\n[SIGNAL SELECTION] En iyi sinyal seçiliyor...")
    
    # Sadece buy/sell sinyallerini değerlendir
    actionable_signals = [s for s in strategies_results if s['signal'] in ['buy', 'sell']]
    
    if not actionable_signals:
        print("[DECISION] Hiç actionable sinyal yok, beklemede.")
        
        # Hold sinyalleri de kaydet
        for strategy_result in strategies_results:
            save_signal_to_db(asset_symbol, strategy_result, last_price)
        
        send_telegram_message(f"📊 {symbol}\n🔄 Tüm stratejiler HOLD sinyali\n💰 Fiyat: ${last_price:.2f}")
        return
    
    # En yüksek confidence'a sahip stratejiyi seç
    best_strategy = max(actionable_signals, key=lambda x: x['confidence'])
    print(f"[BEST] {best_strategy['name']} seçildi - Sinyal: {best_strategy['signal']} | Güven: {best_strategy['confidence']:.2f}")
    
    # 4. Risk Kontrolü ve Paper Trade Execution
    if best_strategy['confidence'] >= 0.6:  # Minimum güven eşiği
        execute_paper_trade(asset_symbol, best_strategy, last_price)
    else:
        print(f"[SKIP] Confidence çok düşük ({best_strategy['confidence']:.2f}), trade atlandı.")
    
    # 5. Tüm sinyalleri kaydet
    for strategy_result in strategies_results:
        save_signal_to_db(asset_symbol, strategy_result, last_price)
    
    # 6. Portföy durumunu raporla
    print_portfolio_summary()

def execute_paper_trade(asset_symbol, strategy_result, current_price):
    """Paper trade gerçekleştir"""
    print(f"\n[TRADE EXECUTION] {strategy_result['name']} stratejisi ile işlem...")
    
    # Risk kontrolü için position size hesapla
    portfolio_value = paper_trader.calculate_total_portfolio_value()
    suggested_quantity = risk_manager.calculate_position_size(
        strategy_result['confidence'], 
        portfolio_value, 
        current_price
    )
    
    print(f"[RISK] Önerilen miktar: {suggested_quantity:.6f} {asset_symbol}")
    
    # Risk limitlerini kontrol et
    risk_check = risk_manager.check_risk_limits(
        signal=strategy_result['signal'],
        asset_symbol=asset_symbol,
        quantity=suggested_quantity,
        price=current_price,
        confidence=strategy_result['confidence']
    )
    
    if not risk_check['approved']:
        print(f"[RISK REJECTED] Trade reddedildi:")
        for reason in risk_check['reasons']:
            print(f"  - {reason}")
        
        # Telegram'a reddetme bilgisi gönder
        send_telegram_message(
            f"🚫 {asset_symbol}/USDT TRADE REDDEDİLDI\n"
            f"📊 Strateji: {strategy_result['name']}\n"
            f"📈 Sinyal: {strategy_result['signal']}\n"
            f"💰 Fiyat: ${current_price:.2f}\n"
            f"❌ Red Sebepleri:\n" + "\n".join([f"• {r}" for r in risk_check['reasons']])
        )
        return
    
    # Risk onaylandıysa miktarı ayarla
    final_quantity = risk_check['adjusted_quantity']
    if final_quantity != suggested_quantity:
        print(f"[RISK ADJUSTED] Miktar ayarlandı: {suggested_quantity:.6f} → {final_quantity:.6f}")
    
    # Paper trade'i gerçekleştir
    print(f"[PAPER TRADE] {strategy_result['signal'].upper()} {final_quantity:.6f} {asset_symbol} @ ${current_price:.2f}")
    
    trade_result = paper_trader.execute_paper_trade(
        asset_symbol=asset_symbol,
        signal=strategy_result['signal'],
        quantity=final_quantity,
        strategy=strategy_result['name'],
        confidence=strategy_result['confidence'],
        notes=strategy_result['notes']
    )
    
    if trade_result['success']:
        print(f"[SUCCESS] Trade başarılı! ID: {trade_result['trade_id']}")
        
        # Telegram bilgilendirmesi
        emoji = "🟢" if strategy_result['signal'] == 'buy' else "🔴"
        pnl_text = f"\n💵 P&L: ${trade_result.get('pnl', 0):.2f}" if 'pnl' in trade_result else ""
        
        send_telegram_message(
            f"{emoji} {asset_symbol}/USDT PAPER TRADE\n"
            f"📊 Strateji: {strategy_result['name']}\n"
            f"📈 Sinyal: {strategy_result['signal'].upper()}\n"
            f"💰 Fiyat: ${current_price:.2f}\n"
            f"📦 Miktar: {final_quantity:.6f}\n"
            f"🎯 Güven: {strategy_result['confidence']:.1%}\n"
            f"💳 Yeni Bakiye: ${trade_result['new_cash_balance']:.2f}"
            f"{pnl_text}"
        )
        
        # P&L varsa günlük kaybı güncelle
        if 'pnl' in trade_result and trade_result['pnl'] < 0:
            risk_manager.update_daily_loss(abs(trade_result['pnl']))
            
    else:
        print(f"[ERROR] Trade başarısız: {trade_result['error']}")
        send_telegram_message(
            f"❌ {asset_symbol}/USDT TRADE HATASI\n"
            f"📊 Strateji: {strategy_result['name']}\n"
            f"🔸 Hata: {trade_result['error']}"
        )

def save_signal_to_db(asset_symbol, strategy_result, price):
    """Sinyal verisini veritabanına kaydet"""
    signal_payload = {
        "symbol": asset_symbol,
        "strategy": strategy_result['name'],
        "signal": strategy_result['signal'],
        "price": price,
        "confidence_score": strategy_result['confidence'],
        "rsi_value": strategy_result['value'] if strategy_result['name'] == 'RSI' else None,
        "notes": strategy_result['notes']
    }
    
    try:
        insert_signal(signal_payload)
        print(f"[DB] {strategy_result['name']} sinyali kaydedildi")
    except Exception as e:
        print(f"[DB ERROR] Sinyal kaydedilemedi: {e}")

def print_portfolio_summary():
    """Portföy özetini yazdır"""
    print(f"\n{'='*30} PORTFÖY ÖZETİ {'='*30}")
    
    summary = paper_trader.get_portfolio_summary()
    
    print(f"💰 Toplam Değer: ${summary['total_value']:.2f}")
    print(f"💵 Nakit: ${summary['cash_balance']:.2f} ({summary['cash_ratio']:.1%})")
    print(f"📊 Yatırılan: ${summary['invested_value']:.2f}")
    print(f"📈 Toplam Getiri: ${summary['total_return']:.2f} ({summary['total_return_pct']:.2f}%)")
    print(f"🔄 Gerçekleşmemiş P&L: ${summary['unrealized_pnl']:.2f}")
    
    if summary['positions']:
        print(f"\n📦 Pozisyonlar:")
        for symbol, pos in summary['positions'].items():
            print(f"  {symbol}: {pos['quantity']:.6f} @ ${pos['avg_price']:.2f}")
            print(f"    💰 Değer: ${pos['position_value']:.2f}")
            print(f"    📊 P&L: ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_pct']:.2f}%)")
    
    # Risk özeti
    risk_summary = risk_manager.get_risk_summary()
    print(f"\n⚠️ Risk Durumu:")
    print(f"  Günlük Kayıp: ${risk_summary['daily_loss']:.2f} ({risk_summary['daily_loss_pct']:.2%})")
    print(f"  Kalan Risk: ${risk_summary['remaining_daily_risk']:.2f}")
    print(f"  Yatırım Oranı: {risk_summary['investment_ratio']:.1%}")
    
    print(f"{'='*70}")

def run_multiple_assets():
    """Birden fazla varlık için analiz"""
    assets = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    
    for asset in assets:
        try:
            run_strategy_analysis(asset)
            time.sleep(2)  # API rate limit için bekleme
        except Exception as e:
            print(f"[ERROR] {asset} analizi sırasında hata: {e}")
            continue

def main():
    """Ana fonksiyon"""
    print(f"🚀 Investment Agent başlatılıyor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tek asset için çalıştır
    run_strategy_analysis("BTC/USDT")
    
    # Çoklu asset için çalıştırmak istersen:
    # run_multiple_assets()

if __name__ == "__main__":
    main()