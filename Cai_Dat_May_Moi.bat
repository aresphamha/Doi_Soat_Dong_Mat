@echo off
chcp 65001 > nul
title Cài Đặt Môi Trường Cho Máy Mới - SCM Tool
cd /d "%~dp0"

echo ==============================================================================
echo 📦 BẮT ĐẦU CÀI ĐẶT CÁC THƯ VIỆN CẦN THIẾT CHO MÁY MỚI...
echo ==============================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ LỖI: Máy tính chưa cài đặt Python!
    echo 👉 Vui lòng tải và cài đặt Python từ: https://www.python.org/downloads/
    echo ⚠️ Lưu ý: Khi cài nhớ tích chọn "Add Python to PATH".
    echo.
    pause
    exit /b
)

echo ✅ Đã tìm thấy Python. Đang tự động cài đặt các thư viện cần thiết...
echo.
pip install -r requirements.txt

echo.
echo ==============================================================================
echo 🎉 CÀI ĐẶT HOÀN TẤT!
echo 👉 Bây giờ bạn chỉ cần mở file "Chay_Local_Runner.bat" là có thể dùng Web bình thường.
echo ==============================================================================
echo.
pause
