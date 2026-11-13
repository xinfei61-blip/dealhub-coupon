from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import current_user, login_required
from extensions import db
from models import Coupon, Category, MerchantProfile, Redemption
from decorators import merchant_required

merchant_bp = Blueprint('merchant', __name__, url_prefix='/merchant')

@merchant_bp.route('/')
@merchant_bp.route('/dashboard')
@login_required
@merchant_required
def dashboard():
    """
    商業數據儀表板：
    行銷資料科學數據量化核心：
    - 總曝光數 (Views)
    - 總點擊數 (Clicks)
    - 總核銷數 (Redemptions)
    - 整體轉換率 (Conversion Rate % = Redemptions / Views * 100)
    - 點擊率 (CTR % = Clicks / Views * 100)
    - 總共為顧客省下的金額 (Total Customer Savings)
    - 優惠活動數據漏斗與長條圖
    """
    merchant = current_user.merchant_profile
    if not merchant:
        flash('請先完成商家品牌檔案設定。', 'warning')
        return redirect(url_for('merchant.profile'))

    coupons = Coupon.query.filter_by(merchant_id=merchant.id)\
        .order_by(Coupon.created_at.desc()).all()

    # 聚合整體指標
    total_views = sum(c.views_count or 0 for c in coupons)
    total_clicks = sum(c.clicks_count or 0 for c in coupons)
    total_redemptions = sum(c.redeemed_count or 0 for c in coupons)
    total_savings_generated = sum((c.redeemed_count or 0) * (c.savings_amount or 0) for c in coupons)

    overall_conversion_rate = round((total_redemptions / total_views * 100), 2) if total_views > 0 else 0.0
    overall_ctr = round((total_clicks / total_views * 100), 2) if total_views > 0 else 0.0

    # 圖表資料準備：各優惠券之曝光 vs 核銷成效 (Top 5 活動)
    chart_labels = [c.title[:12] + ('...' if len(c.title) > 12 else '') for c in coupons[:6]]
    chart_views = [c.views_count or 0 for c in coupons[:6]]
    chart_redemptions = [c.redeemed_count or 0 for c in coupons[:6]]
    chart_conv_rates = [c.conversion_rate for c in coupons[:6]]

    return render_template(
        'merchant/dashboard.html',
        merchant=merchant,
        coupons=coupons,
        total_views=total_views,
        total_clicks=total_clicks,
        total_redemptions=total_redemptions,
        total_savings_generated=round(total_savings_generated, 1),
        overall_conversion_rate=overall_conversion_rate,
        overall_ctr=overall_ctr,
        chart_labels=chart_labels,
        chart_views=chart_views,
        chart_redemptions=chart_redemptions,
        chart_conv_rates=chart_conv_rates
    )


@merchant_bp.route('/coupons')
@login_required
@merchant_required
def coupon_list():
    """商家優惠券管理清單"""
    merchant = current_user.merchant_profile
    if not merchant:
        return redirect(url_for('merchant.profile'))

    coupons = Coupon.query.filter_by(merchant_id=merchant.id)\
        .order_by(Coupon.created_at.desc()).all()

    return render_template('merchant/coupons.html', merchant=merchant, coupons=coupons, now=datetime.utcnow())


@merchant_bp.route('/coupons/new', methods=['GET', 'POST'])
@login_required
@merchant_required
def create_coupon():
    """
    發行新優惠券：
    包含完整的限制機制設定（時效、發行上限、每人次數、條款備註）
    """
    merchant = current_user.merchant_profile
    categories = Category.query.all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()
        image_url = request.form.get('image_url', '').strip()
        discount_tag = request.form.get('discount_tag', '').strip()

        original_price = request.form.get('original_price', type=float, default=0.0)
        discount_price = request.form.get('discount_price', type=float, default=0.0)
        savings_amount = request.form.get('savings_amount', type=float)

        # 自動依原價與特價推算省下金額（若未手動填寫）
        if savings_amount is None or savings_amount <= 0:
            if original_price > discount_price:
                savings_amount = original_price - discount_price
            else:
                savings_amount = 0.0

        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        total_quantity = request.form.get('total_quantity', type=int, default=100)
        max_per_user = request.form.get('max_per_user', type=int, default=1)
        terms = request.form.get('terms_and_conditions', '').strip()

        # 基本防呆驗證
        if not title or not category_id or not start_date_str or not end_date_str:
            flash('請填寫完整之活動標題、垂直分類與有效起迄時間。', 'warning')
            return render_template('merchant/coupon_form.html', categories=categories, coupon=None)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('日期時間格式不正確，請依格式選取。', 'danger')
            return render_template('merchant/coupon_form.html', categories=categories, coupon=None)

        if end_date <= start_date:
            flash('結束時間必須晚於開始時間！', 'danger')
            return render_template('merchant/coupon_form.html', categories=categories, coupon=None)

        coupon = Coupon(
            merchant_id=merchant.id,
            category_id=category_id,
            title=title,
            description=description,
            image_url=image_url or 'https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&auto=format&fit=crop&q=60',
            discount_tag=discount_tag or f'現省 ${int(savings_amount)}',
            original_price=original_price,
            discount_price=discount_price,
            savings_amount=savings_amount,
            start_date=start_date,
            end_date=end_date,
            total_quantity=total_quantity,
            max_per_user=max_per_user,
            terms_and_conditions=terms or '1. 限內用或外帶自取。\n2. 不得與其他優惠併用。\n3. 請於點餐前出示核銷代碼。',
            is_active=True
        )

        db.session.add(coupon)
        db.session.commit()

        flash('優惠券發行成功！已立即於平台上下架生效。', 'success')
        return redirect(url_for('merchant.coupon_list'))

    return render_template('merchant/coupon_form.html', categories=categories, coupon=None)


