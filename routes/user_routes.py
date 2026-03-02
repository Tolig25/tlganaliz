"""
TLG Analiz Pro - Kullanıcı Rotaları
Kullanıcı paneli, hisse analizi, tahminler, favoriler
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from routes import user_bp
from database import db
from utils import login_required, log_system, log_error
from api import fetch_yahoo_data, get_stock_info
from indicators import calculate_all_indicators
from ai_engine import ai_engine
from datetime import datetime, timedelta

@user_bp.route('/predictions')
@login_required
def predictions():
    """Kullanıcı tahminleri sayfası"""
    conn = db.get_connection()
    
    # Aktif tahminler
    active = conn.execute('''
        SELECT p.*, s.name as stock_name 
        FROM predictions p
        LEFT JOIN available_stocks s ON s.symbol = p.stock_symbol
        WHERE p.user_id=? AND p.actual_result='PENDING'
        ORDER BY p.predicted_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Geçmiş tahminler
    history = conn.execute('''
        SELECT p.*, s.name as stock_name 
        FROM predictions p
        LEFT JOIN available_stocks s ON s.symbol = p.stock_symbol
        WHERE p.user_id=? AND p.actual_result!='PENDING'
        ORDER BY p.verified_at DESC LIMIT 50
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('predictions.html', active=active, history=history)

@user_bp.route('/favorites')
@login_required
def favorites():
    """Favori hisseler sayfası"""
    conn = db.get_connection()
    
    favorites = conn.execute('''
        SELECT f.*, s.name, s.sector 
        FROM favorites f
        JOIN available_stocks s ON s.symbol = f.stock_symbol
        WHERE f.user_id=?
        ORDER BY f.added_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Favori hisselerin güncel fiyatlarını çek
    favorite_data = []
    for fav in favorites:
        try:
            data = fetch_yahoo_data(fav['stock_symbol'], '1d')
            if data:
                change = ((data['current'] - data['previous']) / data['previous'] * 100) if data['previous'] else 0
                favorite_data.append({
                    'symbol': fav['stock_symbol'],
                    'name': fav['name'],
                    'sector': fav['sector'],
                    'price': data['current'],
                    'change': round(change, 2),
                    'added_at': fav['added_at']
                })
        except:
            favorite_data.append({
                'symbol': fav['stock_symbol'],
                'name': fav['name'],
                'sector': fav['sector'],
                'price': 0,
                'change': 0,
                'added_at': fav['added_at']
            })
    
    conn.close()
    
    return render_template('favorites.html', favorites=favorite_data)

@user_bp.route('/favorite/<symbol>', methods=['POST'])
@login_required
def toggle_favorite(symbol):
    """Favori ekle/çıkar"""
    try:
        conn = db.get_connection()
        
        # Var mı kontrol et
        exists = conn.execute(
            "SELECT id FROM favorites WHERE user_id=? AND stock_symbol=?",
            (session['user_id'], symbol)
        ).fetchone()
        
        if exists:
            # Sil
            conn.execute(
                "DELETE FROM favorites WHERE user_id=? AND stock_symbol=?",
                (session['user_id'], symbol)
            )
            action = 'removed'
        else:
            # Ekle
            conn.execute(
                "INSERT INTO favorites (user_id, stock_symbol) VALUES (?, ?)",
                (session['user_id'], symbol)
            )
            action = 'added'
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'action': action})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@user_bp.route('/transaction_history')
@login_required
def transaction_history():
    """İşlem geçmişi sayfası"""
    conn = db.get_connection()
    
    transactions = conn.execute('''
        SELECT t.*, s.name as stock_name 
        FROM transactions t
        LEFT JOIN available_stocks s ON s.symbol = t.stock_symbol
        WHERE t.user_id=?
        ORDER BY t.transaction_date DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('history.html', transactions=transactions)

@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Kullanıcı ayarları"""
    if request.method == 'POST':
        # Ayarları güncelle
        theme = request.form.get('theme', 'light')
        notifications = request.form.get('notifications', '1')
        
        try:
            conn = db.get_connection()
            
            # Tema ayarı
            conn.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, setting_key, setting_value)
                VALUES (?, 'theme', ?)
            ''', (session['user_id'], theme))
            
            # Bildirim ayarı
            conn.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, setting_key, setting_value)
                VALUES (?, 'notifications', ?)
            ''', (session['user_id'], notifications))
            
            conn.commit()
            conn.close()
            
            flash('Ayarlar kaydedildi', 'success')
            log_system('SETTINGS_UPDATED', 'Kullanıcı ayarları güncellendi', session['user_id'])
            
        except Exception as e:
            flash('Ayarlar kaydedilirken hata oluştu', 'error')
        
        return redirect(url_for('user.settings'))
    
    # Mevcut ayarları getir
    conn = db.get_connection()
    user_settings = conn.execute('''
        SELECT setting_key, setting_value FROM user_settings WHERE user_id=?
    ''', (session['user_id'],)).fetchall()
    
    settings_dict = {s['setting_key']: s['setting_value'] for s in user_settings}
    conn.close()
    
    return render_template('settings.html', settings=settings_dict)

