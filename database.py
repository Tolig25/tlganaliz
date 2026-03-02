"""
TLG Analiz Pro - Veritabanı Yönetimi
SQLite3 ile basit ve hızlı veritabanı çözümü
"""
import sqlite3
import os
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE
    
    def get_connection(self):
        """Veritabanı bağlantısı oluştur"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Veritabanını başlat ve tabloları oluştur"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Kullanıcılar tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Kullanıcı ayarları
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, setting_key)
            )
        ''')
        
        # Tahminler tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_symbol TEXT NOT NULL,
                prediction_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT,
                predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_date TIMESTAMP,
                actual_result TEXT DEFAULT 'PENDING',
                price_at_prediction REAL,
                target_price REAL,
                stop_loss REAL,
                actual_price REAL,
                is_success INTEGER DEFAULT 0,
                verified_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Tahmin logları
        c.execute('''
            CREATE TABLE IF NOT EXISTS prediction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL,
                log_type TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        ''')
        
        # Hisseler tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS available_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT,
                sector TEXT,
                is_active INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # İndikatörler tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                is_active INTEGER DEFAULT 1,
                color TEXT DEFAULT '#667eea',
                description TEXT,
                parameters TEXT
            )
        ''')
        
        # Loglar tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT,
                action TEXT,
                details TEXT,
                user_id INTEGER,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Sistem hataları
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT,
                message TEXT,
                location TEXT,
                is_resolved INTEGER DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        # Favoriler
        c.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_symbol TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, stock_symbol)
            )
        ''')
        
        # İşlemler
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_symbol TEXT NOT NULL,
                transaction_type TEXT,
                quantity INTEGER,
                price REAL,
                total_amount REAL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # AI Öğrenme
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT,
                indicator_pattern TEXT,
                prediction_type TEXT,
                confidence_range TEXT,
                success_rate REAL,
                total_predictions INTEGER DEFAULT 0,
                successful_predictions INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Site istatistikleri
        c.execute('''
            CREATE TABLE IF NOT EXISTS site_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE UNIQUE,
                total_logins INTEGER DEFAULT 0,
                total_predictions INTEGER DEFAULT 0,
                total_page_views INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0
            )
        ''')
        
        # Site ayarları
        c.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Varsayılan admin kullanıcısı
        c.execute('''
            INSERT OR IGNORE INTO users (id, username, password, is_admin, is_active)
            VALUES (1, 'admin', 'e99a18c428cb38d5f260853678922e03', 1, 1)
        ''')
        
        # Varsayılan hisseler
        default_stocks = [
            ('THYAO.IS', 'Türk Hava Yolları', 'Havacılık'),
            ('GARAN.IS', 'Garanti Bankası', 'Bankacılık'),
            ('ASELS.IS', 'Aselsan', 'Savunma'),
            ('KCHOL.IS', 'Koç Holding', 'Holding'),
            ('BIMAS.IS', 'BİM', 'Perakende'),
            ('AKBNK.IS', 'Akbank', 'Bankacılık'),
            ('YKBNK.IS', 'Yapı Kredi', 'Bankacılık'),
            ('SISE.IS', 'Şişecam', 'Sanayi'),
            ('PETKM.IS', 'Petkim', 'Kimya'),
            ('TOASO.IS', 'Tofaş', 'Otomotiv')
        ]
        c.executemany('''
            INSERT OR IGNORE INTO available_stocks (symbol, name, sector)
            VALUES (?, ?, ?)
        ''', default_stocks)
        
        # Varsayılan indikatörler
        default_indicators = [
            ('rsi', 'RSI', '#10b981', 'Relative Strength Index', '14'),
            ('macd', 'MACD', '#3b82f6', 'Moving Average Convergence Divergence', '12,26,9'),
            ('sma', 'SMA', '#f59e0b', 'Simple Moving Average', '20,50'),
            ('ema', 'EMA', '#8b5cf6', 'Exponential Moving Average', '12,26'),
            ('bollinger', 'Bollinger Bands', '#ec4899', 'Bollinger Bands', '20,2'),
            ('stochastic', 'Stochastic', '#f97316', 'Stochastic Oscillator', '14,3,3'),
            ('atr', 'ATR', '#6366f1', 'Average True Range', '14')
        ]
        c.executemany('''
            INSERT OR IGNORE INTO indicators (name, display_name, color, description, parameters)
            VALUES (?, ?, ?, ?, ?)
        ''', default_indicators)
        
        # Varsayılan site ayarları
        default_settings = [
            ('site_name', 'TLG Analiz Pro'),
            ('maintenance_mode', '0'),
            ('log_retention_days', '30'),
            ('ai_enabled', '1'),
            ('min_confidence', '60')
        ]
        c.executemany('''
            INSERT OR IGNORE INTO site_settings (key, value)
            VALUES (?, ?)
        ''', default_settings)
        
        conn.commit()
        conn.close()
        print("[DB] Veritabanı başlatıldı")
    
    def get_setting(self, key, default=None):
        """Ayar getir"""
        try:
            conn = self.get_connection()
            result = conn.execute(
                "SELECT value FROM site_settings WHERE key=?", (key,)
            ).fetchone()
            conn.close()
            return result['value'] if result else default
        except:
            return default
    
    def increment_stat(self, stat_name):
        """İstatistiği artır"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = self.get_connection()
            
            # Bugün kayıt var mı kontrol et
            exists = conn.execute(
                "SELECT id FROM site_stats WHERE stat_date=?", (today,)
            ).fetchone()
            
            if exists:
                conn.execute(f'''
                    UPDATE site_stats 
                    SET {stat_name} = {stat_name} + 1 
                    WHERE stat_date=?
                ''', (today,))
            else:
                conn.execute(f'''
                    INSERT INTO site_stats (stat_date, {stat_name})
                    VALUES (?, 1)
                ''', (today,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] İstatistik hatası: {e}")
    
    def get_daily_stats(self):
        """Günlük istatistikleri getir"""
        try:
            conn = self.get_connection()
            today = datetime.now().strftime('%Y-%m-%d')
            stats = conn.execute('''
                SELECT * FROM site_stats WHERE stat_date=?
            ''', (today,)).fetchone()
            conn.close()
            return dict(stats) if stats else {}
        except:
            return {}

# Global veritabanı instance
db = Database()
