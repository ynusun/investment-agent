# 🤖 Investment Agent - Akıllı Yatırım Robotu

Gelişmiş risk yönetimi, paper trading ve makine öğrenmesi destekli kripto para yatırım robotu.

## 🚀 Özellikler

### ✅ Mevcut Özellikler
- **Paper Trading**: Gerçek para riski olmadan test ortamı
- **Risk Yönetimi**: Günlük kayıp limitleri, pozisyon büyüklüğü kontrolü
- **Çoklu Strateji**: RSI, SMA Crossover ve gelişmiş varyantlar
- **Gelişmiş Backtest**: Sharpe ratio, max drawdown, walk-forward analizi
- **Telegram Bildirimleri**: Anlık sinyal ve trade bildirimleri
- **Portföy Tracking**: Detaylı performans takibi
- **Monte Carlo Simülasyonu**: Risk analizi için

### 🔮 Gelecek Özellikler
- Makine öğrenmesi tabanlı sinyal üretimi
- Sentiment analizi (Twitter, Reddit, haber)
- Multi-asset portföy optimizasyonu
- Gerçek trading execution (testnet sonrası)

## 📊 Performans Metrikleri

Sistem şu metrikleri takip eder:
- **Sharpe Ratio**: Risk-adjusted getiri
- **Max Drawdown**: Maksimum sermaye kaybı
- **Win Rate**: Kazanan işlem oranı
- **Profit Factor**: Kazanç/kayıp oranı
- **VaR (Value at Risk)**: %95 ve %99 güven aralığında risk

## 🛠 Kurulum

### Gereksinimler
- Python 3.12+
- Supabase hesabı
- Binance API erişimi (public endpoints)
- Telegram Bot (opsiyonel)

### 1. Repository'yi klonlayın
```bash
git clone https://github.com/username/investment-agent.git
cd investment-agent
```

### 2. Virtual environment oluşturun
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

### 3. Bağımlılıkları yükleyin
```bash
pip install -r requirements.txt
```

### 4. Environment dosyasını yapılandırın
`.env` dosyasını oluşturun:
```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Telegram (opsiyonel)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Binance (public endpoints için gerekli değil)
BINANCE_API_KEY=your_api_key_if_needed
BINANCE_API_SECRET=your_secret_if_needed
```

### 5. Veritabanı kurulumu
```bash
python run.py setup
```

Bu komut:
- Gerekli tabloları oluşturur
- Örnek stratejileri ekler
- Portföyü başlatır

## 🎮 Kullanım

### Canlı Paper Trading
```bash
python run.py live
```
BTC/USDT için anlık analiz yapar ve paper trade gerçekleştirir.

### Çoklu Varlık Analizi
```bash
python run.py multi
```
BTC, ETH, BNB için eş zamanlı analiz.

### Backtest Çalıştırma
```bash
# Tüm stratejiler için
python run.py backtest

# Belirli strateji için
python run.py backtest --strategy RSI
```

### Portföy Raporu
```bash
python run.py portfolio
```
Güncel portföy durumu ve risk analizi.

## 📁 Proje Yapısı

```
investment-agent/
├── 📂 agents/
│   └── logger.py              # CSV loglama
├── 📂 analysis/
│   └── backtest.py            # Legacy backtest
├── 📂 data/
│   └── fetch_binance.py       # Binance API client
├── 📂 strategies/
│   ├── rsi_strategy.py        # RSI stratejisi
│   └── sma_crossover.py       # SMA crossover stratejisi
├── 📂 logs/
│   └── decisions.csv          # Karar logları
├── 🔧 advanced_backtest.py    # Gelişmiş backtest motoru
├── 🔧 backtest_engine.py      # Temel backtest
├── 💾 db.py                   # Supabase client
├── 🚀 main_updated.py         # Güncellenmiş ana dosya
├── 📊 optimizer.py            # Strateji optimizasyonu
├── 🎯 paper_trading.py        # Paper trading motoru
├── ⚠️ risk_manager.py         # Risk yönetimi
├── 🤖 run.py                  # Ana çalıştırma scripti
├── 📨 send_signal.py          # Telegram bildirimleri
├── 🏭 strategy_generator.py   # Strateji üretici
├── 🧪 test.py                 # Test dosyası
├── 📋 requirements.txt        # Python bağımlılıkları
├── 🗄️ schema.sql             # Veritabanı şeması
└── 📖 README.md               # Bu dosya
```

## 🎯 Strateji Sistemi

### Mevcut Stratejiler

#### 1. RSI (Relative Strength Index)
```python
# Parametre varyantları
rsi_period: [7, 14, 21]
overbought: [65, 70, 75]  
oversold: [25, 30, 35]
```

#### 2. SMA Crossover
```python
# Parametre varyantları
short_period: [5, 10, 15]
long_period: [30, 50, 100]
```

### Strateji Ekleme
Yeni strateji eklemek için:

1. `strategies/` klasöründe yeni dosya oluşturun
2. `compute_STRATEGY_signal()` fonksiyonu implement edin
3. `strategy_generator.py`'ye ekleyin
4. `python run.py setup` ile yenileyin

## 🛡️ Risk Yönetimi

### Otomatik Kontroller
- **Pozisyon Limiti**: Portföyün max %10'u
- **Günlük Kayıp**: Max %5 günlük kayıp
- **Nakit Rezerv**: Min %20 nakit tutma
- **Confidence Eşiği**: Min 0.6 güven puanı

