@echo off
chcp 65001 >nul
title TELEGRAM SCM CHAT ENGINE - 0978009295 (KFM - SCM - HA PHAM)
color 0B
cls

echo ==============================================================================
echo       KHOI DONG HE THONG TELEGRAM SCM CHAT REALTIME 2-WAY ENGINE
echo  Tai khoan: 0978009295 (KFM - SCM - Ha Pham - SC007251)
echo ==============================================================================
echo.
echo [1/2] Dang khoi dong Backend Telethon aiohttp server (Port 8080)...
start "" http://localhost:8080/index.html?tab=4

cd /d "%~dp0DONG_MAT_DASHBOARD"
python telegram_chat_server.py

pause
