@echo off
chcp 65001 > nul
title CẬP NHẬT BÁO CÁO WEB ĐỐI SOÁT ĐÔNG MÁT
color 0A

echo ==============================================================================
echo 🚀 ĐANG TẢI DỮ LIỆU MỚI TỪ GOOGLE SHEETS & CẬP NHẬT BÁO CÁO WEB...
echo ==============================================================================
echo.

cd /d "%~dp0DONG_MAT_DASHBOARD"
python generate_web_report.py

echo.
echo ==============================================================================
echo ✅ ĐÃ CẬP NHẬT XONG TOÀN BỘ BÁO CÁO WEB ĐỐI SOÁT ĐÔNG MÁT!
echo 🌐 File báo cáo đã được lưu tại:
echo    - DONG_MAT_DASHBOARD\Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html
echo    - Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html
echo ==============================================================================
echo.
pause
