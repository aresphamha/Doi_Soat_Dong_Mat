@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo ==============================================================================
echo [1/2] DANG DONG BO BAO CAO LOGISTICS FMCG TU CDC STARROCKS + GOOGLE SHEET SEEDLOG...
echo ==============================================================================

python xuat_excel_fmcg_tab_moi.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Khong the ket noi toi Database CDC! Hay kiem tra ket noi NetBird (Connected).
    pause
    exit /b 1
)

echo.
echo [2/2] DANG DAY DU LIEU TAB 8 MOI LEN GITHUB PAGES...
git add daily_details/fmcg_matrix.js DONG_MAT_DASHBOARD/daily_details/fmcg_matrix.js daily_details/fmcg_store_details.js DONG_MAT_DASHBOARD/daily_details/fmcg_store_details.js BAO_CAO_FMCG_TAB_MOI_VA_LOGIC.xlsx
git commit -m "Realtime: Dong bo du lieu Bao cao Logistics FMCG tu CDC StarRocks + Seedlog"
git pull --rebase origin main
git push origin main

echo.
echo ==============================================================================
echo [THANH CONG] DA DONG BO XONG! HAY BAM F5 TREN WEB DE XEM SO LIEU MOI NHAT.
echo ==============================================================================
pause
