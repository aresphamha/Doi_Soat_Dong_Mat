"""
Module các thành phần giao diện tái sử dụng (KPI Cards, Header, Format bảng số liệu).
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any


def render_header_banner(title: str, subtitle: str, data_date: str = ""):
    """
    Render tiêu đề chính phong cách hiện đại với thông tin ngày cập nhật.
    """
    date_badge = f'<span class="badge badge-info">{data_date}</span>' if data_date else ""
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">❄️ {title}</h1>
            <div class="dashboard-subtitle">{subtitle}</div>
        </div>
        <div>
            {date_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(kpis: Dict[str, Any]):
    """
    Hiển thị dàn thẻ KPI Glassmorphism chuyên nghiệp.
    """
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-blue">
            <div class="kpi-label">Tổng số vụ chênh lệch</div>
            <div class="kpi-value">{kpis['total_records']:,} <span style="font-size: 14px; font-weight: 500;">vụ</span></div>
            <div class="kpi-sub">Khoảng {kpis['unique_stores']} Siêu thị • {kpis['unique_pts']} Phiếu PT</div>
        </div>
        <div class="kpi-card kpi-red">
            <div class="kpi-label">Tổng giá trị chênh lệch</div>
            <div class="kpi-value">{kpis['total_val_gt']:,.0f} <span style="font-size: 14px; font-weight: 500;">VNĐ</span></div>
            <div class="kpi-sub">Tổng lượng lệch: {kpis['total_qty_lech']:,.2f} kg/pack</div>
        </div>
        <div class="kpi-card kpi-amber">
            <div class="kpi-label">Kho DC chịu trách nhiệm</div>
            <div class="kpi-value">{kpis['total_val_kho']:,.0f} <span style="font-size: 14px; font-weight: 500;">VNĐ</span></div>
            <div class="kpi-sub">Chiếm <b>{kpis['pct_kho']:.1f}%</b> tổng giá trị lệch</div>
        </div>
        <div class="kpi-card kpi-purple">
            <div class="kpi-label">Siêu thị chịu trách nhiệm</div>
            <div class="kpi-value">{kpis['total_val_st']:,.0f} <span style="font-size: 14px; font-weight: 500;">VNĐ</span></div>
            <div class="kpi-sub">Chiếm <b>{kpis['pct_st']:.1f}%</b> tổng giá trị lệch</div>
        </div>
        <div class="kpi-card kpi-green">
            <div class="kpi-label">Hao hụt / Chưa xác định</div>
            <div class="kpi-value">{(kpis['total_val_haohut'] + kpis['total_val_cxd']):,.0f} <span style="font-size: 14px; font-weight: 500;">VNĐ</span></div>
            <div class="kpi-sub">Hao hụt: {kpis['total_val_haohut']:,.0f} đ • CXD: {kpis['total_val_cxd']:,.0f} đ</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def format_dataframe_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chọn lọc và định dạng cột hiển thị dễ đọc cho người dùng.
    """
    display_cols = [
        "Date_Str", "Chi nhánh nhận", "ID ST", "Nhóm hàng", "Mã hàng", "Tên SP", "ĐVT",
        "Số lượng chuyển_Num", "Số lượng nhận_Num", "Chênh lệch_Num",
        "PT chuyển hàng", "Mã thùng", "TO", "Lỗi", "Trạng thái",
        "Giá nhập \n( -VAT)", "Tổng GT_Num", "Tổng kho_Num", "Tổng ST_Num",
        "DC xác nhận", "Xử lý", "Link hình ảnh"
    ]
    
    available_cols = [c for c in display_cols if c in df.columns]
    df_display = df[available_cols].copy()
    
    col_rename = {
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
    }
    
    df_display.rename(columns=col_rename, inplace=True)
    return df_display
