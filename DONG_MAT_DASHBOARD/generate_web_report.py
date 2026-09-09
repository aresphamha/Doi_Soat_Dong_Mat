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
from analytics.kpi_metrics import (
    get_monthly_summary_matrix,
    get_error_type_summary,
    get_top_discrepant_stores,
    get_top_discrepant_products
)


def compute_store_priority_list(df_in: pd.DataFrame) -> list:
    """Tính toán danh sách Siêu thị ưu tiên xử lý (Bảng 4) siêu gọn nhẹ."""
    records = []
    if len(df_in) == 0:
        return records
    grouped = df_in.groupby(['Date_Str', 'ID ST', 'Chi nhánh nhận', 'Nhóm hàng', 'Is_Store_Over_100k'], dropna=False)
    for (d_str, st_id, st_name, group_name, is_over), g in grouped:
        val_total = round(float(g['Val_Tong_GT'].sum()), 2)
        val_da_xl = round(float(g[g['Status_3Level'] == 'Đã xử lý']['Val_Tong_GT'].sum()), 2)
        val_dang_xl = round(float(g[g['Status_3Level'] == 'Đang xử lý']['Val_Tong_GT'].sum()), 2)
        val_khong_xl = round(float(g[g['Status_3Level'] == 'Không xử lý']['Val_Tong_GT'].sum()), 2)
        
        if val_dang_xl > 0:
            prio = 'p1'
        elif val_khong_xl > 0:
            prio = 'p2'
        else:
            prio = 'p3'
            
        pct_done = round((val_da_xl / val_total * 100), 1) if val_total > 0 else 100.0
        
        d_parsed = g['Date_Parsed'].iloc[0] if len(g) > 0 and pd.notnull(g['Date_Parsed'].iloc[0]) else None
        month_str = f'Tháng {d_parsed.month}' if d_parsed else 'Tháng 8'
        
        records.append({
            'date': str(d_str),
            'month': month_str,
            'st': str(st_id),
            'store_name': str(st_name),
            'group': str(group_name),
            'is_store_over_100k': bool(is_over),
            'sku_count': int(len(g)),
            'qty_diff_total': round(float(g['Qty_Lech'].sum()), 2),
            'val_total': val_total,
            'val_da_xl': val_da_xl,
            'val_dang_xl': val_dang_xl,
            'val_khong_xl': val_khong_xl,
            'priority': prio,
            'pct_done': str(pct_done)
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
    df_monthly = get_monthly_summary_matrix(df_sub, threshold=threshold, df_full=df_full)

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
        monthly_matrix_list.append({
            "month": str(tr.get("Tháng", "")),
            "total_cases": int(tr.get("Tổng Số Vụ", 0)),
            "qty_chuyen": round(float(tr.get("Tổng SL Chuyển", 0.0)), 2),
            "qty_nhan": round(float(tr.get("Tổng SL Nhận", 0.0)), 2),
            "qty_lech": round(float(tr.get("Tổng SL Lệch", 0.0)), 2),
            "stores_count": int(tr.get("Tổng Số ST", 0)),
            "stores_over_100k": int(tr.get("ST Over 100k", 0)),
            "stores_under_100k": int(tr.get("ST Under 100k", 0)),
            "st_da_xl": int(tr.get("ST Đã Xử Lý", 0)),
            "st_dang_xl": int(tr.get("ST Đang Xử Lý", 0)),
            "st_khong_xl": int(tr.get("ST Không Xử Lý", 0)),
            "sl_kho": round(float(tr.get("SL Kho", 0.0)), 2),
            "sl_st": round(float(tr.get("SL ST", 0.0)), 2),
            "sl_haohut": round(float(tr.get("SL Hao Hụt", 0.0)), 2),
            "sl_da_xl": round(float(tr.get("SL Đã Xử Lý", 0.0)), 2),
            "sl_dang_xl": round(float(tr.get("SL Đang Xử Lý", 0.0)), 2),
            "sl_khong_xl": round(float(tr.get("SL Không Xử Lý", 0.0)), 2),
            "pct_sl_da_xl": round(float(tr.get("Tỷ Lệ SL Đã XL (%)", 0.0)), 1),
            "val_total": float(tr.get("Tổng Tiền", 0.0)),
            "val_over_100k": float(tr.get("Tiền Over 100k", 0.0)),
            "val_under_100k": float(tr.get("Tiền Under 100k", 0.0)),
            "val_kho": float(tr.get("Tiền Kho", 0.0)),
            "val_st": float(tr.get("Tiền ST", 0.0)),
            "val_haohut": float(tr.get("Tiền Hao Hụt", 0.0)),
            "val_da_xl": float(tr.get("Tiền Đã Xử Lý", 0.0)),
            "val_dang_xl": float(tr.get("Tiền Đang Xử Lý", 0.0)),
            "val_khong_xl": float(tr.get("Tiền Không Xử Lý", 0.0)),
            "pct_val_da_xl": round(float(tr.get("Tỷ Lệ Tiền Đã XL (%)", 0.0)), 1),
            
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

    # Grand Total Metrics
    df_sub_dc = df_sub[df_sub["Destination"] == "Kho ĐÔNG MÁT"]
    gt_dc_total = len(df_sub_dc)
    gt_dc_dongy = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"])
    gt_dc_tuchoi = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"])
    gt_dc_kiemtra = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"])
    gt_dc_chua = len(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])])
    
    gt_dc_resp = gt_dc_dongy + gt_dc_tuchoi + gt_dc_kiemtra
    gt_dc_pct_resp = round((gt_dc_resp / gt_dc_total * 100), 1) if gt_dc_total > 0 else 100.0
    gt_dc_pct_dongy = round((gt_dc_dongy / gt_dc_total * 100), 1) if gt_dc_total > 0 else 0.0

    gt_dc_dongy_done = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Đồng ý claim") & (df_sub_dc["KFM phản hồi"] == "DONE")])
    gt_dc_dongy_not_done = gt_dc_dongy - gt_dc_dongy_done
    gt_dc_dongy_pct_done = round((gt_dc_dongy_done / gt_dc_dongy * 100), 1) if gt_dc_dongy > 0 else 0.0

    gt_dc_tuchoi_kfm_replied = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Từ chối claim") & (df_sub_dc["KFM phản hồi"].fillna("").astype(str).str.strip() != "")])
    gt_dc_tuchoi_kfm_pending = gt_dc_tuchoi - gt_dc_tuchoi_kfm_replied
    gt_dc_tuchoi_pct_replied = round((gt_dc_tuchoi_kfm_replied / gt_dc_tuchoi * 100), 1) if gt_dc_tuchoi > 0 else 0.0

    gt_dc_kiemtra_kfm_replied = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Kiểm tra lại") & (df_sub_dc["KFM phản hồi"].fillna("").astype(str).str.strip() != "")])
    gt_dc_kiemtra_kfm_pending = gt_dc_kiemtra - gt_dc_kiemtra_kfm_replied
    gt_dc_kiemtra_pct_replied = round((gt_dc_kiemtra_kfm_replied / gt_dc_kiemtra * 100), 1) if gt_dc_kiemtra > 0 else 0.0

    # Cross-tab matrix Cột AD x Cột AF
    categories = ["Đồng ý claim", "Từ chối claim", "Kiểm tra lại", "Chưa phản hồi"]
    crosstab_list = []
    for cat in categories:
        if cat == "Chưa phản hồi":
            sub = df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]
        else:
            sub = df_sub_dc[df_sub_dc["DC xác nhận"] == cat]
            
        c_done = int(len(sub[sub["KFM phản hồi"] == "DONE"]))
        c_hlv = int(len(sub[sub["KFM phản hồi"] == "Cấp HLV quyết định"]))
        c_check = int(len(sub[sub["KFM phản hồi"] == "DC check lại thông tin"]))
        c_blank = int(len(sub[~sub["KFM phản hồi"].isin(["DONE", "Cấp HLV quyết định", "DC check lại thông tin"])]))
        c_tot = int(len(sub))
        
        crosstab_list.append({
            "key": cat,
            "done": c_done,
            "hlv": c_hlv,
            "check": c_check,
            "blank": c_blank,
            "total": c_tot
        })

    # Top DC Notes (Cột AE)
    dc_notes_clean = df_sub_dc[df_sub_dc["DC_Note"].fillna("").astype(str).str.strip() != ""]["DC_Note"].str.strip()
    top_dc_notes = [{"note": str(k), "count": int(v)} for k, v in dc_notes_clean.value_counts().head(7).items()]

    # Top KFM Notes (Cột AG)
    kfm_notes_clean = df_sub_dc[df_sub_dc["KFM_Note"].fillna("").astype(str).str.strip() != ""]["KFM_Note"].str.strip()
    top_kfm_notes = [{"note": str(k), "count": int(v)} for k, v in kfm_notes_clean.value_counts().head(7).items()]

    # Non Agree breakdown
    df_tc = df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"]
    df_kt = df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"]
    df_ch = df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]
    
    tc_hlv = int(len(df_tc[df_tc["KFM phản hồi"] == "Cấp HLV quyết định"]))
    tc_pending = int(len(df_tc[~df_tc["KFM phản hồi"].isin(["DONE", "Cấp HLV quyết định", "DC check lại thông tin"])]))
    tc_other = int(len(df_tc)) - tc_hlv - tc_pending
    kt_done = int(len(df_kt[df_kt["KFM phản hồi"].isin(["DONE", "DC check lại thông tin"])]))
    kt_pending = int(len(df_kt)) - kt_done
    ch_tot = int(len(df_ch))
    
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
        "stores_count": int(df_sub["ID ST"].nunique()) if len(df_sub) > 0 else 0,
        "stores_over_100k": int(df_sub[df_sub["Is_Store_Over_100k"]]["ID ST"].nunique()) if len(df_sub) > 0 else 0,
        "stores_under_100k": int(df_sub[~df_sub["Is_Store_Over_100k"]]["ID ST"].nunique()) if len(df_sub) > 0 else 0,
        "st_da_xl": int(df_sub[df_sub["Status_3Level"] == "Đã xử lý"]["ID ST"].nunique()) if len(df_sub) > 0 else 0,
        "st_dang_xl": int(df_sub[df_sub["Status_3Level"] == "Đang xử lý"]["ID ST"].nunique()) if len(df_sub) > 0 else 0,
        "st_khong_xl": int(df_sub[df_sub["Status_3Level"] == "Không xử lý"]["ID ST"].nunique()) if len(df_sub) > 0 else 0,
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
        "dc_st_count": int(df_sub_dc["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        
        "dc_dongy_cases": gt_dc_dongy,
        "dc_dongy_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_dongy_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_dongy_done_cases": gt_dc_dongy_done,
        "dc_dongy_not_done_cases": gt_dc_dongy_not_done,
        "dc_dongy_pct_done": gt_dc_dongy_pct_done,

        "dc_tuchoi_cases": gt_dc_tuchoi,
        "dc_tuchoi_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_tuchoi_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_tuchoi_kfm_replied": gt_dc_tuchoi_kfm_replied,
        "dc_tuchoi_kfm_pending": gt_dc_tuchoi_kfm_pending,
        "dc_tuchoi_pct_replied": gt_dc_tuchoi_pct_replied,

        "dc_kiemtra_cases": gt_dc_kiemtra,
        "dc_kiemtra_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_kiemtra_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_kiemtra_kfm_replied": gt_dc_kiemtra_kfm_replied,
        "dc_kiemtra_kfm_pending": gt_dc_kiemtra_kfm_pending,
        "dc_kiemtra_pct_replied": gt_dc_kiemtra_pct_replied,

        "dc_chua_cases": gt_dc_chua,
        "dc_chua_val": float(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_chua_st": int(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        
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

    for d_str in unique_days:
        safe_date = str(d_str).replace('/', '_').replace('-', '_')
        group = df_enriched[df_enriched["Date_Str"] == d_str]
        records = []
        for _, r in group.iterrows():
            records.append({
                "st": str(r.get("ID ST", "")),
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
            "st": str(r.get("ID ST", "")),
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
    for target_parent in [os.path.dirname(current_dir), os.path.join(os.path.dirname(current_dir), "LOGIC")]:
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
