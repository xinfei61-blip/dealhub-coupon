from datetime import datetime
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # RBAC 角色: 'consumer' (一般消費者), 'merchant' (商家), 'admin' (平台管理員)
    role = db.Column(db.String(20), nullable=False, default='consumer', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯設定
    merchant_profile = db.relationship('MerchantProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    redemptions = db.relationship('Redemption', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_consumer(self):
        return self.role == 'consumer'

    @property
    def is_merchant(self):
        return self.role == 'merchant'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def get_total_savings(self):
        """計算消費者累計省下的金額總和"""
        total = db.session.query(db.func.sum(Redemption.saved_amount))\
            .filter(Redemption.user_id == self.id, Redemption.status == 'completed')\
            .scalar()
        return round(total, 1) if total else 0.0

    def get_redemption_count(self):
        """計算消費者累計核銷次數"""
        return self.redemptions.filter_by(status='completed').count()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class MerchantProfile(db.Model):
    __tablename__ = 'merchant_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    brand_name = db.Column(db.String(100), nullable=False, index=True)
    logo_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category_name = db.Column(db.String(50), default='速食') # 主要垂直分類: '速食' 或 '飲料'
    contact_email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    is_verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    coupons = db.relationship('Coupon', backref='merchant', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'brand_name': self.brand_name,
            'logo_url': self.logo_url or 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=150&auto=format&fit=crop&q=60',
            'description': self.description,
            'category_name': self.category_name,
            'contact_email': self.contact_email,
            'phone': self.phone,
            'address': self.address
        }


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # '速食', '飲料'
    slug = db.Column(db.String(50), unique=True, nullable=False) # 'fastfood', 'beverage'
    icon = db.Column(db.String(50), default='bi-tag') # bi-egg-fried, bi-cup-straw
    description = db.Column(db.String(200), nullable=True)

    coupons = db.relationship('Coupon', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'icon': self.icon,
            'description': self.description
        }


class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    discount_tag = db.Column(db.String(50), nullable=True) # 如 "現省 $30", "買一送一", "第 2 杯半價"
    
    # 金額設定
    original_price = db.Column(db.Float, default=0.0) # 原價
    discount_price = db.Column(db.Float, default=0.0) # 特惠價
    savings_amount = db.Column(db.Float, nullable=False, default=0.0) # 每次核銷省下的金額 (計入錢包)
    
    # 限制機制 1: 時效控管
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # 限制機制 2: 數量控管
    total_quantity = db.Column(db.Integer, nullable=False, default=100) # 總發行數量上限
    redeemed_count = db.Column(db.Integer, nullable=False, default=0) # 已核銷份數
    max_per_user = db.Column(db.Integer, nullable=False, default=1) # 單一帳號每人限用次數
    
    # 限制機制 3: 條款備註
    terms_and_conditions = db.Column(db.Text, nullable=False, default='1. 限內用或外帶自取。\n2. 本券不得與其他優惠或行銷活動合併使用。\n3. 結帳前請主動向門市人員出示核銷序號畫面。')
    
    # 狀態管理
    is_active = db.Column(db.Boolean, default=True)
    
    # 行銷資料科學指標
    views_count = db.Column(db.Integer, default=0) # 曝光數 (Views)
    clicks_count = db.Column(db.Integer, default=0) # 點擊數
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    redemptions = db.relationship('Redemption', backref='coupon', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def remaining_quantity(self):
        """剩餘可核銷數量"""
        return max(0, self.total_quantity - self.redeemed_count)

    @property
    def is_valid_now(self):
        """檢查是否在有效期間內且仍有名額"""
        now = datetime.utcnow()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            self.remaining_quantity > 0
        )

    @property
    def conversion_rate(self):
        """轉換率 (Conversion Rate % = 核銷數 / 曝光數 * 100)"""
        if self.views_count and self.views_count > 0:
            return round((self.redeemed_count / self.views_count) * 100, 2)
        return 0.0

    @property
    def click_through_rate(self):
        """點閱率 (CTR % = 點擊數 / 曝光數 * 100)"""
        if self.views_count and self.views_count > 0:
            return round((self.clicks_count / self.views_count) * 100, 2)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'merchant_id': self.merchant_id,
            'merchant_name': self.merchant.brand_name if self.merchant else '',
            'merchant_logo': self.merchant.logo_url if self.merchant else '',
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url or 'https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&auto=format&fit=crop&q=60',
            'discount_tag': self.discount_tag or f'省 NT${int(self.savings_amount)}',
            'original_price': self.original_price,
            'discount_price': self.discount_price,
            'savings_amount': self.savings_amount,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M') if self.start_date else '',
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M') if self.end_date else '',
            'total_quantity': self.total_quantity,
            'redeemed_count': self.redeemed_count,
            'remaining_quantity': self.remaining_quantity,
            'max_per_user': self.max_per_user,
            'terms_and_conditions': self.terms_and_conditions,
            'is_active': self.is_active,
            'is_valid_now': self.is_valid_now,
            'views_count': self.views_count,
            'clicks_count': self.clicks_count,
            'conversion_rate': self.conversion_rate
        }


class Redemption(db.Model):
    __tablename__ = 'redemptions'

    id = db.Column(db.Integer, primary_key=True)
    redemption_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 紀錄核銷當下為消費者省下的實際金額
    saved_amount = db.Column(db.Float, nullable=False, default=0.0)
    
    redeemed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), default='completed') # 'completed', 'cancelled'
    notes = db.Column(db.String(200), nullable=True)

    @staticmethod
    def generate_code():
        """產生隨機且不易重複的核銷專屬憑證代碼 (例如: CPN-8A2F9B)"""
        return f"CPN-{secrets.token_hex(4).upper()}"

    def to_dict(self):
        return {
            'id': self.id,
            'redemption_code': self.redemption_code,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else '',
            'coupon_id': self.coupon_id,
            'coupon_title': self.coupon.title if self.coupon else '',
            'merchant_name': self.coupon.merchant.brand_name if (self.coupon and self.coupon.merchant) else '',
            'category_name': self.coupon.category.name if (self.coupon and self.coupon.category) else '',
            'saved_amount': self.saved_amount,
            'redeemed_at': self.redeemed_at.strftime('%Y-%m-%d %H:%M:%S') if self.redeemed_at else '',
            'status': self.status
        }