@user_bp.route('/batch_analysis')
@login_required
def batch_analysis():
    """Toplu analiz sayfası"""
    return render_template('batch_analysis.html')

@user_bp.route('/api/batch_analyze', methods=['POST'])
@login_required
def api_batch_analyze():
    """Toplu analiz API"""
    try:
        data = request.get_json()
        sector = data.get('sector', 'all')
        min_confidence = int(data.get('min_confidence', 60))
        
        conn = db.get_connection()
        
        # Hisse listesini al
        if sector == 'all':
            stocks = conn.execute(
                "SELECT symbol FROM available_stocks WHERE is_active=1"
            ).fetchall()
        else:
            stocks = conn.execute(
                "SELECT symbol FROM available_stocks WHERE is_active=1 AND sector=?",
                (sector,)
            ).fetchall()
        
        conn.close()
        
        symbols = [s['symbol'] for s in stocks]
        
        # AI ile toplu analiz yap
        results = ai_engine.batch_analyze(symbols, min_confidence)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        log_error('BATCH_API_ERROR', str(e), 'api_batch_analyze')
        return jsonify({'success': False, 'error': str(e)})

@user_bp.route('/stock/<symbol>')
@login_required
def stock_detail(symbol):
    """Hisse detay sayfası"""
    # Hisse verilerini çek
    data = fetch_yahoo_data(symbol, '1y')
    if not data:
        flash('Hisse verisi alınamadı', 'error')
        return redirect(url_for('dashboard'))
    
    # İndikatörleri hesapla
    prices = calculate_all_indicators(data['prices'])
    
    # AI Analizi yap
    analysis = ai_engine.analyze(prices, symbol)
    
    # Favori mi kontrol et
    conn = db.get_connection()
    is_favorite = conn.execute(
        "SELECT id FROM favorites WHERE user_id=? AND stock_symbol=?",
        (session['user_id'], symbol)
    ).fetchone() is not None
    
    # Son tahminleri getir
    recent_predictions = conn.execute('''
        SELECT * FROM predictions 
        WHERE stock_symbol=? AND user_id=?
        ORDER BY predicted_at DESC LIMIT 5
    ''', (symbol, session['user_id'])).fetchall()
    
    conn.close()
    
    return render_template('stock_detail.html',
                         symbol=symbol,
                         data=data,
                         prices=prices[-100:],  # Son 100 gün
                         analysis=analysis,
                         is_favorite=is_favorite,
                         recent_predictions=recent_predictions)

@user_bp.route('/api/analyze/<symbol>', methods=['POST'])
@login_required
def api_analyze(symbol):
    """Hisse analizi API - Yeni tahmin oluştur"""
    try:
        # Hisse verilerini çek
        data = fetch_yahoo_data(symbol, '6mo')
        if not data:
            return jsonify({'success': False, 'error': 'Veri alınamadı'})
        
        # İndikatörleri hesapla
        prices = calculate_all_indicators(data['prices'])
        
        # AI Analizi yap
        analysis = ai_engine.analyze(prices, symbol)
        
        if not analysis:
            return jsonify({'success': False, 'error': 'Analiz yapılamadı'})
        
        # Tahmini kaydet
        pred_id = ai_engine.save_prediction(session['user_id'], symbol, analysis)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'prediction_id': pred_id
        })
        
    except Exception as e:
        log_error('ANALYZE_API_ERROR', str(e), 'api_analyze')
        return jsonify({'success': False, 'error': str(e)})

@user_bp.route('/api/stock_chart/<symbol>')
@login_required
def api_stock_chart(symbol):
    """Hisse grafik verisi API"""
    try:
        period = request.args.get('period', '1y')
        data = fetch_yahoo_data(symbol, period)
        
        if not data:
            return jsonify({'error': 'Veri alınamadı'}), 404
        
        # İndikatörleri hesapla
        prices = calculate_all_indicators(data['prices'])
        
        return jsonify({
            'symbol': symbol,
            'prices': prices,
            'current': data['current'],
            'change': data['change'],
            'info': data['info']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
