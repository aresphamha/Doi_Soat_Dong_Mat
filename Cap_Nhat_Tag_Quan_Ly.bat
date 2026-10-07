@echo off
chcp 65001 >nul
title 🔄 CẬP NHẬT & ĐỒNG BỘ DANH BẠ TAG QUẢN LÝ / TRƯỞNG CA (SM/TC/GSM)
color 0B
cd /d "%~dp0"

echo ==============================================================================
echo 🔄 SCM TOOL: CẬP NHẬT TAG TELEGRAM (SM, GSM, TC) & ĐỒNG BỘ CLOUD GITHUB
echo ==============================================================================
echo.
echo ⏳ Đang quét danh bạ 220+ nhóm Telegram siêu thị...
echo.

python "TOOLS_DOI_SOAT\cap_nhat_tag_quan_ly.py"

echo.
echo ==============================================================================
echo 🏁 Hoàn tất quá trình cập nhật! Bấm phím bất kỳ để thoát...
echo ==============================================================================
pause >nul
