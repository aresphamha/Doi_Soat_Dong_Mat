@echo off
chcp 65001 >nul
echo ==============================================================================
echo 🚀 TOOL TỰ ĐỘNG ĐỒNG BỘ BẢNG GIÁ NHẬP SẢN PHẨM TRỰC TIẾP TỪ CDC (STARROCKS)
echo ==============================================================================
echo.
python "%~dp0TOOLS_DOI_SOAT\Cap_Nhat_Gia_Nhap_Tu_CDC.py"
echo.
pause
