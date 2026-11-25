@echo off
chcp 65001 >nul
echo ==============================================================================
echo 🚀 TOOL TỰ ĐỘNG CẬP NHẬT BẢNG GIÁ NHẬP SẢN PHẨM TỪ FILE EXCEL (HADA / CDC)
echo ==============================================================================
echo.
python "%~dp0TOOLS_DOI_SOAT\Cap_Nhat_Gia_Nhap_Tu_Excel.py" %*
echo.
pause
