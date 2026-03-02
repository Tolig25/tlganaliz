"""
TLG Analiz Pro - Konfigürasyon Ayarları
"""
import os

class Config:
    # Uygulama Ayarları
    SECRET_KEY = 'tlg_analiz_pro_gizli_anahtar_2024'
    SITE_NAME = 'TLG Analiz Pro'
    VERSION = '2.0'
    
    # Veritabanı
    DATABASE = 'tlg_analiz.db'
    
    # API Ayarları
    YAHOO_FINANCE_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart/'
    
    # AI Ayarları
    AI_CHECK_INTERVAL = 3600  # 1 saat
    MIN_CONFIDENCE = 60
    
    # Log Ayarları
    LOG_RETENTION_DAYS = 30
    
    # Hisse Listesi (BIST)
    BIST_STOCKS = [
        'THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'KCHOL.IS', 'BIMAS.IS',
        'SAHOL.IS', 'AKBNK.IS', 'YKBNK.IS', 'VAKBN.IS', 'HALKB.IS',
        'ISCTR.IS', 'PETKM.IS', 'SISE.IS', 'TOASO.IS', 'TUPRS.IS',
        'EREGL.IS', 'KRDMD.IS', 'ARCLK.IS', 'SASA.IS', 'HEKTS.IS',
        'KOZAA.IS', 'KOZAL.IS', 'ODAS.IS', 'VESTL.IS', 'TTKOM.IS',
        'TCELL.IS', 'ULKER.IS', 'MGROS.IS', 'AEFES.IS', 'CCOLA.IS'
    ]
