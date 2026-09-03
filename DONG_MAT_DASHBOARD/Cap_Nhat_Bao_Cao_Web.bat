@echo off
chcp 65001 > nul
title CẬP NHẬT BÁO CÁO & TỰ ĐỘNG ĐẨY LÊN WEB (CI/CD)
color 0A

echo ==============================================================================
echo 🚀 BƯỚC 1/2: ĐANG TẢI DỮ LIỆU MỚI & TẠO BÁO CÁO WEB ĐỐI SOÁT ĐÔNG MÁT...
echo ==============================================================================
echo.

cd /d "%~dp0DONG_MAT_DASHBOARD"
python generate_web_report.py

echo.
echo ==============================================================================
echo 🚀 BƯỚC 2/2: ĐANG TỰ ĐỘNG ĐẨY LÊN GITHUB & DEPLOY WEB ONLINE (CI/CD)...
echo ==============================================================================
echo.

python push_to_github.py

echo.
echo ==============================================================================
echo 🎉 HOÀN TẤT 100% QUY TRÌNH TỰ ĐỘNG HÓA!
echo 🌐 Xem Báo Cáo Trực Tuyến tại:
echo    👉 https://aresphamha.github.io/Doi_Soat_Dong_Mat/
echo ==============================================================================
echo.
pause