@merchant_bp.route('/coupons/<int:coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@merchant_required
def edit_coupon(coupon_id):
    """編輯優惠券資訊與限制機制"""
    merchant = current_user.merchant_profile
    coupon = Coupon.query.filter_by(id=coupon_id, merchant_id=merchant.id).first_or_404()
    categories = Category.query.all()

    if request.method == 'POST':
        coupon.title = request.form.get('title', '').strip()
        coupon.category_id = request.form.get('category_id', type=int)
        coupon.description = request.form.get('description', '').strip()
        coupon.image_url = request.form.get('image_url', '').strip() or coupon.image_url
        coupon.discount_tag = request.form.get('discount_tag', '').strip()
        coupon.original_price = request.form.get('original_price', type=float, default=0.0)
        coupon.discount_price = request.form.get('discount_price', type=float, default=0.0)
        coupon.savings_amount = request.form.get('savings_amount', type=float, default=coupon.savings_amount)
        
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        if start_date_str and end_date_str:
            coupon.start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            coupon.end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

        coupon.total_quantity = request.form.get('total_quantity', type=int, default=coupon.total_quantity)
        coupon.max_per_user = request.form.get('max_per_user', type=int, default=coupon.max_per_user)
        coupon.terms_and_conditions = request.form.get('terms_and_conditions', '').strip()
        coupon.is_active = bool(request.form.get('is_active'))

        db.session.commit()
        flash('優惠券資訊已成功更新！', 'success')
        return redirect(url_for('merchant.coupon_list'))

    return render_template('merchant/coupon_form.html', categories=categories, coupon=coupon)


@merchant_bp.route('/coupons/<int:coupon_id>/toggle', methods=['POST'])
@login_required
@merchant_required
def toggle_coupon(coupon_id):
    """快速切換優惠券啟用/暫停狀態"""
    merchant = current_user.merchant_profile
    coupon = Coupon.query.filter_by(id=coupon_id, merchant_id=merchant.id).first_or_404()
    coupon.is_active = not coupon.is_active
    db.session.commit()
    status_text = "已上架" if coupon.is_active else "已下架暫停"
    flash(f'活動「{coupon.title}」狀態已變更為：{status_text}', 'info')
    return redirect(url_for('merchant.coupon_list'))


@merchant_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@merchant_required
def profile():
    """商家品牌檔案管理 (Logo, 品牌名稱, 簡介, 垂直類別, 聯絡方式)"""
    merchant = current_user.merchant_profile
    if not merchant:
        merchant = MerchantProfile(user_id=current_user.id, brand_name=f"{current_user.username} 品牌")
        db.session.add(merchant)
        db.session.commit()

    if request.method == 'POST':
        merchant.brand_name = request.form.get('brand_name', '').strip()
        merchant.logo_url = request.form.get('logo_url', '').strip()
        merchant.description = request.form.get('description', '').strip()
        merchant.category_name = request.form.get('category_name', '速食')
        merchant.contact_email = request.form.get('contact_email', '').strip()
        merchant.phone = request.form.get('phone', '').strip()
        merchant.address = request.form.get('address', '').strip()

        db.session.commit()
        flash('品牌資料已順利更新儲存！', 'success')
        return redirect(url_for('merchant.profile'))

    return render_template('merchant/profile.html', merchant=merchant)
