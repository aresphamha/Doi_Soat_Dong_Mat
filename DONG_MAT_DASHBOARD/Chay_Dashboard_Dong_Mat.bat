@echo off
chcp 65001 > nul
title HỆ THỐNG DASHBOARD ĐỐI SOÁT ĐÔNG MÁT (MỚI)
color 0B

echo ==============================================================================
echo 🚀 ĐANG KHỞI CHẠY DASHBOARD ĐỐI SOÁT CHUYÊN SÂU ĐÔNG MÁT...
echo ==============================================================================
echo.
cd /d "%~dp0"
streamlit run app.py
pause
