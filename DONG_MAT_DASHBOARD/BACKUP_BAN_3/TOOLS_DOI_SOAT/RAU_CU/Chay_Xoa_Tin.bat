@echo off
chcp 65001 > nul
title XOÁ TIN NHẮN BOT - RAU CỦ QUẢ
cd /d "%~dp0"
echo ==================================================
echo   XOA TIN NHAN BOT DA SPAM - RAU CU QUA
echo ==================================================
echo.
python Xoa_Tin_Nhan.py
pause
