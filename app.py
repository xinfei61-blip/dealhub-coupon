import os
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime
from flask import Flask
from config import Config
from extensions import db, login_manager
from routes import auth_bp, consumer_bp, merchant_bp, admin_bp, api_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化擴充套件
    db.init_app(app)
    login_manager.init_app(app)

    # 註冊模組藍圖 (Blueprints)
    app.register_blueprint(consumer_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(merchant_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # 全域模板輔助變數
    @app.context_processor
    def inject_global_vars():
        return {
            'now': datetime.utcnow(),
            'current_year': datetime.utcnow().year,
            'app_name': '鈔捷徑 - 速食飲料專屬優惠平台'
        }

    # 自動建立資料表並於首次啟動時注入示範資料 (雲端 Render 自動初始化防護)
    with app.app_context():
        db.create_all()
        try:
            from models import Category
            if not Category.query.first():
                from seed import seed
                print("⚡ 偵測到雲端首次運行，正在自動初始化示範資料庫...")
                seed(drop=False)
                print("✅ 雲端資料庫初始化完成！")
        except Exception as e:
            print(f"⚠️ 資料庫檢查警告: {e}")

    return app

# 提供 Gunicorn 與 WSGI 伺服器之全域 app 實例
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=================================================================")
    print(" 🚀 鈔捷徑 優惠券與核銷平台已啟動！")
    print(f" 🌐 前端訪問網址: http://127.0.0.1:{port}")
    print(" 💡 核心分類聚焦: 「速食」與「飲料」")
    print("=================================================================")
    app.run(host='0.0.0.0', port=port, debug=False)
