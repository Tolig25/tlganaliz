"""
TLG Analiz Pro - Yardımcı Fonksiyonlar
"""
import hashlib
import functools
from flask import session, redirect, url_for, request
from database import db

def hash_password(password):
    """Şifreyi MD5 ile hashle"""
    return hashlib.md5(password.encode()).hexdigest()

def login_required(f):
    """Giriş kontrolü decorator"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Admin kontrolü decorator"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_system(action, details, user_id=None):
    """Sistem logu kaydet"""
    try:
        conn = db.get_connection()
        conn.execute('''
            INSERT INTO logs (log_type, action, details, user_id, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', ('SYSTEM', action, details, user_id, request.remote_addr))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG] Hata: {e}")

def log_error(error_type, message, location):
    """Hata logu kaydet"""
    try:
        conn = db.get_connection()
        conn.execute('''
            INSERT INTO system_errors (error_type, message, location)
            VALUES (?, ?, ?)
        ''', (error_type, message, location))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Log hatası: {e}")

def get_user_stats(user_id):
    """Kullanıcı istatistiklerini getir"""
    try:
        conn = db.get_connection()
        
        # Toplam tahmin
        total_pred = conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE user_id=?", (user_id,)
        ).fetchone()['c']
        
        # Bekleyen tahmin
        pending_pred = conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE user_id=? AND actual_result='PENDING'",
            (user_id,)
        ).fetchone()['c']
        
        # Başarılı tahmin
        success_pred = conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE user_id=? AND is_success=1",
            (user_id,)
        ).fetchone()['c']
        
        # Başarı oranı
        verified = conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE user_id=? AND actual_result!='PENDING'",
            (user_id,)
        ).fetchone()['c']
        
        success_rate = round((success_pred / verified * 100), 1) if verified > 0 else 0
        
        # Favori sayısı
        fav_count = conn.execute(
            "SELECT COUNT(*) as c FROM favorites WHERE user_id=?", (user_id,)
        ).fetchone()['c']
        
        # İşlem sayısı
        trans_count = conn.execute(
            "SELECT COUNT(*) as c FROM transactions WHERE user_id=?", (user_id,)
        ).fetchone()['c']
        
        conn.close()
        
        return {
            'total_predictions': total_pred,
            'pending_predictions': pending_pred,
            'success_predictions': success_pred,
            'success_rate': success_rate,
            'favorite_count': fav_count,
            'transaction_count': trans_count
        }
    except Exception as e:
        print(f"[STATS] Hata: {e}")
        return {
            'total_predictions': 0,
            'pending_predictions': 0,
            'success_predictions': 0,
            'success_rate': 0,
            'favorite_count': 0,
            'transaction_count': 0
        }
