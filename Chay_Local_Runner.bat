@echo off
chcp 65001 > nul
title ⚡ SCM LOCAL RUNNER SERVICE - ĐIỀU KHIỂN TỪ WEB
cd /d "%~dp0"

echo ==============================================================================
echo 🚀 ĐANG KHỞI ĐỘNG TRẠM ĐIỀU KHIỂN SCM LOCAL RUNNER (PORT 8088)...
echo ==============================================================================
echo.
echo 📡 Trạm điều khiển này cho phép bạn bấm nút TRỰC TIẾP trên Web:
echo    👉 https://aresphamha.github.io/Doi_Soat_Dong_Mat/
echo.
echo 💡 Khi trạm này đang mở, bạn chỉ cần bấm nút trên Web là tool sẽ chạy
echo    ngay lập tức trên máy tính của bạn với tốc độ tối đa!
echo.
echo ==============================================================================

python local_runner_service.py

pause
