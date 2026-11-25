"""
Module phân tích chuyên sâu Ngưỡng giá trị (Tính trên Tổng tiền lệch của Siêu thị trong Ngày)
và Phân loại trạng thái xử lý 3 cấp (Đã xử lý, Đang xử lý, Chưa xử lý) chuẩn nghiệp vụ SCM.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def determine_case_destination(row) -> str:
    """
    Xác định điểm quy trách nhiệm / trả tồn chính cho mỗi case chênh lệch:
    - Kho ĐÔNG MÁT
    - Siêu thị
    - Hao hụt
    - Chưa xác định
    """
    # 1. Kiểm tra theo tag cột văn bản trước (Col X, Y, Z)
    k_tag = str(row.get("Kho ĐÔNG MÁT", "")).strip()
    s_tag = str(row.get("Siêu thị", "")).strip()
    h_tag = str(row.get("Hao hụt", "")).strip()
    
    if "Kho đông mát" in k_tag or "CL02" in k_tag:
        return "Kho ĐÔNG MÁT"
    if "Siêu thị" in s_tag:
        return "Siêu thị"
    if "Hao hụt" in h_tag:
        return "Hao hụt"
    if "Chưa xác định" in k_tag:
        return "Chưa xác định"
        
    # 2. Kiểm tra theo số tiền tài chính nếu có
    k = row.get("Val_Tong_Kho", 0.0)
    s = row.get("Val_Tong_ST", 0.0)
    h = row.get("Val_Tong_HaoHut", 0.0)
    c = row.get("Val_Tong_CXD", 0.0)
    
    if k > 0 and k >= s and k >= h and k >= c:
        return "Kho ĐÔNG MÁT"
    elif s > 0 and s >= k and s >= h and s >= c:
        return "Siêu thị"
    elif h > 0 and h >= k and h >= s and h >= c:
        return "Hao hụt"
    elif c > 0:
        return "Chưa xác định"
        
    return "Chưa xác định"


def classify_processing_status(row) -> str:
    """
    Quy chuẩn trạng thái xử lý 3 cấp theo nghiệp vụ mới (bỏ lọc Cột AA, dựa vào Cột Z và Ngưỡng ST):
    - 'Đã xử lý': Khi Điểm nhận đã xác định (Kho ĐÔNG MÁT, Siêu thị, hoặc Hao hụt)
    - 'Đang xử lý': Khi Điểm nhận là 'Chưa xác định' VÀ Siêu thị trong ngày có tổng lệch >= 100k (Is_Store_Over_100k = True)
    - 'Không xử lý': Khi Điểm nhận là 'Chưa xác định' VÀ Siêu thị trong ngày có tổng lệch < 100k (Is_Store_Over_100k = False)
    """
    dest = row.get("Destination", "")
    if not dest:
        dest = determine_case_destination(row)
        
    if dest in ["Kho ĐÔNG MÁT", "Siêu thị", "Hao hụt"]:
        return "Đã xử lý"
    
    # Trường hợp Điểm nhận Chưa xác định (Cột Z)
    is_over = bool(row.get("Is_Store_Over_100k", False))
    if is_over:
        return "Đang xử lý"
    else:
        return "Không xử lý"


def enrich_dataframe_with_threshold_and_status(df: pd.DataFrame, threshold: float = 100000.0, df_full_for_store_total: pd.DataFrame = None) -> pd.DataFrame:
    """
    Bổ sung thông tin:
    1. Destination (Điểm nhận: Kho ĐÔNG MÁT / Siêu thị / Hao hụt / Chưa xác định)
    2. Store_Day_Val_Total: Tổng tiền lệch của Siêu thị đó trong ngày
    3. Is_Store_Over_100k: Đánh dấu Siêu thị đó trong ngày có Tổng Tiền Lệch >= 100k hay không.
    4. Status_3Level (Trạng thái 3 cấp: Đã xử lý / Đang xử lý / Không xử lý)
    """
    if len(df) == 0:
        return df.copy()
        
    df_work = df.copy()
    
    # 1. Xác định Điểm nhận trước
    df_work["Destination"] = df_work.apply(determine_case_destination, axis=1)
    
    # 2. Tính Tổng tiền lệch theo từng Siêu thị trong 1 Ngày (Store-Day Total)
    ref_df = df_full_for_store_total if df_full_for_store_total is not None else df_work
    st_totals = ref_df.groupby(["Date_Str", "ID ST"])["Val_Tong_GT"].sum().reset_index()
    st_totals.rename(columns={"Val_Tong_GT": "Store_Day_Val_Total"}, inplace=True)
    
    if "Store_Day_Val_Total" in df_work.columns:
        df_work.drop(columns=["Store_Day_Val_Total"], inplace=True)
    if "Is_Store_Over_100k" in df_work.columns:
        df_work.drop(columns=["Is_Store_Over_100k"], inplace=True)
        
    df_work = df_work.merge(st_totals, on=["Date_Str", "ID ST"], how="left")
    df_work["Store_Day_Val_Total"] = df_work["Store_Day_Val_Total"].fillna(0.0)
    df_work["Is_Store_Over_100k"] = df_work["Store_Day_Val_Total"] >= threshold
    
    # 3. Tính Trạng thái 3 cấp dựa vào Destination và Is_Store_Over_100k
    df_work["Status_3Level"] = df_work.apply(classify_processing_status, axis=1)
    
    return df_work


def analyze_threshold_metrics(df: pd.DataFrame, threshold: float = 100000.0, df_full: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Tính toán tỷ trọng ST và Giá trị theo ngưỡng 100k (Tính trên tổng tiền ST trong ngày).
    """
    total_records = len(df)
    if total_records == 0:
        return {
            "total_records": 0,
            "total_val": 0.0,
            "total_qty_lech": 0.0,
            "threshold": threshold,
            "over_stores_days": 0,
            "under_stores_days": 0,
            "over_val": 0.0,
            "under_val": 0.0
        }
        
    df_work = enrich_dataframe_with_threshold_and_status(df, threshold=threshold, df_full_for_store_total=df_full)
    
    total_val = df_work["Val_Tong_GT"].sum()
    total_qty = df_work["Qty_Lech"].sum()
    denom_val = total_val if total_val > 0 else 1.0
    
    # Store-Day unique pairs
    st_day_df = df_work.groupby(["Date_Str", "ID ST"]).agg(
        Store_Total=("Store_Day_Val_Total", "first")
    ).reset_index()
    
    over_stores_days = int((st_day_df["Store_Total"] >= threshold).sum())
    under_stores_days = int((st_day_df["Store_Total"] < threshold).sum())
    
    df_over = df_work[df_work["Is_Store_Over_100k"]]
    df_under = df_work[~df_work["Is_Store_Over_100k"]]
    
    over_val = float(df_over["Val_Tong_GT"].sum())
    under_val = float(df_under["Val_Tong_GT"].sum())
    
    df_da_xl = df_work[df_work["Status_3Level"] == "Đã xử lý"]
    df_dang_xl = df_work[df_work["Status_3Level"] == "Đang xử lý"]
    df_khong_xl = df_work[df_work["Status_3Level"] == "Không xử lý"]
    
    return {
        "total_records": total_records,
        "total_val": total_val,
        "total_qty_lech": total_qty,
        "threshold": threshold,
        "over_stores_days": over_stores_days,
        "under_stores_days": under_stores_days,
        "over_val": over_val,
        "over_pct_val": (over_val / denom_val * 100.0) if total_val > 0 else 0.0,
        "under_val": under_val,
        "under_pct_val": (under_val / denom_val * 100.0) if total_val > 0 else 0.0,
        "da_xu_ly_count": len(df_da_xl),
        "da_xu_ly_val": float(df_da_xl["Val_Tong_GT"].sum()),
        "da_xu_ly_pct_val": (df_da_xl["Val_Tong_GT"].sum() / denom_val * 100.0) if total_val > 0 else 0.0,
        "dang_xu_ly_count": len(df_dang_xl),
        "dang_xu_ly_val": float(df_dang_xl["Val_Tong_GT"].sum()),
        "khong_xu_ly_count": len(df_khong_xl),
        "khong_xu_ly_val": float(df_khong_xl["Val_Tong_GT"].sum())
    }


