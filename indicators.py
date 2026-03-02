"""
TLG Analiz Pro - Teknik İndikatör Hesaplamaları
"""
import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    """RSI (Relative Strength Index) hesapla"""
    if len(prices) < period + 1:
        return [50] * len(prices)
    
    closes = [p['close'] for p in prices]
    df = pd.DataFrame({'close': closes})
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.fillna(50).tolist()

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD hesapla"""
    if len(prices) < slow:
        return {'macd': [0]*len(prices), 'signal': [0]*len(prices), 'histogram': [0]*len(prices)}
    
    closes = [p['close'] for p in prices]
    df = pd.DataFrame({'close': closes})
    
    ema_fast = df['close'].ewm(span=fast).mean()
    ema_slow = df['close'].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line.fillna(0).tolist(),
        'signal': signal_line.fillna(0).tolist(),
        'histogram': histogram.fillna(0).tolist()
    }

def calculate_sma(prices, period=20):
    """SMA (Simple Moving Average) hesapla"""
    if len(prices) < period:
        return [prices[-1]['close'] if prices else 0] * len(prices)
    
    closes = [p['close'] for p in prices]
    df = pd.DataFrame({'close': closes})
    sma = df['close'].rolling(window=period).mean()
    
    return sma.fillna(method='bfill').tolist()

def calculate_ema(prices, period=12):
    """EMA (Exponential Moving Average) hesapla"""
    if len(prices) < period:
        return [prices[-1]['close'] if prices else 0] * len(prices)
    
    closes = [p['close'] for p in prices]
    df = pd.DataFrame({'close': closes})
    ema = df['close'].ewm(span=period).mean()
    
    return ema.tolist()

def calculate_bollinger(prices, period=20, std_dev=2):
    """Bollinger Bands hesapla"""
    if len(prices) < period:
        return {'upper': [0]*len(prices), 'middle': [0]*len(prices), 'lower': [0]*len(prices)}
    
    closes = [p['close'] for p in prices]
    df = pd.DataFrame({'close': closes})
    
    middle = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        'upper': upper.fillna(method='bfill').tolist(),
        'middle': middle.fillna(method='bfill').tolist(),
        'lower': lower.fillna(method='bfill').tolist()
    }

def calculate_stochastic(prices, k_period=14, d_period=3):
    """Stochastic Oscillator hesapla"""
    if len(prices) < k_period:
        return {'k': [50]*len(prices), 'd': [50]*len(prices)}
    
    highs = [p['high'] for p in prices]
    lows = [p['low'] for p in prices]
    closes = [p['close'] for p in prices]
    
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
    
    lowest_low = df['low'].rolling(window=k_period).min()
    highest_high = df['high'].rolling(window=k_period).max()
    
    k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_period).mean()
    
    return {
        'k': k.fillna(50).tolist(),
        'd': d.fillna(50).tolist()
    }

def calculate_atr(prices, period=14):
    """ATR (Average True Range) hesapla"""
    if len(prices) < period:
        return [0] * len(prices)
    
    highs = [p['high'] for p in prices]
    lows = [p['low'] for p in prices]
    closes = [p['close'] for p in prices]
    
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
    
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean()
    
    return atr.fillna(0).tolist()

def calculate_all_indicators(prices):
    """Tüm indikatörleri hesapla ve fiyatlara ekle"""
    if not prices or len(prices) < 30:
        return prices
    
    # RSI
    rsi_values = calculate_rsi(prices)
    for i, p in enumerate(prices):
        p['rsi'] = rsi_values[i] if i < len(rsi_values) else 50
    
    # MACD
    macd_data = calculate_macd(prices)
    for i, p in enumerate(prices):
        p['macd'] = macd_data['macd'][i] if i < len(macd_data['macd']) else 0
        p['macd_signal'] = macd_data['signal'][i] if i < len(macd_data['signal']) else 0
        p['macd_histogram'] = macd_data['histogram'][i] if i < len(macd_data['histogram']) else 0
    
    # SMA
    sma20 = calculate_sma(prices, 20)
    sma50 = calculate_sma(prices, 50)
    for i, p in enumerate(prices):
        p['sma20'] = sma20[i] if i < len(sma20) else p['close']
        p['sma50'] = sma50[i] if i < len(sma50) else p['close']
    
    # EMA
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    for i, p in enumerate(prices):
        p['ema12'] = ema12[i] if i < len(ema12) else p['close']
        p['ema26'] = ema26[i] if i < len(ema26) else p['close']
    
    # Bollinger
    bb = calculate_bollinger(prices)
    for i, p in enumerate(prices):
        p['bb_upper'] = bb['upper'][i] if i < len(bb['upper']) else p['close']
        p['bb_middle'] = bb['middle'][i] if i < len(bb['middle']) else p['close']
        p['bb_lower'] = bb['lower'][i] if i < len(bb['lower']) else p['close']
    
    # Stochastic
    stoch = calculate_stochastic(prices)
    for i, p in enumerate(prices):
        p['stoch_k'] = stoch['k'][i] if i < len(stoch['k']) else 50
        p['stoch_d'] = stoch['d'][i] if i < len(stoch['d']) else 50
    
    # ATR
    atr = calculate_atr(prices)
    for i, p in enumerate(prices):
        p['atr'] = atr[i] if i < len(atr) else 0
    
    return prices
