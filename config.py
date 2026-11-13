import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'coupon-platform-secret-key-2026-v1')
    
    # Render.com PostgreSQL 相容處理 (將舊版 postgres:// 轉換為 SQLAlchemy 要求的 postgresql://)
    raw_db_url = os.environ.get('DATABASE_URL')
    if raw_db_url:
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR / "coupon_platform.db"}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 12
    DEFAULT_CURRENCY = 'NT$'
