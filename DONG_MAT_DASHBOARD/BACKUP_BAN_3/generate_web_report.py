# -*- coding: utf-8 -*-
"""
Hệ thống tạo Báo Cáo Web Đối Soát ĐÔNG - MÁT & THỊT CÁ Tự Động Hóa 100%.
Hợp nhất dữ liệu từ cả 3 nguồn Google Sheets:
1. Báo cáo gốc ĐÔNG MÁT (Mát & Đông)
2. Báo cáo Thịt Cá Tháng 7 + 8 (KFM - SCF)
3. Báo cáo Thịt Cá 28.08 - 09.26 (KFM - SCF) Mới
"""

import os
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import shutil
import time
from datetime import datetime
import pandas as pd
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from data.data_loader import fetch_all_sources_combined
from data.data_processor import process_dong_mat_dataframe
from analytics.threshold_analytics import (
    determine_case_destination,
    enrich_dataframe_with_threshold_and_status,
    analyze_threshold_metrics,
    get_daily_threshold_breakdown
)


def compute_store_priority_list(df_in: pd.DataFrame) -> list:
    """Tính toán danh sách Siêu thị ưu tiên xử lý (Bảng 4) siêu nhanh - Vectorized 100%."""
    if len(df_in) == 0:
        return []
    
    st_col = "ID ST" if "ID ST" in df_in.columns else "Chi nhánh nhận"
    name_col = "Chi nhánh nhận"
    grp_cols = ["Date_Str", st_col, name_col, "Nhóm hàng", "Is_Store_Over_100k"]
    
    base_agg = df_in.groupby(grp_cols, as_index=False, dropna=False).agg(
        sku_count=("Val_Tong_GT", "count"),
        qty_diff_total=("Qty_Lech", "sum"),
        val_total=("Val_Tong_GT", "sum"),
        date_parsed=("Date_Parsed", "first")
    )
    
    piv = df_in.pivot_table(
        index=grp_cols,
        columns="Status_3Level",
        values="Val_Tong_GT",
        aggfunc="sum",
        fill_value=0.0
    ).reset_index()
    
    for c in ["Đã xử lý", "Đang xử lý", "Không xử lý"]:
        if c not in piv.columns:
            piv[c] = 0.0
            
    merged = base_agg.merge(piv[grp_cols + ["Đã xử lý", "Đang xử lý", "Không xử lý"]], on=grp_cols, how="left")
    
    records = []
    for _, r in merged.iterrows():
        val_tot = round(float(r["val_total"]), 2)
        val_da = round(float(r["Đã xử lý"]), 2)
        val_dang = round(float(r["Đang xử lý"]), 2)
        val_khong = round(float(r["Không xử lý"]), 2)
        
        if val_dang > 0:
            prio = "p1"
        elif val_khong > 0:
            prio = "p2"
        else:
            prio = "p3"
            
        pct_done = round((val_da / val_tot * 100), 1) if val_tot > 0 else 100.0
        d_parsed = r["date_parsed"]
        month_str = f"Tháng {d_parsed.month}" if pd.notnull(d_parsed) else "Tháng 8"
        
        records.append({
            "date": str(r["Date_Str"]),
            "month": month_str,
            "st": str(r[st_col]),
            "store_name": str(r[name_col]),
            "group": str(r["Nhóm hàng"]),
            "is_store_over_100k": bool(r["Is_Store_Over_100k"]),
            "sku_count": int(r["sku_count"]),
            "qty_diff_total": round(float(r["qty_diff_total"]), 2),
            "val_total": val_tot,
            "val_da_xl": val_da,
            "val_dang_xl": val_dang,
            "val_khong_xl": val_khong,
            "priority": prio,
            "pct_done": str(pct_done)
        })
    return records


