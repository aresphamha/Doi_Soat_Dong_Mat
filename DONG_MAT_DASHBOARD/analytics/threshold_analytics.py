"""
Module phân tích chuyên sâu Ngưỡng giá trị (Tính trên Tổng tiền lệch của Siêu thị trong Ngày)
và Phân loại trạng thái xử lý 3 cấp (Đã xử lý, Đang xử lý, Chưa xử lý) chuẩn nghiệp vụ SCM.
Tối ưu hóa Vectorization 100% cho tốc độ xử lý hàng trăm nghìn dòng chỉ trong chớp mắt.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def determine_case_destination(row) -> str:
    """Xác định điểm quy trách nhiệm / trả tồn chính (Fallback cho 1 dòng đơn lẻ)."""
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
        
    k = float(row.get("Val_Tong_Kho", 0.0) or 0.0)
    s = float(row.get("Val_Tong_ST", 0.0) or 0.0)
    h = float(row.get("Val_Tong_HaoHut", 0.0) or 0.0)
    c = float(row.get("Val_Tong_CXD", 0.0) or 0.0)
    
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
    """Quy chuẩn trạng thái xử lý 3 cấp (Fallback cho 1 dòng đơn lẻ)."""
    dest = row.get("Destination", "")
    if not dest:
        dest = determine_case_destination(row)
        
    if dest in ["Kho ĐÔNG MÁT", "Siêu thị", "Hao hụt"]:
        return "Đã xử lý"
    
    is_over = bool(row.get("Is_Store_Over_100k", False))
    if is_over:
        return "Đang xử lý"
    else:
        return "Không xử lý"


def enrich_dataframe_with_threshold_and_status(df: pd.DataFrame, threshold: float = 100000.0, df_full_for_store_total: pd.DataFrame = None) -> pd.DataFrame:
    """
    Bổ sung thông tin nhanh bằng Vectorized Numpy:
    1. Destination
    2. Store_Day_Val_Total & Is_Store_Over_100k
    3. Status_3Level
    """
    if len(df) == 0:
        return df.copy()
        
    df_work = df.copy()
    
    # 1. Vectorized Destination
    if "Destination" not in df_work.columns or df_work["Destination"].isnull().any():
        vk = pd.to_numeric(df_work.get("Val_Tong_Kho", 0.0), errors="coerce").fillna(0.0).values
        vst = pd.to_numeric(df_work.get("Val_Tong_ST", 0.0), errors="coerce").fillna(0.0).values
        vhh = pd.to_numeric(df_work.get("Val_Tong_HaoHut", 0.0), errors="coerce").fillna(0.0).values
        
        dests = np.full(len(df_work), "Chưa xác định", dtype=object)
        mask_hh = (vhh > 0)
        mask_st = (vst > 0)
        mask_k = (vk > 0)
        
        dests[mask_hh] = "Hao hụt"
        dests[mask_st] = "Siêu thị"
        dests[mask_k] = "Kho ĐÔNG MÁT"
        
        df_work["Destination"] = dests
    
    # 2. Vectorized Store-Day total & Ngưỡng 100k
    if "Is_Store_Over_100k" not in df_work.columns or "Store_Day_Val_Total" not in df_work.columns:
        st_col = "ID ST" if "ID ST" in df_work.columns else "Chi nhánh nhận"
        ref_df = df_full_for_store_total if df_full_for_store_total is not None else df_work
        
        st_totals = ref_df.groupby(["Date_Str", st_col])["Val_Tong_GT"].sum().reset_index()
        st_totals.rename(columns={"Val_Tong_GT": "Store_Day_Val_Total"}, inplace=True)
        
        if "Store_Day_Val_Total" in df_work.columns:
            df_work.drop(columns=["Store_Day_Val_Total"], inplace=True)
        if "Is_Store_Over_100k" in df_work.columns:
            df_work.drop(columns=["Is_Store_Over_100k"], inplace=True)
            
        df_work = df_work.merge(st_totals, on=["Date_Str", st_col], how="left")
        df_work["Store_Day_Val_Total"] = df_work["Store_Day_Val_Total"].fillna(0.0)
        df_work["Is_Store_Over_100k"] = df_work["Store_Day_Val_Total"] >= threshold

    # 3. Vectorized Status_3Level
    if "Status_3Level" not in df_work.columns or df_work["Status_3Level"].isnull().any():
        dests = df_work["Destination"].values
        is_over = df_work["Is_Store_Over_100k"].values
        
        status = np.full(len(df_work), "Không xử lý", dtype=object)
        mask_done = np.isin(dests, ["Kho ĐÔNG MÁT", "Siêu thị", "Hao hụt"])
        mask_pending = (~mask_done) & is_over
        
        status[mask_done] = "Đã xử lý"
        status[mask_pending] = "Đang xử lý"
        df_work["Status_3Level"] = status
    
    return df_work


def analyze_threshold_metrics(df: pd.DataFrame, threshold: float = 100000.0, df_full: pd.DataFrame = None) -> Dict[str, Any]:
    """Tính toán tỷ trọng ST và Giá trị theo ngưỡng 100k."""
    total_records = len(df)
    if total_records == 0:
        return {
            "total_records": 0, "total_val": 0.0, "total_qty_lech": 0.0, "threshold": threshold,
            "over_stores_days": 0, "under_stores_days": 0, "over_val": 0.0, "under_val": 0.0
        }
        
    df_work = enrich_dataframe_with_threshold_and_status(df, threshold=threshold, df_full_for_store_total=df_full)
    
    total_val = float(df_work["Val_Tong_GT"].sum())
    total_qty = float(df_work["Qty_Lech"].sum())
    denom_val = total_val if total_val > 0 else 1.0
    
    st_col = "ID ST" if "ID ST" in df_work.columns else "Chi nhánh nhận"
    st_day_df = df_work.groupby(["Date_Str", st_col])["Store_Day_Val_Total"].first()
    
    over_stores_days = int((st_day_df >= threshold).sum())
    under_stores_days = int((st_day_df < threshold).sum())
    
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
    """Tổng hợp bảng thống kê đa chiều theo từng Ngày siêu tốc."""
    if len(df) == 0:
        return pd.DataFrame(), {}
        
    df_work = enrich_dataframe_with_threshold_and_status(df, threshold=threshold, df_full_for_store_total=df_full)
    daily_rows = []
    
    st_col = "ID ST" if "ID ST" in df_work.columns else "Chi nhánh nhận"
    
    for date_str, group in df_work.groupby("Date_Str", sort=False):
        d_total = len(group)
        d_val_total = float(group["Val_Tong_GT"].sum())
        d_qty_lech = float(group["Qty_Lech"].sum())
        d_qty_chuyen = float(group["Qty_Chuyen"].sum())
        d_qty_nhan = float(group["Qty_Nhan"].sum())
        
        # Thống kê ST theo ngày
        st_day_grp = group.groupby(st_col)["Store_Day_Val_Total"].first()
        st_over_set = set(st_day_grp[st_day_grp >= threshold].index)
        st_under_set = set(st_day_grp[st_day_grp < threshold].index)
        
        st_over_count = len(st_over_set)
        st_under_count = len(st_under_set)
        st_total_count = group[st_col].replace("", pd.NA).dropna().nunique()
        
        # Nhóm dòng theo ST >= 100k vs < 100k
        df_over = group[group[st_col].isin(st_over_set)]
        df_under = group[group[st_col].isin(st_under_set)]
        
        val_over_100k = float(df_over["Val_Tong_GT"].sum())
        val_under_100k = float(df_under["Val_Tong_GT"].sum())
        
        # Điểm nhận
        df_kho = group[group["Destination"] == "Kho ĐÔNG MÁT"]
        df_st = group[group["Destination"] == "Siêu thị"]
        df_hh = group[group["Destination"] == "Hao hụt"]
        
        # Trạng thái 3 cấp
        df_da_xl = group[group["Status_3Level"] == "Đã xử lý"]
        df_dang_xl = group[group["Status_3Level"] == "Đang xử lý"]
        df_khong_xl = group[group["Status_3Level"] == "Không xử lý"]
        
        st_da_xl_count = df_da_xl[st_col].replace("", pd.NA).dropna().nunique()
        st_dang_xl_count = df_dang_xl[st_col].replace("", pd.NA).dropna().nunique()
        st_khong_xl_count = df_khong_xl[st_col].replace("", pd.NA).dropna().nunique()
        
        val_dang_xl = float(df_dang_xl["Val_Tong_GT"].sum())
        val_khong_xl = float(df_khong_xl["Val_Tong_GT"].sum())
        sl_dang_xl = float(df_dang_xl["Qty_Lech"].sum())
        sl_khong_xl = float(df_khong_xl["Qty_Lech"].sum())
        
        date_parsed = group["Date_Parsed"].iloc[0] if "Date_Parsed" in group.columns else pd.NaT
        month_str = f"Tháng {date_parsed.month}" if pd.notna(date_parsed) else "Tháng 8"
        
        pct_val_da_xl = (df_da_xl["Val_Tong_GT"].sum() / d_val_total * 100.0) if d_val_total > 0 else 0.0
        pct_sl_da_xl = (df_da_xl["Qty_Lech"].sum() / d_qty_lech * 100.0) if d_qty_lech > 0 else 0.0
        
        # DC Confirmations
        dc_conf_col = "DC_Confirm" if "DC_Confirm" in group.columns else ("DC xác nhận" if "DC xác nhận" in group.columns else None)
        kfm_reply_col = "KFM_Reply" if "KFM_Reply" in group.columns else ("KFM phản hồi" if "KFM phản hồi" in group.columns else None)
        
        df_dc = df_kho
        dc_total_cases = len(df_dc)
        dc_total_qty = float(df_dc["Qty_Lech"].sum())
        dc_total_val = float(df_dc["Val_Tong_GT"].sum())
        dc_st_count = int(df_dc[st_col].replace("", pd.NA).dropna().nunique())
        
        if dc_conf_col and len(df_dc) > 0:
            df_dc_dongy = df_dc[df_dc[dc_conf_col].astype(str).str.contains("Đồng ý", case=False, na=False)]
            df_dc_tuchoi = df_dc[df_dc[dc_conf_col].astype(str).str.contains("Từ chối", case=False, na=False)]
            df_dc_kiemtra = df_dc[df_dc[dc_conf_col].astype(str).str.contains("Kiểm tra", case=False, na=False)]
            df_dc_chua = df_dc[~df_dc.index.isin(df_dc_dongy.index.union(df_dc_tuchoi.index).union(df_dc_kiemtra.index))]
        else:
            df_dc_dongy = df_dc.iloc[0:0]
            df_dc_tuchoi = df_dc.iloc[0:0]
            df_dc_kiemtra = df_dc.iloc[0:0]
            df_dc_chua = df_dc
            
        dc_dongy_cases = len(df_dc_dongy)
        dc_dongy_val = float(df_dc_dongy["Val_Tong_GT"].sum())
        dc_dongy_qty = float(df_dc_dongy["Qty_Lech"].sum())
        dc_dongy_st = int(df_dc_dongy[st_col].replace("", pd.NA).dropna().nunique())
        
        dc_tuchoi_cases = len(df_dc_tuchoi)
        dc_tuchoi_val = float(df_dc_tuchoi["Val_Tong_GT"].sum())
        dc_tuchoi_qty = float(df_dc_tuchoi["Qty_Lech"].sum())
        dc_tuchoi_st = int(df_dc_tuchoi[st_col].replace("", pd.NA).dropna().nunique())
        
        dc_kiemtra_cases = len(df_dc_kiemtra)
        dc_kiemtra_val = float(df_dc_kiemtra["Val_Tong_GT"].sum())
        dc_kiemtra_qty = float(df_dc_kiemtra["Qty_Lech"].sum())
        dc_kiemtra_st = int(df_dc_kiemtra[st_col].replace("", pd.NA).dropna().nunique())
        
        dc_chua_cases = len(df_dc_chua)
        dc_chua_val = float(df_dc_chua["Val_Tong_GT"].sum())
        dc_chua_qty = float(df_dc_chua["Qty_Lech"].sum())
        dc_chua_st = int(df_dc_chua[st_col].replace("", pd.NA).dropna().nunique())
        
        dc_responded_cases = dc_dongy_cases + dc_tuchoi_cases + dc_kiemtra_cases
        dc_pct_phan_hoi = round((dc_responded_cases / dc_total_cases * 100.0), 1) if dc_total_cases > 0 else 100.0
        dc_pct_dongy = round((dc_dongy_cases / dc_total_cases * 100.0), 1) if dc_total_cases > 0 else 0.0
        
        dc_dongy_done_cases = int(len(df_dc_dongy[df_dc_dongy[kfm_reply_col] == "DONE"])) if kfm_reply_col and len(df_dc_dongy) > 0 else 0
        dc_dongy_not_done_cases = dc_dongy_cases - dc_dongy_done_cases
        dc_dongy_pct_done = round((dc_dongy_done_cases / dc_dongy_cases * 100.0), 1) if dc_dongy_cases > 0 else 0.0

        dc_tuchoi_kfm_replied = int(len(df_dc_tuchoi[df_dc_tuchoi[kfm_reply_col].astype(str).str.strip() != ""])) if kfm_reply_col and len(df_dc_tuchoi) > 0 else 0
        dc_tuchoi_kfm_pending = dc_tuchoi_cases - dc_tuchoi_kfm_replied
        dc_tuchoi_pct_replied = round((dc_tuchoi_kfm_replied / dc_tuchoi_cases * 100.0), 1) if dc_tuchoi_cases > 0 else 0.0

        dc_kiemtra_kfm_replied = int(len(df_dc_kiemtra[df_dc_kiemtra[kfm_reply_col].astype(str).str.strip() != ""])) if kfm_reply_col and len(df_dc_kiemtra) > 0 else 0
        dc_kiemtra_kfm_pending = dc_kiemtra_cases - dc_kiemtra_kfm_replied
        dc_kiemtra_pct_replied = round((dc_kiemtra_kfm_replied / dc_kiemtra_cases * 100.0), 1) if dc_kiemtra_cases > 0 else 0.0

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
            
            # Thống kê chi tiết Số Vụ Việc (Cases)
            "Cases_Over_100k": len(df_over),
            "Cases_Under_100k": len(df_under),
            "Cases_Over_Da_XL": len(df_over[df_over["Status_3Level"] == "Đã xử lý"]),
            "Cases_Over_Dang_XL": len(df_over[df_over["Status_3Level"] == "Đang xử lý"]),
            "Cases_Under_Da_XL": len(df_under[df_under["Status_3Level"] == "Đã xử lý"]),
            "Cases_Under_Khong_XL": len(df_under[df_under["Status_3Level"] == "Không xử lý"]),
            "ST_Over_Da_XL": int(df_over[df_over["Status_3Level"] == "Đã xử lý"][st_col].replace("", pd.NA).dropna().nunique()),
            "ST_Over_Dang_XL": int(df_over[df_over["Status_3Level"] == "Đang xử lý"][st_col].replace("", pd.NA).dropna().nunique()),
            "ST_Under_Da_XL": int(df_under[df_under["Status_3Level"] == "Đã xử lý"][st_col].replace("", pd.NA).dropna().nunique()),
            "ST_Under_Khong_XL": int(df_under[df_under["Status_3Level"] == "Không xử lý"][st_col].replace("", pd.NA).dropna().nunique()),
            "Pct_Over_Da_XL": round(float((df_over[df_over["Status_3Level"] == "Đã xử lý"]["Val_Tong_GT"].sum() / val_over_100k * 100.0) if val_over_100k > 0 else 100.0), 1),
            "Pct_Under_Da_XL": round(float((df_under[df_under["Status_3Level"] == "Đã xử lý"]["Val_Tong_GT"].sum() / val_under_100k * 100.0) if val_under_100k > 0 else 100.0), 1),
            
            # Thống kê DC Phản Hồi
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
            "DC_TuChoi_Pct_Replied": dc_tuchoi_pct_replied,
            "DC_KiemTra_Cases": dc_kiemtra_cases,
            "DC_KiemTra_Val": dc_kiemtra_val,
            "DC_KiemTra_Qty": dc_kiemtra_qty,
            "DC_KiemTra_ST": dc_kiemtra_st,
            "DC_KiemTra_KFM_Replied": dc_kiemtra_kfm_replied,
            "DC_KiemTra_KFM_Pending": dc_kiemtra_kfm_pending,
            "DC_KiemTra_Pct_Replied": dc_kiemtra_pct_replied,
            "DC_Chua_Cases": dc_chua_cases,
            "DC_Chua_Val": dc_chua_val,
            "DC_Chua_Qty": dc_chua_qty,
            "DC_Chua_ST": dc_chua_st,
            "DC_Pct_Phan_Hoi": dc_pct_phan_hoi,
            "DC_Pct_DongY": dc_pct_dongy
        })
        
    df_daily = pd.DataFrame(daily_rows)
    if "Date_Parsed" in df_daily.columns:
        df_daily.sort_values(by="Date_Parsed", ascending=False, inplace=True)
        
    return df_daily, {}
