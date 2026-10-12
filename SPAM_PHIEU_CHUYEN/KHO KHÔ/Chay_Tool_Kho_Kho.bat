@echo off
chcp 65001 >nul
title TOOL SPAM KHO KHÔ FGA10101 SCM KINGFOODMART
color 0E

echo ==============================================================================
echo        📦 TRUNG TÂM TOOL SPAM KHO KHÔ FGA10101 (BÌNH THẮNG)
echo ==============================================================================
echo.
echo   [1] 📦 Spam Phiếu CHI TIẾT KHO KHÔ FGA10101
echo   [2] ⚖️ Spam Phiếu HẬU KIỂM KHO KHÔ FGA10101
echo   [3] 🚀 Chạy Cả 2 Tool Kho Khô
echo   [0] ❌ Thoát
echo.
set /p opt="👉 Vui lòng chọn (1-3 hoặc 0): "

if "%opt%"=="1" (
    python Spam_Phieu_Chi_Tiet_Kho_Kho.py
)
if "%opt%"=="2" (
    python Spam_Phieu_Hau_Kiem_Kho_Kho.py
)
if "%opt%"=="3" (
    python Spam_Phieu_Chi_Tiet_Kho_Kho.py
    python Spam_Phieu_Hau_Kiem_Kho_Kho.py
)
pause
