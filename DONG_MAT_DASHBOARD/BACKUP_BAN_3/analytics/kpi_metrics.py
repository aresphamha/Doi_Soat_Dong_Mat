"""
Module tính toán các chỉ số KPI, ma trận đối soát và xếp hạng chênh lệch SCM.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def get_daily_summary_matrix(df: pd.DataFrame, threshold: float = 100000.0, df_full: pd.DataFrame = None) -> pd.DataFrame:
    """
    Tạo Ma Trận Đối Soát Tổng Hợp Toàn Diện Theo Từng Ngày:
    - SL Chuyển, Nhận, Lệch, Tổng Tiền
    - Đếm số lượng Siêu Thị (Tổng ST, ST >= 100k, ST < 100k)
    - Phân khúc Tiền: Tiền ST >= 100k vs Tiền ST < 100k
    - Điểm nhận (Kho ĐÔNG MÁT, Siêu thị, Hao hụt)
    - Trạng thái 3 cấp (Đã xử lý, Đang xử lý, Chưa xử lý) & Tỷ lệ hoàn tất.
    """
    if len(df) == 0 or "Date_Str" not in df.columns:
        return pd.DataFrame()
        
    from analytics.threshold_analytics import get_daily_threshold_breakdown
    df_daily, _ = get_daily_threshold_breakdown(df, threshold=threshold, df_full=df_full)
    return df_daily


def get_monthly_summary_matrix(df: pd.DataFrame, threshold: float = 100000.0, df_full: pd.DataFrame = None) -> pd.DataFrame:
    """
    Tạo Bảng Báo Cáo Tổng Hợp Theo Cấp Tháng.
    """
    df_daily = get_daily_summary_matrix(df, threshold=threshold, df_full=df_full)
    if len(df_daily) == 0:
        return pd.DataFrame()
        
    agg_dict = {
        "Tong_So_Vu": "sum",
        "Tong_SL_Chuyen": "sum",
        "Tong_SL_Nhan": "sum",
        "Tong_SL_Lech": "sum",
        "Tong_Gia_Tri": "sum",
        "Tong_ST": "sum",
        "ST_Over_100k": "sum",
        "ST_Under_100k": "sum",
        "ST_Da_Xu_Ly": "sum",
        "ST_Dang_Xu_Ly": "sum",
        "ST_Khong_Xu_Ly": "sum",
        "Val_Over_100k": "sum",
        "Val_Under_100k": "sum",
        "Val_Kho": "sum",
        "Val_ST": "sum",
        "Val_HaoHut": "sum",
        "Val_Da_Xu_Ly": "sum",
        "Val_Dang_Xu_Ly": "sum",
        "Val_Khong_Xu_Ly": "sum",
        "SL_Kho": "sum",
        "SL_ST": "sum",
        "SL_HaoHut": "sum",
        "SL_Da_Xu_Ly": "sum",
        "SL_Dang_Xu_Ly": "sum",
        "SL_Khong_Xu_Ly": "sum"
    }
    
    # Filter only available columns
    agg_clean = {k: v for k, v in agg_dict.items() if k in df_daily.columns}
    
    monthly = df_daily.groupby("Tháng").agg(agg_clean).reset_index()
    
    monthly["Pct_Da_Xu_Ly"] = monthly.apply(
        lambda r: round((r["Val_Da_Xu_Ly"] / r["Tong_Gia_Tri"] * 100.0), 1) if r.get("Tong_Gia_Tri", 0.0) > 0 else 0.0, axis=1
    )
    monthly["Pct_SL_Da_Xu_Ly"] = monthly.apply(
        lambda r: round((r["SL_Da_Xu_Ly"] / r["Tong_SL_Lech"] * 100.0), 1) if r.get("Tong_SL_Lech", 0.0) > 0 else 0.0, axis=1
    )
    
    return monthly


def get_error_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tổng hợp phân tích theo từng loại lỗi ghi nhận.
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    err_grp = df.groupby("Lỗi").agg(
        So_Vu=("ID ST", "count"),
        Tong_SL_Lech=("Qty_Lech", "sum"),
        Tong_Gia_Tri=("Val_Tong_GT", "sum"),
        So_ST=("ID ST", "nunique")
    ).reset_index()
    
    err_grp.sort_values(by="Tong_Gia_Tri", ascending=False, inplace=True)
    return err_grp


def get_top_discrepant_stores(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Xếp hạng Top N Siêu thị có tổng chênh lệch lớn nhất.
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    st_grp = df.groupby(["ID ST", "Chi nhánh nhận"]).agg(
        So_Vu=("Mã hàng", "count"),
        Tong_SL_Lech=("Qty_Lech", "sum"),
        Tong_Gia_Tri=("Val_Tong_GT", "sum"),
        So_Ngay_Lech=("Date_Str", "nunique")
    ).reset_index()
    
    st_grp.sort_values(by="Tong_Gia_Tri", ascending=False, inplace=True)
    return st_grp.head(top_n)


def get_top_discrepant_products(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Xếp hạng Top N Mã hàng có tổng chênh lệch lớn nhất.
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    prod_grp = df.groupby(["Mã hàng", "Tên SP", "ĐVT", "Nhóm hàng"]).agg(
        So_Vu=("ID ST", "count"),
        Tong_SL_Lech=("Qty_Lech", "sum"),
        Tong_Gia_Tri=("Val_Tong_GT", "sum"),
        So_ST_Anh_Huong=("ID ST", "nunique")
    ).reset_index()
    
    prod_grp.sort_values(by="Tong_Gia_Tri", ascending=False, inplace=True)
    return prod_grp.head(top_n)
