from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import current_user, login_required
from extensions import db
from models import Coupon, Category, MerchantProfile, Redemption
from decorators import consumer_required

consumer_bp = Blueprint('consumer', __name__)

@consumer_bp.route('/')
def index():
    """
    消費者端首頁：
    垂直聚焦「速食」與「飲料」兩大高頻消費類別，支援分類切換、關鍵字搜尋
    """
    category_slug = request.args.get('category', '').strip()
    search_query = request.args.get('q', '').strip()
    
    # 取得兩大核心垂直分類與全部類別
    categories = Category.query.all()
    
    # 建立優惠券查詢
    query = Coupon.query.filter(Coupon.is_active.is_(True))
    
    selected_category = None
    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug).first()
        if selected_category:
            query = query.filter(Coupon.category_id == selected_category.id)
            
    if search_query:
        query = query.join(MerchantProfile).filter(
            (Coupon.title.ilike(f'%{search_query}%')) |
            (Coupon.description.ilike(f'%{search_query}%')) |
            (MerchantProfile.brand_name.ilike(f'%{search_query}%'))
        )

    # 排序：優先展示未過期且可核銷之熱門優惠
    coupons = query.order_by(Coupon.created_at.desc()).all()
    
    # 行銷數據追蹤：在首頁被渲染曝光的優惠券曝光數 (views_count) +1
    try:
        for c in coupons:
            c.views_count = (c.views_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    # 計算消費者個人錢包摘要 (若已登入)
    user_savings = 0.0
    user_redemptions_count = 0
    if current_user.is_authenticated and current_user.is_consumer:
        user_savings = current_user.get_total_savings()
        user_redemptions_count = current_user.get_redemption_count()

    return render_template(
        'index.html',
        coupons=coupons,
        categories=categories,
        current_category=selected_category,
        search_query=search_query,
        user_savings=user_savings,
        user_redemptions_count=user_redemptions_count,
        now=datetime.utcnow()
    )


@consumer_bp.route('/coupon/<int:coupon_id>')
def coupon_detail(coupon_id):
    """優惠券詳情頁 (含完整使用條款、店家資訊、核銷按鈕)"""
    coupon = Coupon.query.get_or_404(coupon_id)
    
    # 追蹤點擊數與曝光數
    coupon.clicks_count = (coupon.clicks_count or 0) + 1
    coupon.views_count = (coupon.views_count or 0) + 1
    db.session.commit()

    # 檢查當前用戶是否已達領取上限
    user_redeemed_count = 0
    can_redeem = False
    cant_redeem_reason = ""

    if current_user.is_authenticated:
        if current_user.is_consumer:
            user_redeemed_count = Redemption.query.filter_by(
                user_id=current_user.id,
                coupon_id=coupon.id,
                status='completed'
            ).count()

            if not coupon.is_valid_now:
                cant_redeem_reason = "此優惠券目前非有效狀態（可能尚未開始、已過期或已發放完畢）。"
            elif user_redeemed_count >= coupon.max_per_user:
                cant_redeem_reason = f"您已達到此優惠券每人限用 {coupon.max_per_user} 次之上限。"
            else:
                can_redeem = True
        else:
            cant_redeem_reason = "僅一般消費者帳號可進行優惠核銷。"
    else:
        cant_redeem_reason = "請先登入會員以進行核銷。"

    return render_template(
        'consumer/coupon_detail.html',
        coupon=coupon,
        can_redeem=can_redeem,
        cant_redeem_reason=cant_redeem_reason,
        user_redeemed_count=user_redeemed_count,
        now=datetime.utcnow()
    )


@consumer_bp.route('/wallet')
@login_required
@consumer_required
def wallet():
    """
    「我的錢包」省錢追蹤中心：
    - 累計為使用者省下多少錢 ($ NTD)
    - 總核銷張數
    - 視覺化圖表數據 (按月份/按店家分類)
    - 詳細核銷歷程
    """
    user_id = current_user.id
    
    # 取得此使用者的所有成功核銷紀錄
    redemptions = Redemption.query.filter_by(user_id=user_id, status='completed')\
        .order_by(Redemption.redeemed_at.desc()).all()

    # 計算統計數字
    total_savings = sum(r.saved_amount for r in redemptions)
    total_count = len(redemptions)

    # 依分類統計省錢金額 (速食 vs 飲料) 用於圓餅圖
    savings_by_category = {}
    for r in redemptions:
        cat_name = r.coupon.category.name if (r.coupon and r.coupon.category) else '其他'
        savings_by_category[cat_name] = savings_by_category.get(cat_name, 0) + r.saved_amount

    # 依月份趨勢統計 (近 6 個月) 用於折線圖
    savings_by_month = {}
    for r in reversed(redemptions):
        month_key = r.redeemed_at.strftime('%Y-%m')
        savings_by_month[month_key] = savings_by_month.get(month_key, 0) + r.saved_amount

    # 省錢等級稱號
    if total_savings >= 1000:
        badge_title = "👑 省錢宗師"
        badge_desc = "已累計省下破千元！平台超級尊榮省錢王。"
    elif total_savings >= 300:
        badge_title = "⭐ 優惠獵人"
        badge_desc = "精準掌握每次吃喝玩樂的高 CP 優惠！"
    else:
        badge_title = "🌱 小資新星"
        badge_desc = "踏上精打細算的智慧消費第一步！"

    return render_template(
        'consumer/wallet.html',
        redemptions=redemptions,
        total_savings=round(total_savings, 1),
        total_count=total_count,
        savings_by_category=savings_by_category,
        savings_by_month=savings_by_month,
        badge_title=badge_title,
        badge_desc=badge_desc
    )


@consumer_bp.route('/coupon/<int:coupon_id>/redeem', methods=['POST'])
@login_required
@consumer_required
def redeem_coupon(coupon_id):
    """
    執行優惠核銷機制 (嚴格防呆與交易鎖定)：
    1. 驗證登入與身份
    2. 驗證時效 (start_date <= now <= end_date)
    3. 驗證總發行數量 (redeemed_count < total_quantity)
    4. 驗證單一帳號限用次數 (user count < max_per_user)
    5. 建立核銷紀錄並扣抵額度
    """
    coupon = Coupon.query.with_for_update().get_or_404(coupon_id)
    now = datetime.utcnow()

    # 1. 檢查優惠券啟用狀態
    if not coupon.is_active:
        flash('很抱歉，該優惠活動已結束或已暫停。', 'danger')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))

    # 2. 檢查時效 (精確至分秒)
    if now < coupon.start_date:
        flash(f'活動尚未開始！開始時間為：{coupon.start_date.strftime("%Y-%m-%d %H:%M")}', 'warning')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))

    if now > coupon.end_date:
        flash('很抱歉，該優惠券已超過兌換有效期限！', 'danger')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))

    # 3. 檢查總數量上限
    if coupon.redeemed_count >= coupon.total_quantity:
        flash('太可惜了！該優惠券已全數被兌換完畢。', 'danger')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))

    # 4. 檢查每人限用次數
    user_already_redeemed = Redemption.query.filter_by(
        user_id=current_user.id,
        coupon_id=coupon.id,
        status='completed'
    ).count()

    if user_already_redeemed >= coupon.max_per_user:
        flash(f'您已達到此優惠券每人限領 {coupon.max_per_user} 次之限制！', 'warning')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))

    try:
        # 5. 原子交易建立核銷紀錄
        redemption_code = Redemption.generate_code()
        redemption = Redemption(
            redemption_code=redemption_code,
            user_id=current_user.id,
            coupon_id=coupon.id,
            saved_amount=coupon.savings_amount,
            status='completed',
            notes=f'消費者 {current_user.username} 自行透過網頁端核銷'
        )
        
        # 遞增已核銷次數
        coupon.redeemed_count += 1
        
        db.session.add(redemption)
        db.session.commit()

        flash(f'🎉 核銷成功！已為您省下 NT${int(coupon.savings_amount)} 元！憑證代碼：{redemption_code}', 'success')
        return redirect(url_for('consumer.wallet'))

    except Exception as e:
        db.session.rollback()
        flash('系統核銷過程中發生錯誤，請稍後再試。', 'danger')
        return redirect(url_for('consumer.coupon_detail', coupon_id=coupon.id))
