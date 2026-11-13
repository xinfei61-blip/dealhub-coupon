from functools import wraps
from flask import abort, flash, redirect, url_for, request, jsonify
from flask_login import current_user

def role_required(*allowed_roles):
    """
    RBAC 權限裝飾器：限制特定身份才能訪問端點
    支援 'consumer', 'merchant', 'admin'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 若為 API 請求，返回 JSON 錯誤碼
            is_api = request.path.startswith('/api/') or request.is_json
            
            if not current_user.is_authenticated:
                if is_api:
                    return jsonify({'success': False, 'message': '未登入或憑證已失效，請先登入'}), 401
                flash('請先登入帳號以訪問此頁面。', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if current_user.role not in allowed_roles:
                if is_api:
                    return jsonify({'success': False, 'message': '權限不足，拒絕訪問'}), 403
                flash('您的帳號身份無權訪問該專案後台。', 'danger')
                # 根據用戶角色重導向到合適的首頁
                if current_user.role == 'merchant':
                    return redirect(url_for('merchant.dashboard'))
                elif current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('consumer.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def consumer_required(f):
    return role_required('consumer', 'admin')(f)

def merchant_required(f):
    return role_required('merchant', 'admin')(f)

def admin_required(f):
    return role_required('admin')(f)
