@echo off
chcp 65001 >nul
echo ==============================================================================
echo ⏳ ĐANG ĐỒNG BỘ BÁO CÁO LOGISTICS FMCG TỪ CDC STARROCKS + GOOGLE SHEET SEEDLOG...
echo ==============================================================================

python xuat_excel_fmcg_tab_moi.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo 🚀 ĐANG ĐẨY DỮ LIỆU TAB 8 MỚI LÊN GITHUB PAGES...
    git pull --rebase origin main
    git add daily_details/fmcg_matrix.js DONG_MAT_DASHBOARD/daily_details/fmcg_matrix.js BAO_CAO_FMCG_TAB_MOI_VA_LOGIC.xlsx
    git commit -m "🤖 [Realtime] Đồng bộ dữ liệu Báo cáo Logistics FMCG mới nhất từ CDC StarRocks + Seedlog"
    git push origin main
    echo.
    echo ==============================================================================
    echo 🎉 ĐÃ ĐỒNG BỘ THÀNH CÔNG! HÃY BẤM CTRL+F5 TRÊN WEB ĐỂ XEM SỐ LIỆU MỚI NHẤT.
    echo ==============================================================================
) else (
    echo.
    echo ❌ LỖI: Không thể kết nối tới Database CDC! Hãy kiểm tra kết nối NetBird (Connected).
)

pause
