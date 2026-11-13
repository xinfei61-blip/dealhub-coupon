import os
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, MerchantProfile, Category, Coupon, Redemption

app = create_app()

def seed(drop=True):
    with app.app_context():
        if drop:
            print("🌱 正在重置資料庫與預設假資料...")
            db.drop_all()
        db.create_all()

        # 若已存在分類資料且非強制重置，則略過
        if not drop and Category.query.first():
            return

        # 1. 建立兩大核心垂直分類 (聚焦速食與飲料)
        fastfood_cat = Category(
            name='速食',
            slug='fastfood',
            icon='bi-egg-fried',
            description='漢堡、炸雞、薯條等高頻熱門連鎖速食餐廳專屬優惠'
        )
        beverage_cat = Category(
            name='飲料',
            slug='beverage',
            icon='bi-cup-straw',
            description='手搖飲、手作鮮果茶、醇厚拿鐵等每日下午茶必備好康'
        )
        db.session.add_all([fastfood_cat, beverage_cat])
        db.session.flush()

        # 2. 建立 RBAC 系統帳號
        # 平台管理員 (Admin)
        admin_user = User(username='admin', email='admin@dealhub.com', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)

        # 測試消費者 (Consumer)
        demo_consumer = User(username='user_demo', email='demo@dealhub.com', role='consumer')
        demo_consumer.set_password('user123')
        
        consumer2 = User(username='alex_foodie', email='alex@dealhub.com', role='consumer')
        consumer2.set_password('alex123')
        db.session.add_all([demo_consumer, consumer2])
        db.session.flush()

        # 商家帳號 (Merchants)
        merchants_data = [
            {
                'username': 'mcd_tw',
                'email': 'mcd@dealhub.com',
                'password': 'mcd123',
                'brand_name': '麥當勞 McDonald\'s',
                'category_name': '速食',
                'logo_url': 'https://images.unsplash.com/photo-1552566626-52f8b828add9?w=150&auto=format&fit=crop&q=80',
                'description': '全球知名連鎖速食品牌，提供經典大麥克、金黃薯條與麥克鷄塊。',
                'phone': '0800-211-321',
                'address': '全台門市適用'
            },
            {
                'username': 'kfc_tw',
                'email': 'kfc@dealhub.com',
                'password': 'kfc123',
                'brand_name': '肯德基 KFC',
                'category_name': '速食',
                'logo_url': 'https://images.unsplash.com/photo-1513639776629-7b61b0ac49cb?w=150&auto=format&fit=crop&q=80',
                'description': '經典咔啦脆雞、吮指嫩雞與香濃原味蛋撻，炸雞愛好者的第一選擇。',
                'phone': '0800-068-007',
                'address': '全台門市適用'
            },
            {
                'username': 'burgerking_tw',
                'email': 'bk@dealhub.com',
                'password': 'bk123',
                'brand_name': '漢堡王 Burger King',
                'category_name': '速食',
                'logo_url': 'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=150&auto=format&fit=crop&q=80',
                'description': '火烤純牛肉漢堡權威，經典華堡多汁飽滿，獨家美味令人回味無窮。',
                'phone': '0800-251-281',
                'address': '全台門市適用'
            },
            {
                'username': 'milksha_tw',
                'email': 'milksha@dealhub.com',
                'password': 'milksha123',
                'brand_name': '迷客夏 Milksha',
                'category_name': '飲料',
                'logo_url': 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=150&auto=format&fit=crop&q=80',
                'description': '堅持使用綠光牧場鮮奶，招牌珍珠紅茶拿鐵與大甲芋頭鮮奶深受喜愛。',
                'phone': '06-200-8800',
                'address': '全台指定門市'
            },
            {
                'username': 'macu_tw',
                'email': 'macu@dealhub.com',
                'password': 'macu123',
                'brand_name': '麻古茶坊 MACU',
                'category_name': '飲料',
                'logo_url': 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=150&auto=format&fit=crop&q=80',
                'description': '鮮果手搖引領潮流，芝芝芒果果粒、柳橙果粒茶新鮮現榨口感絕佳。',
                'phone': '0800-888-888',
                'address': '全台指定門市'
            },
            {
                'username': '50lan_tw',
                'email': '50lan@dealhub.com',
                'password': '50lan123',
                'brand_name': '50嵐',
                'category_name': '飲料',
                'logo_url': 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=150&auto=format&fit=crop&q=80',
                'description': '台灣老牌經典手搖品牌，四季春珍波椰（1號）與黃金烏龍茶香四溢。',
                'phone': '02-2345-6789',
                'address': '全台門市適用'
            }
        ]

        merchant_objects = {}
        for m_data in merchants_data:
            user = User(username=m_data['username'], email=m_data['email'], role='merchant')
            user.set_password(m_data['password'])
            db.session.add(user)
            db.session.flush()

            profile = MerchantProfile(
                user_id=user.id,
                brand_name=m_data['brand_name'],
                category_name=m_data['category_name'],
                logo_url=m_data['logo_url'],
                description=m_data['description'],
                phone=m_data['phone'],
                address=m_data['address'],
                contact_email=m_data['email']
            )
            db.session.add(profile)
            db.session.flush()
            merchant_objects[m_data['username']] = profile

        # 3. 建立代表性優惠券 (含時效、數量、每人限用、條款規範與行銷資料科學數據)
        now = datetime.utcnow()
        coupons_data = [
            {
                'merchant': merchant_objects['mcd_tw'],
                'category': fastfood_cat,
                'title': '經典大麥克套餐現折 $30 優惠券',
                'description': '包含雙層純牛肉大麥克漢堡 + 中包金黃薯條 + 中杯可口可樂。',
                'image_url': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '現折 $30',
                'original_price': 140.0,
                'discount_price': 110.0,
                'savings_amount': 30.0,
                'start_date': now - timedelta(days=5),
                'end_date': now + timedelta(days=25),
                'total_quantity': 200,
                'redeemed_count': 42,
                'max_per_user': 1,
                'terms': '1. 本券限於全台麥當勞餐廳櫃檯出示核銷代碼使用。\n2. 得來速與歡樂送外送服務不適用。\n3. 本優惠不得與其他折價券或學生專案併用。',
                'views_count': 420,
                'clicks_count': 85
            },
            {
                'merchant': merchant_objects['kfc_tw'],
                'category': fastfood_cat,
                'title': '咔啦脆雞 2 塊 + 蛋撻 1 顆超值獨享餐',
                'description': '現炸金黃酥脆咔啦脆雞兩塊，搭配肯德基香濃原味蛋撻一顆。',
                'image_url': 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '現省 $45',
                'original_price': 155.0,
                'discount_price': 110.0,
                'savings_amount': 45.0,
                'start_date': now - timedelta(days=3),
                'end_date': now + timedelta(days=30),
                'total_quantity': 150,
                'redeemed_count': 55,
                'max_per_user': 2,
                'terms': '1. 需主動向門市結帳人員出示核銷序號畫面。\n2. 部份特殊門市（機場、台鐵）恕不提供兌換。\n3. 每筆交易限核銷一張。',
                'views_count': 490,
                'clicks_count': 110
            },
            {
                'merchant': merchant_objects['burgerking_tw'],
                'category': fastfood_cat,
                'title': '經典火烤安格斯厚牛堡買一送一',
                'description': '厚實三倍厚切澳洲安格斯黑牛，真火直火炙燒，香氣撲鼻。',
                'image_url': 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '買一送一',
                'original_price': 145.0,
                'discount_price': 72.5,
                'savings_amount': 72.5,
                'start_date': now - timedelta(days=2),
                'end_date': now + timedelta(days=14),
                'total_quantity': 80,
                'redeemed_count': 61,
                'max_per_user': 1,
                'terms': '1. 限週一至週五平日 14:00 - 17:00 使用。\n2. 不得更換其他品項漢堡。\n3. 單一會員帳號限領用乙次。',
                'views_count': 680,
                'clicks_count': 160
            },
            {
                'merchant': merchant_objects['milksha_tw'],
                'category': beverage_cat,
                'title': '招牌珍珠紅茶拿鐵 (大杯) 現省 $15',
                'description': '綠光牧場鮮奶佐阿薩姆原葉紅茶，搭上白玉蜂蜜珍珠軟 Q 順口。',
                'image_url': 'https://images.unsplash.com/photo-1558857563-b37df2dd319a?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '現折 $15',
                'original_price': 65.0,
                'discount_price': 50.0,
                'savings_amount': 15.0,
                'start_date': now - timedelta(days=7),
                'end_date': now + timedelta(days=21),
                'total_quantity': 300,
                'redeemed_count': 88,
                'max_per_user': 2,
                'terms': '1. 限購買大杯珍珠紅茶拿鐵適用，可客製甜度與冰塊。\n2. 限現場門市點餐，電話外送不適用。\n3. 結帳時請主動出示核銷序號。',
                'views_count': 720,
                'clicks_count': 180
            },
            {
                'merchant': merchant_objects['macu_tw'],
                'category': beverage_cat,
                'title': '芝芝芒果果粒第二杯半價券',
                'description': '台灣在地愛文芒果新鮮冰沙打底，淋上紐西蘭起司芝芝奶蓋。',
                'image_url': 'https://images.unsplash.com/photo-1546173159-315724a31696?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '第二杯半價',
                'original_price': 95.0,
                'discount_price': 71.0,
                'savings_amount': 24.0,
                'start_date': now - timedelta(days=4),
                'end_date': now + timedelta(days=18),
                'total_quantity': 120,
                'redeemed_count': 39,
                'max_per_user': 1,
                'terms': '1. 限一次購買同品項兩杯，其中一杯享有半價優惠。\n2. 每日限量供應，若當日芒果果粒完售需另行擇日兌換。\n3. 不得與環保杯折扣重複抵扣。',
                'views_count': 410,
                'clicks_count': 92
            },
            {
                'merchant': merchant_objects['50lan_tw'],
                'category': beverage_cat,
                'title': '四季春珍波椰 (大杯) 免費升級折 $15',
                'description': '招牌 1 號！茶香清新回甘的四季春，加入滿滿波霸、珍珠與椰果。',
                'image_url': 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80',
                'discount_tag': '超值省 $15',
                'original_price': 50.0,
                'discount_price': 35.0,
                'savings_amount': 15.0,
                'start_date': now - timedelta(days=6),
                'end_date': now + timedelta(days=28),
                'total_quantity': 250,
                'redeemed_count': 74,
                'max_per_user': 1,
                'terms': '1. 限 50 嵐全台街邊門市適用。\n2. 限現場點單並出示手機核銷條碼。\n3. 恕不折換現金。',
                'views_count': 610,
                'clicks_count': 140
            }
        ]

        created_coupons = []
        for c_data in coupons_data:
            c = Coupon(
                merchant_id=c_data['merchant'].id,
                category_id=c_data['category'].id,
                title=c_data['title'],
                description=c_data['description'],
                image_url=c_data['image_url'],
                discount_tag=c_data['discount_tag'],
                original_price=c_data['original_price'],
                discount_price=c_data['discount_price'],
                savings_amount=c_data['savings_amount'],
                start_date=c_data['start_date'],
                end_date=c_data['end_date'],
                total_quantity=c_data['total_quantity'],
                redeemed_count=c_data['redeemed_count'],
                max_per_user=c_data['max_per_user'],
                terms_and_conditions=c_data['terms'],
                is_active=True,
                views_count=c_data['views_count'],
                clicks_count=c_data['clicks_count']
            )
            db.session.add(c)
            created_coupons.append(c)

        db.session.flush()

        # 4. 為測試消費者 (user_demo) 注入幾筆已核銷紀錄以展示「我的錢包」省錢視覺化成就感
        demo_redemptions = [
            {
                'coupon': created_coupons[0], # 麥當勞折 30
                'amount': 30.0,
                'days_ago': 4
            },
            {
                'coupon': created_coupons[1], # 肯德基省 45
                'amount': 45.0,
                'days_ago': 2
            },
            {
                'coupon': created_coupons[3], # 迷客夏省 15
                'amount': 15.0,
                'days_ago': 1
            },
            {
                'coupon': created_coupons[4], # 麻古省 24
                'amount': 24.0,
                'days_ago': 0
            }
        ]

        for r_item in demo_redemptions:
            redemption = Redemption(
                redemption_code=Redemption.generate_code(),
                user_id=demo_consumer.id,
                coupon_id=r_item['coupon'].id,
                saved_amount=r_item['amount'],
                redeemed_at=now - timedelta(days=r_item['days_ago']),
                status='completed',
                notes='歷史核銷成功示範'
            )
            db.session.add(redemption)

        db.session.commit()
        print("✅ 測試資料植入成功！")
        print("-----------------------------------------------------------------")
        print("📋 預設帳號與密碼清單：")
        print(" 1. 平台管理員 (Admin)   : admin@dealhub.com / admin123")
        print(" 2. 麥當勞商家 (Merchant): mcd@dealhub.com   / mcd123")
        print(" 3. 肯德基商家 (Merchant): kfc@dealhub.com   / kfc123")
        print(" 4. 迷客夏商家 (Merchant): milksha@dealhub.com / milksha123")
        print(" 5. 一般消費者 (Consumer): demo@dealhub.com  / user123 (已具備錢包省錢紀錄)")
        print("-----------------------------------------------------------------")

if __name__ == '__main__':
    seed()