### Risk Parametreleri
```python
# risk_manager.py içinde özelleştirilebilir
max_position_size_pct = 0.10    # %10 max pozisyon
max_daily_loss_pct = 0.05       # %5 max günlük kayıp
max_total_risk_pct = 0.80       # %80 max toplam risk
min_cash_reserve = 0.20         # %20 min nakit
```

## 📈 Backtest Özellikleri

### Temel Metrikler
- Total Return %
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor

### Gelişmiş Analizler
- **Walk-Forward**: 12 dönem ileriye dönük test
- **Monte Carlo**: 1000 simulasyon risk analizi  
- **Out-of-Sample**: Overfitting kontrolü

## 🔄 Çalışma Döngüsü

1. **Veri Toplama**: Binance'den OHLCV verileri
2. **Sinyal Üretimi**: Tüm stratejiler paralel çalışır
3. **Sinyal Seçimi**: En yüksek confidence'a sahip sinyal
4. **Risk Kontrolü**: Otomatik risk limiti kontrolları
5. **Paper Trade**: Simülasyon ortamında işlem
6. **Performans Takibi**: Sonuçları veritabanına kaydet
7. **Bildirim**: Telegram'a durum bildirimi

## 📊 Veritabanı Şeması

### Ana Tablolar
- `strategies`: Strateji tanımları ve parametreleri
- `paper_trades`: Paper trading işlemleri
- `portfolio_positions`: Mevcut pozisyonlar
- `portfolio_snapshots`: Portföy anlık görünümleri
- `risk_logs`: Risk yönetimi kararları
- `backtest_results`: Backtest sonuçları
- `signals`: Strateji sinyalleri

### Performans Views
- `portfolio_performance`: Günlük portföy performansı
- `strategy_performance_summary`: Strateji bazlı özet
- `daily_pnl_summary`: Günlük kar/zarar özeti

## 🚨 Güvenlik ve Risk

### ⚠️ Önemli Uyarılar
- Bu sistem **sadece paper trading** içindir
- Gerçek para ile işlem yapmadan önce kapsamlı test yapın
- Risk yönetimi ayarlarını kendi risk profilinize göre ayarlayın
- Yatırım tavsiyesi değildir, sadece eğitim amaçlıdır

### 🔒 Güvenlik Önlemleri
- API anahtarları environment variables'da saklanır
- Veritabanı erişimi Supabase RLS ile korunur
- Risk limitleri kod seviyesinde zorunlu
- Tüm işlemler loglanır

## 🧪 Test ve Geliştirme

### Unit Test Çalıştırma
```bash
pytest tests/ -v
```

### Kod Formatlaması
```bash
black .
flake8 .
```

### Performance Profiling
```bash
python -m cProfile -o profile.stats run.py backtest
```

## 📞 Telegram Bot Kurulumu

1. BotFather'dan yeni bot oluşturun
2. Bot token'ını alın
3. Chat ID'nizi öğrenin:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```
4. `.env` dosyasına ekleyin

## 🤝 Katkıda Bulunma

### Yeni Strateji Ekleme
```python
# strategies/your_strategy.py
def compute_your_strategy_signal(ohlcv, **params):
    # Strateji logiğiniz
    return signal, value
```

### Pull Request Süreci
1. Fork yapın
2. Feature branch oluşturun
3. Test ekleyin
4. Pull request açın

## 📋 TODO Liste

### Kısa Vadeli (1-2 hafta)
- [ ] Bollinger Bands stratejisi
- [ ] MACD stratejisi  
- [ ] Email bildirimleri
- [ ] Web dashboard (Streamlit)
- [ ] Position sizing optimizasyonu

### Orta Vadeli (1-2 ay)
- [ ] Machine Learning model integration
- [ ] Sentiment analysis (Twitter/Reddit)
- [ ] Multi-asset correlation analysis
- [ ] Advanced portfolio optimization
- [ ] Real-time WebSocket data feed

### Uzun Vadeli (3+ ay)
- [ ] Deep Learning price prediction
- [ ] Options strategies
- [ ] Cross-exchange arbitrage
- [ ] Mobile app notifications
- [ ] Institutional features

## 📈 Performans Örnekleri

```
[BEST STRATEGIES] Son backtest sonuçları:
═══════════════════════════════════════════════════

 1. RSI_rsi_period14_overbought70_oversold30
    Return:  +12.45% | Sharpe: 1.23 | Win Rate: 0.67 | Max DD: -3.21%

 2. SMA_Crossover_short_period10_long_period50  
    Return:   +8.91% | Sharpe: 0.89 | Win Rate: 0.62 | Max DD: -5.67%

 3. RSI_rsi_period7_overbought65_oversold25
    Return:   +7.23% | Sharpe: 0.76 | Win Rate: 0.58 | Max DD: -4.12%
```

## 🔗 Faydalı Linkler

- [Supabase Documentation](https://docs.supabase.com/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Pandas-TA Documentation](https://github.com/twopirllc/pandas-ta)
- [Risk Management Best Practices](https://www.investopedia.com/risk-management/)

## ⚖️ Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

## 📧 İletişim

- GitHub Issues: Bug report ve öneriler
- Telegram: [@your_username](https://t.me/your_username)
- Email: your.email@domain.com

---

**⚠️ Yasal Uyarı**: Bu yazılım sadece eğitim amaçlıdır. Finansal piyasalarda yatırım yapmak risklidir ve kayıplara neden olabilir. Yatırım kararlarınızı vermeden önce profesyonel finansal tavsiye alın.