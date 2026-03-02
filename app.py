"""
TLG Analiz Pro v2.0 - Ana Uygulama
Flask uygulama başlatıcı ve yapılandırma
Çoklu dosya yapısı, mobil uyumlu, AI entegrasyonlu
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
import sys

# Proje dizini ayarları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Konfigürasyon ve veritabanı
from config import Config
from database import db

# Yardımcı fonksiyonlar
from utils import login_required, admin_required, log_system, hash_password

# AI Motoru
from ai_engine import ai_engine

# Blueprint'ler (routes)
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

def create_app():
    """Uygulama fabrikası - Flask app oluştur"""
    app = Flask(__name__, 
                template_folder=os.path.join(BASE_DIR, 'templates'),
                static_folder=os.path.join(BASE_DIR, 'static'))
    
    # Konfigürasyon
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['JSON_AS_ASCII'] = False  # Türkçe karakter desteği
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Veritabanını başlat
    db.init_db()
    
    # Blueprint'leri kaydet
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # AI motorunu başlat
    ai_engine.start()
    
    # Hata yakalama
    register_error_handlers(app)
    
    # Rotaları kaydet
    register_routes(app)
    
    # Context processor - Tüm şablonlarda kullanılabilir değişkenler
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {
            'site_name': Config.SITE_NAME,
            'version': Config.VERSION,
            'now': datetime.now()
        }
    
    return app

def register_error_handlers(app):
    """Hata yakalama işleyicileri"""
    
    @app.errorhandler(404)
    def not_found(e):
        log_system('ERROR_404', f'Sayfa bulunamadı: {request.path}')
        return render_template('error.html', 
                             error_code=404, 
                             error_message='Sayfa bulunamadı'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        log_error('SERVER_ERROR', str(e), 'app')
        return render_template('error.html',
                             error_code=500,
                             error_message='Sunucu hatası oluştu'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html',
                             error_code=403,
                             error_message='Erişim reddedildi'), 403

def register_routes(app):
    """Ana rotalar - Auth ve genel sayfalar"""
    
    @app.route('/')
    def index():
        """Ana sayfa - Giriş öncesi"""
        if 'user_id' in session:
            return redirect('/dashboard')
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Giriş sayfası"""
        if 'user_id' in session:
            return redirect('/dashboard')
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Kullanıcı adı ve şifre gerekli', 'error')
                return render_template('login.html')
            
            hashed_pw = hash_password(password)
            
            conn = db.get_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=? AND is_active=1",
                (username, hashed_pw)
            ).fetchone()
            
            if user:
                # Son girişi güncelle
                conn.execute(
                    "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?",
                    (user['id'],)
                )
                conn.commit()
                conn.close()
                
                # Session ayarla
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = bool(user['is_admin'])
                
                log_system('LOGIN', f'Giriş yapıldı: {username}', user_id=user['id'])
                
                next_page = request.args.get('next', '/dashboard')
                return redirect(next_page)
            else:
                conn.close()
                flash('Kullanıcı adı veya şifre hatalı', 'error')
                log_system('LOGIN_FAIL', f'Başarısız giriş denemesi: {username}')
        
        return render_template('login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Kayıt sayfası"""
        if 'user_id' in session:
            return redirect('/dashboard')
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            
            # Validasyon
            if not username or not password:
                flash('Tüm alanları doldurun', 'error')
                return render_template('register.html')
            
            if len(username) < 3:
                flash('Kullanıcı adı en az 3 karakter olmalı', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Şifre en az 6 karakter olmalı', 'error')
                return render_template('register.html')
            
            if password != password_confirm:
                flash('Şifreler eşleşmiyor', 'error')
                return render_template('register.html')
            
            hashed_pw = hash_password(password)
            
            import sqlite3
            conn = db.get_connection()
            try:
                conn.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)",
                    (username, hashed_pw)
                )
                conn.commit()
                conn.close()
                
                log_system('REGISTER', f'Yeni kayıt: {username}')
                flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
                return redirect('/login')
                
            except sqlite3.IntegrityError:
                conn.close()
                flash('Bu kullanıcı adı zaten kullanılıyor', 'error')
        
        return render_template('register.html')
    
    @app.route('/logout')
    def logout():
        """Çıkış yap"""
        if 'user_id' in session:
            log_system('LOGOUT', f'Çıkış yapıldı: {session.get("username")}')
        session.clear()
        return redirect('/')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Kullanıcı paneli - Ana sayfa"""
        conn = db.get_connection()
        
        # Aktif hisseleri al
        stocks = conn.execute(
            "SELECT * FROM available_stocks WHERE is_active=1 ORDER BY symbol"
        ).fetchall()
        
        # Kullanıcı favorilerini al
        favorites = conn.execute(
            "SELECT stock_symbol FROM favorites WHERE user_id=?",
            (session['user_id'],)
        ).fetchall()
        favorite_symbols = {f['stock_symbol'] for f in favorites}
        
        conn.close()
        
        from api import fetch_yahoo_data
        
        stock_data = []
        for stock in stocks[:20]:  # İlk 20 hisse (performans için)
            try:
                quote = fetch_yahoo_data(stock['symbol'], '1d')
                if quote:
                    change = ((quote['current'] - quote['previous']) / quote['previous'] * 100) if quote['previous'] else 0
                    stock_data.append({
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'sector': stock['sector'],
                        'price': round(quote['current'], 2),
                        'change': round(change, 2),
                        'is_favorite': stock['symbol'] in favorite_symbols
                    })
            except:
                continue
        
        return render_template('dashboard.html', 
                             stocks=stock_data,
                             is_admin=session.get('is_admin'))
    
    @app.route('/search')
    @login_required
    def search():
        """Hisse arama API"""
        query = request.args.get('q', '').upper().strip()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        conn = db.get_connection()
        stocks = conn.execute(
            """SELECT symbol, name, sector FROM available_stocks 
               WHERE is_active=1 AND (symbol LIKE ? OR name LIKE ?)
               LIMIT 10""",
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        conn.close()
        
        return jsonify([{
            'symbol': s['symbol'],
            'name': s['name'],
            'sector': s['sector']
        } for s in stocks])
    
    @app.route('/api/stock/<symbol>')
    @login_required
    def api_stock_data(symbol):
        """Hisse verisi API - Grafik için"""
        from api import fetch_yahoo_data, get_stock_info
        from indicators import calculate_all_indicators
        
        period = request.args.get('period', '1y')
        
        data = fetch_yahoo_data(symbol, period)
        if not data:
            return jsonify({'error': 'Veri alınamadı'}), 404
        
        prices = calculate_all_indicators(data['prices'])
        info = get_stock_info(symbol)
        
        return jsonify({
            'prices': prices[-100:],
            'info': info,
            'current': data['current'],
            'previous': data['previous']
        })
    
    @app.route('/api/stats')
    @login_required
    def api_stats():
        """Kullanıcı istatistikleri API"""
        from utils import get_user_stats
        stats = get_user_stats(session['user_id'])
        return jsonify(stats)

# Uygulama başlat
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("TLG ANALIZ PRO v2.0 BASLATILIYOR...")
    print("=" * 60)
    print(f"Klasör: {BASE_DIR}")
    print("Adres: http://localhost:5000")
    print("Admin: admin / admin123")
    print("=" * 60)
    
    # Mobil cihazlardan erişim için host='0.0.0.0'
    app.run(
        debug=True, 
        host='0.0.0.0',
        port=5000, 
        threaded=True,
        use_reloader=False
    )
