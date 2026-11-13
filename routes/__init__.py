from .auth import auth_bp
from .consumer import consumer_bp
from .merchant import merchant_bp
from .admin import admin_bp
from .api import api_bp

__all__ = ['auth_bp', 'consumer_bp', 'merchant_bp', 'admin_bp', 'api_bp']
