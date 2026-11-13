from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import User, MerchantProfile, Coupon, Redemption, Category
from decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    平台最高管理員總覽數據中心：
    - 全平台總用戶數 (分消費者與商家)
    - 全平台發行中與總優惠券數
    - 全平台總核銷紀錄與總累積省下金額
    - 商家列表與審核狀態
    - 全平台最新核銷串流流水號
    """
    total_users = User.query.count()
    total_consumers = User.query.filter_by(role='consumer').count()
    total_merchants = User.query.filter_by(role='merchant').count()
    
    total_coupons = Coupon.query.count()
    active_coupons = Coupon.query.filter_by(is_active=True).count()
    
    total_redemptions = Redemption.query.filter_by(status='completed').count()
    platform_total_savings = db.session.query(db.func.sum(Redemption.saved_amount))\
        .filter(Redemption.status == 'completed').scalar() or 0.0

    merchants = MerchantProfile.query.order_by(MerchantProfile.created_at.desc()).all()
    recent_redemptions = Redemption.query.order_by(Redemption.redeemed_at.desc()).limit(15).all()
    all_users = User.query.order_by(User.created_at.desc()).limit(20).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_consumers=total_consumers,
        total_merchants=total_merchants,
        total_coupons=total_coupons,
        active_coupons=active_coupons,
        total_redemptions=total_redemptions,
        platform_total_savings=round(platform_total_savings, 1),
        merchants=merchants,
        recent_redemptions=recent_redemptions,
        all_users=all_users
    )


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    """RBAC 角色動態指派與權限變更"""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['consumer', 'merchant', 'admin']:
        flash('無效之角色名稱！', 'danger')
        return redirect(url_for('admin.dashboard'))

    # 防止管理員誤取消自己的 admin 權限
    if user.id == current_user.id and new_role != 'admin':
        flash('為確保系統安全，您無法變更自己的管理員身份！', 'warning')
        return redirect(url_for('admin.dashboard'))

    user.role = new_role
    
    # 若轉為商家但尚無 profile，自動補建
    if new_role == 'merchant' and not user.merchant_profile:
        profile = MerchantProfile(
            user_id=user.id,
            brand_name=f"{user.username} 的品牌店",
            category_name='速食',
            contact_email=user.email
        )
        db.session.add(profile)

    db.session.commit()
    flash(f'使用者 {user.username} 之權限身份已成功變更為：{new_role}', 'success')
    return redirect(url_for('admin.dashboard'))