def compute_group_bundle(df_sub: pd.DataFrame, df_full: pd.DataFrame, threshold: float = 100000.0) -> dict:
    if len(df_sub) == 0:
        return {
            "daily_matrix": [],
            "monthly_matrix": [],
            "overall_metrics": {},
            "grand_total": {}
        }

    overall_metrics = analyze_threshold_metrics(df_sub, threshold=threshold, df_full=df_full)
    df_daily_th, _ = get_daily_threshold_breakdown(df_sub, threshold=threshold, df_full=df_full)

    # Tính monthly matrix trực tiếp từ df_daily_th mà không cần lặp lại
    agg_dict = {
        "Tong_So_Vu": "sum", "Tong_SL_Chuyen": "sum", "Tong_SL_Nhan": "sum", "Tong_SL_Lech": "sum",
        "Tong_Gia_Tri": "sum", "Tong_ST": "sum", "ST_Over_100k": "sum", "ST_Under_100k": "sum",
        "ST_Da_Xu_Ly": "sum", "ST_Dang_Xu_Ly": "sum", "ST_Khong_Xu_Ly": "sum",
        "Val_Over_100k": "sum", "Val_Under_100k": "sum", "Val_Kho": "sum", "Val_ST": "sum",
        "Val_HaoHut": "sum", "Val_Da_Xu_Ly": "sum", "Val_Dang_Xu_Ly": "sum", "Val_Khong_Xu_Ly": "sum",
        "SL_Kho": "sum", "SL_ST": "sum", "SL_HaoHut": "sum", "SL_Da_Xu_Ly": "sum",
        "SL_Dang_Xu_Ly": "sum", "SL_Khong_Xu_Ly": "sum",
        "DC_Total_Cases": "sum", "DC_Total_Qty": "sum", "DC_Total_Val": "sum", "DC_ST_Count": "sum",
        "DC_DongY_Cases": "sum", "DC_DongY_Val": "sum", "DC_DongY_Qty": "sum", "DC_DongY_ST": "sum",
        "DC_DongY_Done_Cases": "sum", "DC_DongY_Not_Done_Cases": "sum",
        "DC_TuChoi_Cases": "sum", "DC_TuChoi_Val": "sum", "DC_TuChoi_Qty": "sum", "DC_TuChoi_ST": "sum",
        "DC_TuChoi_KFM_Replied": "sum", "DC_TuChoi_KFM_Pending": "sum",
        "DC_KiemTra_Cases": "sum", "DC_KiemTra_Val": "sum", "DC_KiemTra_Qty": "sum", "DC_KiemTra_ST": "sum",
        "DC_KiemTra_KFM_Replied": "sum", "DC_KiemTra_KFM_Pending": "sum",
        "DC_Chua_Cases": "sum", "DC_Chua_Val": "sum", "DC_Chua_Qty": "sum", "DC_Chua_ST": "sum"
    }
    agg_clean = {k: v for k, v in agg_dict.items() if k in df_daily_th.columns}
    df_monthly = df_daily_th.groupby("Tháng").agg(agg_clean).reset_index() if len(df_daily_th) > 0 else pd.DataFrame()

    daily_matrix_list = []
    for _, tr in df_daily_th.iterrows():
        daily_matrix_list.append({
            "month": str(tr.get("Tháng", "Tháng 8")),
            "date": str(tr.get("Ngày", "")),
            "total_cases": int(tr.get("Tong_So_Vu", 0)),
            
            # Khối Số lượng giao nhận
            "qty_chuyen": round(float(tr.get("Tong_SL_Chuyen", 0.0)), 2),
            "qty_nhan": round(float(tr.get("Tong_SL_Nhan", 0.0)), 2),
            "qty_lech": round(float(tr.get("Tong_SL_Lech", 0.0)), 2),
            
            # Khối Đếm Số Lượng Siêu Thị
            "stores_count": int(tr.get("Tong_ST", 0)),
            "stores_over_100k": int(tr.get("ST_Over_100k", 0)),
            "stores_under_100k": int(tr.get("ST_Under_100k", 0)),
            "st_da_xl": int(tr.get("ST_Da_Xu_Ly", 0)),
            "st_dang_xl": int(tr.get("ST_Dang_Xu_Ly", 0)),
            "st_khong_xl": int(tr.get("ST_Khong_Xu_Ly", 0)),
            "st_over_da_xl": int(tr.get("ST_Over_Da_XL", 0)),
            "st_over_dang_xl": int(tr.get("ST_Over_Dang_XL", 0)),
            "st_under_da_xl": int(tr.get("ST_Under_Da_XL", 0)),
            "st_under_khong_xl": int(tr.get("ST_Under_Khong_XL", 0)),
            
            # Khối Số lượng điểm nhận
            "sl_kho": round(float(tr.get("SL_Kho", 0.0)), 2),
            "sl_st": round(float(tr.get("SL_ST", 0.0)), 2),
            "sl_haohut": round(float(tr.get("SL_HaoHut", 0.0)), 2),
            
            # Khối Số lượng tiến độ 3 Cột
            "sl_da_xl": round(float(tr.get("SL_Da_Xu_Ly", 0.0)), 2),
            "sl_dang_xl": round(float(tr.get("SL_Dang_Xu_Ly", 0.0)), 2),
            "sl_khong_xl": round(float(tr.get("SL_Khong_Xu_Ly", 0.0)), 2),
            "pct_sl_da_xl": round(float(tr.get("Pct_SL_Da_Xu_Ly", 0.0)), 1),
            
            # Khối Giá trị (VNĐ) thuần túy
            "val_total": float(tr.get("Tong_Gia_Tri", 0.0)),
            "val_over_100k": float(tr.get("Val_Over_100k", 0.0)),
            "val_under_100k": float(tr.get("Val_Under_100k", 0.0)),
            "val_kho": float(tr.get("Val_Kho", 0.0)),
            "val_st": float(tr.get("Val_ST", 0.0)),
            "val_haohut": float(tr.get("Val_HaoHut", 0.0)),
            "val_da_xl": float(tr.get("Val_Da_Xu_Ly", 0.0)),
            "val_dang_xl": float(tr.get("Val_Dang_Xu_Ly", 0.0)),
            "val_khong_xl": float(tr.get("Val_Khong_Xu_Ly", 0.0)),
            "pct_val_da_xl": round(float(tr.get("Pct_Da_Xu_Ly", 0.0)), 1),
            
            # Thống kê Case theo Nhóm Ngưỡng & Tỷ lệ xử lý từng nhóm
            "cases_over_100k": int(tr.get("Cases_Over_100k", 0)),
            "cases_under_100k": int(tr.get("Cases_Under_100k", 0)),
            "cases_over_da_xl": int(tr.get("Cases_Over_Da_XL", 0)),
            "cases_over_dang_xl": int(tr.get("Cases_Over_Dang_XL", 0)),
            "cases_under_da_xl": int(tr.get("Cases_Under_Da_XL", 0)),
            "cases_under_khong_xl": int(tr.get("Cases_Under_Khong_XL", 0)),
            "pct_over_da_xl": round(float(tr.get("Pct_Over_Da_XL", 0.0)), 1),
            "pct_under_da_xl": round(float(tr.get("Pct_Under_Da_XL", 0.0)), 1),

            # Thống kê chuyên sâu Xử Lý Trả DC & DC Phản Hồi (4 Cột AD - AG)
            "dc_total_cases": int(tr.get("DC_Total_Cases", 0)),
            "dc_total_qty": round(float(tr.get("DC_Total_Qty", 0.0)), 2),
            "dc_total_val": float(tr.get("DC_Total_Val", 0.0)),
            "dc_st_count": int(tr.get("DC_ST_Count", 0)),
            "dc_dongy_cases": int(tr.get("DC_DongY_Cases", 0)),
            "dc_dongy_val": float(tr.get("DC_DongY_Val", 0.0)),
            "dc_dongy_qty": round(float(tr.get("DC_DongY_Qty", 0.0)), 2),
            "dc_dongy_st": int(tr.get("DC_DongY_ST", 0)),
            "dc_dongy_done_cases": int(tr.get("DC_DongY_Done_Cases", 0)),
            "dc_dongy_not_done_cases": int(tr.get("DC_DongY_Not_Done_Cases", 0)),
            "dc_dongy_pct_done": round(float(tr.get("DC_DongY_Pct_Done", 0.0)), 1),
            "dc_tuchoi_cases": int(tr.get("DC_TuChoi_Cases", 0)),
            "dc_tuchoi_val": float(tr.get("DC_TuChoi_Val", 0.0)),
            "dc_tuchoi_st": int(tr.get("DC_TuChoi_ST", 0)),
            "dc_tuchoi_kfm_replied": int(tr.get("DC_TuChoi_KFM_Replied", 0)),
            "dc_tuchoi_kfm_pending": int(tr.get("DC_TuChoi_KFM_Pending", 0)),
            "dc_tuchoi_pct_replied": round(float(tr.get("DC_TuChoi_Pct_Replied", 0.0)), 1),
            "dc_kiemtra_cases": int(tr.get("DC_KiemTra_Cases", 0)),
            "dc_kiemtra_val": float(tr.get("DC_KiemTra_Val", 0.0)),
            "dc_kiemtra_st": int(tr.get("DC_KiemTra_ST", 0)),
            "dc_kiemtra_kfm_replied": int(tr.get("DC_KiemTra_KFM_Replied", 0)),
            "dc_kiemtra_kfm_pending": int(tr.get("DC_KiemTra_KFM_Pending", 0)),
            "dc_kiemtra_pct_replied": round(float(tr.get("DC_KiemTra_Pct_Replied", 0.0)), 1),
            "dc_chua_cases": int(tr.get("DC_Chua_Cases", 0)),
            "dc_chua_val": float(tr.get("DC_Chua_Val", 0.0)),
            "dc_chua_st": int(tr.get("DC_Chua_ST", 0)),
            "dc_pct_phan_hoi": round(float(tr.get("DC_Pct_Phan_Hoi", 0.0)), 1),
            "dc_pct_dongy": round(float(tr.get("DC_Pct_Dong_Y", 0.0)), 1)
        })

    monthly_matrix_list = []
    for _, tr in df_monthly.iterrows():
        val_tot = float(tr.get("Tong_Gia_Tri", 0.0))
        val_da = float(tr.get("Val_Da_Xu_Ly", 0.0))
        sl_tot = float(tr.get("Tong_SL_Lech", 0.0))
        sl_da = float(tr.get("SL_Da_Xu_Ly", 0.0))
        
        monthly_matrix_list.append({
            "month": str(tr.get("Tháng", "")),
            "total_cases": int(tr.get("Tong_So_Vu", 0)),
            "qty_chuyen": round(float(tr.get("Tong_SL_Chuyen", 0.0)), 2),
            "qty_nhan": round(float(tr.get("Tong_SL_Nhan", 0.0)), 2),
            "qty_lech": round(float(tr.get("Tong_SL_Lech", 0.0)), 2),
            "stores_count": int(tr.get("Tong_ST", 0)),
            "stores_over_100k": int(tr.get("ST_Over_100k", 0)),
            "stores_under_100k": int(tr.get("ST_Under_100k", 0)),
            "st_da_xl": int(tr.get("ST_Da_Xu_Ly", 0)),
            "st_dang_xl": int(tr.get("ST_Dang_Xu_Ly", 0)),
            "st_khong_xl": int(tr.get("ST_Khong_Xu_Ly", 0)),
            "sl_kho": round(float(tr.get("SL_Kho", 0.0)), 2),
            "sl_st": round(float(tr.get("SL_ST", 0.0)), 2),
            "sl_haohut": round(float(tr.get("SL_HaoHut", 0.0)), 2),
            "sl_da_xl": round(sl_da, 2),
            "sl_dang_xl": round(float(tr.get("SL_Dang_Xu_Ly", 0.0)), 2),
            "sl_khong_xl": round(float(tr.get("SL_Khong_Xu_Ly", 0.0)), 2),
            "pct_sl_da_xl": round(sl_da / sl_tot * 100.0, 1) if sl_tot > 0 else 0.0,
            "val_total": val_tot,
            "val_over_100k": float(tr.get("Val_Over_100k", 0.0)),
            "val_under_100k": float(tr.get("Val_Under_100k", 0.0)),
            "val_kho": float(tr.get("Val_Kho", 0.0)),
            "val_st": float(tr.get("Val_ST", 0.0)),
            "val_haohut": float(tr.get("Val_HaoHut", 0.0)),
            "val_da_xl": val_da,
            "val_dang_xl": float(tr.get("Val_Dang_Xu_Ly", 0.0)),
            "val_khong_xl": float(tr.get("Val_Khong_Xu_Ly", 0.0)),
            "pct_val_da_xl": round(val_da / val_tot * 100.0, 1) if val_tot > 0 else 0.0,
            
            # Thống kê DC Theo Tháng
            "dc_total_cases": int(tr.get("DC_Total_Cases", 0)),
            "dc_total_qty": round(float(tr.get("DC_Total_Qty", 0.0)), 2),
            "dc_total_val": float(tr.get("DC_Total_Val", 0.0)),
            "dc_st_count": int(tr.get("DC_ST_Count", 0)),
            "dc_dongy_cases": int(tr.get("DC_DongY_Cases", 0)),
            "dc_dongy_val": float(tr.get("DC_DongY_Val", 0.0)),
            "dc_dongy_qty": round(float(tr.get("DC_DongY_Qty", 0.0)), 2),
            "dc_dongy_st": int(tr.get("DC_DongY_ST", 0)),
            "dc_dongy_done_cases": int(tr.get("DC_DongY_Done_Cases", 0)),
            "dc_dongy_not_done_cases": int(tr.get("DC_DongY_Not_Done_Cases", 0)),
            "dc_dongy_pct_done": round(float(tr.get("DC_DongY_Done_Cases", 0)) / (float(tr.get("DC_DongY_Cases", 0)) or 1.0) * 100.0, 1),
            "dc_tuchoi_cases": int(tr.get("DC_TuChoi_Cases", 0)),
            "dc_tuchoi_val": float(tr.get("DC_TuChoi_Val", 0.0)),
            "dc_tuchoi_st": int(tr.get("DC_TuChoi_ST", 0)),
            "dc_tuchoi_kfm_replied": int(tr.get("DC_TuChoi_KFM_Replied", 0)),
            "dc_tuchoi_kfm_pending": int(tr.get("DC_TuChoi_KFM_Pending", 0)),
            "dc_tuchoi_pct_replied": round(float(tr.get("DC_TuChoi_KFM_Replied", 0)) / (float(tr.get("DC_TuChoi_Cases", 0)) or 1.0) * 100.0, 1),
            "dc_kiemtra_cases": int(tr.get("DC_KiemTra_Cases", 0)),
            "dc_kiemtra_val": float(tr.get("DC_KiemTra_Val", 0.0)),
            "dc_kiemtra_st": int(tr.get("DC_KiemTra_ST", 0)),
            "dc_kiemtra_kfm_replied": int(tr.get("DC_KiemTra_KFM_Replied", 0)),
            "dc_kiemtra_kfm_pending": int(tr.get("DC_KiemTra_KFM_Pending", 0)),
            "dc_kiemtra_pct_replied": round(float(tr.get("DC_KiemTra_KFM_Replied", 0)) / (float(tr.get("DC_KiemTra_Cases", 0)) or 1.0) * 100.0, 1),
            "dc_chua_cases": int(tr.get("DC_Chua_Cases", 0)),
            "dc_chua_val": float(tr.get("DC_Chua_Val", 0.0)),
            "dc_chua_st": int(tr.get("DC_Chua_ST", 0)),
            "dc_pct_phan_hoi": round((float(tr.get("DC_DongY_Cases", 0)) + float(tr.get("DC_TuChoi_Cases", 0)) + float(tr.get("DC_KiemTra_Cases", 0))) / (float(tr.get("DC_Total_Cases", 0)) or 1.0) * 100.0, 1),
            "dc_pct_dongy": round(float(tr.get("DC_DongY_Cases", 0)) / (float(tr.get("DC_Total_Cases", 0)) or 1.0) * 100.0, 1)
        })

    # Grand Total Metrics
    df_sub_dc = df_sub[df_sub["Destination"] == "Kho ĐÔNG MÁT"]
    gt_dc_total = len(df_sub_dc)
    
    dc_conf_col = "DC_Confirm" if "DC_Confirm" in df_sub_dc.columns else ("DC xác nhận" if "DC xác nhận" in df_sub_dc.columns else None)
    kfm_reply_col = "KFM_Reply" if "KFM_Reply" in df_sub_dc.columns else ("KFM phản hồi" if "KFM phản hồi" in df_sub_dc.columns else None)
    st_col = "ID ST" if "ID ST" in df_sub_dc.columns else "Chi nhánh nhận"
    
    if dc_conf_col and gt_dc_total > 0:
        df_dc_dongy = df_sub_dc[df_sub_dc[dc_conf_col].astype(str).str.contains("Đồng ý", case=False, na=False)]
        df_dc_tuchoi = df_sub_dc[df_sub_dc[dc_conf_col].astype(str).str.contains("Từ chối", case=False, na=False)]
        df_dc_kiemtra = df_sub_dc[df_sub_dc[dc_conf_col].astype(str).str.contains("Kiểm tra", case=False, na=False)]
        df_dc_chua = df_sub_dc[~df_sub_dc.index.isin(df_dc_dongy.index.union(df_dc_tuchoi.index).union(df_dc_kiemtra.index))]
    else:
        df_dc_dongy = df_sub_dc.iloc[0:0]
        df_dc_tuchoi = df_sub_dc.iloc[0:0]
        df_dc_kiemtra = df_sub_dc.iloc[0:0]
        df_dc_chua = df_sub_dc
        
    gt_dc_dongy = len(df_dc_dongy)
    gt_dc_tuchoi = len(df_dc_tuchoi)
    gt_dc_kiemtra = len(df_dc_kiemtra)
    gt_dc_chua = len(df_dc_chua)
    
    gt_dc_resp = gt_dc_dongy + gt_dc_tuchoi + gt_dc_kiemtra
    gt_dc_pct_resp = round((gt_dc_resp / gt_dc_total * 100), 1) if gt_dc_total > 0 else 100.0
    gt_dc_pct_dongy = round((gt_dc_dongy / gt_dc_total * 100), 1) if gt_dc_total > 0 else 0.0

    gt_dc_dongy_done = int(len(df_dc_dongy[df_dc_dongy[kfm_reply_col] == "DONE"])) if kfm_reply_col and gt_dc_dongy > 0 else 0
    gt_dc_dongy_not_done = gt_dc_dongy - gt_dc_dongy_done
    gt_dc_dongy_pct_done = round((gt_dc_dongy_done / gt_dc_dongy * 100), 1) if gt_dc_dongy > 0 else 0.0

    gt_dc_tuchoi_kfm_replied = int(len(df_dc_tuchoi[df_dc_tuchoi[kfm_reply_col].astype(str).str.strip() != ""])) if kfm_reply_col and gt_dc_tuchoi > 0 else 0
    gt_dc_tuchoi_kfm_pending = gt_dc_tuchoi - gt_dc_tuchoi_kfm_replied
    gt_dc_tuchoi_pct_replied = round((gt_dc_tuchoi_kfm_replied / gt_dc_tuchoi * 100), 1) if gt_dc_tuchoi > 0 else 0.0

    gt_dc_kiemtra_kfm_replied = int(len(df_dc_kiemtra[df_dc_kiemtra[kfm_reply_col].astype(str).str.strip() != ""])) if kfm_reply_col and gt_dc_kiemtra > 0 else 0
    gt_dc_kiemtra_kfm_pending = gt_dc_kiemtra - gt_dc_kiemtra_kfm_replied
    gt_dc_kiemtra_pct_replied = round((gt_dc_kiemtra_kfm_replied / gt_dc_kiemtra * 100), 1) if gt_dc_kiemtra > 0 else 0.0

    # Cross-tab matrix
    crosstab_list = []
    for cat_name, sub in [("Đồng ý claim", df_dc_dongy), ("Từ chối claim", df_dc_tuchoi), ("Kiểm tra lại", df_dc_kiemtra), ("Chưa phản hồi", df_dc_chua)]:
        if kfm_reply_col and len(sub) > 0:
            c_done = int(len(sub[sub[kfm_reply_col] == "DONE"]))
            c_hlv = int(len(sub[sub[kfm_reply_col] == "Cấp HLV quyết định"]))
            c_check = int(len(sub[sub[kfm_reply_col] == "DC check lại thông tin"]))
            c_blank = int(len(sub[~sub[kfm_reply_col].isin(["DONE", "Cấp HLV quyết định", "DC check lại thông tin"])]))
        else:
            c_done = 0; c_hlv = 0; c_check = 0; c_blank = len(sub)
            
        crosstab_list.append({
            "key": cat_name,
            "done": c_done,
            "hlv": c_hlv,
            "check": c_check,
            "blank": c_blank,
            "total": int(len(sub))
        })

    # Top DC Notes
    dc_note_col = "DC_Note" if "DC_Note" in df_sub_dc.columns else ("NOTE.1" if "NOTE.1" in df_sub_dc.columns else None)
    top_dc_notes = []
    if dc_note_col and len(df_sub_dc) > 0:
        dc_notes_clean = df_sub_dc[df_sub_dc[dc_note_col].fillna("").astype(str).str.strip() != ""][dc_note_col].str.strip()
        top_dc_notes = [{"note": str(k), "count": int(v)} for k, v in dc_notes_clean.value_counts().head(7).items()]

    # Top KFM Notes
    kfm_note_col = "KFM_Note" if "KFM_Note" in df_sub_dc.columns else ("NOTE.2" if "NOTE.2" in df_sub_dc.columns else None)
    top_kfm_notes = []
    if kfm_note_col and len(df_sub_dc) > 0:
        kfm_notes_clean = df_sub_dc[df_sub_dc[kfm_note_col].fillna("").astype(str).str.strip() != ""][kfm_note_col].str.strip()
        top_kfm_notes = [{"note": str(k), "count": int(v)} for k, v in kfm_notes_clean.value_counts().head(7).items()]

    # Non Agree breakdown
    tc_hlv = int(len(df_dc_tuchoi[df_dc_tuchoi[kfm_reply_col] == "Cấp HLV quyết định"])) if kfm_reply_col and len(df_dc_tuchoi) > 0 else 0
    tc_pending = int(len(df_dc_tuchoi[~df_dc_tuchoi[kfm_reply_col].isin(["DONE", "Cấp HLV quyết định", "DC check lại thông tin"])])) if kfm_reply_col and len(df_dc_tuchoi) > 0 else len(df_dc_tuchoi)
    tc_other = len(df_dc_tuchoi) - tc_hlv - tc_pending
    kt_done = int(len(df_dc_kiemtra[df_dc_kiemtra[kfm_reply_col].isin(["DONE", "DC check lại thông tin"])])) if kfm_reply_col and len(df_dc_kiemtra) > 0 else 0
    kt_pending = len(df_dc_kiemtra) - kt_done
    ch_tot = len(df_dc_chua)
    
    non_agree_items = [
        {"label": "🔴 Từ Chối - Cấp HLV Quyết Định", "val": tc_hlv, "color": "#f87171"},
        {"label": "⚠️ Từ Chối - KFM Chưa Phản Hồi", "val": tc_pending, "color": "#fb923c"},
        {"label": "🟡 Kiểm Tra Lại - Đã Phản Hồi", "val": kt_done, "color": "#fbbf24"},
        {"label": "⏳ DC Chưa Phản Hồi (Trống)", "val": ch_tot, "color": "#94a3b8"},
        {"label": "🟢 Từ Chối - Đã Xử Lý Khác", "val": tc_other, "color": "#34d399"}
    ]
    non_agree_items = [x for x in non_agree_items if x["val"] > 0]

    grand_total = {
        "total_cases": int(df_daily_th["Tong_So_Vu"].sum()) if len(df_daily_th) > 0 else 0,
        "qty_chuyen": round(float(df_daily_th["Tong_SL_Chuyen"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "qty_nhan": round(float(df_daily_th["Tong_SL_Nhan"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "qty_lech": round(float(df_daily_th["Tong_SL_Lech"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "stores_count": int(df_sub[st_col].nunique()) if len(df_sub) > 0 else 0,
        "stores_over_100k": int(df_sub[df_sub["Is_Store_Over_100k"]][st_col].nunique()) if len(df_sub) > 0 else 0,
        "stores_under_100k": int(df_sub[~df_sub["Is_Store_Over_100k"]][st_col].nunique()) if len(df_sub) > 0 else 0,
        "st_da_xl": int(df_sub[df_sub["Status_3Level"] == "Đã xử lý"][st_col].nunique()) if len(df_sub) > 0 else 0,
        "st_dang_xl": int(df_sub[df_sub["Status_3Level"] == "Đang xử lý"][st_col].nunique()) if len(df_sub) > 0 else 0,
        "st_khong_xl": int(df_sub[df_sub["Status_3Level"] == "Không xử lý"][st_col].nunique()) if len(df_sub) > 0 else 0,
        "sl_kho": round(float(df_daily_th["SL_Kho"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_st": round(float(df_daily_th["SL_ST"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_haohut": round(float(df_daily_th["SL_HaoHut"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_da_xl": round(float(df_daily_th["SL_Da_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_dang_xl": round(float(df_daily_th["SL_Dang_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_khong_xl": round(float(df_daily_th["SL_Khong_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "val_total": float(df_daily_th["Tong_Gia_Tri"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_over_100k": float(df_daily_th["Val_Over_100k"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_under_100k": float(df_daily_th["Val_Under_100k"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_kho": float(df_daily_th["Val_Kho"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_st": float(df_daily_th["Val_ST"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_haohut": float(df_daily_th["Val_HaoHut"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_da_xl": float(df_daily_th["Val_Da_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_dang_xl": float(df_daily_th["Val_Dang_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0.0,
        "val_khong_xl": float(df_daily_th["Val_Khong_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0.0,

        # DC Grand Total Metrics (4 Cột AD - AG)
        "dc_total_cases": gt_dc_total,
        "dc_total_qty": round(float(df_sub_dc["Qty_Lech"].sum()), 2) if len(df_sub_dc) > 0 else 0.0,
        "dc_total_val": float(df_sub_dc["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_st_count": int(df_sub_dc[st_col].nunique()) if len(df_sub_dc) > 0 else 0,
        
        "dc_dongy_cases": gt_dc_dongy,
        "dc_dongy_val": float(df_dc_dongy["Val_Tong_GT"].sum()) if len(df_dc_dongy) > 0 else 0.0,
        "dc_dongy_st": int(df_dc_dongy[st_col].nunique()) if len(df_dc_dongy) > 0 else 0,
        "dc_dongy_done_cases": gt_dc_dongy_done,
        "dc_dongy_not_done_cases": gt_dc_dongy_not_done,
        "dc_dongy_pct_done": gt_dc_dongy_pct_done,

        "dc_tuchoi_cases": gt_dc_tuchoi,
        "dc_tuchoi_val": float(df_dc_tuchoi["Val_Tong_GT"].sum()) if len(df_dc_tuchoi) > 0 else 0.0,
        "dc_tuchoi_st": int(df_dc_tuchoi[st_col].nunique()) if len(df_dc_tuchoi) > 0 else 0,
        "dc_tuchoi_kfm_replied": gt_dc_tuchoi_kfm_replied,
        "dc_tuchoi_kfm_pending": gt_dc_tuchoi_kfm_pending,
        "dc_tuchoi_pct_replied": gt_dc_tuchoi_pct_replied,

        "dc_kiemtra_cases": gt_dc_kiemtra,
        "dc_kiemtra_val": float(df_dc_kiemtra["Val_Tong_GT"].sum()) if len(df_dc_kiemtra) > 0 else 0.0,
        "dc_kiemtra_st": int(df_dc_kiemtra[st_col].nunique()) if len(df_dc_kiemtra) > 0 else 0,
        "dc_kiemtra_kfm_replied": gt_dc_kiemtra_kfm_replied,
        "dc_kiemtra_kfm_pending": gt_dc_kiemtra_kfm_pending,
        "dc_kiemtra_pct_replied": gt_dc_kiemtra_pct_replied,

        "dc_chua_cases": gt_dc_chua,
        "dc_chua_val": float(df_dc_chua["Val_Tong_GT"].sum()) if len(df_dc_chua) > 0 else 0.0,
        "dc_chua_st": int(df_dc_chua[st_col].nunique()) if len(df_dc_chua) > 0 else 0,
        
        "dc_pct_phan_hoi": gt_dc_pct_resp,
        "dc_pct_dongy": gt_dc_pct_dongy,
        "dc_crosstab": crosstab_list,
        "top_dc_notes": top_dc_notes,
        "top_kfm_notes": top_kfm_notes,
        "non_agree_breakdown": non_agree_items
    }

    return {
        "daily_matrix": daily_matrix_list,
        "monthly_matrix": monthly_matrix_list,
        "overall_metrics": overall_metrics,
        "grand_total": grand_total
    }


def build_and_export_web_report():
    """
    Pipeline hoàn chỉnh: Tải dữ liệu 3 nguồn -> Tính toán 4 Tab -> Xuất file JS ngày -> Xuất HTML báo cáo.
    """
    start_time = time.time()
    print("==============================================================================")
    print("🚀 BẮT ĐẦU TẠO BÁO CÁO WEB ĐỐI SOÁT ĐÔNG MÁT - TỰ ĐỘNG HÓA 100%")
    print("==============================================================================")

    # 1. Tải dữ liệu 3 nguồn
    df_raw = fetch_all_sources_combined()

    # 2. Tiền xử lý & làm sạch dữ liệu
    print("⚙️ Đang làm sạch và chuẩn hóa dữ liệu...")
    df_clean = process_dong_mat_dataframe(df_raw)
    threshold = 100000.0
    df_enriched = enrich_dataframe_with_threshold_and_status(df_clean, threshold=threshold, df_full_for_store_total=df_clean)
    print(f"✅ Dữ liệu hoàn chỉnh: {len(df_enriched):,} dòng đã được gắn nhãn nghiệp vụ.")

    # 3. Xuất các file chi tiết theo ngày (Lazy Load cho Modal)
    print("📁 Đang xuất các file dữ liệu chi tiết theo ngày (daily_details/)...")
    daily_details_dir = os.path.join(current_dir, "daily_details")
    os.makedirs(daily_details_dir, exist_ok=True)

    def parse_d(d):
        try:
            return datetime.strptime(str(d).strip(), "%d/%m/%Y")
        except Exception:
            return datetime.min

    unique_days = [d for d in df_enriched["Date_Str"].unique().tolist() if d and str(d).strip()]
    unique_days.sort(key=parse_d, reverse=True)

    st_col = "ID ST" if "ID ST" in df_enriched.columns else "Chi nhánh nhận"
    
    for d_str in unique_days:
        safe_date = str(d_str).replace('/', '_').replace('-', '_')
        group = df_enriched[df_enriched["Date_Str"] == d_str]
        records = []
        for _, r in group.iterrows():
            records.append({
                "st": str(r.get(st_col, "")),
                "store_name": str(r.get("Chi nhánh nhận", "")),
                "group": str(r.get("Nhóm hàng", "")),
                "sku": str(r.get("Mã hàng", "")),
                "sku_name": str(r.get("Tên SP", "")),
                "qty_transfer": round(float(r.get("Qty_Chuyen", 0.0)), 2),
                "qty_receive": round(float(r.get("Qty_Nhan", 0.0)), 2),
                "qty_diff": round(float(r.get("Qty_Lech", 0.0)), 2),
                "price": float(r.get("Gia_Nhap_Num", 0.0)),
                "val_total": float(r.get("Val_Tong_GT", 0.0)),
                "destination": str(r.get("Destination", "")),
                "error": str(r.get("Lỗi", "")),
                "is_store_over_100k": bool(r.get("Is_Store_Over_100k", False)),
                "store_day_total": float(r.get("Store_Day_Val_Total", 0.0)),
                "status_3level": str(r.get("Status_3Level", "")),
                "dc_confirm": str(r.get("DC_Confirm", "") or ""),
                "dc_note": str(r.get("DC_Note", "") or ""),
                "kfm_reply": str(r.get("KFM_Reply", "") or ""),
                "kfm_note": str(r.get("KFM_Note", "") or "")
            })
        js_content = f"window.LOADED_DAILY_RECORDS = window.LOADED_DAILY_RECORDS || {{}};\nwindow.LOADED_DAILY_RECORDS['{d_str}'] = {json.dumps(records, ensure_ascii=False)};"
        with open(os.path.join(daily_details_dir, f"d_{safe_date}.js"), "w", encoding="utf-8") as f:
            f.write(js_content)

    # 4. Xuất DC Cases riêng
    df_dc_all = df_enriched[df_enriched["Destination"] == "Kho ĐÔNG MÁT"]
    dc_records = []
    for _, r in df_dc_all.iterrows():
        d_parsed = r.get("Date_Parsed")
        month_str = f"Tháng {d_parsed.month}" if pd.notnull(d_parsed) else "Tháng 8"
        dc_records.append({
            "date": str(r.get("Date_Str", "")),
            "month": month_str,
            "st": str(r.get(st_col, "")),
            "store_name": str(r.get("Chi nhánh nhận", "")),
            "group": str(r.get("Nhóm hàng", "")),
            "sku": str(r.get("Mã hàng", "")),
            "sku_name": str(r.get("Tên SP", "")),
            "qty_diff": round(float(r.get("Qty_Lech", 0.0)), 2),
            "val_total": float(r.get("Val_Tong_GT", 0.0)),
            "dc_confirm": str(r.get("DC_Confirm", "") or ""),
            "dc_note": str(r.get("DC_Note", "") or ""),
            "kfm_reply": str(r.get("KFM_Reply", "") or ""),
            "kfm_note": str(r.get("KFM_Note", "") or ""),
            "destination": str(r.get("Destination", "")),
            "is_store_over_100k": bool(r.get("Is_Store_Over_100k", False)),
            "status_3level": str(r.get("Status_3Level", ""))
        })
    with open(os.path.join(daily_details_dir, "dc_cases.js"), "w", encoding="utf-8") as f:
        f.write(f"window.DC_CASES_DATA = {json.dumps(dc_records, ensure_ascii=False)};")

    # 5. Đồng bộ thư mục daily_details sang root & LOGIC
    for target_parent in [os.path.dirname(current_dir), os.path.join(os.path.dirname(current_dir), "LOGIC"), "C:\\Users\\Thu Ha\\Doi_Soat_Dong_Mat"]:
        try:
            target_dt_dir = os.path.join(target_parent, "daily_details")
            os.makedirs(target_dt_dir, exist_ok=True)
            for fname in os.listdir(daily_details_dir):
                shutil.copy2(os.path.join(daily_details_dir, fname), os.path.join(target_dt_dir, fname))
        except Exception as e:
            print(f"Warning sync daily_details: {e}")

    # 6. Tính toán 4 Bundles Nhóm Ngành Hàng
    print("📊 Đang tổng hợp dữ liệu KPI & Ma Trận cho 4 Nhóm Tab (Tất Cả, Thịt Cá, Mát, Đông)...")
    df_thit_ca = df_enriched[df_enriched["Nhóm hàng"] == "THỊT CÁ"].copy()
    df_mat = df_enriched[df_enriched["Nhóm hàng"] == "MÁT"].copy()
    df_dong = df_enriched[df_enriched["Nhóm hàng"] == "ĐÔNG"].copy()

    bundle_all = compute_group_bundle(df_enriched, df_full=df_enriched, threshold=threshold)
    bundle_thit_ca = compute_group_bundle(df_thit_ca, df_full=df_enriched, threshold=threshold)
    bundle_mat = compute_group_bundle(df_mat, df_full=df_enriched, threshold=threshold)
    bundle_dong = compute_group_bundle(df_dong, df_full=df_enriched, threshold=threshold)
    store_prio_all = compute_store_priority_list(df_enriched)

    bundles_dict = {
        "all": bundle_all,
        "thit_ca": bundle_thit_ca,
        "mat": bundle_mat,
        "dong": bundle_dong,
        "store_priority_list": store_prio_all
    }

    # 7. Đọc template HTML và bơm dữ liệu BUNDLES
    template_path = os.path.join(current_dir, "dashboard_template.html")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(current_dir), "LOGIC", "dashboard_template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Bơm BUNDLES
    bundles_json_str = json.dumps(bundles_dict, ensure_ascii=False)
    if "/*__BUNDLES_JSON__*/{}" in html_content:
        html_content = html_content.replace("/*__BUNDLES_JSON__*/{}", bundles_json_str)
    elif "/*__BUNDLES_JSON__*/" in html_content:
        html_content = html_content.replace("/*__BUNDLES_JSON__*/", bundles_json_str)
    elif "const BUNDLES = " in html_content:
        import re
        html_content = re.sub(r'const BUNDLES\s*=\s*.*?;', f'const BUNDLES = {bundles_json_str};', html_content, count=1)

    # 8. Ghi file HTML Báo Cáo
    output_file = "Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html"
    local_output = os.path.join(current_dir, output_file)
    with open(local_output, "w", encoding="utf-8") as f:
        f.write(html_content)

    root_output = os.path.join(os.path.dirname(current_dir), output_file)
    root_index = os.path.join(os.path.dirname(current_dir), "index.html")
    try:
        with open(root_output, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(root_index, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Warning writing root index: {e}")

    # Đồng bộ sang repo trên C: để đảm bảo đồng bộ hoàn hảo
    c_index = "C:\\Users\\Thu Ha\\Doi_Soat_Dong_Mat\\index.html"
    c_output = "C:\\Users\\Thu Ha\\Doi_Soat_Dong_Mat\\Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html"
    try:
        with open(c_index, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(c_output, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Warning writing C: index: {e}")

    logic_output = os.path.join(os.path.dirname(current_dir), "LOGIC", "LOGIC_DASHBOARD_DONG_MAT.html")
    try:
        with open(logic_output, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Warning writing logic output: {e}")

    elapsed = time.time() - start_time
    print("==============================================================================")
    print(f"🎉 ĐÃ XUẤT BẢN THÀNH CÔNG BÁO CÁO WEB ĐỐI SOÁT ĐÔNG MÁT! (Thời gian: {elapsed:.1f}s)")
    print(f"📦 Dung lượng file HTML: {len(html_content.encode('utf-8')) / 1024:.1f} KB")
    print(f"📁 Thư mục chi tiết: daily_details/ ({len(unique_days)} ngày, tải theo yêu cầu)")
    print("==============================================================================")
    return local_output


if __name__ == "__main__":
    build_and_export_web_report()
