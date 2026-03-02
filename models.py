"""
TLG Analiz Pro - Veritabanı Modelleri
SQLAlchemy modelleri ve veritabanı şema tanımlamaları
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class User:
    """Kullanıcı modeli"""
    id: int
    username: str
    password: str
    is_admin: bool
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_login': self.last_login
        }

@dataclass
class Prediction:
    """Tahmin modeli"""
    id: int
    user_id: int
    stock_symbol: str
    prediction_type: str
    confidence: float
    reason: str
    predicted_at: str
    target_date: str
    actual_result: str
    price_at_prediction: float
    target_price: float
    stop_loss: float
    actual_price: Optional[float] = None
    is_success: bool = False
    verified_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_symbol': self.stock_symbol,
            'prediction_type': self.prediction_type,
            'confidence': self.confidence,
            'reason': self.reason,
            'predicted_at': self.predicted_at,
            'target_date': self.target_date,
            'actual_result': self.actual_result,
            'price_at_prediction': self.price_at_prediction,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'actual_price': self.actual_price,
            'is_success': self.is_success,
            'verified_at': self.verified_at
        }

@dataclass
class Stock:
    """Hisse modeli"""
    id: int
    symbol: str
    name: str
    sector: str
    is_active: bool
    added_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'is_active': self.is_active,
            'added_at': self.added_at
        }

@dataclass
class Indicator:
    """İndikatör modeli"""
    id: int
    name: str
    display_name: str
    is_active: bool
    color: str
    description: str
    parameters: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'color': self.color,
            'description': self.description,
            'parameters': self.parameters
        }

@dataclass
class Log:
    """Log modeli"""
    id: int
    log_type: str
    action: str
    details: str
    user_id: Optional[int]
    ip_address: Optional[str]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'log_type': self.log_type,
            'action': self.action,
            'details': self.details,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'created_at': self.created_at
        }

@dataclass
class SystemError:
    """Sistem hatası modeli"""
    id: int
    error_type: str
    message: str
    location: str
    is_resolved: bool
    detected_at: str
    resolved_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'error_type': self.error_type,
            'message': self.message,
            'location': self.location,
            'is_resolved': self.is_resolved,
            'detected_at': self.detected_at,
            'resolved_at': self.resolved_at
        }

@dataclass
class Favorite:
    """Favori modeli"""
    id: int
    user_id: int
    stock_symbol: str
    added_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_symbol': self.stock_symbol,
            'added_at': self.added_at
        }

@dataclass
class Transaction:
    """İşlem modeli"""
    id: int
    user_id: int
    stock_symbol: str
    transaction_type: str
    quantity: Optional[int]
    price: Optional[float]
    total_amount: Optional[float]
    transaction_date: str
    notes: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_symbol': self.stock_symbol,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'price': self.price,
            'total_amount': self.total_amount,
            'transaction_date': self.transaction_date,
            'notes': self.notes
        }

@dataclass
class AILearning:
    """AI öğrenme modeli"""
    id: int
    stock_symbol: str
    indicator_pattern: str
    prediction_type: str
    confidence_range: str
    success_rate: float
    total_predictions: int
    successful_predictions: int
    last_updated: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'stock_symbol': self.stock_symbol,
            'indicator_pattern': self.indicator_pattern,
            'prediction_type': self.prediction_type,
            'confidence_range': self.confidence_range,
            'success_rate': self.success_rate,
            'total_predictions': self.total_predictions,
            'successful_predictions': self.successful_predictions,
            'last_updated': self.last_updated
        }

@dataclass
class SiteStats:
    """Site istatistikleri modeli"""
    id: int
    stat_date: str
    total_logins: int
    total_predictions: int
    total_page_views: int
    api_calls: int
    errors_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'stat_date': self.stat_date,
            'total_logins': self.total_logins,
            'total_predictions': self.total_predictions,
            'total_page_views': self.total_page_views,
            'api_calls': self.api_calls,
            'errors_count': self.errors_count
        }
