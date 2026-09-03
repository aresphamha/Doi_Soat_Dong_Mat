"""
Module xuất báo cáo Excel đa Sheet định dạng doanh nghiệp chuẩn (Enterprise Excel Exporter).
"""

import io
import pandas as pd
from typing import Dict, Any


def export_multi_sheet_excel(
    df_filtered: pd.DataFrame,
    df_error_summary: pd.DataFrame,
    streams: Dict[str, pd.DataFrame],
    kpis: Dict[str, Any]
) -> bytes:
    """
    Tạo tệp Excel đa Sheet định dạng chuyên nghiệp với XlsxWriter.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # 1. Định dạng ô (Styles)
        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "vcenter",
            "align": "center",
            "fg_color": "#0284c7",
            "font_color": "#ffffff",
            "border": 1,
            "font_size": 11
        })
        
        kpi_title_fmt = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "font_color": "#0f172a",
            "bottom": 2
        })
        
        kpi_label_fmt = workbook.add_format({"bold": True, "font_color": "#475569", "border": 1})
        kpi_num_fmt = workbook.add_format({"num_format": "#,##0", "font_color": "#0f172a", "border": 1})
        currency_fmt = workbook.add_format({"num_format": '#,##0 "đ"', "border": 1})
        number_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        border_fmt = workbook.add_format({"border": 1})
        
        # --- SHEET 1: TỔNG QUAN KPI & CƠ CẤU LỖI ---
        ws_kpi = workbook.add_worksheet("1. Tổng Quan KPI & Lỗi")
        ws_kpi.write("A1", "BÁO CÁO TỔNG HỢP ĐỐI SOÁT HÀNG ĐÔNG MÁT", kpi_title_fmt)
        
        ws_kpi.write("A3", "Chỉ số KPI", kpi_label_fmt)
        ws_kpi.write("B3", "Giá trị", kpi_label_fmt)
        
        ws_kpi.write("A4", "Tổng số vụ chênh lệch", border_fmt)
        ws_kpi.write("B4", kpis["total_records"], kpi_num_fmt)
        
        ws_kpi.write("A5", "Tổng khối lượng lệch (kg/pack)", border_fmt)
        ws_kpi.write("B5", kpis["total_qty_lech"], number_fmt)
        
        ws_kpi.write("A6", "Tổng giá trị chênh lệch (VNĐ)", border_fmt)
        ws_kpi.write("B6", kpis["total_val_gt"], currency_fmt)
        
        ws_kpi.write("A7", "Kho DC chịu trách nhiệm (VNĐ)", border_fmt)
        ws_kpi.write("B7", kpis["total_val_kho"], currency_fmt)
        
        ws_kpi.write("A8", "Siêu thị chịu trách nhiệm (VNĐ)", border_fmt)
        ws_kpi.write("B8", kpis["total_val_st"], currency_fmt)
        
        ws_kpi.write("A9", "Hao hụt tự nhiên (VNĐ)", border_fmt)
        ws_kpi.write("B9", kpis["total_val_haohut"], currency_fmt)
        
        ws_kpi.write("A10", "Chưa xác định (VNĐ)", border_fmt)
        ws_kpi.write("B10", kpis["total_val_cxd"], currency_fmt)
        
        # Bảng cơ cấu lỗi
        if len(df_error_summary) > 0:
            ws_kpi.write("D3", "BẢNG CƠ CẤU THEO LOẠI LỖI", kpi_title_fmt)
            df_error_summary.to_excel(writer, sheet_name="1. Tổng Quan KPI & Lỗi", startrow=3, startcol=3, index=False)
            
        ws_kpi.set_column("A:A", 32)
        ws_kpi.set_column("B:B", 22)
        ws_kpi.set_column("D:I", 20)

        # --- SHEET 2: DỮ LIỆU CHI TIẾT ---
        cols_to_export = [
            "Date_Str", "Chi nhánh nhận", "ID ST", "Nhóm hàng", "Mã hàng", "Tên SP", "ĐVT",
            "Số lượng chuyển_Num", "Số lượng nhận_Num", "Chênh lệch_Num",
            "PT chuyển hàng", "Mã thùng", "TO", "Lỗi", "Trạng thái",
            "Giá nhập \n( -VAT)", "Tổng GT_Num", "Tổng kho_Num", "Tổng ST_Num",
            "DC xác nhận", "Xử lý", "Link hình ảnh"
        ]
        available_cols = [c for c in cols_to_export if c in df_filtered.columns]
        df_export_main = df_filtered[available_cols].copy()
        df_export_main.rename(columns={
            "Date_Str": "Ngày",
            "Số lượng chuyển_Num": "SL Chuyển",
            "Số lượng nhận_Num": "SL Nhận",
            "Chênh lệch_Num": "SL Lệch",
            "PT chuyển hàng": "Mã Phiếu (PT)",
            "Giá nhập \n( -VAT)": "Đơn Giá",
            "Tổng GT_Num": "Tổng Tiền Lệch (VNĐ)",
            "Tổng kho_Num": "Kho Chịu (VNĐ)",
            "Tổng ST_Num": "ST Chịu (VNĐ)",
            "DC xác nhận": "DC Phản Hồi",
            "Link hình ảnh": "Video Bằng Chứng"
        }, inplace=True)
        
        df_export_main.to_excel(writer, sheet_name="2. Dữ Liệu Chi Tiết", index=False)
        ws_main = writer.sheets["2. Dữ Liệu Chi Tiết"]
        ws_main.set_column("A:Z", 18)

        # --- CÁC SHEET ĐỐI SOÁT PHÂN LUỒNG 6 NHÓM ---
        sheet_mapping = [
            ("3. Khớp Nội Bộ 100%", streams["stream_1_exact"]),
            ("4. Khớp Nội Bộ 1 Phần", streams["stream_2_partial"]),
            ("5. Giao Nhầm Siêu Thị", streams["stream_3_cross"]),
            ("6. Bù Đắp Thừa Dư", streams["stream_4_surplus_gte"]),
            ("7. Thiếu Ròng (DC Thiếu)", streams["stream_5_net_shortage"]),
            ("8. Trả Tồn DC", streams["stream_6_net_surplus"]),
        ]
        
        for sheet_title, df_stream in sheet_mapping:
            if len(df_stream) > 0:
                cols = [c for c in cols_to_export if c in df_stream.columns]
                df_st_exp = df_stream[cols].copy()
                df_st_exp.rename(columns={
                    "Date_Str": "Ngày",
                    "Số lượng chuyển_Num": "SL Chuyển",
                    "Số lượng nhận_Num": "SL Nhận",
                    "Chênh lệch_Num": "SL Lệch",
                    "PT chuyển hàng": "Mã Phiếu (PT)",
                    "Tổng GT_Num": "Tổng Tiền Lệch (VNĐ)",
                    "Tổng kho_Num": "Kho Chịu (VNĐ)",
                    "Tổng ST_Num": "ST Chịu (VNĐ)",
                }, inplace=True)
                df_st_exp.to_excel(writer, sheet_name=sheet_title, index=False)
                ws_st = writer.sheets[sheet_title]
                ws_st.set_column("A:Z", 18)
                
    return output.getvalue()
