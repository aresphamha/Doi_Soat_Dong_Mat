@echo off
chcp 65001 > nul
title TOOL ADD THÀNH VIÊN TELEGRAM
cd /d "%~dp0"
echo ==================================================
echo   TOOL ADD THANH VIEN VAO TAT CA GROUP SIEU THI
echo ==================================================
echo.
python 4_Add_Thanh_Vien.py
pause
