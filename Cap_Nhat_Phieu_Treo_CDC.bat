@echo off
chcp 65001 >nul
echo ==============================================================================
echo ⏳ ĐANG ĐỒNG BỘ PHIẾU TREO TỪ WMS CDC STARROCKS (103.140.248.250:9030)...
echo ==============================================================================

python DONG_MAT_DASHBOARD\sync_pending_tickets.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo 🚀 ĐANG ĐẨY DỮ LIỆU MỚI LÊN GITHUB PAGES...
    git pull --rebase origin main
    git add daily_details/pending_tickets.js DONG_MAT_DASHBOARD/daily_details/pending_tickets.js
    git commit -m "🤖 [Realtime] Đồng bộ danh sách phiếu treo mới nhất từ CDC WMS"
    git push origin main
    echo.
    echo ==============================================================================
    echo 🎉 ĐÃ ĐỒNG BỘ THÀNH CÔNG! HÃY BẤM F5 TRÊN WEB ĐỂ XEM SỐ LIỆU MỚI NHẤT.
    echo ==============================================================================
) else (
    echo.
    echo ❌ LỖI: Không thể kết nối tới Database CDC! Hãy kiểm tra WireGuard VPN.
)

pause
