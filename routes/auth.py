from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, MerchantProfile

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'merchant':
            return redirect(url_for('merchant.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('consumer.index'))

    if request.method == 'POST':
        login_input = request.form.get('login_input', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_input or not password:
            flash('請輸入帳號/電子信箱與密碼。', 'warning')
            return render_template('auth/login.html')

        # 支援使用者名稱或 Email 登入
        user = User.query.filter(
            (User.username == login_input) | (User.email == login_input)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'歡迎回來，{user.username}！', 'success')
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            if user.role == 'merchant':
                return redirect(url_for('merchant.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('consumer.index'))
        else:
            flash('帳號或密碼錯誤，請重新確認。', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('consumer.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'consumer') # 'consumer' 或 'merchant'

        if not username or not email or not password:
            flash('請填寫所有必填欄位。', 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('兩次輸入的密碼不一致。', 'danger')
            return render_template('auth/register.html')

        if role not in ['consumer', 'merchant']:
            role = 'consumer'

        # 檢查帳號或 Email 是否重複
        if User.query.filter_by(username=username).first():
            flash('此使用者名稱已被註冊，請換一個。', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('此電子信箱已被註冊，請直接登入。', 'danger')
            return render_template('auth/register.html')

        # 建立使用者
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush() # 取得 user.id

        # 若註冊為商家，同步建立 MerchantProfile
        if role == 'merchant':
            brand_name = request.form.get('brand_name', '').strip() or f"{username} 的品牌店"
            category_name = request.form.get('category_name', '速食')
            phone = request.form.get('phone', '').strip()
            
            profile = MerchantProfile(
                user_id=user.id,
                brand_name=brand_name,
                category_name=category_name,
                contact_email=email,
                phone=phone,
                description=request.form.get('description', '')
            )
            db.session.add(profile)

        db.session.commit()
        login_user(user)

        flash('恭喜註冊成功！已為您自動登入。', 'success')
        if role == 'merchant':
            return redirect(url_for('merchant.dashboard'))
        return redirect(url_for('consumer.index'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功安全登出。', 'info')
    return redirect(url_for('consumer.index'))
