@echo off
chcp 65001 >nul
title MENU ĐIỀU HÀNH TOOL SPAM TELEGRAM SCM KINGFOODMART
color 0B

:MENU
cls
echo ==============================================================================
echo        🚀 TRUNG TÂM ĐIỀU HÀNH BỘ TOOL SPAM TELEGRAM SCM KINGFOODMART
echo ==============================================================================
echo.
echo   [1] 🥩 Spam Phiếu Chuyển THỊT CÁ (Chụp bảng chênh lệch & gửi Group Telegram ST)
echo   [2] 🥗 Spam Phiếu Chuyển HÀNG MÁT (Gửi phiếu đang chuyển hàng mát cho ST)
echo   [3] 🥬 Spam Phiếu HẬU KIỂM RAU CỦ (Nhắc nhở kiểm tra camera & vị trí nhận)
echo   [4] 🐟 Spam Phiếu HẬU KIỂM THỊT CÁ (Nhắc nhở hoàn thành phiếu hậu kiểm)
echo   [5] 📦 Chạy kiểm tra kết nối Database Cloud (103.147.122.103:9030)
echo   [0] ❌ Thoát
echo.
echo ==============================================================================
set /p opt="👉 Vui lòng nhập lựa chọn (1-5 hoặc 0): "

if "%opt%"=="1" goto THIT_CA
if "%opt%"=="2" goto HANG_MAT
if "%opt%"=="3" goto HAU_KIEM_RAU
if "%opt%"=="4" goto HAU_KIEM_TC
if "%opt%"=="5" goto TEST_DB
if "%opt%"=="0" exit
goto MENU

:THIT_CA
cls
echo [ĐANG CHẠY] Spam Phiếu Chuyển THỊT CÁ...
cd /d "%~dp0CHI TIẾT THỊT CÁ"
python "Spam_Phieu_Chuyen_Thit_Ca.py"
pause
goto MENU

:HANG_MAT
cls
echo [ĐANG CHẠY] Spam Phiếu Chuyển HÀNG MÁT...
cd /d "%~dp0CHI TIẾT MÁT"
python "Spam_Phieu_Chuyen_Hang_Mat.py"
pause
goto MENU

:HAU_KIEM_RAU
cls
echo [ĐANG CHẠY] Spam Phiếu HẬU KIỂM RAU CỦ...
cd /d "%~dp0HẬU KIỂM RAU"
python "Spam_Phieu_Hau_Kiem_Rau_Cu.py"
pause
goto MENU

:HAU_KIEM_TC
cls
echo [ĐANG CHẠY] Spam Phiếu HẬU KIỂM THỊT CÁ...
cd /d "%~dp0HẬU KIỂM THỊ CÁ"
python "Spam_Phieu_Hau_Kiem_Thit_Ca.py"
pause
goto MENU

:TEST_DB
cls
echo [ĐANG KIỂM TRA] Kết nối MySQL Database Cloud...
python -c "import pymysql; conn = pymysql.connect(host='103.147.122.103', port=9030, user='kfm_scm_tho_nguyen', password='oh1dtJwR4ihLGrX4E7bs', database='kfm_scm', connect_timeout=5); print('✅ KẾT NỐI DATABASE THÀNH CÔNG!'); conn.close()"
pause
goto MENU