def get_daily_threshold_breakdown(df: pd.DataFrame, threshold: float = 100000.0, df_full: pd.DataFrame = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Tổng hợp bảng thống kê đa chiều theo từng Ngày:
    - SL Lệch, Tổng Tiền
    - Đếm số lượng Siêu Thị: Tổng ST, Số ST lệch >= 100k, Số ST lệch < 100k
    - Phân bổ Giá trị: Tiền của nhóm ST >= 100k, Tiền của nhóm ST < 100k
    - Điểm trả tồn: Kho ĐÔNG MÁT, Siêu thị, Hao hụt
    - Tiến độ xử lý 3 Cột: Đã xử lý, Đang xử lý (ST >= 100k), Không xử lý (ST < 100k)
    """
    if len(df) == 0:
        return pd.DataFrame(), {}
        
    df_work = enrich_dataframe_with_threshold_and_status(df, threshold=threshold, df_full_for_store_total=df_full)
    daily_rows = []
    
    for date_str, group in df_work.groupby("Date_Str", sort=False):
        d_total = len(group)
        d_val_total = float(group["Val_Tong_GT"].sum())
        d_qty_lech = float(group["Qty_Lech"].sum())
        d_qty_chuyen = float(group["Qty_Chuyen"].sum())
        d_qty_nhan = float(group["Qty_Nhan"].sum())
        
        # Thống kê ST theo ngày (mỗi ST tính tổng tiền của cả ST trong ngày)
        st_day_grp = group.groupby("ID ST")["Store_Day_Val_Total"].first()
        st_over_set = set(st_day_grp[st_day_grp >= threshold].index)
        st_under_set = set(st_day_grp[st_day_grp < threshold].index)
        
        st_over_count = len(st_over_set)
        st_under_count = len(st_under_set)
        st_total_count = group["ID ST"].replace("", pd.NA).dropna().nunique()
        
        # Nhóm dòng theo ST >= 100k vs < 100k
        df_over = group[group["ID ST"].isin(st_over_set)]
        df_under = group[group["ID ST"].isin(st_under_set)]
        
        val_over_100k = float(df_over["Val_Tong_GT"].sum())
        val_under_100k = float(df_under["Val_Tong_GT"].sum())
        
        # Điểm nhận (SL & Tiền)
        df_kho = group[group["Destination"] == "Kho ĐÔNG MÁT"]
        df_st = group[group["Destination"] == "Siêu thị"]
        df_hh = group[group["Destination"] == "Hao hụt"]
        
        # Trạng thái 3 cấp (SL & Tiền & Đếm ST)
        df_da_xl = group[group["Status_3Level"] == "Đã xử lý"]
        df_dang_xl = group[group["Status_3Level"] == "Đang xử lý"]
        df_khong_xl = group[group["Status_3Level"] == "Không xử lý"]
        
        st_da_xl_count = df_da_xl["ID ST"].replace("", pd.NA).dropna().nunique()
        st_dang_xl_count = df_dang_xl["ID ST"].replace("", pd.NA).dropna().nunique()
        st_khong_xl_count = df_khong_xl["ID ST"].replace("", pd.NA).dropna().nunique()
        
        val_dang_xl = float(df_dang_xl["Val_Tong_GT"].sum())
        val_khong_xl = float(df_khong_xl["Val_Tong_GT"].sum())
        sl_dang_xl = float(df_dang_xl["Qty_Lech"].sum())
        sl_khong_xl = float(df_khong_xl["Qty_Lech"].sum())
        
        date_parsed = group["Date_Parsed"].iloc[0] if "Date_Parsed" in group.columns else pd.NaT
        month_str = f"Tháng {date_parsed.month}" if pd.notna(date_parsed) else "Tháng 8"
        
        pct_val_da_xl = (df_da_xl["Val_Tong_GT"].sum() / d_val_total * 100.0) if d_val_total > 0 else 0.0
        pct_sl_da_xl = (df_da_xl["Qty_Lech"].sum() / d_qty_lech * 100.0) if d_qty_lech > 0 else 0.0
        
        # Thống kê DC Phản Hồi (Kho ĐÔNG MÁT)
        df_dc = df_kho
        dc_total_cases = len(df_dc)
        dc_total_qty = float(df_dc["Qty_Lech"].sum())
        dc_total_val = float(df_dc["Val_Tong_GT"].sum())
        dc_st_count = int(df_dc["ID ST"].replace("", pd.NA).dropna().nunique())
        
        df_dc_dongy = df_dc[df_dc["DC xác nhận"] == "Đồng ý claim"]
        df_dc_tuchoi = df_dc[df_dc["DC xác nhận"] == "Từ chối claim"]
        df_dc_kiemtra = df_dc[df_dc["DC xác nhận"] == "Kiểm tra lại"]
        df_dc_chua = df_dc[~df_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]
        
        dc_dongy_cases = len(df_dc_dongy)
        dc_dongy_val = float(df_dc_dongy["Val_Tong_GT"].sum())
        dc_dongy_qty = float(df_dc_dongy["Qty_Lech"].sum())
        dc_dongy_st = int(df_dc_dongy["ID ST"].replace("", pd.NA).dropna().nunique())
        
        dc_tuchoi_cases = len(df_dc_tuchoi)
        dc_tuchoi_val = float(df_dc_tuchoi["Val_Tong_GT"].sum())
        dc_tuchoi_qty = float(df_dc_tuchoi["Qty_Lech"].sum())
        dc_tuchoi_st = int(df_dc_tuchoi["ID ST"].replace("", pd.NA).dropna().nunique())
        
        dc_kiemtra_cases = len(df_dc_kiemtra)
        dc_kiemtra_val = float(df_dc_kiemtra["Val_Tong_GT"].sum())
        dc_kiemtra_qty = float(df_dc_kiemtra["Qty_Lech"].sum())
        dc_kiemtra_st = int(df_dc_kiemtra["ID ST"].replace("", pd.NA).dropna().nunique())
        
        dc_chua_cases = len(df_dc_chua)
        dc_chua_val = float(df_dc_chua["Val_Tong_GT"].sum())
        dc_chua_qty = float(df_dc_chua["Qty_Lech"].sum())
        dc_chua_st = int(df_dc_chua["ID ST"].replace("", pd.NA).dropna().nunique())
        
        if len(df_dc) > 0 and "PT trả tồn về DC" in df_dc.columns:
            has_pt = df_dc["PT trả tồn về DC"].astype(str).str.strip().apply(lambda x: bool(x and x != "" and x.lower() != "nan"))
            dc_pt_cases = int(has_pt.sum()) if len(has_pt) > 0 else 0
        else:
            dc_pt_cases = 0
        
        dc_responded_cases = dc_dongy_cases + dc_tuchoi_cases + dc_kiemtra_cases
        dc_pct_phan_hoi = round((dc_responded_cases / dc_total_cases * 100.0), 1) if dc_total_cases > 0 else 100.0
        dc_pct_dongy = round((dc_dongy_cases / dc_total_cases * 100.0), 1) if dc_total_cases > 0 else 0.0
        
        # KFM metrics on DC Đồng ý claim
        dc_dongy_done_cases = int(len(df_dc_dongy[df_dc_dongy["KFM phản hồi"] == "DONE"]))
        dc_dongy_not_done_cases = int(len(df_dc_dongy[df_dc_dongy["KFM phản hồi"] != "DONE"]))
        dc_dongy_pct_done = round((dc_dongy_done_cases / dc_dongy_cases * 100.0), 1) if dc_dongy_cases > 0 else 0.0

        # KFM metrics on DC Từ chối & Kiểm tra lại
        dc_tuchoi_kfm_replied = int(len(df_dc_tuchoi[df_dc_tuchoi["KFM phản hồi"].astype(str).str.strip() != ""]))
        dc_tuchoi_kfm_pending = dc_tuchoi_cases - dc_tuchoi_kfm_replied
        dc_kiemtra_kfm_replied = int(len(df_dc_kiemtra[df_dc_kiemtra["KFM phản hồi"].astype(str).str.strip() != ""]))
        dc_kiemtra_kfm_pending = dc_kiemtra_cases - dc_kiemtra_kfm_replied

        daily_rows.append({
            "Tháng": month_str,
            "Ngày": date_str,
            "Date_Parsed": date_parsed,
            "Tong_So_Vu": d_total,
            "Tong_SL_Chuyen": d_qty_chuyen,
            "Tong_SL_Nhan": d_qty_nhan,
            "Tong_SL_Lech": d_qty_lech,
            "Tong_Gia_Tri": d_val_total,
            
            # Số lượng Siêu Thị
            "Tong_ST": st_total_count,
            "ST_Over_100k": st_over_count,
            "ST_Under_100k": st_under_count,
            "ST_Da_Xu_Ly": st_da_xl_count,
            "ST_Dang_Xu_Ly": st_dang_xl_count,
            "ST_Khong_Xu_Ly": st_khong_xl_count,
            
            # Giá trị phân khúc theo Siêu Thị
            "Val_Over_100k": val_over_100k,
            "Val_Under_100k": val_under_100k,
            
            # Phân bổ Giá trị (VNĐ)
            "Val_Kho": float(df_kho["Val_Tong_GT"].sum()),
            "Val_ST": float(df_st["Val_Tong_GT"].sum()),
            "Val_HaoHut": float(df_hh["Val_Tong_GT"].sum()),
            
            # Tiến độ Giá trị (VNĐ)
            "Val_Da_Xu_Ly": float(df_da_xl["Val_Tong_GT"].sum()),
            "Val_Dang_Xu_Ly": val_dang_xl,
            "Val_Khong_Xu_Ly": val_khong_xl,
            "Pct_Da_Xu_Ly": pct_val_da_xl,
            
            # Phân bổ Số lượng (PCS / KG)
            "SL_Kho": float(df_kho["Qty_Lech"].sum()),
            "SL_ST": float(df_st["Qty_Lech"].sum()),
            "SL_HaoHut": float(df_hh["Qty_Lech"].sum()),
            
            # Tiến độ Số lượng (PCS / KG)
            "SL_Da_Xu_Ly": float(df_da_xl["Qty_Lech"].sum()),
            "SL_Dang_Xu_Ly": sl_dang_xl,
            "SL_Khong_Xu_Ly": sl_khong_xl,
            "Pct_SL_Da_Xu_Ly": pct_sl_da_xl,
            
            # Thống kê chi tiết Số Vụ Việc (Cases) & Tiến Độ Từng Nhóm Ngưỡng
            "Cases_Over_100k": len(df_over),
            "Cases_Under_100k": len(df_under),
            "Cases_Over_Da_XL": len(df_over[df_over["Status_3Level"] == "Đã xử lý"]),
            "Cases_Over_Dang_XL": len(df_over[df_over["Status_3Level"] == "Đang xử lý"]),
            "Cases_Under_Da_XL": len(df_under[df_under["Status_3Level"] == "Đã xử lý"]),
            "Cases_Under_Khong_XL": len(df_under[df_under["Status_3Level"] == "Không xử lý"]),
            "ST_Over_Da_XL": int(df_over[df_over["Status_3Level"] == "Đã xử lý"]["ID ST"].replace("", pd.NA).dropna().nunique()),
            "ST_Over_Dang_XL": int(df_over[df_over["Status_3Level"] == "Đang xử lý"]["ID ST"].replace("", pd.NA).dropna().nunique()),
            "ST_Under_Da_XL": int(df_under[df_under["Status_3Level"] == "Đã xử lý"]["ID ST"].replace("", pd.NA).dropna().nunique()),
            "ST_Under_Khong_XL": int(df_under[df_under["Status_3Level"] == "Không xử lý"]["ID ST"].replace("", pd.NA).dropna().nunique()),
            "Pct_Over_Da_XL": round(float((df_over[df_over["Status_3Level"] == "Đã xử lý"]["Val_Tong_GT"].sum() / val_over_100k * 100.0) if val_over_100k > 0 else 100.0), 1),
            "Pct_Under_Da_XL": round(float((df_under[df_under["Status_3Level"] == "Đã xử lý"]["Val_Tong_GT"].sum() / val_under_100k * 100.0) if val_under_100k > 0 else 100.0), 1),
            
            # Thống kê chuyên sâu Xử Lý Trả DC & DC Phản Hồi
            "DC_Total_Cases": dc_total_cases,
            "DC_Total_Qty": dc_total_qty,
            "DC_Total_Val": dc_total_val,
            "DC_ST_Count": dc_st_count,
            "DC_DongY_Cases": dc_dongy_cases,
            "DC_DongY_Val": dc_dongy_val,
            "DC_DongY_Qty": dc_dongy_qty,
            "DC_DongY_ST": dc_dongy_st,
            "DC_DongY_Done_Cases": dc_dongy_done_cases,
            "DC_DongY_Not_Done_Cases": dc_dongy_not_done_cases,
            "DC_DongY_Pct_Done": dc_dongy_pct_done,
            "DC_TuChoi_Cases": dc_tuchoi_cases,
            "DC_TuChoi_Val": dc_tuchoi_val,
            "DC_TuChoi_Qty": dc_tuchoi_qty,
            "DC_TuChoi_ST": dc_tuchoi_st,
            "DC_TuChoi_KFM_Replied": dc_tuchoi_kfm_replied,
            "DC_TuChoi_KFM_Pending": dc_tuchoi_kfm_pending,
            "DC_KiemTra_Cases": dc_kiemtra_cases,
            "DC_KiemTra_Val": dc_kiemtra_val,
            "DC_KiemTra_Qty": dc_kiemtra_qty,
            "DC_KiemTra_ST": dc_kiemtra_st,
            "DC_KiemTra_KFM_Replied": dc_kiemtra_kfm_replied,
            "DC_KiemTra_KFM_Pending": dc_kiemtra_kfm_pending,
            "DC_Chua_Cases": dc_chua_cases,
            "DC_Chua_Val": dc_chua_val,
            "DC_Chua_Qty": dc_chua_qty,
            "DC_Chua_ST": dc_chua_st,
            "DC_PT_Cases": dc_pt_cases,
            "DC_Pct_Phan_Hoi": dc_pct_phan_hoi,
            "DC_Pct_DongY": dc_pct_dongy
        })
        
    df_daily = pd.DataFrame(daily_rows)
    if "Date_Parsed" in df_daily.columns:
        df_daily.sort_values(by="Date_Parsed", ascending=False, inplace=True)
        
    return df_daily, {}
