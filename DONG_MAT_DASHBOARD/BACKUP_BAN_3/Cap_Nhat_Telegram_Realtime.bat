@echo off
chcp 65001 > nul
title CẬP NHẬT REALTIME TELEGRAM SCM (0978009295)
color 0B

echo ==============================================================================
echo 🚀 ĐANG ĐỒNG BỘ TIN NHẮN & GOM CỤM NHÓM TELEGRAM REALTIME (ACCOUNT: 0978009295)...
echo ==============================================================================
echo.

cd /d "%~dp0DONG_MAT_DASHBOARD"
python sync_telegram_groups.py

echo.
echo ==============================================================================
echo 🌐 ĐANG ĐẨY CẬP NHẬT LÊN WEB GITHUB PAGES...
echo ==============================================================================
echo.

cd /d "%~dp0"
git add daily_details/telegram_groups.js DONG_MAT_DASHBOARD/daily_details/telegram_groups.js LOGIC/daily_details/telegram_groups.js DONG_MAT_DASHBOARD/data/telegram_groups.json Danh_Sach_Group_Telegram_SCM.xlsx index.html
git commit -m "Update: Realtime Telegram groups and store clusters"
git push origin main

echo.
echo ==============================================================================
echo 🎉 ĐÃ CẬP NHẬT THÀNH CÔNG DỮ LIỆU TELEGRAM REALTIME!
echo 🔗 Xem trực tiếp tại: https://aresphamha.github.io/Doi_Soat_Dong_Mat/
echo ==============================================================================
echo.
pause
