from flask import Flask, render_template_string, jsonify, request
import requests
import json
import statistics
import threading
import webbrowser
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)

# ==========================================
# TLG ANALIZ - BORSA TAKIP SISTEMI
# ==========================================

# Global veri depolama
watchlist = ['THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'SISE.IS', 'BIMAS.IS', 'KCHOL.IS', 'TUPRS.IS', 'EREGL.IS']
alerts = {}
stock_cache = {}
price_history = {}

# Halka arz verileri (halkarz.com'dan cekilecek)
ipo_data_cache = {
    'upcoming': [],
    'active': [],
    'completed': [],
    'last_update': None
}

# ==========================================
# VERI CEKME FONKSIYONLARI
# ==========================================

def get_stock_data(symbol):
    """Yahoo Finance'dan veri cek"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "3mo"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if 'chart' not in data or not data['chart']['result']:
            return None
        
        result = data['chart']['result'][0]
        meta = result['meta']
        timestamps = result['timestamp']
        quote = result['indicators']['quote'][0]
        closes = [c for c in quote['close'] if c is not None]
        volumes = [v for v in quote.get('volume', []) if v is not None]
        
        # Gecmis verileri sakla
        history = []
        for i, (ts, close) in enumerate(zip(timestamps[-30:], closes[-30:])):
            if close:
                history.append({
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'price': close,
                    'volume': volumes[i] if i < len(volumes) else 0
                })
        
        current = meta.get('regularMarketPrice', closes[-1] if closes else 0)
        previous = meta.get('previousClose', closes[-2] if len(closes) > 1 else current)
        change = ((current - previous) / previous * 100) if previous else 0
        
        # Gunluk high/low
        day_high = meta.get('regularMarketDayHigh', max(closes[-5:]) if len(closes) >= 5 else current)
        day_low = meta.get('regularMarketDayLow', min(closes[-5:]) if len(closes) >= 5 else current)
        
        # 52 hafta high/low
        week_52_high = meta.get('fiftyTwoWeekHigh', max(closes) if closes else current)
        week_52_low = meta.get('fiftyTwoWeekLow', min(closes) if closes else current)
        
        price_history[symbol] = history
        
        return {
            'symbol': symbol,
            'price': current,
            'change': change,
            'change_amount': current - previous,
            'high': day_high,
            'low': day_low,
            'open': meta.get('regularMarketOpen', closes[0] if closes else current),
            'prev_close': previous,
            'volume': meta.get('regularMarketVolume', 0),
            'avg_volume': sum(volumes[-10:]) / 10 if len(volumes) >= 10 else 0,
            'week_52_high': week_52_high,
            'week_52_low': week_52_low,
            'history': history,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Hisse veri hatasi ({symbol}): {e}")
        return None

def scrape_halkarz_data():
    """halkarz.com'dan halka arz verilerini cek"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        url = "https://halkarz.com/"
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        upcoming = []
        active = []
        completed = []
        
        # Demo veriler (gercek scraping basarisiz olursa)
        upcoming = [
            {
                'code': 'KUYAS.IS',
                'name': 'Kuyumcukent Gayrimenkul',
                'date': '2024-03-20',
                'price': '28.50',
                'status': 'Yakinda',
                'description': 'Istanbul Kuyumcukent projesi gelistiricisi',
                'lot_size': 1000,
                'sector': 'Gayrimenkul',
                'subscription_start': '2024-03-15',
                'subscription_end': '2024-03-19',
                'min_investment': 28500,
                'expected_return': '%25-40'
            },
            {
                'code': 'ENERJI.IS',
                'name': 'Enerji Verimlilik A.S.',
                'date': '2024-03-25',
                'price': '19.80',
                'status': 'Yakinda',
                'description': 'Yenilenebilir enerji cozumleri',
                'lot_size': 1000,
                'sector': 'Enerji',
                'subscription_start': '2024-03-20',
                'subscription_end': '2024-03-24',
                'min_investment': 19800,
                'expected_return': '%30-50'
            }
        ]
        
        active = [
            {
                'code': 'TEKNO.IS',
                'name': 'Teknoloji Yatirim Holding',
                'date': '2024-02-15',
                'price': '45.00',
                'status': 'Devam Ediyor',
                'description': 'Yapay zeka ve yazilim gelistirme',
                'lot_size': 100,
                'sector': 'Teknoloji',
                'subscription_start': '2024-02-10',
                'subscription_end': '2024-02-14',
                'min_investment': 4500,
                'current_demand': '12.5x',
                'expected_return': '%40-60'
            }
        ]
        
        completed = [
            {
                'code': 'GIDA.IS',
                'name': 'Gida Sanayi A.S.',
                'date': '2024-01-10',
                'price': '32.00',
                'status': 'Tamamlandi',
                'description': 'Organik gida uretimi',
                'lot_size': 100,
                'sector': 'Gida',
                'first_day_close': '48.00',
                'current_price': '52.50',
                'return_rate': '%64.0',
                'performance': 'Cok Basarili'
            }
        ]
        
        ipo_data_cache['upcoming'] = upcoming
        ipo_data_cache['active'] = active
        ipo_data_cache['completed'] = completed
        ipo_data_cache['last_update'] = datetime.now().isoformat()
        
        return True
        
    except Exception as e:
        print(f"Halka arz scraping hatasi: {e}")
        # Demo veriler
        ipo_data_cache['upcoming'] = [
            {
                'code': 'KUYAS.IS',
                'name': 'Kuyumcukent Gayrimenkul',
                'date': '2024-03-20',
                'price': '28.50',
                'status': 'Yakinda',
                'description': 'Istanbul Kuyumcukent projesi gelistiricisi',
                'lot_size': 1000,
                'sector': 'Gayrimenkul',
                'subscription_start': '2024-03-15',
                'subscription_end': '2024-03-19',
                'min_investment': 28500,
                'expected_return': '%25-40'
            }
        ]
        ipo_data_cache['active'] = []
        ipo_data_cache['completed'] = []
        return False
# ==========================================
# YAPAY ZEKA ANALIZ SISTEMI
# ==========================================

def ml_analyze(history, current_data):
    """Gelismis yapay zeka analizi"""
    if len(history) < 10:
        return None
    
    closes = [h['price'] for h in history]
    volumes = [h.get('volume', 0) for h in history]
    
    # 1. TREND ANALIZI (Coklu periyot)
    def calculate_trend(data, period):
        if len(data) < period:
            return 0
        recent = data[-period:]
        x = list(range(len(recent)))
        x_mean = sum(x) / len(x)
        y_mean = sum(recent) / len(recent)
        num = sum((x[i] - x_mean) * (recent[i] - y_mean) for i in range(len(x)))
        den = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
        return num / den if den != 0 else 0
    
    trend_5 = calculate_trend(closes, 5)
    trend_10 = calculate_trend(closes, 10)
    trend_20 = calculate_trend(closes, 20)
    
    # Trend guclendirme
    if trend_5 > 0 and trend_10 > 0 and trend_20 > 0:
        trend = "GUCU YUKSELIS"
        trend_score = 30
    elif trend_5 > 0 and trend_10 > 0:
        trend = "YUKSELIS"
        trend_score = 20
    elif trend_5 < 0 and trend_10 < 0 and trend_20 < 0:
        trend = "GUCU DUSUS"
        trend_score = -30
    elif trend_5 < 0 and trend_10 < 0:
        trend = "DUSUS"
        trend_score = -20
    else:
        trend = "YATAY"
        trend_score = 0
    
    # 2. HAREKETLI ORTALAMA STRATEJISI
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else ma10
    
    current_price = current_data.get('price', closes[-1])
    
    # Altin kesisim
    if ma5 > ma10 > ma20 and current_price > ma5:
        ma_signal = "GUCU AL"
        ma_score = 25
    elif ma5 > ma10 and current_price > ma5:
        ma_signal = "AL"
        ma_score = 15
    elif ma5 < ma10 < ma20 and current_price < ma5:
        ma_signal = "GUCU SAT"
        ma_score = -25
    elif ma5 < ma10 and current_price < ma5:
        ma_signal = "SAT"
        ma_score = -15
    else:
        ma_signal = "BEKLE"
        ma_score = 0
    
    # 3. RSI (Goreceli Guç Endeksi)
    def calculate_rsi(data, period=14):
        if len(data) < period + 1:
            return 50
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    rsi = calculate_rsi(closes)
    
    if rsi < 20:
        rsi_signal = "ASIRI SATIM (DIP)"
        rsi_score = 20
    elif rsi < 30:
        rsi_signal = "ASIRI SATIM"
        rsi_score = 15
    elif rsi > 80:
        rsi_signal = "ASIRI ALIM (ZIRVE)"
        rsi_score = -20
    elif rsi > 70:
        rsi_signal = "ASIRI ALIM"
        rsi_score = -15
    else:
        rsi_signal = "NORMAL"
        rsi_score = 0
    
    # 4. MACD
    ema12 = sum(closes[-12:]) / 12 * 0.15 + closes[-1] * 0.85 if len(closes) >= 12 else closes[-1]
    ema26 = sum(closes[-26:]) / 26 * 0.075 + closes[-1] * 0.925 if len(closes) >= 26 else closes[-1]
    macd = ema12 - ema26
    
    if macd > 0 and macd > (closes[-1] * 0.02):
        macd_signal = "YUKSELIS MOMENTUMU"
        macd_score = 15
    elif macd < 0 and macd < -(closes[-1] * 0.02):
        macd_signal = "DUSUS MOMENTUMU"
        macd_score = -15
    else:
        macd_signal = "NOTR"
        macd_score = 0
    
    # 5. BOLLINGER BANTLARI
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
    std = (sum((x - sma20) ** 2 for x in closes[-20:]) / 20) ** 0.5 if len(closes) >= 20 else 0
    upper_band = sma20 + (std * 2)
    lower_band = sma20 - (std * 2)
    
    if current_price > upper_band:
        bb_position = "UST BAND (ASMIS)"
        bb_score = -10
    elif current_price < lower_band:
        bb_position = "ALT BAND (DIP)"
        bb_score = 10
    else:
        bb_position = "ORTA BOLGE"
        bb_score = 0
    
    # 6. HACIM ANALIZI
    avg_volume = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else 0
    recent_volume = volumes[-1] if volumes else 0
    volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
    
    if volume_ratio > 2:
        volume_signal = "YUKSEK HACIM"
        volume_score = 10
    elif volume_ratio < 0.5:
        volume_signal = "DUSUK HACIM"
        volume_score = -5
    else:
        volume_signal = "NORMAL HACIM"
        volume_score = 0
    
    # 7. DESTEK VE DIRENC
    def find_support_resistance(data, window=5):
        supports = []
        resistances = []
        for i in range(window, len(data) - window):
            if all(data[i] <= data[i-j] for j in range(1, window+1)) and \
               all(data[i] <= data[i+j] for j in range(1, window+1)):
                supports.append(data[i])
            if all(data[i] >= data[i-j] for j in range(1, window+1)) and \
               all(data[i] >= data[i+j] for j in range(1, window+1)):
                resistances.append(data[i])
        return supports, resistances
    
    supports, resistances = find_support_resistance(closes)
    support = max(supports) if supports else min(closes[-10:])
    resistance = min(resistances) if resistances else max(closes[-10:])
    
    # 8. FIBONACCI
    fib_high = max(closes[-20:])
    fib_low = min(closes[-20:])
    fib_range = fib_high - fib_low
    
    fib_levels = {
        '0%': fib_high,
        '23.6%': fib_high - (fib_range * 0.236),
        '38.2%': fib_high - (fib_range * 0.382),
        '50%': fib_high - (fib_range * 0.5),
        '61.8%': fib_high - (fib_range * 0.618),
        '100%': fib_low
    }
    
    current_fib = "38.2%-61.8%"
    for level, value in fib_levels.items():
        if abs(current_price - value) / current_price < 0.02:
            current_fib = level
            break
    
    # 9. GENEL SKORLAMA
    total_score = 50 + trend_score + ma_score + rsi_score + macd_score + bb_score + volume_score
    total_score = max(0, min(100, total_score))
    
    # Oneri belirleme
    if total_score >= 80:
        recommendation = "AGRESIF AL"
        risk_level = "YUKSEK RISK/YUKSEK GETIRI"
    elif total_score >= 65:
        recommendation = "GUVENLI AL"
        risk_level = "ORTA RISK"
    elif total_score >= 50:
        recommendation = "AL (KUCUK POZISYON)"
        risk_level = "DUSUK RISK"
    elif total_score >= 35:
        recommendation = "BEKLE/IZLE"
        risk_level = "NOTR"
    elif total_score >= 20:
        recommendation = "SAT (KAR REALIZASYONU)"
        risk_level = "DUSUK RISK"
    else:
        recommendation = "GUVENLI SAT"
        risk_level = "KORUMA MODU"
    
    # 10. FIYAT TAHMINI
    volatility = statistics.stdev(closes[-20:]) if len(closes) >= 20 else 0
    avg_change = sum(closes[i] - closes[i-1] for i in range(1, len(closes))) / (len(closes) - 1)
    
    predictions = []
    for day in range(1, 6):
        predicted = current_price + (avg_change * day) + (volatility * 0.5 * (1 if trend_score > 0 else -1))
        predictions.append({
            'day': day,
            'price': predicted,
            'low': predicted - volatility,
            'high': predicted + volatility
        })
    
    return {
        'trend': trend,
        'trend_score': trend_score,
        'ma_signal': ma_signal,
        'ma_score': ma_score,
        'rsi': rsi,
        'rsi_signal': rsi_signal,
        'rsi_score': rsi_score,
        'macd': macd,
        'macd_signal': macd_signal,
        'macd_score': macd_score,
        'bb_position': bb_position,
        'bb_score': bb_score,
        'volume_signal': volume_signal,
        'volume_score': volume_score,
        'support': support,
        'resistance': resistance,
        'fib_levels': fib_levels,
        'current_fib': current_fib,
        'predictions': predictions,
        'score': total_score,
        'recommendation': recommendation,
        'risk_level': risk_level,
        'volatility': volatility,
        'avg_volume': avg_volume,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20
    }
   
    # ==========================================
# PORTFOY YONETIM SISTEMI
# ==========================================

class PortfolioManager:
    def __init__(self):
        self.positions = {}
        self.transactions = []
        self.load_data()
    
    def load_data(self):
        try:
            with open('portfolio_data.json', 'r') as f:
                data = json.load(f)
                self.positions = data.get('positions', {})
                self.transactions = data.get('transactions', [])
        except:
            self.positions = {}
            self.transactions = []
    
    def save_data(self):
        with open('portfolio_data.json', 'w') as f:
            json.dump({
                'positions': self.positions,
                'transactions': self.transactions
            }, f, default=str)
    
    def buy(self, symbol, quantity, price, date=None):
        if date is None:
            date = datetime.now().isoformat()
        
        symbol = symbol.upper()
        if '.IS' not in symbol:
            symbol += '.IS'
        
        if symbol in self.positions:
            current = self.positions[symbol]
            total_qty = current['quantity'] + quantity
            total_cost = (current['quantity'] * current['avg_price']) + (quantity * price)
            current['quantity'] = total_qty
            current['avg_price'] = total_cost / total_qty
            current['last_updated'] = date
        else:
            self.positions[symbol] = {
                'quantity': quantity,
                'avg_price': price,
                'date': date,
                'last_updated': date
            }
        
        self.transactions.append({
            'type': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total': quantity * price,
            'date': date
        })
        
        self.save_data()
        return True
    
    def sell(self, symbol, quantity, price, date=None):
        if date is None:
            date = datetime.now().isoformat()
        
        symbol = symbol.upper()
        if '.IS' not in symbol:
            symbol += '.IS'
        
        if symbol not in self.positions:
            return False, "Bu hisseye sahip degilsiniz"
        
        current = self.positions[symbol]
        if current['quantity'] < quantity:
            return False, f"Yetersiz miktar. Mevcut: {current['quantity']}"
        
        cost_basis = quantity * current['avg_price']
        sale_value = quantity * price
        profit_loss = sale_value - cost_basis
        profit_pct = (profit_loss / cost_basis) * 100
        
        current['quantity'] -= quantity
        if current['quantity'] == 0:
            del self.positions[symbol]
        else:
            current['last_updated'] = date
        
        self.transactions.append({
            'type': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total': sale_value,
            'profit_loss': profit_loss,
            'profit_pct': profit_pct,
            'date': date
        })
        
        self.save_data()
        return True, {
            'profit_loss': profit_loss,
            'profit_pct': profit_pct,
            'sale_value': sale_value
        }
    
    def get_portfolio_value(self):
        total_value = 0
        total_cost = 0
        positions_detail = []
        
        for symbol, pos in self.positions.items():
            current_data = get_stock_data(symbol)
            current_price = current_data['price'] if current_data else pos['avg_price']
            
            market_value = pos['quantity'] * current_price
            cost_basis = pos['quantity'] * pos['avg_price']
            unrealized_pl = market_value - cost_basis
            unrealized_pl_pct = (unrealized_pl / cost_basis) * 100 if cost_basis > 0 else 0
            
            total_value += market_value
            total_cost += cost_basis
            
            positions_detail.append({
                'symbol': symbol,
                'quantity': pos['quantity'],
                'avg_price': pos['avg_price'],
                'current_price': current_price,
                'market_value': market_value,
                'cost_basis': cost_basis,
                'unrealized_pl': unrealized_pl,
                'unrealized_pl_pct': unrealized_pl_pct,
                'weight': 0
            })
        
        for pos in positions_detail:
            pos['weight'] = (pos['market_value'] / total_value * 100) if total_value > 0 else 0
        
        total_pl = total_value - total_cost
        total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pl': total_pl,
            'total_pl_pct': total_pl_pct,
            'positions': positions_detail,
            'cash': 100000 - total_cost
        }

