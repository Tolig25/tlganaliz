"""
TLG Analiz Pro - Yapay Zeka Analiz Motoru
Makine öğrenmesi ile kendini geliştiren AI sistemi
Tahminleri sürekli kontrol eder ve başarı oranlarına göre kendini eğitir
"""
import threading
import time
import json
from datetime import datetime, timedelta
from database import db
from utils import log_system, log_error, log_system as log
from api import fetch_yahoo_data
from indicators import calculate_all_indicators

class AIEngine:
    """
    Yapay Zeka Analiz Motoru
    - Teknik indikatörlere göre tahmin yapar
    - Tahminleri sürekli kontrol eder
    - Başarı/başarısızlık oranlarına göre kendini eğitir
    - Kullanıcı işlem geçmişini tutar
    """
    
    def __init__(self):
        self.learning_enabled = True
        self.check_interval = 3600  # 1 saat
        self.min_confidence = 60
        self.is_running = False
        self.thread = None
        self.prediction_accuracy = {}  # Hisse bazlı başarı oranları
        self.last_check = None
        
    def start(self):
        """AI motorunu başlat"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._main_loop, daemon=True)
            self.thread.start()
            log_system('AI_START', 'AI motoru başlatıldı - Tahmin kontrol döngüsü aktif')
            print("[AI] Motor başlatıldı")
    
    def stop(self):
        """AI motorunu durdur"""
        self.is_running = False
        log_system('AI_STOP', 'AI motoru durduruldu')
        print("[AI] Motor durduruldu")
    
    def _main_loop(self):
        """Ana döngü - tahminleri doğrula ve öğren"""
        while self.is_running:
            try:
                print(f"[AI] Kontrol döngüsü başladı - {datetime.now()}")
                
                # Tahminleri doğrula
                self.verify_predictions()
                
                # Eski logları temizle
                self.cleanup_old_logs()
                
                # Sistem hatalarını kontrol et
                self.check_system_health()
                
                self.last_check = datetime.now()
                print(f"[AI] Kontrol tamamlandı, {self.check_interval} saniye bekleniyor...")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                error_msg = f"AI döngü hatası: {str(e)}"
                log_error('AI_LOOP_ERROR', error_msg, 'AIEngine._main_loop')
                print(f"[AI HATA] {error_msg}")
                time.sleep(60)  # Hata durumunda 1 dakika bekle
    
    def analyze(self, prices, symbol=None):
        """
        Hisse verilerini analiz et ve tahmin yap
        Geçmiş başarı oranlarını da dikkate alır
        """
        if not prices or len(prices) < 30:
            return None
        
        latest = prices[-1]
        current = latest['close']
        
        # İndikatör değerlerini al
        indicators = {
            'rsi': latest.get('rsi', 50),
            'macd': latest.get('macd', 0),
            'macd_signal': latest.get('macd_signal', 0),
            'sma20': latest.get('sma20'),
            'sma50': latest.get('sma50'),
            'ema12': latest.get('ema12'),
            'ema26': latest.get('ema26'),
            'bb_upper': latest.get('bb_upper'),
            'bb_lower': latest.get('bb_lower'),
            'bb_middle': latest.get('bb_middle'),
            'atr': latest.get('atr', 0),
            'stoch_k': latest.get('stoch_k', 50),
            'stoch_d': latest.get('stoch_d', 50)
        }
        
        # Skorlama sistemi (0-100)
        scores = {}
        
        # RSI Skoru (30 aşırı satım, 70 aşırı alım)
        rsi = indicators['rsi']
        if rsi is None:
            scores['rsi'] = 50
        elif rsi < 25:
            scores['rsi'] = 95  # Güçlü alım
        elif rsi < 30:
            scores['rsi'] = 85
        elif rsi > 75:
            scores['rsi'] = 5   # Güçlü satım
        elif rsi > 70:
            scores['rsi'] = 15
        elif rsi < 45:
            scores['rsi'] = 70
        elif rsi > 55:
            scores['rsi'] = 30
        else:
            scores['rsi'] = 50
        
        # MACD Skoru
        macd = indicators['macd']
        macd_signal = indicators['macd_signal']
        if macd is None or macd_signal is None:
            scores['macd'] = 50
        elif macd > macd_signal and macd > 0:
            scores['macd'] = 90  # Güçlü alım
        elif macd > macd_signal:
            scores['macd'] = 75  # Alım
        elif macd < macd_signal and macd < 0:
            scores['macd'] = 10  # Güçlü satım
        else:
            scores['macd'] = 25  # Satım
        
        # Trend Skoru (SMA)
        sma20 = indicators['sma20']
        sma50 = indicators['sma50']
        if sma20 and sma50:
            if sma20 > sma50 * 1.05:  # %5 üzerinde
                scores['trend_sma'] = 90
            elif sma20 > sma50:
                scores['trend_sma'] = 75
            elif sma20 < sma50 * 0.95:  # %5 altında
                scores['trend_sma'] = 10
            else:
                scores['trend_sma'] = 25
        else:
            scores['trend_sma'] = 50
        
        # EMA Trend Skoru
        ema12 = indicators['ema12']
        ema26 = indicators['ema26']
        if ema12 and ema26:
            if ema12 > ema26 * 1.03:
                scores['trend_ema'] = 85
            elif ema12 > ema26:
                scores['trend_ema'] = 70
            elif ema12 < ema26 * 0.97:
                scores['trend_ema'] = 15
            else:
                scores['trend_ema'] = 30
        else:
            scores['trend_ema'] = 50
        
        # Bollinger Skoru
        bb_upper = indicators['bb_upper']
        bb_lower = indicators['bb_lower']
        if bb_upper and bb_lower and bb_upper != bb_lower:
            band_width = bb_upper - bb_lower
            position = (current - bb_lower) / band_width
            
            if position < 0.05:  # Alt banda çok yakın
                scores['bollinger'] = 95  # Aşırı satım
            elif position < 0.2:
                scores['bollinger'] = 80
            elif position < 0.4:
                scores['bollinger'] = 60
            elif position > 0.95:  # Üst banda çok yakın
                scores['bollinger'] = 5   # Aşırı alım
            elif position > 0.8:
                scores['bollinger'] = 20
            elif position > 0.6:
                scores['bollinger'] = 40
            else:
                scores['bollinger'] = 50
        else:
            scores['bollinger'] = 50
        
        # Stochastic Skoru
        stoch_k = indicators['stoch_k']
        if stoch_k is not None:
            if stoch_k < 20:
                scores['stochastic'] = 90
            elif stoch_k > 80:
                scores['stochastic'] = 10
            elif stoch_k < 50:
                scores['stochastic'] = 70
            else:
                scores['stochastic'] = 30
        else:
            scores['stochastic'] = 50
        
        # Volatilite Skoru (ATR bazlı)
        atr = indicators['atr']
        if atr and current > 0:
            atr_percent = (atr / current) * 100
            if atr_percent > 5:
                scores['volatility'] = 30  # Yüksek volatilite = riskli
            elif atr_percent > 3:
                scores['volatility'] = 50
            else:
                scores['volatility'] = 75  # Düşük volatilite = stabil
        else:
            scores['volatility'] = 50
        
        # Ağırlıklı toplam skor
        weights = {
            'rsi': 0.20,
            'macd': 0.20,
            'trend_sma': 0.15,
            'trend_ema': 0.10,
            'bollinger': 0.15,
            'stochastic': 0.10,
            'volatility': 0.10
        }
        
        total_score = sum(scores[key] * weights[key] for key in weights)
        
        # Geçmiş başarı oranını hesapla ve uygula
        historical_accuracy = self.get_historical_accuracy(symbol, total_score)
        if historical_accuracy is not None:
            # Geçmiş başarıyı %25 oranında mevcut skora ekle
            adjusted_score = (total_score * 0.75) + (historical_accuracy * 0.25)
            total_score = adjusted_score
        
        # Karar belirle
        if total_score >= 85:
            decision = "GÜÇLÜ AL"
            confidence_level = "Çok Yüksek"
        elif total_score >= 70:
            decision = "AL"
            confidence_level = "Yüksek"
        elif total_score >= 55:
            decision = "NÖTR"
            confidence_level = "Orta"
        elif total_score >= 40:
            decision = "SAT"
            confidence_level = "Düşük-Orta"
        elif total_score >= 25:
            decision = "GÜÇLÜ SAT"
            confidence_level = "Düşük"
        else:
            decision = "AŞIRI SAT"
            confidence_level = "Çok Düşük"
        
        # Hedef fiyat hesaplama (ATR bazlı)
        if atr and atr > 0:
            if "AL" in decision:
                target = current + (atr * 3)
                stop_loss = current - (atr * 2)
            elif "SAT" in decision:
                target = current - (atr * 3)
                stop_loss = current + (atr * 2)
            else:
                target = current * 1.02
                stop_loss = current * 0.98
        else:
            # ATR yoksa %5 ve %3 kullan
            if "AL" in decision:
                target = current * 1.05
                stop_loss = current * 0.97
            elif "SAT" in decision:
                target = current * 0.95
                stop_loss = current * 1.03
            else:
                target = current * 1.02
                stop_loss = current * 0.98
        
        # Risk/Ödül oranı
        risk = abs(current - stop_loss)
        reward = abs(target - current)
        risk_reward = round(reward / risk, 2) if risk > 0 else 1.5
        
        # Potansiyel getiri/kayıp
        if "AL" in decision:
            potential_gain = round(((target - current) / current) * 100, 1)
            potential_loss = round(((current - stop_loss) / current) * 100, 1)
        elif "SAT" in decision:
            potential_gain = round(((current - target) / current) * 100, 1)
            potential_loss = round(((stop_loss - current) / current) * 100, 1)
        else:
            potential_gain = round(abs(((target - current) / current) * 100), 1)
            potential_loss = potential_gain
        
        # Nedenler oluştur
        reasons = []
        
        if scores['rsi'] > 70:
            reasons.append(f"RSI {rsi:.1f} - Aşırı alım bölgesi, düzeltme gelebilir")
        elif scores['rsi'] < 30:
            reasons.append(f"RSI {rsi:.1f} - Aşırı satım bölgesi, alım fırsatı")
        elif scores['rsi'] > 55:
            reasons.append(f"RSI {rsi:.1f} - Pozitif momentum")
        else:
            reasons.append(f"RSI {rsi:.1f} - Negatif momentum")
        
        if scores['macd'] > 70:
            reasons.append("MACD pozitif - Yukarı trend devam ediyor")
        elif scores['macd'] < 30:
            reasons.append("MACD negatif - Aşağı trend devam ediyor")
        
        if scores['trend_sma'] > 70:
            reasons.append("SMA 20 > SMA 50 - Yükseliş trendi aktif")
        elif scores['trend_sma'] < 30:
            reasons.append("SMA 20 < SMA 50 - Düşüş trendi aktif")
        
        if scores['bollinger'] > 70:
            reasons.append("Fiyat alt banda yakın - Aşırı satım bölgesi")
        elif scores['bollinger'] < 30:
            reasons.append("Fiyat üst banda yakın - Aşırı alım bölgesi")
        
        if scores['stochastic'] > 70:
            reasons.append("Stochastic aşırı satım - Dönüş sinyali")
        elif scores['stochastic'] < 30:
            reasons.append("Stochastic aşırı alım - Dönüş sinyali")
        
        # Sonuç döndür
        return {
            'decision': decision,
            'confidence': round(total_score, 1),
            'confidence_level': confidence_level,
            'target_price': round(target, 2),
            'stop_loss': round(stop_loss, 2),
            'current_price': round(current, 2),
            'risk_reward': risk_reward,
            'potential_gain': potential_gain,
            'potential_loss': potential_loss,
            'reasons': reasons,
            'indicators': {
                'rsi': round(rsi, 1) if rsi else 50,
                'macd': round(macd, 3) if macd else 0,
                'macd_signal': round(macd_signal, 3) if macd_signal else 0,
                'sma20': round(sma20, 2) if sma20 else 0,
                'sma50': round(sma50, 2) if sma50 else 0,
                'ema12': round(ema12, 2) if ema12 else 0,
                'ema26': round(ema26, 2) if ema26 else 0,
                'atr': round(atr, 2) if atr else 0,
                'stoch_k': round(stoch_k, 1) if stoch_k else 50,
                'bb_position': round(((current - bb_lower) / (bb_upper - bb_lower)) * 100, 1) if bb_upper and bb_lower else 50
            },
            'scores': scores,
            'historical_accuracy': historical_accuracy,
            'suggested_holding_period': '7-14 gün' if "GÜÇLÜ" in decision else '3-7 gün' if decision != "NÖTR" else 'Belirsiz',
            'analysis_timestamp': datetime.now().isoformat()
        }
    def get_historical_accuracy(self, symbol, current_score):
        """Geçmiş tahmin başarı oranını getir"""
        if not symbol:
            return None
        
        try:
            conn = db.get_connection()
            
            # Son 30 tahmini al
            past = conn.execute('''
                SELECT actual_result, is_success, confidence 
                FROM predictions 
                WHERE stock_symbol=? AND actual_result != 'PENDING'
                ORDER BY predicted_at DESC LIMIT 30
            ''', (symbol,)).fetchall()
            
            conn.close()
            
            if len(past) < 5:  # Yeterli veri yok
                return None
            
            success_count = sum(1 for p in past if p['is_success'] == 1)
            total = len(past)
            accuracy = (success_count / total) * 100
            
            # Benzer confidence seviyesindeki tahminleri kontrol et
            similar = [p for p in past if abs(p['confidence'] - current_score) < 15]
            if len(similar) >= 3:
                similar_success = sum(1 for p in similar if p['is_success'] == 1)
                similar_accuracy = (similar_success / len(similar)) * 100
                # Ağırlıklı ortalama
                return round((accuracy * 0.6) + (similar_accuracy * 0.4), 1)
            
            return round(accuracy, 1)
            
        except Exception as e:
            log_error('AI_HISTORY_ERROR', str(e), 'get_historical_accuracy')
            return None
    
    def save_prediction(self, user_id, symbol, analysis):
        """Tahmini veritabanına kaydet ve işlem geçmişine ekle"""
        try:
            target_date = datetime.now() + timedelta(days=7)
            
            conn = db.get_connection()
            c = conn.cursor()
            
            # Tahmini kaydet
            c.execute('''
                INSERT INTO predictions 
                (user_id, stock_symbol, prediction_type, confidence, reason,
                 predicted_at, target_date, price_at_prediction, target_price, stop_loss)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ''', (
                user_id, symbol, analysis['decision'], analysis['confidence'],
                '; '.join(analysis['reasons']), target_date,
                analysis['current_price'], analysis['target_price'], analysis['stop_loss']
            ))
            
            pred_id = c.lastrowid
            
            # Log kaydet
            c.execute('''
                INSERT INTO prediction_logs (prediction_id, log_type, message)
                VALUES (?, ?, ?)
            ''', (pred_id, 'CREATED', f"Yeni tahmin: {analysis['decision']} (%{analysis['confidence']})"))
            
            # İşlem geçmişine ekle (transactions tablosuna)
            c.execute('''
                INSERT INTO transactions 
                (user_id, stock_symbol, transaction_type, price, notes, transaction_date)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id, symbol, f"AI_TAHMIN_{analysis['decision']}",
                analysis['current_price'],
                f"Hedef: {analysis['target_price']}, Stop: {analysis['stop_loss']}, Güven: %{analysis['confidence']}"
            ))
            
            conn.commit()
            conn.close()
            
            # İstatistiği güncelle
            db.increment_stat('total_predictions')
            
            log_system('PREDICTION_CREATED', f'{symbol} - {analysis["decision"]} (%{analysis["confidence"]})', user_id=user_id)
            
            return pred_id
            
        except Exception as e:
            log_error('AI_SAVE_ERROR', str(e), 'save_prediction')
            return None
    
    def verify_predictions(self):
        """Bekleyen tahminleri kontrol et ve sonuçlandır - AI öğrenmesi için kritik"""
        try:
            conn = db.get_connection()
            
            # Doğrulanmamış ve tarihi geçmiş tahminleri al
            week_ago = datetime.now() - timedelta(days=7)
            predictions = conn.execute('''
                SELECT * FROM predictions 
                WHERE actual_result='PENDING' 
                AND target_date < CURRENT_TIMESTAMP
            ''').fetchall()
            
            print(f"[AI] {len(predictions)} tahmin doğrulanacak")
            
            verified_count = 0
            success_count = 0
            
            for pred in predictions:
                try:
                    # Güncel fiyatı çek
                    data = fetch_yahoo_data(pred['stock_symbol'], '5d')
                    if not data:
                        continue
                    
                    current_price = data['current']
                    target_price = pred['target_price']
                    stop_loss = pred['stop_loss']
                    prediction_type = pred['prediction_type']
                    entry_price = pred['price_at_prediction']
                    
                    # Sonucu belirle
                    result = None
                    is_success = 0
                    
                    if 'AL' in prediction_type:
                        if current_price >= target_price:
                            result = 'SUCCESS'
                            is_success = 1
                        elif current_price <= stop_loss:
                            result = 'FAIL'
                        elif current_price > entry_price * 1.02:  # %2 kar realizasyonu
                            result = 'PARTIAL'
                            is_success = 1
                    elif 'SAT' in prediction_type:
                        if current_price <= target_price:
                            result = 'SUCCESS'
                            is_success = 1
                        elif current_price >= stop_loss:
                            result = 'FAIL'
                        elif current_price < entry_price * 0.98:  # %2 kar realizasyonu
                            result = 'PARTIAL'
                            is_success = 1
                    
                    # Hala bekliyorsa ve çok uzun sürdüyse
                    if result is None:
                        days_waiting = (datetime.now() - datetime.fromisoformat(pred['predicted_at'])).days
                        if days_waiting > 14:  # 14 günden uzun sürdü
                            if ('AL' in prediction_type and current_price > entry_price) or \
                               ('SAT' in prediction_type and current_price < entry_price):
                                result = 'SUCCESS'
                                is_success = 1
                            else:
                                result = 'EXPIRED'
                    
                    if result:
                        # Tahmini güncelle
                        conn.execute('''
                            UPDATE predictions 
                            SET actual_result=?, actual_price=?, is_success=?, verified_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (result, current_price, is_success, pred['id']))
                        
                        # Log kaydet
                        conn.execute('''
                            INSERT INTO prediction_logs (prediction_id, log_type, message)
                            VALUES (?, ?, ?)
                        ''', (pred['id'], 'VERIFICATION', 
                              f'Tahmin sonuçlandı: {result}. Hedef: {target_price}, Gerçek: {current_price}'))
                        
                        # AI öğrenme kaydı - Başarılı parametreleri kaydet
                        if self.learning_enabled:
                            self._learn_from_result(pred, result, current_price)
                        
                        verified_count += 1
                        if is_success:
                            success_count += 1
                    
                except Exception as e:
                    log_error('VERIFY_SINGLE_ERROR', str(e), f'verify_predictions-{pred["id"]}')
                    continue
            
            conn.commit()
            conn.close()
            
            if verified_count > 0:
                success_rate = (success_count / verified_count) * 100
                log_system('PREDICTION_BATCH_VERIFIED', 
                          f'{verified_count} tahmin doğrulandı, %{success_rate:.1f} başarı oranı')
                print(f"[AI] {verified_count} tahmin doğrulandı, %{success_rate:.1f} başarı")
            
        except Exception as e:
            log_error('VERIFY_ERROR', str(e), 'verify_predictions')
    
    def _learn_from_result(self, prediction, result, actual_price):
        """Tahmin sonucundan öğren - AI geliştirme"""
        try:
            conn = db.get_connection()
            
            # Başarılı parametreleri kaydet
            conn.execute('''
                INSERT OR REPLACE INTO ai_learning 
                (stock_symbol, prediction_type, confidence_range, success_rate, 
                 total_predictions, successful_predictions, last_updated)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT total_predictions FROM ai_learning 
                             WHERE stock_symbol=? AND prediction_type=? AND confidence_range=?), 0) + 1,
                    COALESCE((SELECT successful_predictions FROM ai_learning 
                             WHERE stock_symbol=? AND prediction_type=? AND confidence_range=?), 0) + ?,
                    CURRENT_TIMESTAMP)
            ''', (
                prediction['stock_symbol'],
                prediction['prediction_type'],
                f"{int(prediction['confidence'] // 10 * 10)}-{int(prediction['confidence'] // 10 * 10) + 10}",
                1 if result in ['SUCCESS', 'PARTIAL'] else 0,
                prediction['stock_symbol'], prediction['prediction_type'],
                f"{int(prediction['confidence'] // 10 * 10)}-{int(prediction['confidence'] // 10 * 10) + 10}",
                prediction['stock_symbol'], prediction['prediction_type'],
                f"{int(prediction['confidence'] // 10 * 10)}-{int(prediction['confidence'] // 10 * 10) + 10}",
                1 if result in ['SUCCESS', 'PARTIAL'] else 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            log_error('LEARN_ERROR', str(e), '_learn_from_result')
    
    def cleanup_old_logs(self):
        """Eski logları temizle - otomatik bakım"""
        try:
            retention_days = int(db.get_setting('log_retention_days', '30'))
            if retention_days <= 0:
                return
            
            cutoff = datetime.now() - timedelta(days=retention_days)
            
            conn = db.get_connection()
            
            # Eski logları sil
            c = conn.cursor()
            c.execute("DELETE FROM logs WHERE created_at < ?", (cutoff,))
            logs_deleted = c.rowcount
            
            c.execute("DELETE FROM prediction_logs WHERE created_at < ?", (cutoff,))
            pred_logs_deleted = c.rowcount
            
            # Çözümlenmiş eski hataları sil
            c.execute('''
                DELETE FROM system_errors 
                WHERE is_resolved=1 AND detected_at < ?
            ''', (cutoff,))
            errors_deleted = c.rowcount
            
            conn.commit()
            conn.close()
            
            if logs_deleted > 0 or pred_logs_deleted > 0:
                log_system('CLEANUP', 
                          f'Eski loglar temizlendi: {logs_deleted} sistem, {pred_logs_deleted} tahmin, {errors_deleted} hata')
            
        except Exception as e:
            log_error('CLEANUP_ERROR', str(e), 'cleanup_old_logs')
    
    def check_system_health(self):
        """Sistem sağlığını kontrol et ve hataları tespit et"""
        try:
            # API bağlantısını kontrol et
            test_data = fetch_yahoo_data('THYAO.IS', '1d')
            if not test_data:
                log_error('API_HEALTH_CHECK', 'API bağlantısı başarısız', 'check_system_health')
            
            # Veritabanı bağlantısını kontrol et
            conn = db.get_connection()
            conn.execute("SELECT 1")
            
            # Uzun süredir doğrulanmamış tahminleri kontrol et
            old_pending = conn.execute('''
                SELECT COUNT(*) as c FROM predictions 
                WHERE actual_result='PENDING' 
                AND predicted_at < datetime('now', '-14 days')
            ''').fetchone()['c']
            
            if old_pending > 10:
                log_error('OLD_PREDICTIONS', f'{old_pending} eski bekleyen tahmin var', 'check_system_health')
            
            conn.close()
            
        except Exception as e:
            log_error('HEALTH_CHECK_ERROR', str(e), 'check_system_health')
    
    def batch_analyze(self, symbols, min_confidence=60):
        """Toplu hisse analizi yap - En iyi 5 hisseyi bul"""
        results = []
        
        print(f"[AI] Toplu analiz başladı: {len(symbols)} hisse")
        
        for symbol in symbols:
            try:
                data = fetch_yahoo_data(symbol, "6mo")
                if not data or len(data['prices']) < 30:
                    continue
                
                prices = calculate_all_indicators(data['prices'])
                analysis = self.analyze(prices, symbol)
                
                if analysis and analysis['confidence'] >= min_confidence:
                    # Sadece AL sinyallerini döndür (SAT kısa pozisyon için kullanılabilir)
                    if "AL" in analysis['decision']:
                        results.append({
                            'symbol': symbol,
                            'name': data.get('info', {}).get('longName', symbol),
                            'decision': analysis['decision'],
                            'confidence': analysis['confidence'],
                            'target_price': analysis['target_price'],
                            'current_price': analysis['current_price'],
                            'potential': analysis['potential_gain'],
                            'risk_reward': analysis['risk_reward'],
                            'reasons': analysis['reasons'][:2]  # İlk 2 neden
                        })
                        
            except Exception as e:
                log_error('BATCH_ERROR', f"{symbol}: {str(e)}", 'batch_analyze')
                continue
        
        # Güven skoruna göre sırala
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"[AI] Toplu analiz tamamlandı: {len(results)} hisse bulundu")
        
        # En iyi 5 hisseyi döndür
        return results[:5]
    
    def get_learning_stats(self):
        """AI öğrenme istatistiklerini getir"""
        try:
            conn = db.get_connection()
            
            stats = conn.execute('''
                SELECT 
                    COUNT(*) as total_patterns,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_predictions) as total_predictions,
                    SUM(successful_predictions) as successful_predictions
                FROM ai_learning
            ''').fetchone()
            
            conn.close()
            
            return {
                'total_patterns': stats['total_patterns'] or 0,
                'avg_success_rate': round(stats['avg_success_rate'] or 0, 1),
                'total_predictions': stats['total_predictions'] or 0,
                'successful_predictions': stats['successful_predictions'] or 0,
                'overall_success_rate': round(
                    (stats['successful_predictions'] / stats['total_predictions'] * 100), 1
                ) if stats['total_predictions'] else 0
            }
            
        except Exception as e:
            log_error('LEARNING_STATS_ERROR', str(e), 'get_learning_stats')
            return None

# Global AI instance
ai_engine = AIEngine()
