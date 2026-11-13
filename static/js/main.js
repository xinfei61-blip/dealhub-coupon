/**
 * 快省 DealHub 前端互動核心腳本
 * 支援 RESTful 動態抽換優惠列表、即時核銷防抖動、表單驗證
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. 自動計算商家折價金額 (原價 - 特價)
  const origPriceInput = document.getElementById('original_price');
  const discPriceInput = document.getElementById('discount_price');
  const savingsInput = document.getElementById('savings_amount');

  function calculateSavings() {
    if (origPriceInput && discPriceInput && savingsInput) {
      const orig = parseFloat(origPriceInput.value) || 0;
      const disc = parseFloat(discPriceInput.value) || 0;
      if (orig > 0 && disc > 0 && orig > disc) {
        savingsInput.value = (orig - disc).toFixed(1);
      }
    }
  }

  if (origPriceInput && discPriceInput) {
    origPriceInput.addEventListener('input', calculateSavings);
    discPriceInput.addEventListener('input', calculateSavings);
  }

  // 2. 商家建立優惠券日期防呆驗證
  const form = document.querySelector('form.coupon-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      const start = document.getElementById('start_date');
      const end = document.getElementById('end_date');
      if (start && end && start.value && end.value) {
        if (new Date(end.value) <= new Date(start.value)) {
          e.preventDefault();
          alert('結束時間必須晚於開始時間！');
        }
      }
    });
  }
});

/**
 * RESTful 即時核銷視窗觸發 (支援前端 AJAX 無重整核銷)
 */
let currentRedeemCouponId = null;

function openRedeemModal(couponId, title, savings, merchant) {
  currentRedeemCouponId = couponId;
  const modalEl = document.getElementById('quickRedeemModal');
  if (!modalEl) return;

  document.getElementById('modalCouponTitle').innerText = title;
  document.getElementById('modalMerchantName').innerText = merchant;
  document.getElementById('modalSavings').innerText = 'NT$ ' + savings;
  
  // 重設狀態為初始確認畫面
  document.getElementById('redeemConfirmSection').classList.remove('d-none');
  document.getElementById('redeemSuccessSection').classList.add('d-none');
  document.getElementById('redeemErrorAlert').classList.add('d-none');
  
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

/**
 * 執行 AJAX 核銷請求
 */
async function executeRedeem() {
  if (!currentRedeemCouponId) return;

  const btn = document.getElementById('confirmRedeemBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>核銷處理中...';

  const errAlert = document.getElementById('redeemErrorAlert');
  errAlert.classList.add('d-none');

  try {
    const response = await fetch(`/api/v1/coupons/${currentRedeemCouponId}/redeem`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // 成功核銷：切換至憑證顯示畫面
      document.getElementById('redeemConfirmSection').classList.add('d-none');
      document.getElementById('redeemSuccessSection').classList.remove('d-none');
      
      document.getElementById('resultRedemptionCode').innerText = data.redemption.redemption_code;
      document.getElementById('resultSavedAmount').innerText = data.redemption.saved_amount;

      // 更新導航列錢包累積金額
      const navSavingsBadge = document.getElementById('navWalletSavings');
      if (navSavingsBadge && data.wallet) {
        navSavingsBadge.innerText = `NT$ ${data.wallet.total_savings}`;
      }

      // 剩餘額度動態扣減
      const remainBadge = document.getElementById(`remain-qty-${currentRedeemCouponId}`);
      if (remainBadge) {
        const cur = parseInt(remainBadge.innerText) || 0;
        if (cur > 0) remainBadge.innerText = cur - 1;
      }
    } else {
      // 失敗或權限未符合
      errAlert.innerText = data.message || '核銷未成功，請確認限制條件。';
      errAlert.classList.remove('d-none');
    }
  } catch (err) {
    console.error(err);
    errAlert.innerText = '連線失敗或伺服器異常，請重新再試。';
    errAlert.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '確認核銷並享受折扣';
  }
}
