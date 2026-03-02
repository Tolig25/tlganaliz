"""
TLG Analiz Pro - Routes Paketi
Blueprint tanımlamaları ve route organizasyonu
"""
from flask import Blueprint

# User blueprint - Kullanıcı işlemleri
user_bp = Blueprint('user', __name__)

# Admin blueprint - Yönetim paneli işlemleri  
admin_bp = Blueprint('admin', __name__)

__all__ = ['user_bp', 'admin_bp']
