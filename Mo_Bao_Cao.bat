@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 1. Tự động kiểm tra và khởi động Local Runner Service chạy ngầm (Silent mode) nếu chưa chạy
netstat -ano | findstr 8088 >nul 2>&1
if %errorlevel% neq 0 (
    start "" pythonw "%~dp0local_runner_service.py"
)

:: 2. Mở Báo Cáo Đối Soát trên Trình Duyệt
start "" msedge "%~dp0Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html"
