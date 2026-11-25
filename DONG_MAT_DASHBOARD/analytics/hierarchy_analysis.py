"""
Module phân tích cơ cấu đa tầng theo danh mục ngành hàng (CLV2 / CLV3 / Loại hàng).
"""

import pandas as pd


def get_category_hierarchy_tree(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo dữ liệu phân cấp 3 tầng (Nhóm hàng -> CLV2 -> CLV3) phục vụ vẽ biểu đồ Treemap/Sunburst.
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    filtered = df.copy()
    filtered["Nhóm hàng"] = filtered["Nhóm hàng"].replace("", "KHÁC")
    filtered["CLV2"] = filtered["CLV2"].replace("", "CHƯA PHÂN LOẠI")
    filtered["CLV3"] = filtered["CLV3"].replace("", "CHƯA PHÂN LOẠI")
    
    grouped = filtered.groupby(["Nhóm hàng", "CLV2", "CLV3"]).agg(
        So_Vu=("Mã hàng", "count"),
        Tong_GT=("Val_Tong_GT", "sum"),
        SL_Lech=("Qty_Lech", "sum")
    ).reset_index()
    
    grouped.sort_values(by="Tong_GT", ascending=False, inplace=True)
    return grouped


def get_clv2_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thống kê tổng hợp theo ngành hàng cấp 2 (CLV2).
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    filtered = df.copy()
    filtered["CLV2"] = filtered["CLV2"].replace("", "CHƯA PHÂN LOẠI")
    
    summary = filtered.groupby("CLV2").agg(
        So_Vu=("CLV2", "count"),
        SL_Lech=("Qty_Lech", "sum"),
        Tong_GT=("Val_Tong_GT", "sum"),
        Tong_Kho=("Val_Tong_Kho", "sum")
    ).reset_index()
    
    summary.sort_values(by="Tong_GT", ascending=False, inplace=True)
    summary.rename(columns={
        "CLV2": "Ngành hàng cấp 2 (CLV2)",
        "So_Vu": "Số vụ lệch",
        "SL_Lech": "Số lượng lệch",
        "Tong_GT": "Tổng giá trị (VNĐ)",
        "Tong_Kho": "Kho chịu (VNĐ)"
    }, inplace=True)
    
    return summary
