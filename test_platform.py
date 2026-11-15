import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import create_app
from extensions import db
from models import User, Coupon, Redemption

def test_platform():
    app = create_app()
    client = app.test_client()

    print("🔍 [1/7] 測試首頁與垂直分類 (速食 & 飲料)...")
    res = client.get('/')
    assert res.status_code == 200
    assert '鈔捷徑' in res.data.decode('utf-8')
    assert '速食專區' in res.data.decode('utf-8')
    assert '手搖飲料' in res.data.decode('utf-8')
    print("   ✅ 首頁渲染成功！")

    print("🔍 [2/7] 測試 RESTful API /api/v1/coupons...")
    res = client.get('/api/v1/coupons?category=fastfood')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert len(json_data['coupons']) > 0
    print(f"   ✅ API 成功回傳 {len(json_data['coupons'])} 檔速食優惠券！")

    print("🔍 [3/7] 測試消費者登入與我的錢包...")
    # 登入 demo 消費者
    login_res = client.post('/auth/login', data={
        'login_input': 'demo@dealhub.com',
        'password': 'user123'
    }, follow_redirects=True)
    assert login_res.status_code == 200

    wallet_res = client.get('/wallet')
    assert wallet_res.status_code == 200
    assert '我的省錢錢包' in wallet_res.data.decode('utf-8')
    print("   ✅ 消費者登入與錢包頁面渲染成功！")

    print("🔍 [4/7] 測試 RESTful 核銷 API 與每人限額防呆...")
    with app.app_context():
        user = User.query.filter_by(email='demo@dealhub.com').first()
        redeemed_ids = [r.coupon_id for r in Redemption.query.filter_by(user_id=user.id).all()]
        available_coupon = Coupon.query.filter(~Coupon.id.in_(redeemed_ids), Coupon.is_active == True).first()
        available_id = available_coupon.id
        title = available_coupon.title

    # 1. 成功核銷尚未領取的優惠券
    redeem_res = client.post(f'/api/v1/coupons/{available_id}/redeem')
    print("   Response status:", redeem_res.status_code, redeem_res.get_json())
    assert redeem_res.status_code == 200
    redeem_json = redeem_res.get_json()
    assert redeem_json['success'] is True
    print(f"   ✅ 「{title}」首次核銷成功！代碼: {redeem_json['redemption']['redemption_code']}，現省 NT${redeem_json['redemption']['saved_amount']}")

    # 2. 測試每人限領 1 次防呆機制 (再次核銷同一張應被拒絕)
    retry_res = client.post(f'/api/v1/coupons/{available_id}/redeem')
    assert retry_res.status_code == 400
    retry_json = retry_res.get_json()
    assert retry_json['success'] is False
    print(f"   ✅ 防呆機制成功觸發！回應: {retry_json['message']}")

    print("🔍 [5/7] 測試商家登入與商業數據儀表板 (行銷資料科學)...")
    client.get('/auth/logout', follow_redirects=True)
    m_login = client.post('/auth/login', data={
        'login_input': 'mcd@dealhub.com',
        'password': 'mcd123'
    }, follow_redirects=True)
    assert m_login.status_code == 200

    dash_res = client.get('/merchant/dashboard')
    assert dash_res.status_code == 200
    assert '商業數據儀表板' in dash_res.data.decode('utf-8')
    assert '總曝光次數' in dash_res.data.decode('utf-8')
    assert '整體轉換率' in dash_res.data.decode('utf-8')

    analytics_api = client.get('/api/v1/merchant/analytics')
    assert analytics_api.status_code == 200
    a_json = analytics_api.get_json()
    assert a_json['success'] is True
    print(f"   ✅ 麥當勞商家儀表板成功載入！總曝光: {a_json['metrics']['total_views']}, 轉換率: {a_json['metrics']['conversion_rate']}%")

    print("🔍 [6/7] 測試平台最高管理員總控台 (RBAC 防越權)...")
    client.get('/auth/logout', follow_redirects=True)
    a_login = client.post('/auth/login', data={
        'login_input': 'admin@dealhub.com',
        'password': 'admin123'
    }, follow_redirects=True)
    assert a_login.status_code == 200

    admin_res = client.get('/admin/dashboard')
    assert admin_res.status_code == 200
    assert 'RBAC 最高權限核心' in admin_res.data.decode('utf-8')
    assert '全平台總會員數' in admin_res.data.decode('utf-8')
    print("   ✅ 平台管理員 RBAC 總控台驗證通過！")

    print("🔍 [7/7] 測試未授權防護 (RBAC Security Guard)...")
    client.get('/auth/logout', follow_redirects=True)
    # 訪客直接存取商家或管理員頁面應被擋下
    guard_res = client.get('/merchant/dashboard', follow_redirects=True)
    assert '請先登入帳號' in guard_res.data.decode('utf-8')
    print("   ✅ RBAC 權限攔截防護機制正常運作！")

    print("\n🎉 平台所有 7 項核心功能與架構測試全數通過！")

if __name__ == '__main__':
    test_platform()
