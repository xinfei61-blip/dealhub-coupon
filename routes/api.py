from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user
from extensions import db
from models import Coupon, Category, MerchantProfile, Redemption, User
from decorators import role_required

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """取得所有垂直分類清單與各分類目前活躍優惠券數量"""
    categories = Category.query.all()
    results = []
    for cat in categories:
        active_count = cat.coupons.filter(Coupon.is_active.is_(True)).count()
        data = cat.to_dict()
        data['active_coupons_count'] = active_count
        results.append(data)
    return jsonify({'success': True, 'categories': results})


@api_bp.route('/coupons', methods=['GET'])
def get_coupons():
    """
    RESTful 優惠券列表 API (支援前端無重整動態抽換與未來 App 底層)：
    支援分類過濾 (?category=fastfood 或 ?category=速食)、關鍵字搜尋 (?q=漢堡)
    """
    category_param = request.args.get('category', '').strip()
    search_param = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest')

    query = Coupon.query.filter(Coupon.is_active.is_(True))

    if category_param:
        cat = Category.query.filter(
            (Category.slug == category_param) | (Category.name == category_param)
        ).first()
        if cat:
            query = query.filter(Coupon.category_id == cat.id)

    if search_param:
        query = query.join(MerchantProfile).filter(
            (Coupon.title.ilike(f'%{search_param}%')) |
            (Coupon.description.ilike(f'%{search_param}%')) |
            (MerchantProfile.brand_name.ilike(f'%{search_param}%'))
        )

    if sort_by == 'savings':
        query = query.order_by(Coupon.savings_amount.desc())
    elif sort_by == 'popular':
        query = query.order_by(Coupon.redeemed_count.desc())
    else:
        query = query.order_by(Coupon.created_at.desc())

    coupons = query.all()

    # 批次遞增曝光數 (Views Count) 供行銷資料科學統計
    try:
        for c in coupons:
            c.views_count = (c.views_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({
        'success': True,
        'count': len(coupons),
        'coupons': [c.to_dict() for c in coupons]
    })


@api_bp.route('/coupons/<int:coupon_id>', methods=['GET'])
def get_coupon_detail(coupon_id):
    """單一優惠券詳情 API (點擊計數 +1)"""
    coupon = Coupon.query.get_or_404(coupon_id)
    
    # 遞增點擊數
    coupon.clicks_count = (coupon.clicks_count or 0) + 1
    db.session.commit()

    return jsonify({
        'success': True,
        'coupon': coupon.to_dict()
    })


@api_bp.route('/coupons/<int:coupon_id>/redeem', methods=['POST'])
def api_redeem(coupon_id):
    """
    RESTful 即時核銷 API：
    提供前端非同步 AJAX 呼叫或未來手機 App 點擊核銷：
    具備嚴格的時效控管、限量總額防超領與每人限領次數檢核。
    """
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'code': 'AUTH_REQUIRED',
            'message': '請先登入消費者帳號以執行核銷！'
        }), 401

    if not current_user.is_consumer and not current_user.is_admin:
        return jsonify({
            'success': False,
            'code': 'FORBIDDEN_ROLE',
            'message': '僅消費者身份可進行核銷。'
        }), 403

    coupon = Coupon.query.with_for_update().get_or_404(coupon_id)
    now = datetime.utcnow()

    # 1. 活動有效狀態
    if not coupon.is_active:
        return jsonify({'success': False, 'message': '該優惠活動目前已停用或已結束。'}), 400

    # 2. 時效控管
    if now < coupon.start_date:
        return jsonify({
            'success': False,
            'message': f'活動尚未開始，開始時間為：{coupon.start_date.strftime("%Y-%m-%d %H:%M")}'
        }), 400

    if now > coupon.end_date:
        return jsonify({'success': False, 'message': '該優惠券已逾期無效！'}), 400

    # 3. 數量控管 (總量)
    if coupon.redeemed_count >= coupon.total_quantity:
        return jsonify({'success': False, 'message': '名額已滿！該優惠券已全數被兌換完畢。'}), 400

    # 4. 數量控管 (單人限制)
    user_redeemed_count = Redemption.query.filter_by(
        user_id=current_user.id,
        coupon_id=coupon.id,
        status='completed'
    ).count()

    if user_redeemed_count >= coupon.max_per_user:
        return jsonify({
            'success': False,
            'message': f'已達每人限領次數上限 ({coupon.max_per_user} 次)！'
        }), 400

    try:
        # 5. 原子交易核銷
        code = Redemption.generate_code()
        redemption = Redemption(
            redemption_code=code,
            user_id=current_user.id,
            coupon_id=coupon.id,
            saved_amount=coupon.savings_amount,
            status='completed',
            notes='RESTful API 成功核銷'
        )
        coupon.redeemed_count += 1
        db.session.add(redemption)
        db.session.commit()

        # 重新計算錢包最新統計
        total_savings = current_user.get_total_savings()
        redemption_count = current_user.get_redemption_count()

        return jsonify({
            'success': True,
            'message': f'🎉 核銷成功！已為您省下 NT${int(coupon.savings_amount)} 元！',
            'redemption': redemption.to_dict(),
            'wallet': {
                'total_savings': total_savings,
                'redemption_count': redemption_count
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'核銷處理失敗: {str(e)}'}), 500


@api_bp.route('/wallet', methods=['GET'])
def get_wallet():
    """消費者「我的錢包」即時省錢數據 API"""
    if not current_user.is_authenticated or not current_user.is_consumer:
        return jsonify({'success': False, 'message': '請先登入消費者帳號'}), 401

    redemptions = Redemption.query.filter_by(user_id=current_user.id, status='completed')\
        .order_by(Redemption.redeemed_at.desc()).all()

    total_savings = sum(r.saved_amount for r in redemptions)
    
    # 依垂直分類統計
    savings_by_category = {}
    for r in redemptions:
        c_name = r.coupon.category.name if (r.coupon and r.coupon.category) else '其他'
        savings_by_category[c_name] = savings_by_category.get(c_name, 0) + r.saved_amount

    return jsonify({
        'success': True,
        'wallet': {
            'total_savings': round(total_savings, 1),
            'redemptions_count': len(redemptions),
            'savings_by_category': savings_by_category,
            'history': [r.to_dict() for r in redemptions]
        }
    })


@api_bp.route('/merchant/analytics', methods=['GET'])
def get_merchant_analytics():
    """商家商業數據儀表板 API (行銷資料科學指標)"""
    if not current_user.is_authenticated or not current_user.is_merchant:
        return jsonify({'success': False, 'message': '請先登入商家帳號'}), 401

    merchant = current_user.merchant_profile
    if not merchant:
        return jsonify({'success': False, 'message': '尚未建立商家檔案'}), 400

    coupons = Coupon.query.filter_by(merchant_id=merchant.id).all()
    
    total_views = sum(c.views_count or 0 for c in coupons)
    total_clicks = sum(c.clicks_count or 0 for c in coupons)
    total_redemptions = sum(c.redeemed_count or 0 for c in coupons)
    
    conversion_rate = round((total_redemptions / total_views * 100), 2) if total_views > 0 else 0.0
    ctr = round((total_clicks / total_views * 100), 2) if total_views > 0 else 0.0

    return jsonify({
        'success': True,
        'merchant_name': merchant.brand_name,
        'metrics': {
            'total_views': total_views,
            'total_clicks': total_clicks,
            'total_redemptions': total_redemptions,
            'conversion_rate': conversion_rate,
            'ctr': ctr
        },
        'coupons': [c.to_dict() for c in coupons]
    })
