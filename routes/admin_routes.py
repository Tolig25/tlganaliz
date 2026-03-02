"""
TLG Analiz Pro - Admin Rotaları
Kullanıcı yönetimi, sistem ayarları, hisse/indikatör yönetimi, loglar, site istatistikleri
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from routes import admin_bp
from database import db
from utils import admin_required, log_system, log_error, hash_password
from api import fetch_yahoo_data
from ai_engine import ai_engine
import sqlite3
import json
from datetime import datetime, timedelta

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    """Admin ana paneli - Site istatistikleri ve durum"""
    conn = db.get_connection()
    
    # İstatistikler
    stats = {
        'total_users': conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c'],
        'total_admins': conn.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=1").fetchone()['c'],
        'active_users': conn.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1").fetchone()['c'],
        'total_stocks': conn.execute("SELECT COUNT(*) as c FROM available_stocks").fetchone()['c'],
        'active_stocks': conn.execute("SELECT COUNT(*) as c FROM available_stocks WHERE is_active=1").fetchone()['c'],
        'total_predictions': conn.execute("SELECT COUNT(*) as c FROM predictions").fetchone()['c'],
        'today_predictions': conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE date(predicted_at)=date('now')"
        ).fetchone()['c'],
        'total_logins': conn.execute("SELECT COUNT(*) as c FROM logs WHERE action='LOGIN'").fetchone()['c'],
        'today_logins': conn.execute(
            "SELECT COUNT(*) as c FROM logs WHERE action='LOGIN' AND date(created_at)=date('now')"
        ).fetchone()['c'],
        'pending_predictions': conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE actual_result='PENDING'"
        ).fetchone()['c'],
        'success_predictions': conn.execute(
            "SELECT COUNT(*) as c FROM predictions WHERE is_success=1"
        ).fetchone()['c']
    }
    
    # Başarı oranı hesapla
    total_verified = conn.execute(
        "SELECT COUNT(*) as c FROM predictions WHERE actual_result!='PENDING'"
    ).fetchone()['c']
    stats['success_rate'] = round(
        (stats['success_predictions'] / total_verified * 100), 1
    ) if total_verified > 0 else 0
    
    # API durumu kontrol et
    try:
        test_data = fetch_yahoo_data('THYAO.IS', '1d')
        api_status = 'ONLINE' if test_data else 'OFFLINE'
    except Exception as e:
        api_status = 'OFFLINE'
        log_error('API_STATUS_CHECK', str(e), 'admin_dashboard')
    
    # Sistem hataları - AI tarafından tespit edilenler
    errors = conn.execute('''
        SELECT * FROM system_errors 
        WHERE is_resolved=0 
        ORDER BY detected_at DESC 
        LIMIT 10
    ''').fetchall()
    
    # Son loglar
    recent_logs = conn.execute('''
        SELECT * FROM logs 
        ORDER BY created_at DESC 
        LIMIT 20
    ''').fetchall()
    
    # AI öğrenme istatistikleri
    ai_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_patterns,
            AVG(success_rate) as avg_success_rate
        FROM ai_learning
    ''').fetchone()
    
    # Günlük istatistikler
    today_stats = db.get_daily_stats()
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         api_status=api_status,
                         errors=errors,
                         recent_logs=recent_logs,
                         ai_stats=ai_stats,
                         today_stats=today_stats)

@admin_bp.route('/users')
@admin_required
def admin_users():
    """Kullanıcı yönetimi - Listele, rol değiştir, sil"""
    conn = db.get_connection()
    users = conn.execute('''
        SELECT u.*, 
               COUNT(DISTINCT p.id) as pred_count,
               COUNT(DISTINCT f.id) as fav_count,
               (SELECT MAX(created_at) FROM logs WHERE user_id=u.id AND action='LOGIN') as last_login
        FROM users u
        LEFT JOIN predictions p ON p.user_id = u.id
        LEFT JOIN favorites f ON f.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/<int:user_id>/action', methods=['POST'])
@admin_required
def user_action(user_id):
    """Kullanıcı işlemi (sil, admin yap, aktif/pasif)"""
    data = request.get_json()
    action = data.get('action')
    
    if user_id == session['user_id'] and action in ['delete', 'toggle_admin']:
        return jsonify({'success': False, 'error': 'Kendi hesabınız üzerinde bu işlem yapılamaz'})
    
    conn = db.get_connection()
    
    if action == 'delete':
        # Kullanıcıyı ve tüm verilerini sil
        conn.execute("DELETE FROM predictions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM favorites WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM logs WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        log_system('ADMIN_USER_DELETE', f'Kullanıcı silindi: ID {user_id}')
        
    elif action == 'toggle_admin':
        user = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
        new_status = 0 if user['is_admin'] else 1
        conn.execute("UPDATE users SET is_admin=? WHERE id=?", (new_status, user_id))
        status_text = 'Admin' if new_status else 'Kullanıcı'
        log_system('ADMIN_ROLE_CHANGE', f'Kullanıcı {user_id} -> {status_text}')
        
    elif action == 'toggle_active':
        user = conn.execute("SELECT is_active FROM users WHERE id=?", (user_id,)).fetchone()
        new_status = 0 if user['is_active'] else 1
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, user_id))
        status_text = 'Aktif' if new_status else 'Pasif'
        log_system('ADMIN_STATUS_CHANGE', f'Kullanıcı {user_id} -> {status_text}')
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@admin_bp.route('/system')
@admin_required
def admin_system():
    """Sistem ayarları - Tüm yapılandırma"""
    conn = db.get_connection()
    settings = conn.execute("SELECT * FROM site_settings").fetchall()
    settings_dict = {s['key']: s['value'] for s in settings}
    conn.close()
    
    # AI motor durumu
    ai_running = ai_engine.is_running
    last_check = ai_engine.last_check.isoformat() if ai_engine.last_check else None
    
    return render_template('admin/system.html', 
                         settings=settings_dict,
                         ai_running=ai_running,
                         last_check=last_check)

@admin_bp.route('/system/action', methods=['POST'])
@admin_required
def system_action():
    """Sistem işlemleri - Restart, temizlik, yenileme"""
    import time
    data = request.get_json()
    action = data.get('action')
    
    conn = db.get_connection()
    
    if action == 'clear_logs':
        conn.execute("DELETE FROM logs")
        conn.execute("DELETE FROM prediction_logs")
        log_system('SYSTEM', 'Tüm loglar temizlendi')
        
    elif action == 'clear_predictions':
        conn.execute("DELETE FROM predictions")
        conn.execute("DELETE FROM prediction_logs")
        log_system('SYSTEM', 'Tüm tahminler temizlendi')
        
    elif action == 'reset_users':
        # Admin hariç tüm kullanıcıları sil
        admin_ids = conn.execute("SELECT id FROM users WHERE is_admin=1").fetchall()
        admin_id_list = [a['id'] for a in admin_ids]
        
        if admin_id_list:
            placeholders = ','.join('?' * len(admin_id_list))
            conn.execute(f"DELETE FROM predictions WHERE user_id NOT IN ({placeholders})", admin_id_list)
            conn.execute(f"DELETE FROM favorites WHERE user_id NOT IN ({placeholders})", admin_id_list)
            conn.execute(f"DELETE FROM transactions WHERE user_id NOT IN ({placeholders})", admin_id_list)
            conn.execute(f"DELETE FROM logs WHERE user_id NOT IN ({placeholders})", admin_id_list)
            conn.execute(f"DELETE FROM users WHERE id NOT IN ({placeholders})", admin_id_list)
        log_system('SYSTEM', 'Kullanıcılar sıfırlandı (admin hariç)')
        
    elif action == 'refresh_data':
        # Tüm hisse verilerini yenile
        log_system('SYSTEM', 'Manuel veri yenileme isteği')
        
    elif action == 'restart_ai':
        ai_engine.stop()
        time.sleep(1)
        ai_engine.start()
        log_system('SYSTEM', 'AI motoru yeniden başlatıldı')
        
    elif action == 'verify_now':
        ai_engine.verify_predictions()
        log_system('SYSTEM', 'Manuel tahmin doğrulama çalıştırıldı')
        
    elif action == 'cleanup_now':
        ai_engine.cleanup_old_logs()
        log_system('SYSTEM', 'Manuel temizlik çalıştırıldı')
        
    elif action == 'update_setting':
        key = data.get('key')
        value = data.get('value')
        if key and value is not None:
            conn.execute(
                "UPDATE site_settings SET value=?, updated_at=CURRENT_TIMESTAMP WHERE key=?",
                (value, key)
            )
            log_system('SYSTEM', f'Ayar güncellendi: {key}={value}')
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@admin_bp.route('/stocks')
@admin_required
def admin_stocks():
    """Hisse yönetimi - Ekle, sil, aktif/pasif"""
    conn = db.get_connection()
    stocks = conn.execute('''
        SELECT s.*, 
               COUNT(DISTINCT p.id) as pred_count,
               COUNT(DISTINCT f.id) as fav_count
        FROM available_stocks s
        LEFT JOIN predictions p ON p.stock_symbol = s.symbol
        LEFT JOIN favorites f ON f.stock_symbol = s.symbol
        GROUP BY s.id
        ORDER BY s.symbol
    ''').fetchall()
    conn.close()
    
    return render_template('admin/stocks.html', stocks=stocks)

@admin_bp.route('/stock', methods=['POST'])
@admin_required
def manage_stock():
    """Hisse ekle/sil/durum değiştir"""
    data = request.get_json()
    action = data.get('action')
    
    conn = db.get_connection()
    
    if action == 'add':
        symbol = data.get('symbol', '').upper().strip()
        name = data.get('name', '').strip()
        sector = data.get('sector', 'Diğer').strip()
        
        if not symbol or len(symbol) > 10:
            return jsonify({'success': False, 'error': 'Geçersiz sembol'})
        
        try:
            conn.execute(
                "INSERT INTO available_stocks (symbol, name, sector) VALUES (?, ?, ?)",
                (symbol, name or symbol, sector)
            )
            log_system('ADMIN', f'Hisse eklendi: {symbol}')
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Bu hisse zaten var'})
    
    elif action == 'toggle':
        symbol = data.get('symbol')
        stock = conn.execute(
            "SELECT is_active FROM available_stocks WHERE symbol=?",
            (symbol,)
        ).fetchone()
        if stock:
            new_status = 0 if stock['is_active'] else 1
            conn.execute(
                "UPDATE available_stocks SET is_active=? WHERE symbol=?",
                (new_status, symbol)
            )
            status_text = 'Aktif' if new_status else 'Pasif'
            log_system('ADMIN', f'Hisse durumu: {symbol} -> {status_text}')
    
    elif action == 'delete':
        symbol = data.get('symbol')
        conn.execute("DELETE FROM available_stocks WHERE symbol=?", (symbol,))
        log_system('ADMIN', f'Hisse silindi: {symbol}')
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@admin_bp.route('/indicators')
@admin_required
def admin_indicators():
    """İndikatör yönetimi - Aktif/pasif yap, renk değiştir"""
    conn = db.get_connection()
    indicators = conn.execute("SELECT * FROM indicators ORDER BY name").fetchall()
    conn.close()
    
    return render_template('admin/indicators.html', indicators=indicators)

@admin_bp.route('/indicator', methods=['POST'])
@admin_required
def manage_indicator():
    """İndikatör güncelle"""
    data = request.get_json()
    name = data.get('name')
    is_active = data.get('is_active')
    color = data.get('color')
    
    if not name:
        return jsonify({'success': False, 'error': 'İndikatör adı gerekli'})
    
    conn = db.get_connection()
    
    updates = []
    params = []
    
    if is_active is not None:
        updates.append("is_active=?")
        params.append(1 if is_active else 0)
    
    if color:
        updates.append("color=?")
        params.append(color)
    
    if updates:
        params.append(name)
        conn.execute(
            f"UPDATE indicators SET {', '.join(updates)} WHERE name=?",
            params
        )
        log_system('ADMIN', f'İndikatör güncellendi: {name}')
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@admin_bp.route('/logs')
@admin_required
def admin_logs():
    """Sistem logları - Filtreleme ve görüntüleme"""
    conn = db.get_connection()
    
    # Filtreleme
    log_type = request.args.get('type', 'all')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if log_type != 'all':
        query += " AND log_type=?"
        params.append(log_type)
    
    if date_from:
        query += " AND date(created_at)>=?"
        params.append(date_from)
    
    if date_to:
        query += " AND date(created_at)<=?"
        params.append(date_to)
    
    query += " ORDER BY created_at DESC LIMIT 500"
    
    logs = conn.execute(query, params).fetchall()
    
    # Tahmin logları
    pred_logs = conn.execute('''
        SELECT pl.*, p.stock_symbol, u.username
        FROM prediction_logs pl
        JOIN predictions p ON p.id = pl.prediction_id
        JOIN users u ON u.id = p.user_id
        ORDER BY pl.created_at DESC
        LIMIT 200
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/logs.html', logs=logs, pred_logs=pred_logs)

@admin_bp.route('/resolve_error', methods=['POST'])
@admin_required
def resolve_error():
    """Hatayı çözüldü olarak işaretle"""
    data = request.get_json()
    error_id = data.get('error_id')
    
    if error_id:
        conn = db.get_connection()
        conn.execute(
            "UPDATE system_errors SET is_resolved=1, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
            (error_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Hata ID gerekli'})

@admin_bp.route('/site_stats')
@admin_required
def site_stats():
    """Site istatistikleri API"""
    conn = db.get_connection()
    
    # Günlük istatistikler (son 30 gün)
    daily_stats = conn.execute('''
        SELECT * FROM site_stats 
        WHERE stat_date >= date('now', '-30 days')
        ORDER BY stat_date DESC
    ''').fetchall()
    
    # Toplam istatistikler
    totals = conn.execute('''
        SELECT 
            SUM(total_logins) as total_logins,
            SUM(total_predictions) as total_predictions,
            SUM(total_page_views) as total_page_views,
            SUM(api_calls) as api_calls,
            SUM(errors_count) as total_errors
        FROM site_stats
    ''').fetchone()
    
    conn.close()
    
    return jsonify({
        'daily': [dict(s) for s in daily_stats],
        'totals': dict(totals)
    })

@admin_bp.route('/ai_stats')
@admin_required
def ai_stats():
    """AI istatistikleri API"""
    stats = ai_engine.get_learning_stats()
    return jsonify(stats or {})
