"""
TLG Analiz Pro - Borsa API Entegrasyonu
Yahoo Finance üzerinden gerçek zamanlı veri çekme
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from database import db, log_error

def fetch_yahoo_data(symbol, period="1y"):
    """
    Yahoo Finance'dan hisse verisi çek
    Gerçek zamanlı ve geçmiş veriler
    """
    try:
        # Yahoo Finance ticker
        ticker = yf.Ticker(symbol)
        
        # Geçmiş verileri çek
        hist = ticker.history(period=period)
        
        if hist.empty:
            print(f"[API] Veri bulunamadı: {symbol}")
            return None
        
        # Fiyat listesi oluştur
        prices = []
        for index, row in hist.iterrows():
            prices.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        
        # Güncel fiyat bilgileri
        current_price = prices[-1]['close'] if prices else 0
        previous_price = prices[-2]['close'] if len(prices) > 1 else current_price
        
        # Hisse bilgileri
        info = ticker.info
        stock_info = {
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'Bilinmiyor'),
            'industry': info.get('industry', 'Bilinmiyor'),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
            'website': info.get('website', ''),
            'description': info.get('longBusinessSummary', '')[:200] + '...' if info.get('longBusinessSummary') else ''
        }
        
        # API çağrı istatistiği
        db.increment_stat('api_calls')
        
        return {
            'symbol': symbol,
            'current': current_price,
            'previous': previous_price,
            'change': round(((current_price - previous_price) / previous_price * 100), 2) if previous_price else 0,
            'prices': prices,
            'info': stock_info
        }
        
    except Exception as e:
        error_msg = f"API Hatası ({symbol}): {str(e)}"
        print(f"[API] {error_msg}")
        log_error('API_ERROR', error_msg, 'fetch_yahoo_data')
        return None

def get_stock_info(symbol):
    """Hisse hakkında detaylı bilgi getir"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            'name': info.get('longName', symbol),
            'symbol': symbol,
            'sector': info.get('sector', 'Bilinmiyor'),
            'industry': info.get('industry', 'Bilinmiyor'),
            'country': info.get('country', 'Bilinmiyor'),
            'market_cap': info.get('marketCap', 0),
            'enterprise_value': info.get('enterpriseValue', 0),
            'trailing_pe': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'peg_ratio': info.get('pegRatio', 0),
            'price_to_book': info.get('priceToBook', 0),
            'price_to_sales': info.get('priceToSalesTrailing12Months', 0),
            'enterprise_to_revenue': info.get('enterpriseToRevenue', 0),
            'enterprise_to_ebitda': info.get('enterpriseToEbitda', 0),
            'profit_margins': info.get('profitMargins', 0),
            'revenue_growth': info.get('revenueGrowth', 0),
            'earnings_growth': info.get('earningsGrowth', 0),
            'current_ratio': info.get('currentRatio', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'return_on_equity': info.get('returnOnEquity', 0),
            'return_on_assets': info.get('returnOnAssets', 0),
            'total_cash': info.get('totalCash', 0),
            'total_debt': info.get('totalDebt', 0),
            'total_revenue': info.get('totalRevenue', 0),
            'revenue_per_share': info.get('revenuePerShare', 0),
            'book_value': info.get('bookValue', 0),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
            'fifty_day_average': info.get('fiftyDayAverage', 0),
            'two_hundred_day_average': info.get('twoHundredDayAverage', 0),
            'average_volume': info.get('averageVolume', 0),
            'dividend_rate': info.get('dividendRate', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'ex_dividend_date': info.get('exDividendDate', ''),
            'website': info.get('website', ''),
            'description': info.get('longBusinessSummary', '')
        }
    except Exception as e:
        print(f"[API] Bilgi hatası ({symbol}): {e}")
        return {'name': symbol, 'symbol': symbol}

def get_multiple_stocks(symbols):
    """Birden fazla hisse verisi çek"""
    results = []
    for symbol in symbols:
        data = fetch_yahoo_data(symbol, '1d')
        if data:
            results.append({
                'symbol': symbol,
                'price': data['current'],
                'change': data['change'],
                'name': data['info']['name']
            })
    return results
