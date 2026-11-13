@echo off
chcp 65001 >nul
title 快省 DealHub 優惠券平台
echo =================================================================
echo  🚀 正在啟動 DealHub 餐飲優惠平台...
echo  🌐 瀏覽器開啟網址: http://127.0.0.1:5000
echo  💡 按 Ctrl + C 即可停止伺服器
echo =================================================================
cd /d "C:\Users\xinfe\.gemini\antigravity\scratch\coupon_platform"
"C:\Users\xinfe\AppData\Local\Programs\Python\Python312\python.exe" app.py
pause