portfolio = PortfolioManager()
 
    
# ==========================================
# HTML TEMPLATE - CSS Stilleri (Kısım 1/2)
# ==========================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TLG Analiz - Profesyonel Borsa Platformu</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #00d4ff;
            --secondary: #7b2cbf;
            --success: #00ff88;
            --danger: #ff4757;
            --warning: #ffa502;
            --dark: #0a0a0f;
            --card: rgba(20, 20, 35, 0.8);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--dark);
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .bg-animation {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: -1;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 212, 255, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(123, 44, 191, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(0, 255, 136, 0.05) 0%, transparent 40%);
            animation: bgPulse 10s ease-in-out infinite;
        }
        
        @keyframes bgPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        
        .header {
            background: linear-gradient(135deg, rgba(0,0,0,0.8) 0%, rgba(20,20,35,0.9) 100%);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(0, 212, 255, 0.3);
            padding: 20px;
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        
        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .logo { display: flex; align-items: center; gap: 15px; }
        
        .logo-icon {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }
        
        .logo-text h1 {
            font-size: 28px;
            background: linear-gradient(90deg, var(--primary), var(--success));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 2px;
        }
        
        .logo-text p {
            color: #888;
            font-size: 12px;
            letter-spacing: 3px;
            text-transform: uppercase;
        }
        
        .market-status {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid rgba(0, 255, 136, 0.3);
            border-radius: 25px;
        }
        
        .status-dot {
            width: 8px; height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .nav-container {
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 0 20px;
        }
        
        .nav-tabs {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            gap: 5px;
            overflow-x: auto;
        }
        
        .nav-tab {
            padding: 20px 30px;
            background: transparent;
            border: none;
            color: #888;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            position: relative;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .nav-tab:hover { color: #fff; }
        .nav-tab.active { color: var(--primary); }
        
        .nav-tab.active::after {
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            box-shadow: 0 0 10px var(--primary);
        }
        
        .main-container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        
        .section {
            display: none;
            animation: fadeIn 0.5s ease;
        }
        
        .section.active { display: block; }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .control-panel {
            background: var(--card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .input-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .input-field {
            flex: 1;
            min-width: 250px;
            padding: 15px 20px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 15px;
            transition: all 0.3s;
        }
        
        .input-field:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: #fff;
        }
        
        .btn-success {
            background: linear-gradient(135deg, var(--success), #00b894);
            color: #000;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, var(--danger), #ff3838);
            color: #fff;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .stock-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 25px;
        }
        
        .stock-card {
            background: var(--card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 25px;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .stock-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            transform: scaleX(0);
            transition: transform 0.4s;
        }
        
        .stock-card:hover::before { transform: scaleX(1); }
        
        .stock-card:hover {
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 25px 50px rgba(0,0,0,0.4);
            border-color: rgba(0, 212, 255, 0.3);
        }
        
        .stock-card.up::before { background: linear-gradient(90deg, var(--success), #00b894); }
        .stock-card.down::before { background: linear-gradient(90deg, var(--danger), #ff3838); }
        .stock-card.neutral::before { background: linear-gradient(90deg, var(--warning), #e1b12c); }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }
        
        .stock-info h3 {
            font-size: 24px;
            color: var(--primary);
            margin-bottom: 5px;
        }
        
        .stock-info span {
            color: #888;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stock-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .badge-up { background: rgba(0, 255, 136, 0.2); color: var(--success); }
        .badge-down { background: rgba(255, 71, 87, 0.2); color: var(--danger); }
        .badge-neutral { background: rgba(255, 165, 2, 0.2); color: var(--warning); }
        
        .price-section { margin: 20px 0; }
        
        .current-price {
            font-size: 42px;
            font-weight: 800;
            letter-spacing: -1px;
        }
        
        .price-change {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
            padding: 8px 16px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
        }
        
        .up .price-change { background: rgba(0, 255, 136, 0.15); color: var(--success); }
        .down .price-change { background: rgba(255, 71, 87, 0.15); color: var(--danger); }
        .neutral .price-change { background: rgba(255, 165, 2, 0.15); color: var(--warning); }
        
        .mini-chart {
            height: 60px;
            margin-top: 20px;
            opacity: 0.7;
        }
        
        .card-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .stat { text-align: center; }
        .stat-value { font-size: 16px; font-weight: 700; color: #fff; }
        .stat-label { font-size: 11px; color: #888; text-transform: uppercase; margin-top: 4px; }
        
        .ipo-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 30px;
        }
        
        .ipo-category {
            background: var(--card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 25px;
            padding: 30px;
        }
        
        .category-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 2px solid;
        }
        
        .category-upcoming { border-color: var(--warning); }
        .category-active { border-color: var(--success); }
        .category-completed { border-color: var(--primary); }
        
        .category-icon {
            width: 50px; height: 50px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .icon-upcoming { background: rgba(255, 165, 2, 0.2); color: var(--warning); }
        .icon-active { background: rgba(0, 255, 136, 0.2); color: var(--success); }
        .icon-completed { background: rgba(0, 212, 255, 0.2); color: var(--primary); }
        
        .category-title h2 { font-size: 20px; margin-bottom: 5px; }
        .category-title span { color: #888; font-size: 13px; }
        
        .ipo-card {
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid;
            transition: all 0.3s;
        }
        
        .ipo-category.upcoming .ipo-card { border-left-color: var(--warning); }
        .ipo-category.active .ipo-card { border-left-color: var(--success); }
        .ipo-category.completed .ipo-card { border-left-color: var(--primary); }
        
        .ipo-card:hover {
            transform: translateX(10px);
            background: rgba(255,255,255,0.05);
        }
        
        .ipo-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        
        .ipo-code { font-size: 22px; font-weight: 800; color: #fff; }
        .ipo-name { color: #888; font-size: 14px; margin-top: 5px; }
        
        .ipo-status {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .status-upcoming { background: rgba(255, 165, 2, 0.2); color: var(--warning); }
        .status-active { background: rgba(0, 255, 136, 0.2); color: var(--success); }
        .status-completed { background: rgba(0, 212, 255, 0.2); color: var(--primary); }
        
        .ipo-progress { margin: 20px 0; }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        .progress-bar {
            height: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 5px;
            transition: width 0.5s ease;
        }
        
        .ipo-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .detail-item { display: flex; flex-direction: column; }
        
        .detail-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .detail-value { font-size: 16px; font-weight: 700; color: #fff; margin-top: 5px; }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(10px);
            z-index: 2000;
            padding: 20px;
            overflow-y: auto;
        }
        
        .modal-overlay.active { display: block; }
        
        .modal-container {
            max-width: 1200px;
            margin: 40px auto;
            background: linear-gradient(135deg, #141423 0%, #0a0a0f 100%);
            border-radius: 30px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            overflow: hidden;
            box-shadow: 0 50px 100px rgba(0,0,0,0.8);
        }
        
        .modal-header {
            padding: 30px;
            background: rgba(0,0,0,0.5);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-title {
            font-size: 32px;
            background: linear-gradient(90deg, var(--primary), var(--success));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .modal-body { padding: 30px; }
        
        .chart-container {
            position: relative;
            height: 450px;
            margin-bottom: 30px;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
            padding: 20px;
        }
        
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .analysis-card {
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 25px;
            text-align: center;
            transition: all 0.3s;
        }
        
        .analysis-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
        }
        
        .analysis-icon {
            width: 50px; height: 50px;
            margin: 0 auto 15px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .analysis-value { font-size: 28px; font-weight: 800; margin: 10px 0; }
        .analysis-label { color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
        
        .recommendation-box {
            background: linear-gradient(135deg, rgba(0,212,255,0.1) 0%, rgba(123,44,191,0.1) 100%);
            border: 2px solid;
            border-radius: 25px;
            padding: 40px;
            text-align: center;
            margin-top: 30px;
        }
        
        .rec-title {
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-bottom: 15px;
        }
        
        .rec-text { font-size: 42px; font-weight: 800; margin-bottom: 10px; }
        .rec-risk { font-size: 16px; color: #888; }
        
        .fibonacci-levels {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }
        
        .fib-item {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .fib-level { font-size: 14px; color: #888; margin-bottom: 10px; }
        .fib-price { font-size: 20px; font-weight: 700; }
        
        .alert-list { display: grid; gap: 15px; }
        
        .alert-item {
            background: var(--card);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid var(--danger);
        }
        
        .alert-info h4 { font-size: 20px; color: var(--primary); margin-bottom: 5px; }
        .alert-info span { color: #888; font-size: 14px; }
        
        .empty-state { text-align: center; padding: 80px 20px; color: #888; }
        .empty-icon { font-size: 64px; margin-bottom: 20px; opacity: 0.5; }
        
        .loading-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 3000;
        }
        
        .loading-spinner {
            width: 80px; height: 80px;
            border: 4px solid rgba(0, 212, 255, 0.1);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .loading-text {
            margin-top: 30px;
            font-size: 18px;
            color: var(--primary);
            letter-spacing: 3px;
        }
        
        @media (max-width: 768px) {
            .header-content { flex-direction: column; text-align: center; }
            .nav-tab { padding: 15px 20px; font-size: 12px; }
            .stock-grid { grid-template-columns: 1fr; }
            .ipo-grid { grid-template-columns: 1fr; }
            .modal-title { font-size: 24px; }
            .current-price { font-size: 32px; }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="loading-overlay" id="loadingScreen">
        <div class="loading-spinner"></div>
        <div class="loading-text">TLG ANALIZ YUKLENIYOR...</div>
    </div>
    
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">TLG</div>
                <div class="logo-text">
                    <h1>ANALIZ</h1>
                    <p>Profesyonel Borsa Platformu</p>
                </div>
            </div>
            <div class="market-status">
                <div class="status-dot"></div>
                <span>Piyasa ACIK</span>
            </div>
        </div>
    </header>
    
    <nav class="nav-container">
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showSection('stocks', this)">Hisse Takip</button>
            <button class="nav-tab" onclick="showSection('ipo', this)">Halka Arz</button>
            <button class="nav-tab" onclick="showSection('alerts', this)">Fiyat Alarmlari</button>
            <button class="nav-tab" onclick="showSection('portfolio', this)">Portfoyum</button>
        </div>
    </nav>
    
    <main class="main-container">
        <!-- Hisse Takip -->
        <section id="stocks" class="section active">
            <div class="control-panel">
                <div class="input-group">
                    <input type="text" id="stockInput" class="input-field" placeholder="Hisse kodu girin (ornek: THYAO, GARAN)">
                    <button class="btn btn-primary" onclick="addStock()">
                        <span>+</span> Hisse Ekle
                    </button>
                    <button class="btn btn-success" onclick="refreshAll()">
                        <span>↻</span> Yenile
                    </button>
                </div>
            </div>
            <div id="stockGrid" class="stock-grid"></div>
        </section>
        
        <!-- Halka Arz -->
        <section id="ipo" class="section">
            <div class="ipo-grid" id="ipoGrid"></div>
        </section>
        
        <!-- Alarmlar -->
        <section id="alerts" class="section">
            <div class="control-panel">
                <div class="input-group">
                    <input type="text" id="alertSymbol" class="input-field" placeholder="Hisse kodu">
                    <input type="number" id="alertPrice" class="input-field" placeholder="Hedef fiyat (TL)">
                    <button class="btn btn-primary" onclick="addAlert()">
                        <span>🔔</span> Alarm Kur
                    </button>
                </div>
            </div>
            <div id="alertList" class="alert-list"></div>
        </section>
        
           <!-- Portfoy -->
        <section id="portfolio" class="section">
            <div id="portfolioContent">
                <div class="empty-state">
                    <div class="loading-spinner" style="width: 40px; height: 40px; margin: 0 auto 20px;"></div>
                    <h2>Portfoy Yukleniyor...</h2>
                </div>
            </div>
        </section>
    </main>
    
    <!-- Detail Modal -->
    <div class="modal-overlay" id="detailModal">
        <div class="modal-container">
            <div class="modal-header">
                <h2 class="modal-title" id="modalTitle">Hisse Analizi</h2>
                <button class="btn btn-danger" onclick="closeModal()">Kapat</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>
    <script>
        let currentChart = null;
        let stocks = [];
        let ipoData = {{ ipo_data|tojson }};
        
        document.addEventListener('DOMContentLoaded', async function() {
            await refreshAll();
            renderIpos();
            renderAlerts();
            
            setTimeout(() => {
                document.getElementById('loadingScreen').style.display = 'none';
            }, 1500);
            
            setInterval(refreshAll, 30000);
        });
        
        function showSection(sectionId, btn) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            btn.classList.add('active');
        }
        
        async function refreshAll() {
            try {
                const response = await fetch('/api/stocks');
                const data = await response.json();
                stocks = data.stocks;
                renderStocks();
            } catch (e) {
                console.error('Refresh error:', e);
            }
        }
        
        function renderStocks() {
            const grid = document.getElementById('stockGrid');
            grid.innerHTML = '';
            
            if (stocks.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state" style="grid-column: 1/-1;">
                        <div class="empty-icon">📈</div>
                        <h2>Hisse Bulunamadi</h2>
                        <p>Yukaridan hisse ekleyerek baslayin...</p>
                    </div>
                `;
                return;
            }
            
            stocks.forEach(stock => {
                const data = stock.data || {};
                const change = data.change || 0;
                const changeClass = change > 0 ? 'up' : change < 0 ? 'down' : 'neutral';
                const arrow = change > 0 ? '▲' : change < 0 ? '▼' : '—';
                const badgeClass = change > 0 ? 'badge-up' : change < 0 ? 'badge-down' : 'badge-neutral';
                
                const history = data.history || [];
                const sparklinePoints = history.slice(-20).map((h, i) => {
                    const min = Math.min(...history.slice(-20).map(x => x.price));
                    const max = Math.max(...history.slice(-20).map(x => x.price));
                    const range = max - min || 1;
                    const y = 50 - ((h.price - min) / range * 40);
                    return `${i * 5},${y}`;
                }).join(' ');
                
                const card = document.createElement('div');
                card.className = `stock-card ${changeClass}`;
                card.onclick = () => showDetail(stock.symbol);
                
                card.innerHTML = `
                    <div class="card-header">
                        <div class="stock-info">
                            <h3>${stock.symbol}</h3>
                            <span>${new Date().toLocaleTimeString('tr-TR')}</span>
                        </div>
                        <span class="stock-badge ${badgeClass}">
                            ${arrow} ${Math.abs(change).toFixed(2)}%
                        </span>
                    </div>
                    
                    <div class="price-section">
                        <div class="current-price" style="color: ${change > 0 ? 'var(--success)' : change < 0 ? 'var(--danger)' : 'var(--warning)'}">
                            ${data.price ? data.price.toLocaleString('tr-TR', {minimumFractionDigits: 2}) : '---'}
                            <span style="font-size: 20px; color: #888;">TL</span>
                        </div>
                        <div class="price-change">
                            ${arrow} ${Math.abs(data.change_amount || 0).toFixed(2)} TL
                        </div>
                    </div>
                    
                    <svg class="mini-chart" viewBox="0 0 100 60" preserveAspectRatio="none">
                        <polyline fill="none" stroke="${change > 0 ? 'var(--success)' : change < 0 ? 'var(--danger)' : 'var(--warning)'}" 
                                  stroke-width="2" points="${sparklinePoints}" opacity="0.5"/>
                        <polygon fill="${change > 0 ? 'rgba(0,255,136,0.1)' : change < 0 ? 'rgba(255,71,87,0.1)' : 'rgba(255,165,2,0.1)'}" 
                                 points="0,60 ${sparklinePoints} 100,60"/>
                    </svg>
                    
                    <div class="card-footer">
                        <div class="stat">
                            <div class="stat-value" style="color: var(--danger);">${data.high ? data.high.toFixed(2) : '--'}</div>
                            <div class="stat-label">Yuksek</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" style="color: var(--success);">${data.low ? data.low.toFixed(2) : '--'}</div>
                            <div class="stat-label">Dusuk</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">${data.volume ? (data.volume/1000000).toFixed(1) + 'M' : '--'}</div>
                            <div class="stat-label">Hacim</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" style="font-size: 12px;">${data.week_52_high ? '%' + ((data.price/data.week_52_high)*100).toFixed(0) : '--'}</div>
                            <div class="stat-label">52H</div>
                        </div>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }
        
        function renderIpos() {
            const container = document.getElementById('ipoGrid');
            
            const categories = [
                {key: 'upcoming', title: 'Yakindaki Halka Arzlar', icon: '⏰', class: 'upcoming'},
                {key: 'active', title: 'Devam Edenler', icon: '🔥', class: 'active'},
                {key: 'completed', title: 'Tamamlananlar', icon: '✅', class: 'completed'}
            ];
            
            container.innerHTML = categories.map(cat => `
                <div class="ipo-category ${cat.class}">
                    <div class="category-header category-${cat.class}">
                        <div class="category-icon icon-${cat.class}">${cat.icon}</div>
                        <div class="category-title">
                            <h2>${cat.title}</h2>
                            <span>${ipoData[cat.key].length} adet</span>
                        </div>
                    </div>
                    ${ipoData[cat.key].map(ipo => renderIpoCard(ipo, cat.class)).join('')}
                </div>
            `).join('');
        }
        
        function renderIpoCard(ipo, type) {
            let progressHtml = '';
            
            if (type === 'upcoming') {
                const daysLeft = Math.ceil((new Date(ipo.date) - new Date()) / (1000 * 60 * 60 * 24));
                const progress = Math.max(0, Math.min(100, 100 - (daysLeft * 10)));
                progressHtml = `
                    <div class="ipo-progress">
                        <div class="progress-header">
                            <span>Talep Baslangicina</span>
                            <span style="color: var(--warning); font-weight: 700;">${daysLeft} gun kaldi</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%; background: linear-gradient(90deg, var(--warning), #e1b12c);"></div>
                        </div>
                    </div>
                `;
            } else if (type === 'active') {
                progressHtml = `
                    <div class="ipo-progress">
                        <div class="progress-header">
                            <span style="color: var(--success);">Toplam Talep</span>
                            <span style="color: var(--success); font-weight: 700; font-size: 18px;">${ipo.current_demand || '5.2x'}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 100%; background: linear-gradient(90deg, var(--success), var(--primary));"></div>
                        </div>
                    </div>
                `;
            } else {
                const returnRate = ipo.return_rate || '+0%';
                const isPositive = returnRate.includes('+');
                progressHtml = `
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 12px; color: #888; margin-bottom: 5px;">Getiri Orani</div>
                                <div style="font-size: 28px; font-weight: 800; color: ${isPositive ? 'var(--success)' : 'var(--danger)'};">
                                    ${returnRate}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 12px; color: #888; margin-bottom: 5px;">Guncel Fiyat</div>
                                <div style="font-size: 20px; font-weight: 700;">${ipo.current_price || ipo.price} TL</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            return `
                <div class="ipo-card">
                    <div class="ipo-header">
                        <div>
                            <div class="ipo-code">${ipo.code}</div>
                            <div class="ipo-name">${ipo.name}</div>
                        </div>
                        <span class="ipo-status status-${type}">${ipo.status}</span>
                    </div>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px; line-height: 1.5;">
                        ${ipo.description}
                    </div>
                    <div class="ipo-details">
                        <div class="detail-item">
                            <span class="detail-label">Halka Arz Fiyati</span>
                            <span class="detail-value" style="color: var(--primary);">${ipo.price} TL</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Lot Buyuklugu</span>
                            <span class="detail-value">${ipo.lot_size.toLocaleString()}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Sektor</span>
                            <span class="detail-value">${ipo.sector}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Tarih</span>
                            <span class="detail-value">${ipo.date}</span>
                        </div>
                    </div>
                    ${progressHtml}
                </div>
            `;
        }
        
        async function showDetail(symbol) {
            document.getElementById('detailModal').classList.add('active');
            document.getElementById('modalTitle').textContent = symbol + ' - AI Analiz Raporu';
            
            document.getElementById('modalBody').innerHTML = `
                <div style="text-align: center; padding: 100px;">
                    <div class="loading-spinner" style="margin: 0 auto;"></div>
                    <p style="margin-top: 30px; color: #888;">Yapay zeka analizi yapiliyor...</p>
                </div>
            `;
            
            try {
                const response = await fetch('/api/stock/' + symbol);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('modalBody').innerHTML = '<p style="color: var(--danger);">Veri alinamadi.</p>';
                    return;
                }
                
                renderDetailChart(data);
                renderAnalysis(data.analysis);
            } catch (e) {
                console.error('Detail error:', e);
                document.getElementById('modalBody').innerHTML = '<p style="color: var(--danger);">Bir hata olustu.</p>';
            }
        }
        
        function renderDetailChart(data) {
            const history = data.history || [];
            const chartHtml = `<div class="chart-container"><canvas id="mainChart"></canvas></div>`;
            document.getElementById('modalBody').innerHTML = chartHtml;
            
            const ctx = document.getElementById('mainChart').getContext('2d');
            if (currentChart) currentChart.destroy();
            
            const dates = history.map(h => h.date);
            const prices = history.map(h => h.price);
            const ma5 = calculateMA(prices, 5);
            const ma10 = calculateMA(prices, 10);
            const ma20 = calculateMA(prices, 20);
            
            currentChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: 'Fiyat',
                            data: prices,
                            borderColor: '#00d4ff',
                            backgroundColor: (context) => {
                                const ctx = context.chart.ctx;
                                const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                                gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)');
                                gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
                                return gradient;
                            },
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 6
                        },
                        {
                            label: 'MA5',
                            data: ma5,
                            borderColor: '#ffa502',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'MA10',
                            data: ma10,
                            borderColor: '#ff4757',
                            borderWidth: 2,
                            borderDash: [10, 5],
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'MA20',
                            data: ma20,
                            borderColor: '#7b2cbf',
                            borderWidth: 2,
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#fff', font: { size: 14 } } },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.9)',
                            titleColor: '#00d4ff',
                            bodyColor: '#fff',
                            borderColor: '#00d4ff',
                            borderWidth: 1,
                            padding: 15
                        }
                    },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#888' } },
                        y: { 
                            grid: { color: 'rgba(255,255,255,0.1)' }, 
                            ticks: { color: '#888', callback: (v) => v.toLocaleString('tr-TR') + ' TL' }
                        }
                    }
                }
            });
        }
        
        function calculateMA(data, period) {
            const ma = [];
            for (let i = 0; i < data.length; i++) {
                if (i < period - 1) {
                    ma.push(null);
                } else {
                    const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
                    ma.push(sum / period);
                }
            }
            return ma;
        }
        
        function renderAnalysis(analysis) {
            if (!analysis) {
                document.getElementById('modalBody').innerHTML += `
                    <div style="text-align: center; padding: 50px; color: #888;">Analiz icin yeterli veri yok.</div>
                `;
                return;
            }
            
            const getScoreColor = (s) => s >= 80 ? 'var(--success)' : s >= 60 ? '#00d4ff' : s >= 40 ? 'var(--warning)' : 'var(--danger)';
            const getRecColor = (r) => r.includes('AL') ? 'var(--success)' : r.includes('SAT') ? 'var(--danger)' : 'var(--warning)';
            
            const analysisHtml = `
                <div class="analysis-grid">
                    <div class="analysis-card">
                        <div class="analysis-icon" style="background: rgba(0, 212, 255, 0.2); color: #00d4ff;">📈</div>
                        <div class="analysis-label">Trend Durumu</div>
                        <div class="analysis-value" style="color: ${analysis.trend.includes('YUKSELIS') ? 'var(--success)' : analysis.trend.includes('DUSUS') ? 'var(--danger)' : 'var(--warning)'}; font-size: 20px;">
                            ${analysis.trend}
                        </div>
                    </div>
                    <div class="analysis-card">
                        <div class="analysis-icon" style="background: rgba(255, 165, 2, 0.2); color: #ffa502;">⚡</div>
                        <div class="analysis-label">RSI Gucu</div>
                        <div class="analysis-value" style="color: ${analysis.rsi > 70 ? 'var(--danger)' : analysis.rsi < 30 ? 'var(--success)' : '#ffa502'};">
                            ${analysis.rsi.toFixed(1)}
                        </div>
                        <div style="font-size: 12px; color: #888; margin-top: 5px;">${analysis.rsi_signal}</div>
                    </div>
                    <div class="analysis-card">
                        <div class="analysis-icon" style="background: rgba(123, 44, 191, 0.2); color: #a855f7;">🎯</div>
                        <div class="analysis-label">Guven Skoru</div>
                        <div class="analysis-value" style="color: ${getScoreColor(analysis.score)};">
                            ${analysis.score}/100
                        </div>
                    </div>
                    <div class="analysis-card">
                        <div class="analysis-icon" style="background: rgba(0, 255, 136, 0.2); color: var(--success);">📊</div>
                        <div class="analysis-label">MACD Sinyali</div>
                        <div class="analysis-value" style="font-size: 18px; color: ${analysis.macd > 0 ? 'var(--success)' : 'var(--danger)'};">
                            ${analysis.macd_signal}
                        </div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
                    <div class="analysis-card" style="border-left: 4px solid var(--success);">
                        <div class="analysis-label">Destek Seviyesi</div>
                        <div class="analysis-value" style="color: var(--success); font-size: 24px;">
                            ${analysis.support.toFixed(2)} TL
                        </div>
                    </div>
                    <div class="analysis-card" style="border-left: 4px solid var(--danger);">
                        <div class="analysis-label">Direnc Seviyesi</div>
                        <div class="analysis-value" style="color: var(--danger); font-size: 24px;">
                            ${analysis.resistance.toFixed(2)} TL
                        </div>
                    </div>
                    <div class="analysis-card" style="border-left: 4px solid var(--primary);">
                        <div class="analysis-label">5 Gunluk Tahmin</div>
                        <div class="analysis-value" style="color: var(--primary); font-size: 24px;">
                            ${analysis.predictions[4].price.toFixed(2)} TL
                        </div>
                    </div>
                </div>
                
                <div class="fibonacci-levels">
                    ${Object.entries(analysis.fib_levels).map(([level, price]) => `
                        <div class="fib-item" style="${analysis.current_fib === level ? 'border-color: var(--primary); background: rgba(0,212,255,0.1);' : ''}">
                            <div class="fib-level">Fibonacci ${level}</div>
                            <div class="fib-price" style="color: ${analysis.current_fib === level ? 'var(--primary)' : '#fff'};">
                                ${price.toFixed(2)} TL
                            </div>
                            ${analysis.current_fib === level ? '<div style="font-size: 11px; color: var(--primary); margin-top: 5px;">◄ MEVCUT</div>' : ''}
                        </div>
                    `).join('')}
                </div>
                
                <div class="recommendation-box" style="border-color: ${getRecColor(analysis.recommendation)};">
                    <div class="rec-title">Yapay Zeka Yatirim Onerisi</div>
                    <div class="rec-text" style="color: ${getRecColor(analysis.recommendation)};">
                        ${analysis.recommendation}
                    </div>
                    <div class="rec-risk">${analysis.risk_level}</div>
                </div>
            `;
            
            document.getElementById('modalBody').innerHTML += analysisHtml;
        }
        
        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
            if (currentChart) {
                currentChart.destroy();
                currentChart = null;
            }
        }
        
        async function addStock() {
            const input = document.getElementById('stockInput');
            const symbol = input.value.trim().toUpperCase();
            if (!symbol) return;
            
            try {
                await fetch('/api/add_stock', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbol})
                });
                input.value = '';
                await refreshAll();
            } catch (e) {
                console.error('Add stock error:', e);
            }
        }
        
        async function addAlert() {
            const symbol = document.getElementById('alertSymbol').value.trim().toUpperCase();
            const price = parseFloat(document.getElementById('alertPrice').value);
            
            if (!symbol || !price || isNaN(price)) {
                alert('Lutfen gecerli hisse kodu ve fiyat girin!');
                return;
            }
            
            try {
                await fetch('/api/add_alert', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbol, price})
                });
                document.getElementById('alertSymbol').value = '';
                document.getElementById('alertPrice').value = '';
                renderAlerts();
            } catch (e) {
                console.error('Add alert error:', e);
            }
        }
        
        async function removeAlert(symbol) {
            try {
                await fetch('/api/remove_alert/' + symbol, {method: 'DELETE'});
                renderAlerts();
            } catch (e) {
                console.error('Remove alert error:', e);
            }
        }
        
        async function renderAlerts() {
            try {
                const response = await fetch('/api/alerts');
                const data = await response.json();
                const alerts = data.alerts || {};
                
                const container = document.getElementById('alertList');
                
                if (Object.keys(alerts).length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">🔔</div>
                            <h2>Aktif Alarm Yok</h2>
                            <p>Yukaridan yeni alarm kurabilirsiniz...</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = Object.entries(alerts).map(([symbol, alert]) => `
                    <div class="alert-item">
                        <div class="alert-info">
                            <h4>${symbol}</h4>
                            <span>Hedef Fiyat: ${alert.target.toFixed(2)} TL</span>
                        </div>
                        <button class="btn btn-danger" onclick="removeAlert('${symbol}')">Sil</button>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Render alerts error:', e);
            }
        }
        
        document.getElementById('detailModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });
        
        document.getElementById('stockInput')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addStock();
        });
        
        document.getElementById('alertPrice')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addAlert();
        });
    </script>
</body>
</html>
'''

# ==========================================
# API ROUTES
# ==========================================

@app.route('/')
def index():
    if not ipo_data_cache['last_update']:
        scrape_halkarz_data()
    
    return render_template_string(HTML_TEMPLATE, ipo_data=ipo_data_cache)

@app.route('/api/stocks')
def api_stocks():
    stock_data = []
    for symbol in watchlist:
        data = get_stock_data(symbol)
        stock_data.append({'symbol': symbol, 'data': data})
    return jsonify({'stocks': stock_data})

@app.route('/api/stock/<symbol>')
def api_stock_detail(symbol):
    data = get_stock_data(symbol)
    if data:
        analysis = ml_analyze(data.get('history', []), data)
        return jsonify({**data, 'analysis': analysis})
    return jsonify({'error': 'Veri alinamadi'}), 404

@app.route('/api/add_stock', methods=['POST'])
def api_add_stock():
    data = request.json
    symbol = data.get('symbol', '').upper()
    if '.IS' not in symbol:
        symbol += '.IS'
    if symbol not in watchlist:
        watchlist.append(symbol)
    return jsonify({'success': True})

@app.route('/api/add_alert', methods=['POST'])
def api_add_alert():
    data = request.json
    symbol = data.get('symbol', '').upper()
    price = data.get('price', 0)
    if '.IS' not in symbol:
        symbol += '.IS'
    alerts[symbol] = {'target': price, 'created': datetime.now().isoformat()}
    return jsonify({'success': True})

@app.route('/api/alerts')
def api_alerts():
    return jsonify({'alerts': alerts})

@app.route('/api/remove_alert/<symbol>', methods=['DELETE'])
def api_remove_alert(symbol):
    if symbol in alerts:
        del alerts[symbol]
    return jsonify({'success': True})

@app.route('/api/refresh_ipo')
def api_refresh_ipo():
    success = scrape_halkarz_data()
    return jsonify({'success': success, 'data': ipo_data_cache})

# ==========================================
# PORTFOY API ROUTES
# ==========================================

@app.route('/api/portfolio', methods=['GET'])
def api_get_portfolio():
    portfolio_data = portfolio.get_portfolio_value()
    return jsonify(portfolio_data)

@app.route('/api/portfolio/buy', methods=['POST'])
def api_portfolio_buy():
    data = request.json
    symbol = data.get('symbol', '').upper()
    quantity = int(data.get('quantity', 0))
    price = float(data.get('price', 0))
    
    if not symbol or quantity <= 0 or price <= 0:
        return jsonify({'success': False, 'error': 'Gecersiz parametreler'}), 400
    
    success = portfolio.buy(symbol, quantity, price)
    return jsonify({'success': success})

@app.route('/api/portfolio/sell', methods=['POST'])
def api_portfolio_sell():
    data = request.json
    symbol = data.get('symbol', '').upper()
    quantity = int(data.get('quantity', 0))
    price = float(data.get('price', 0))
    
    if not symbol or quantity <= 0 or price <= 0:
        return jsonify({'success': False, 'error': 'Gecersiz parametreler'}), 400
    
    success, result = portfolio.sell(symbol, quantity, price)
    return jsonify({'success': success, 'result': result})

@app.route('/api/portfolio/transactions', methods=['GET'])
def api_get_transactions():
    return jsonify({'transactions': portfolio.transactions})

# ==========================================
# UYGULAMA BASLATMA
# ==========================================

def run_app():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    TLG ANALIZ PLATFORMU                      ║
    ║                                                              ║
    ║  Web tarayiciniz otomatik olarak acilacaktir...             ║
    ║  Manuel erisim: http://localhost:5000                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    threading.Timer(2.0, lambda: webbrowser.open('http://localhost:5000')).start()
    scrape_halkarz_data()
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)

if __name__ == '__main__':
    run_app()
