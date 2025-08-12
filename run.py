# run.py - Ana çalıştırma scripti

import sys
import argparse
from datetime import datetime
from main_updated import main, run_multiple_assets
from advanced_backtest import run_comprehensive_backtest
from strategy_generator import store_strategies
from paper_trading import paper_trader
from risk_manager import risk_manager

def setup_database():
    """Veritabanı kurulumu"""
    print("📊 Veritabanı kurulumu yapılıyor...")
    
    # Stratejileri generate et
    print("🔧 Stratejiler oluşturuluyor...")
    store_strategies()
    
    print("✅ Kurulum tamamlandı!")

def run_live_trading():
    """Canlı trading modu"""
    print("🚀 Canlı paper trading başlatılıyor...")
    
    # Ana analiz
    main()

def run_backtest_mode(strategy_name=None):
    """Backtest modu"""
    print("📈 Backtest modu başlatılıyor...")
    
    if strategy_name:
        print(f"🎯 Sadece '{strategy_name}' stratejisi test edilecek")
    
    run_comprehensive_backtest(strategy_name)

def run_portfolio_report():
    """Portföy raporu"""
    print("📊 Portföy raporu oluşturuluyor...")
    
    summary = paper_trader.get_portfolio_summary()
    risk_summary = risk_manager.get_risk_summary()
    
    print(f"\n{'='*50}")
    print(f"         PORTFÖY RAPORU - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    print(f"\n💰 GENEL DURUM:")
    print(f"   Toplam Değer: ${summary['total_value']:,.2f}")
    print(f"   Nakit Bakiye: ${summary['cash_balance']:,.2f}")
    print(f"   Yatırılan Tutar: ${summary['invested_value']:,.2f}")
    print(f"   Toplam Getiri: ${summary['total_return']:,.2f} ({summary['total_return_pct']:+.2f}%)")
    
    if summary['positions']:
        print(f"\n📦 POZİSYONLAR:")
        for symbol, pos in summary['positions'].items():
            pnl_emoji = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
            print(f"   {symbol}: {pos['quantity']:.6f} @ ${pos['avg_price']:.2f}")
            print(f"     {pnl_emoji} P&L: ${pos['unrealized_pnl']:+.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
    
    print(f"\n⚠️ RİSK DURUMU:")
    print(f"   Günlük Kayıp: ${risk_summary['daily_loss']:.2f}")
    print(f"   Kalan Risk Limiti: ${risk_summary['remaining_daily_risk']:.2f}")
    print(f"   Nakit Oranı: {risk_summary['cash_ratio']:.1%}")
    print(f"   Yatırım Oranı: {risk_summary['investment_ratio']:.1%}")
    
    print(f"\n{'='*50}")

def run_multi_asset_mode():
    """Çoklu varlık analizi"""
    print("🌍 Çoklu varlık analizi başlatılıyor...")
    run_multiple_assets()

def main_cli():
    """Ana CLI fonksiyonu"""
    parser = argparse.ArgumentParser(description='Investment Agent - Akıllı Yatırım Robotu')
    
    parser.add_argument('mode', choices=[
        'setup', 'live', 'backtest', 'portfolio', 'multi'
    ], help='Çalıştırma modu')
    
    parser.add_argument('--strategy', '-s', type=str, 
                       help='Belirli bir strateji için backtest (örn: RSI)')
    
    parser.add_argument('--symbol', type=str, default='BTC/USDT',
                       help='Trading çifti (varsayılan: BTC/USDT)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Detaylı çıktı')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    INVESTMENT AGENT                      ║
║                  Akıllı Yatırım Robotu                   ║
╚══════════════════════════════════════════════════════════╝

🕐 Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 Mod: {args.mode.upper()}
💱 Symbol: {args.symbol}
    """)
    
    try:
        if args.mode == 'setup':
            setup_database()
            
        elif args.mode == 'live':
            run_live_trading()
            
        elif args.mode == 'backtest':
            run_backtest_mode(args.strategy)
            
        elif args.mode == 'portfolio':
            run_portfolio_report()
            
        elif args.mode == 'multi':
            run_multi_asset_mode()
            
        print(f"\n✅ İşlem tamamlandı - {datetime.now().strftime('%H:%M:%S')}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Kullanıcı tarafından durduruldu")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Argüman verilmemişse interaktif mod
        print("""
🤖 Investment Agent - Interaktif Mod

Mevcut komutlar:
1. setup     - Veritabanı kurulumu
2. live      - Canlı paper trading
3. backtest  - Strateji backtesting
4. portfolio - Portföy raporu
5. multi     - Çoklu varlık analizi

Örnek kullanım:
  python run.py live
  python run.py backtest --strategy RSI
  python run.py portfolio
        """)
        
        mode = input("\nHangi modu çalıştırmak istiyorsunuz? (live/backtest/portfolio/setup): ").strip().lower()
        
        if mode in ['live', 'backtest', 'portfolio', 'setup', 'multi']:
            sys.argv.append(mode)
            main_cli()
        else:
            print("❌ Geçersiz mod!")
    else:
        main_cli()