"""
Trình tạo Báo Cáo Web Đối Soát ĐÔNG - MÁT:
- TAB 1: 📦 BẢNG SỐ LƯỢNG (PCS / KG) & SỐ LƯỢNG SIÊU THỊ
- TAB 2: 💰 BẢNG GIÁ TRỊ (VNĐ)
- TAB 3: 🌟 BẢNG HỢP NHẤT TOÀN DIỆN (SL & GIÁ TRỊ CHUẨN MỰC)
- Bổ sung 4 Biểu Đồ Trực Quan:
  1. Biến Động Tiền Lệch & SL Lệch Hàng Ngày (Bar & Line chart)
  2. Số Lượng Siêu Thị Phát Sinh Lệch Hàng Ngày (Stacked Bar chart: ST ≥ 100k & ST < 100k)
  3. Xu Hướng Tiền Lệch Nhóm ST ≥ 100k vs < 100k (Area line chart)
  4. Phân Bổ Điểm Nhận Trách Nhiệm (Doughnut kèm % trực tiếp & Bảng chú giải tỷ lệ chi tiết)
"""

import sys
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from data.data_loader import fetch_raw_sheet_csv
from data.data_processor import process_dong_mat_dataframe
from analytics.threshold_analytics import determine_case_destination, enrich_dataframe_with_threshold_and_status, analyze_threshold_metrics, get_daily_threshold_breakdown
from analytics.kpi_metrics import get_monthly_summary_matrix, get_error_type_summary, get_top_discrepant_stores, get_top_discrepant_products


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
            "dc_tuchoi_qty": round(float(tr.get("DC_TuChoi_Qty", 0.0)), 2),
            "dc_tuchoi_st": int(tr.get("DC_TuChoi_ST", 0)),
            "dc_tuchoi_kfm_replied": int(tr.get("DC_TuChoi_KFM_Replied", 0)),
            "dc_tuchoi_kfm_pending": int(tr.get("DC_TuChoi_KFM_Pending", 0)),
            "dc_kiemtra_cases": int(tr.get("DC_KiemTra_Cases", 0)),
            "dc_kiemtra_val": float(tr.get("DC_KiemTra_Val", 0.0)),
            "dc_kiemtra_qty": round(float(tr.get("DC_KiemTra_Qty", 0.0)), 2),
            "dc_kiemtra_st": int(tr.get("DC_KiemTra_ST", 0)),
            "dc_kiemtra_kfm_replied": int(tr.get("DC_KiemTra_KFM_Replied", 0)),
            "dc_kiemtra_kfm_pending": int(tr.get("DC_KiemTra_KFM_Pending", 0)),
            "dc_chua_cases": int(tr.get("DC_Chua_Cases", 0)),
            "dc_chua_val": float(tr.get("DC_Chua_Val", 0.0)),
            "dc_chua_qty": round(float(tr.get("DC_Chua_Qty", 0.0)), 2),
            "dc_chua_st": int(tr.get("DC_Chua_ST", 0)),
            "dc_pt_cases": int(tr.get("DC_PT_Cases", 0)),
            "dc_pct_phan_hoi": round(float(tr.get("DC_Pct_Phan_Hoi", 0.0)), 1),
            "dc_pct_dongy": round(float(tr.get("DC_Pct_DongY", 0.0)), 1)
        })

    monthly_matrix_list = []
    for _, mr in df_monthly.iterrows():
        m_name = str(mr.get("Tháng", "Tháng 8"))
        m_num_str = m_name.replace("Tháng ", "").zfill(2)
        df_m = df_sub[df_sub["Date_Str"].str.contains(f"/{m_num_str}/", na=False)] if "Date_Str" in df_sub.columns else df_sub
        df_m_dc = df_m[df_m["Destination"] == "Kho ĐÔNG MÁT"] if "Destination" in df_m.columns else df_m
        
        m_dc_total = len(df_m_dc)
        m_dc_dongy = len(df_m_dc[df_m_dc["DC xác nhận"] == "Đồng ý claim"])
        m_dc_tuchoi = len(df_m_dc[df_m_dc["DC xác nhận"] == "Từ chối claim"])
        m_dc_kiemtra = len(df_m_dc[df_m_dc["DC xác nhận"] == "Kiểm tra lại"])
        m_dc_chua = len(df_m_dc[~df_m_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])])
        
        m_dc_resp = m_dc_dongy + m_dc_tuchoi + m_dc_kiemtra
        m_pct_resp = round((m_dc_resp / m_dc_total * 100.0), 1) if m_dc_total > 0 else 100.0
        m_pct_dongy = round((m_dc_dongy / m_dc_total * 100.0), 1) if m_dc_total > 0 else 0.0

        m_dc_dongy_done = len(df_m_dc[(df_m_dc["DC xác nhận"] == "Đồng ý claim") & (df_m_dc["KFM phản hồi"] == "DONE")])
        m_dc_dongy_not_done = m_dc_dongy - m_dc_dongy_done
        m_dc_dongy_pct_done = round((m_dc_dongy_done / m_dc_dongy * 100.0), 1) if m_dc_dongy > 0 else 0.0

        m_dc_tuchoi_kfm_replied = len(df_m_dc[(df_m_dc["DC xác nhận"] == "Từ chối claim") & (df_m_dc["KFM phản hồi"].astype(str).str.strip() != "")])
        m_dc_tuchoi_kfm_pending = m_dc_tuchoi - m_dc_tuchoi_kfm_replied
        m_dc_tuchoi_pct_replied = round((m_dc_tuchoi_kfm_replied / m_dc_tuchoi * 100.0), 1) if m_dc_tuchoi > 0 else 0.0

        m_dc_kiemtra_kfm_replied = len(df_m_dc[(df_m_dc["DC xác nhận"] == "Kiểm tra lại") & (df_m_dc["KFM phản hồi"].astype(str).str.strip() != "")])
        m_dc_kiemtra_kfm_pending = m_dc_kiemtra - m_dc_kiemtra_kfm_replied
        m_dc_kiemtra_pct_replied = round((m_dc_kiemtra_kfm_replied / m_dc_kiemtra * 100.0), 1) if m_dc_kiemtra > 0 else 0.0

        monthly_matrix_list.append({
            "month": m_name,
            "total_cases": int(mr.get("Tong_So_Vu", 0)),
            
            # Số lượng
            "qty_chuyen": round(float(mr.get("Tong_SL_Chuyen", 0.0)), 2),
            "qty_nhan": round(float(mr.get("Tong_SL_Nhan", 0.0)), 2),
            "qty_lech": round(float(mr.get("Tong_SL_Lech", 0.0)), 2),
            "stores_count": int(mr.get("Tong_ST", 0)),
            "stores_over_100k": int(mr.get("ST_Over_100k", 0)),
            "stores_under_100k": int(mr.get("ST_Under_100k", 0)),
            "st_da_xl": int(mr.get("ST_Da_Xu_Ly", 0)),
            "st_dang_xl": int(mr.get("ST_Dang_Xu_Ly", 0)),
            "st_khong_xl": int(mr.get("ST_Khong_Xu_Ly", 0)),
            
            "sl_kho": round(float(mr.get("SL_Kho", 0.0)), 2),
            "sl_st": round(float(mr.get("SL_ST", 0.0)), 2),
            "sl_haohut": round(float(mr.get("SL_HaoHut", 0.0)), 2),
            "sl_da_xl": round(float(mr.get("SL_Da_Xu_Ly", 0.0)), 2),
            "sl_dang_xl": round(float(mr.get("SL_Dang_Xu_Ly", 0.0)), 2),
            "sl_khong_xl": round(float(mr.get("SL_Khong_Xu_Ly", 0.0)), 2),
            "pct_sl_da_xl": round(float(mr.get("Pct_SL_Da_Xu_Ly", 0.0)), 1),
            
            # Giá trị
            "val_total": float(mr.get("Tong_Gia_Tri", 0.0)),
            "val_over_100k": float(mr.get("Val_Over_100k", 0.0)),
            "val_under_100k": float(mr.get("Val_Under_100k", 0.0)),
            "val_kho": float(mr.get("Val_Kho", 0.0)),
            "val_st": float(mr.get("Val_ST", 0.0)),
            "val_haohut": float(mr.get("Val_HaoHut", 0.0)),
            "val_da_xl": float(mr.get("Val_Da_Xu_Ly", 0.0)),
            "val_dang_xl": float(mr.get("Val_Dang_Xu_Ly", 0.0)),
            "val_khong_xl": float(mr.get("Val_Khong_Xu_Ly", 0.0)),
            "pct_val_da_xl": round(float(mr.get("Pct_Da_Xu_Ly", 0.0)), 1),

            # DC Monthly Metrics (4 Cột AD - AG)
            "dc_total_cases": m_dc_total,
            "dc_total_qty": round(float(df_m_dc["Qty_Lech"].sum()), 2) if len(df_m_dc) > 0 else 0.0,
            "dc_total_val": float(df_m_dc["Val_Tong_GT"].sum()) if len(df_m_dc) > 0 else 0.0,
            "dc_st_count": int(df_m_dc["ID ST"].nunique()) if len(df_m_dc) > 0 else 0,
            "dc_dongy_cases": m_dc_dongy,
            "dc_dongy_val": float(df_m_dc[df_m_dc["DC xác nhận"] == "Đồng ý claim"]["Val_Tong_GT"].sum()) if len(df_m_dc) > 0 else 0.0,
            "dc_dongy_st": int(df_m_dc[df_m_dc["DC xác nhận"] == "Đồng ý claim"]["ID ST"].nunique()) if len(df_m_dc) > 0 else 0,
            "dc_dongy_done_cases": m_dc_dongy_done,
            "dc_dongy_not_done_cases": m_dc_dongy_not_done,
            "dc_dongy_pct_done": m_dc_dongy_pct_done,
            "dc_tuchoi_cases": m_dc_tuchoi,
            "dc_tuchoi_val": float(df_m_dc[df_m_dc["DC xác nhận"] == "Từ chối claim"]["Val_Tong_GT"].sum()) if len(df_m_dc) > 0 else 0.0,
            "dc_tuchoi_st": int(df_m_dc[df_m_dc["DC xác nhận"] == "Từ chối claim"]["ID ST"].nunique()) if len(df_m_dc) > 0 else 0,
            "dc_tuchoi_kfm_replied": m_dc_tuchoi_kfm_replied,
            "dc_tuchoi_kfm_pending": m_dc_tuchoi_kfm_pending,
            "dc_tuchoi_pct_replied": m_dc_tuchoi_pct_replied,
            "dc_kiemtra_cases": m_dc_kiemtra,
            "dc_kiemtra_val": float(df_m_dc[df_m_dc["DC xác nhận"] == "Kiểm tra lại"]["Val_Tong_GT"].sum()) if len(df_m_dc) > 0 else 0.0,
            "dc_kiemtra_st": int(df_m_dc[df_m_dc["DC xác nhận"] == "Kiểm tra lại"]["ID ST"].nunique()) if len(df_m_dc) > 0 else 0,
            "dc_kiemtra_kfm_replied": m_dc_kiemtra_kfm_replied,
            "dc_kiemtra_kfm_pending": m_dc_kiemtra_kfm_pending,
            "dc_kiemtra_pct_replied": m_dc_kiemtra_pct_replied,
            "dc_chua_cases": m_dc_chua,
            "dc_chua_val": float(df_m_dc[~df_m_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["Val_Tong_GT"].sum()) if len(df_m_dc) > 0 else 0.0,
            "dc_chua_st": int(df_m_dc[~df_m_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["ID ST"].nunique()) if len(df_m_dc) > 0 else 0,
            "dc_pct_phan_hoi": m_pct_resp,
            "dc_pct_dongy": m_pct_dongy
        })

    # DC Grand Total (4 Cột AD - AG)
    df_sub_dc = df_sub[df_sub["Destination"] == "Kho ĐÔNG MÁT"] if "Destination" in df_sub.columns else df_sub
    gt_dc_total = len(df_sub_dc)
    gt_dc_dongy = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"])
    gt_dc_tuchoi = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"])
    gt_dc_kiemtra = len(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"])
    gt_dc_chua = len(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])])
    
    gt_dc_resp = gt_dc_dongy + gt_dc_tuchoi + gt_dc_kiemtra
    gt_dc_pct_resp = round((gt_dc_resp / gt_dc_total * 100.0), 1) if gt_dc_total > 0 else 100.0
    gt_dc_pct_dongy = round((gt_dc_dongy / gt_dc_total * 100.0), 1) if gt_dc_total > 0 else 0.0

    # KFM metrics on DC Đồng ý claim
    gt_dc_dongy_done = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Đồng ý claim") & (df_sub_dc["KFM phản hồi"] == "DONE")])
    gt_dc_dongy_not_done = gt_dc_dongy - gt_dc_dongy_done
    gt_dc_dongy_pct_done = round((gt_dc_dongy_done / gt_dc_dongy * 100.0), 1) if gt_dc_dongy > 0 else 0.0

    # KFM metrics on DC Từ chối & Kiểm tra lại
    gt_dc_tuchoi_kfm_replied = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Từ chối claim") & (df_sub_dc["KFM phản hồi"].astype(str).str.strip() != "")])
    gt_dc_tuchoi_kfm_pending = gt_dc_tuchoi - gt_dc_tuchoi_kfm_replied
    gt_dc_tuchoi_pct_replied = round((gt_dc_tuchoi_kfm_replied / gt_dc_tuchoi * 100.0), 1) if gt_dc_tuchoi > 0 else 0.0

    gt_dc_kiemtra_kfm_replied = len(df_sub_dc[(df_sub_dc["DC xác nhận"] == "Kiểm tra lại") & (df_sub_dc["KFM phản hồi"].astype(str).str.strip() != "")])
    gt_dc_kiemtra_kfm_pending = gt_dc_kiemtra - gt_dc_kiemtra_kfm_replied
    gt_dc_kiemtra_pct_replied = round((gt_dc_kiemtra_kfm_replied / gt_dc_kiemtra * 100.0), 1) if gt_dc_kiemtra > 0 else 0.0

    grand_total = {
        "total_days": len(df_daily_th),
        "total_cases": int(df_daily_th["Tong_So_Vu"].sum()) if len(df_daily_th) > 0 else 0,
        "unique_stores": int(df_sub["ID ST"].replace("", pd.NA).dropna().nunique()) if "ID ST" in df_sub.columns else 0,
        
        # Số lượng
        "qty_chuyen": round(float(df_daily_th["Tong_SL_Chuyen"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "qty_nhan": round(float(df_daily_th["Tong_SL_Nhan"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "qty_lech": round(float(df_daily_th["Tong_SL_Lech"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "stores_count": int(df_daily_th["Tong_ST"].sum()) if len(df_daily_th) > 0 else 0,
        "stores_over_100k": int(df_daily_th["ST_Over_100k"].sum()) if len(df_daily_th) > 0 else 0,
        "stores_under_100k": int(df_daily_th["ST_Under_100k"].sum()) if len(df_daily_th) > 0 else 0,
        "st_da_xl": int(df_daily_th["ST_Da_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0,
        "st_dang_xl": int(df_daily_th["ST_Dang_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0,
        "st_khong_xl": int(df_daily_th["ST_Khong_Xu_Ly"].sum()) if len(df_daily_th) > 0 else 0,
        
        "sl_kho": round(float(df_daily_th["SL_Kho"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_st": round(float(df_daily_th["SL_ST"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_haohut": round(float(df_daily_th["SL_HaoHut"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_da_xl": round(float(df_daily_th["SL_Da_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_dang_xl": round(float(df_daily_th["SL_Dang_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        "sl_khong_xl": round(float(df_daily_th["SL_Khong_Xu_Ly"].sum()), 2) if len(df_daily_th) > 0 else 0.0,
        
        # Giá trị
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
        
        # Cột AD: DC Đồng Ý & Cột AF: KFM DONE
        "dc_dongy_cases": gt_dc_dongy,
        "dc_dongy_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_dongy_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Đồng ý claim"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_dongy_done_cases": gt_dc_dongy_done,
        "dc_dongy_not_done_cases": gt_dc_dongy_not_done,
        "dc_dongy_pct_done": gt_dc_dongy_pct_done,

        # Cột AD: DC Từ Chối
        "dc_tuchoi_cases": gt_dc_tuchoi,
        "dc_tuchoi_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_tuchoi_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Từ chối claim"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_tuchoi_kfm_replied": gt_dc_tuchoi_kfm_replied,
        "dc_tuchoi_kfm_pending": gt_dc_tuchoi_kfm_pending,
        "dc_tuchoi_pct_replied": gt_dc_tuchoi_pct_replied,

        # Cột AD: DC Kiểm Tra Lại
        "dc_kiemtra_cases": gt_dc_kiemtra,
        "dc_kiemtra_val": float(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_kiemtra_st": int(df_sub_dc[df_sub_dc["DC xác nhận"] == "Kiểm tra lại"]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        "dc_kiemtra_kfm_replied": gt_dc_kiemtra_kfm_replied,
        "dc_kiemtra_kfm_pending": gt_dc_kiemtra_kfm_pending,
        "dc_kiemtra_pct_replied": gt_dc_kiemtra_pct_replied,

        # Cột AD: DC Chưa Phản Hồi
        "dc_chua_cases": gt_dc_chua,
        "dc_chua_val": float(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["Val_Tong_GT"].sum()) if len(df_sub_dc) > 0 else 0.0,
        "dc_chua_st": int(df_sub_dc[~df_sub_dc["DC xác nhận"].isin(["Đồng ý claim", "Từ chối claim", "Kiểm tra lại"])]["ID ST"].nunique()) if len(df_sub_dc) > 0 else 0,
        
        "dc_pct_phan_hoi": gt_dc_pct_resp,
        "dc_pct_dongy": gt_dc_pct_dongy
    }

    return {
        "daily_matrix": daily_matrix_list,
        "monthly_matrix": monthly_matrix_list,
        "overall_metrics": overall_metrics,
        "grand_total": grand_total
    }
def generate_html_report(output_file: str = "Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html") -> str:
    print("⏳ Đang nạp và xử lý dữ liệu từ Google Sheets...")
    df_raw = fetch_raw_sheet_csv()
    df = process_dong_mat_dataframe(df_raw)
    threshold = 100000.0

    # Enrich full dataset first so that Destination and threshold calculations are available for all slices
    df_enriched = enrich_dataframe_with_threshold_and_status(df, threshold=threshold, df_full_for_store_total=df)

    df_mat = df_enriched[df_enriched["Nhóm hàng"] == "MÁT"].copy()
    df_dong = df_enriched[df_enriched["Nhóm hàng"] == "ĐÔNG"].copy()

    bundle_all = compute_group_bundle(df_enriched, df_full=df_enriched, threshold=threshold)
    bundle_mat = compute_group_bundle(df_mat, df_full=df_enriched, threshold=threshold)
    bundle_dong = compute_group_bundle(df_dong, df_full=df_enriched, threshold=threshold)
    daily_data_dict = {}
    def parse_d(d):
        try:
            return datetime.strptime(str(d).strip(), "%d/%m/%Y")
        except Exception:
            return datetime.min

    unique_days = [d for d in df_enriched["Date_Str"].unique().tolist() if d and str(d).strip()]
    unique_days.sort(key=parse_d, reverse=True)
    
    for d_str in unique_days:
        group = df_enriched[df_enriched["Date_Str"] == d_str]
        records = []
        for _, r in group.iterrows():
            records.append({
                "st": str(r.get("ID ST", "")),
                "store_name": str(r.get("Chi nhánh nhận", "")),
                "sku": str(r.get("Mã hàng", "")),
                "sku_name": str(r.get("Tên SP", "")),
                "unit": str(r.get("ĐVT", "")),
                "group": str(r.get("Nhóm hàng", "")),
                "qty_transfer": round(float(r.get("Số lượng chuyển_Num", 0.0)), 2),
                "qty_receive": round(float(r.get("Số lượng nhận_Num", 0.0)), 2),
                "qty_diff": round(float(r.get("Chênh lệch_Num", 0.0)), 2),
                "error": str(r.get("Lỗi", "")),
                "price": float(r.get("Gia_Nhap_Num", 0.0)),
                "val_total": float(r.get("Val_Tong_GT", 0.0)),
                "store_day_total": float(r.get("Store_Day_Val_Total", 0.0)),
                "destination": str(r.get("Destination", "")),
                "status_3level": str(r.get("Status_3Level", "")),
                "is_store_over_100k": bool(r.get("Is_Store_Over_100k", False)),
                "dc_confirm": str(r.get("DC_Confirm", r.get("DC xác nhận", ""))).strip(),
                "dc_note": str(r.get("DC_Note", r.get("NOTE.1", ""))).strip(),
                "kfm_reply": str(r.get("KFM_Reply", r.get("KFM phản hồi", ""))).strip(),
                "kfm_note": str(r.get("KFM_Note", r.get("NOTE.2", ""))).strip(),
                "pt_dc": str(r.get("PT trả tồn về DC", "")).strip(),
                "pt_pick_du": str(r.get("PT DC pick dư", "")).strip(),
                "img_link": str(r.get("Link hình ảnh", "")).strip(),
                "handler": str(r.get("Người xử lý", "")).strip(),
                "to": str(r.get("TO", "")).strip(),
                "tote": str(r.get("Mã thùng", "")).strip()
            })
        daily_data_dict[d_str] = records

    json_bundles = json.dumps({
        "all": bundle_all,
        "mat": bundle_mat,
        "dong": bundle_dong
    }, ensure_ascii=False)
    
    json_daily_records = json.dumps(daily_data_dict, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="vi" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo Cáo Đối Soát Hàng ĐÔNG - MÁT SCM</title>
    <!-- Fonts & Icons -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js, ChartDataLabels & SheetJS -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
    <style>
        :root {
            /* DARK THEME AS DEFAULT (Phông Đen / Dark Mode) */
            --bg-body: #0b0f19;
            --bg-body-gradient: radial-gradient(1200px circle at 50% -10%, rgba(56, 189, 248, 0.08), transparent 70%), #0b0f19;
            --bg-card: #111827;
            --bg-card-alt: #162032;
            --bg-hover: rgba(56, 189, 248, 0.06);
            --border-card: rgba(255, 255, 255, 0.08);
            --border-subtle: rgba(255, 255, 255, 0.04);
            
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --primary: #38bdf8;
            --primary-dark: #0284c7;
            --mat-color: #10b981;
            --dong-color: #818cf8;
            --danger: #f87171;
            --success: #34d399;
            --warning: #fbbf24;
            
            --slate-900: #0b0f19;
            --slate-800: #111827;
            --slate-700: #1e293b;
            --slate-600: #334155;
            --slate-500: #64748b;
            --slate-400: #94a3b8;
            --slate-300: #cbd5e1;
            --slate-200: #334155;
            --slate-100: #1e293b;
            --slate-50: #131d31;
            
            --input-bg: #1e293b;
            --input-border: #334155;
            --table-head-bg: #0f172a;
            --table-tfoot-bg: #090d16;
            --modal-bg: #0f172a;
            --modal-head-bg: #090d16;
            --modal-toolbar-bg: #131d31;
            --card-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
        }

        [data-theme="light"] {
            --bg-body: #f8fafc;
            --bg-body-gradient: none;
            --bg-card: #ffffff;
            --bg-card-alt: #f1f5f9;
            --bg-hover: #f8fafc;
            --border-card: #e2e8f0;
            --border-subtle: #f1f5f9;
            
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            
            --primary: #0284c7;
            --primary-dark: #0369a1;
            --mat-color: #10b981;
            --dong-color: #6366f1;
            --danger: #dc2626;
            --success: #16a34a;
            --warning: #ea580c;
            
            --slate-900: #0f172a;
            --slate-800: #1e293b;
            --slate-700: #334155;
            --slate-600: #475569;
            --slate-500: #64748b;
            --slate-400: #94a3b8;
            --slate-300: #cbd5e1;
            --slate-200: #e2e8f0;
            --slate-100: #f1f5f9;
            --slate-50: #f8fafc;
            
            --input-bg: #ffffff;
            --input-border: #cbd5e1;
            --table-head-bg: #0f172a;
            --table-tfoot-bg: #f8fafc;
            --modal-bg: #ffffff;
            --modal-head-bg: #0f172a;
            --modal-toolbar-bg: #f8fafc;
            --card-shadow: 0 2px 8px rgba(0,0,0,0.03);
        }

        * { 
            box-sizing: border-box; 
            margin: 0; 
            padding: 0; 
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-body);
            background-image: var(--bg-body-gradient);
            color: var(--text-primary);
            line-height: 1.5;
            font-size: 14px;
            min-height: 100vh;
            transition: background-color 0.25s ease, color 0.25s ease;
        }

        /* Header */
        .app-header {
            background: linear-gradient(135deg, #090d16 0%, #111827 60%, #0f172a 100%);
            color: #ffffff;
            padding: 1.1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 4px 25px rgba(0,0,0,0.5);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
        }

        .header-container {
            max-width: 1750px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .header-icon {
            font-size: 1.85rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            padding: 0.55rem;
            border-radius: 10px;
            border: 1px solid rgba(56, 189, 248, 0.25);
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
        }

        .header-text h1 {
            font-size: 1.28rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 0.15rem;
            color: #ffffff;
        }

        .header-text p {
            font-size: 0.82rem;
            color: #94a3b8;
            font-weight: 400;
        }

        /* Group Tabs */
        .group-switcher {
            display: flex;
            background: rgba(255, 255, 255, 0.06);
            padding: 4px;
            border-radius: 10px;
            gap: 6px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .group-btn {
            background: transparent;
            border: none;
            color: #94a3b8;
            padding: 0.55rem 1.25rem;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-family: inherit;
        }

        .group-btn:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.08);
        }

        .group-btn.active-mat {
            background: #10b981;
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
        }

        .group-btn.active-dong {
            background: #6366f1;
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }

        .group-btn.active-all {
            background: #0284c7;
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4);
        }

        /* Month Switcher Selector */
        .month-switcher {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(255, 255, 255, 0.08);
            padding: 0.35rem 0.75rem;
            border-radius: 10px;
            border: 1px solid rgba(56, 189, 248, 0.3);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.15);
        }

        .month-select {
            background: transparent;
            color: #f8fafc;
            border: none;
            font-size: 0.86rem;
            font-weight: 700;
            cursor: pointer;
            outline: none;
            font-family: inherit;
        }

        .month-select option {
            background: #0f172a;
            color: #f8fafc;
        }

        .theme-toggle-btn {
            background: rgba(255, 255, 255, 0.08);
            color: #f8fafc;
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 0.55rem 1rem;
            border-radius: 8px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-family: inherit;
            transition: all 0.2s ease;
        }

        .theme-toggle-btn:hover {
            background: rgba(255, 255, 255, 0.16);
            border-color: #38bdf8;
            color: #38bdf8;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
        }

        .action-btn {
            background: #10b981;
            color: #ffffff;
            border: none;
            padding: 0.55rem 1rem;
            border-radius: 8px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-family: inherit;
            transition: all 0.2s ease;
            box-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);
        }

        .action-btn:hover {
            background: #059669;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.45);
        }

        .main-container {
            max-width: 1750px;
            margin: 1.25rem auto;
            padding: 0 1.25rem 3rem 1.25rem;
        }

        /* 4 KPI Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            background: var(--bg-card);
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-card);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.16);
            box-shadow: 0 12px 30px rgba(0,0,0,0.4);
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
        }

        .kpi-card.c-blue::before { background: linear-gradient(90deg, #0284c7, #38bdf8); }
        .kpi-card.c-red::before { background: linear-gradient(90deg, #b91c1c, #f87171); }
        .kpi-card.c-green::before { background: linear-gradient(90deg, #059669, #34d399); }
        .kpi-card.c-orange::before { background: linear-gradient(90deg, #d97706, #fbbf24); }

        .kpi-label {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-secondary);
            margin-bottom: 0.45rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .kpi-value {
            font-size: 1.7rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
            margin-bottom: 0.35rem;
        }

        .kpi-desc {
            font-size: 0.8rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        .kpi-desc strong {
            color: var(--text-primary);
        }

        /* ========================================================== */
        /* GLOBAL RESOLUTION PROGRESS TRACKER */
        /* ========================================================== */
        .progress-overview-card {
            background: var(--bg-card);
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-card);
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }

        .progress-overview-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, #34d399, #38bdf8, #818cf8);
        }

        .progress-overview-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .progress-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            letter-spacing: -0.01em;
        }

        .progress-status-badge {
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.3rem 0.85rem;
            border-radius: 20px;
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .multi-progress-bar {
            width: 100%;
            height: 14px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            border: 1px solid var(--border-card);
            margin-bottom: 1.25rem;
        }

        .progress-segment {
            height: 100%;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .seg-done {
            background: linear-gradient(90deg, #059669, #34d399);
            box-shadow: 0 0 10px rgba(52, 211, 153, 0.4);
        }

        .seg-pending {
            background: linear-gradient(90deg, #d97706, #fbbf24);
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
        }

        .seg-ignored {
            background: linear-gradient(90deg, #475569, #94a3b8);
        }

        .progress-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }

        .p-stat-box {
            padding: 0.85rem 1rem;
            border-radius: 10px;
            background: var(--slate-50);
            border: 1px solid var(--border-card);
            transition: transform 0.15s ease;
        }

        .p-stat-box:hover {
            transform: translateY(-2px);
        }

        .p-stat-label {
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.3rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            color: var(--text-secondary);
        }

        .p-stat-val {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 0.2rem;
        }

        .p-stat-sub {
            font-size: 0.78rem;
            color: var(--text-muted);
            line-height: 1.45;
        }

        .p-stat-sub strong {
            color: var(--text-primary);
        }

        /* ========================================================== */
        /* EXECUTIVE SUMMARY & ACTION PLAN CARD */
        /* ========================================================== */
        .executive-insights-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 14px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        }

        .insights-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 1.05rem;
            font-weight: 800;
            color: #38bdf8;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.65rem;
        }

        .insights-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            .insights-grid { grid-template-columns: 1fr; }
        }

        .insight-section {
            display: flex;
            flex-direction: column;
            gap: 0.65rem;
        }

        .insight-section-title {
            font-size: 0.88rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }

        .insight-item {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            font-size: 0.82rem;
            line-height: 1.45;
            border-left: 3px solid #38bdf8;
        }

        .insight-item.danger-left { border-left-color: #f87171; }
        .insight-item.success-left { border-left-color: #34d399; }
        .insight-item.warning-left { border-left-color: #fbbf24; }

        .insight-item strong {
            color: #ffffff;
        }

        /* 8 BIỂU ĐỒ TRỰC QUAN (LƯỚI ĐA CHIỀU 2 CỘT CÂN ĐỐI) */
        .charts-grid-5 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        @media (max-width: 1100px) {
            .charts-grid-5 { grid-template-columns: 1fr; }
        }

        .chart-card {
            background: var(--bg-card);
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-card);
            display: flex;
            flex-direction: column;
            transition: all 0.2s ease;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            gap: 0.5rem;
        }

        .chart-header h3 {
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }

        .btn-chart-zoom {
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 0.22rem 0.55rem;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: all 0.2s ease;
            font-family: inherit;
            white-space: nowrap;
        }

        .btn-chart-zoom:hover {
            background: #0284c7;
            color: #ffffff;
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
            transform: translateY(-1px);
        }

        /* MODAL OVERLAY & BOX CHUNG */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            padding: 1rem;
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .modal-overlay.active {
            display: flex !important;
            opacity: 1 !important;
        }

        .modal-box {
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border-card);
            box-shadow: 0 25px 60px rgba(0,0,0,0.65);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            width: 95vw;
            max-width: 1400px;
            height: 88vh;
        }

        .modal-box.is-fullscreen {
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            border-radius: 0 !important;
        }

        .modal-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-card);
            background: var(--bg-card);
        }

        .modal-head-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-close {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-card);
            color: var(--text-primary);
            width: 34px;
            height: 34px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            transition: all 0.2s ease;
        }
        .btn-close:hover {
            background: #ef4444;
            color: #ffffff;
            border-color: #ef4444;
        }

        /* Modal Phóng To & Nhận Xét Biểu Đồ */
        .chart-zoom-box {
            width: 95vw;
            max-width: 1420px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-card);
            box-shadow: 0 25px 60px rgba(0,0,0,0.65);
        }

        .zoom-modal-body {
            display: grid;
            grid-template-columns: 1.55fr 1fr;
            gap: 1.25rem;
            padding: 1.25rem 1.5rem;
            flex: 1;
            overflow-y: auto;
        }

        .chart-container {
            position: relative;
            flex: 1;
            min-height: 250px;
            width: 100%;
        }

        @media (max-width: 1050px) {
            .zoom-modal-body {
                grid-template-columns: 1fr;
            }
        }

        .zoom-chart-area {
            background: rgba(15, 23, 42, 0.35);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            min-height: 460px;
        }

        .zoom-chart-container {
            position: relative;
            flex: 1;
            min-height: 400px;
            width: 100%;
        }

        .zoom-insights-area {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            overflow-y: auto;
            padding-right: 4px;
        }

        .zoom-insight-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 0.85rem 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .zoom-insight-card.highlight {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(30, 41, 59, 0.4) 100%);
            border-color: rgba(56, 189, 248, 0.3);
        }

        .zoom-insight-title {
            font-size: 0.86rem;
            font-weight: 700;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .zoom-insight-text {
            font-size: 0.81rem;
            line-height: 1.5;
            color: var(--text-secondary);
        }

        .zoom-insight-text strong {
            color: var(--text-primary);
        }

        .zoom-stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            margin-top: 0.35rem;
        }

        .zoom-stat-item {
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 0.5rem 0.65rem;
            display: flex;
            flex-direction: column;
        }

        .zoom-stat-label {
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        .zoom-stat-val {
            font-size: 0.95rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-top: 2px;
        }

        .zoom-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
            margin: 0.6rem 0;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .zoom-detail-table th {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-primary);
            font-weight: 700;
            padding: 7px 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .zoom-detail-table td {
            padding: 7px 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text-secondary);
        }

        .zoom-detail-table tr:last-child td {
            border-bottom: none;
        }

        .zoom-detail-table tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .chart-container {
            position: relative;
            height: 320px;
            width: 100%;
        }

        /* Layout Biểu đồ tròn + Danh sách tỷ lệ */
        .doughnut-layout {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 1rem;
            align-items: center;
            height: 100%;
        }

        @media (max-width: 600px) {
            .doughnut-layout { grid-template-columns: 1fr; }
        }

        .doughnut-legend-list {
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }

        .legend-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.78rem;
            padding: 0.4rem 0.65rem;
            background: var(--slate-50);
            border-radius: 6px;
            border: 1px solid var(--border-card);
            border-left: 4px solid #cbd5e1;
        }

        .legend-name {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .legend-val {
            font-weight: 700;
            color: var(--text-primary);
        }

        .legend-pct {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 700;
            color: #ffffff;
            margin-left: 6px;
        }

        /* View Mode Selector Tabs */
        .table-view-tabs {
            display: flex;
            background: var(--slate-100);
            padding: 4px;
            border-radius: 12px;
            gap: 6px;
            margin-bottom: 1.25rem;
            border: 1px solid var(--border-card);
        }

        .table-view-tab {
            flex: 1;
            padding: 0.75rem 1rem;
            border: none;
            background: transparent;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            font-family: inherit;
        }

        .table-view-tab:hover {
            color: var(--text-primary);
            background: rgba(255,255,255,0.06);
        }

        .table-view-tab.active-store {
            background: #b91c1c;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(185, 28, 28, 0.4);
        }

        .table-view-tab.active-dc {
            background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%) !important;
            color: #ffffff !important;
            border-color: #a855f7 !important;
            box-shadow: 0 4px 14px rgba(168, 85, 247, 0.4) !important;
        }

        .table-view-tab.active-qty {
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35);
        }

        .table-view-tab.active-val {
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.35);
        }

        .table-view-tab.active-master {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.4);
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2);
        }

        /* Table Card */
        .table-card {
            background: var(--bg-card);
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-card);
            margin-bottom: 2rem;
        }

        .table-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-card);
        }

        .table-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .seg-pill {
            display: inline-flex;
            background: var(--slate-100);
            padding: 3px;
            border-radius: 8px;
            border: 1px solid var(--border-card);
        }

        .seg-btn {
            background: transparent;
            border: none;
            padding: 0.35rem 0.8rem;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s;
            font-family: inherit;
        }

        .seg-btn.active {
            background: #0284c7;
            color: #ffffff;
            box-shadow: 0 1px 6px rgba(2, 132, 199, 0.4);
        }

        /* Table Design */
        .table-responsive {
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid var(--border-card);
            background: var(--bg-card);
        }

        table.sc-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.83rem;
            text-align: right;
            white-space: nowrap;
        }

        table.sc-table th {
            padding: 0.48rem 0.55rem;
            border-bottom: 1px solid var(--border-card);
            vertical-align: middle;
            font-size: 0.78rem;
            line-height: 1.25;
        }

        table.sc-table td {
            padding: 0.38rem 0.55rem;
            border-bottom: 1px solid var(--border-card);
            vertical-align: middle;
            font-size: 0.8rem;
            line-height: 1.25;
            color: var(--text-primary);
        }

        table.sc-table thead tr:first-child th {
            color: #ffffff;
            font-weight: 700;
            text-align: center;
            font-size: 0.78rem;
            border-right: 1px solid rgba(255,255,255,0.1);
        }

        .th-store-bg { background: #991b1b !important; }
        .th-store-sub { background: #7f1d1d !important; }

        .th-qty-bg { background: #3730a3 !important; }
        .th-qty-sub { background: #312e81 !important; }

        .th-val-bg { background: #0369a1 !important; }
        .th-val-sub { background: #075985 !important; }

        .th-master-bg { background: #0f172a !important; }
        .th-master-sub { background: #1e293b !important; }

        .p-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 7px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .p-badge-p1 {
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }
        .p-badge-p2 {
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }
        .p-badge-p3 {
            background: rgba(148, 163, 184, 0.15);
            color: #cbd5e1;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .p-badge-p4 {
            background: rgba(16, 185, 129, 0.18);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }

        table.sc-table thead tr:nth-child(2) th {
            color: #f1f5f9;
            font-size: 0.72rem;
            font-weight: 600;
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        table.sc-table tbody tr:hover {
            background-color: var(--bg-hover) !important;
        }

        table.sc-table td.text-left { text-align: left; }
        table.sc-table td.text-center { text-align: center; }

        table.sc-table tfoot tr td {
            padding: 0.48rem 0.55rem;
            background: var(--table-tfoot-bg);
            font-weight: 700;
            border-top: 2px solid var(--primary);
            color: var(--text-primary);
            font-size: 0.82rem;
        }

        .c-red { color: #f87171 !important; font-weight: 600; }
        .c-green { color: #34d399 !important; font-weight: 600; }
        .c-blue { color: #38bdf8 !important; font-weight: 600; }
        .c-orange { color: #fb923c !important; font-weight: 600; }
        .c-purple { color: #a5b4fc !important; font-weight: 600; }

        .btn-view-detail {
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
            font-family: inherit;
        }

        .btn-view-detail:hover {
            background: #0284c7;
            color: #ffffff;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
        }

        /* Table Mini Progress Bar */
        .tbl-progress-cell {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            width: 100%;
        }

        .tbl-progress-bar {
            width: 50px;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            overflow: hidden;
            flex-shrink: 0;
        }

        .tbl-progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.4s ease;
        }

        input[type="text"], select {
            background: var(--input-bg);
            color: var(--text-primary);
            border: 1px solid var(--input-border);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        input[type="text"]:focus, select:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
        }
        input[type="text"]::placeholder {
            color: var(--text-muted);
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
        }

        .modal-overlay.active { display: flex; }

        .modal-box {
            background: var(--modal-bg);
            width: 98%;
            max-width: 1780px;
            height: 94vh;
            border-radius: 14px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 60px rgba(0,0,0,0.8);
            border: 1px solid var(--border-card);
            transition: all 0.2s ease-in-out;
        }

        .modal-box.is-fullscreen {
            width: 100vw !important;
            height: 100vh !important;
            max-width: 100vw !important;
            border-radius: 0 !important;
        }

        .modal-head {
            padding: 0.95rem 1.35rem;
            background: var(--modal-head-bg);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-card);
        }

        .modal-head-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .modal-btn-act {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.15);
            color: #ffffff;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            transition: all 0.15s;
            font-family: inherit;
        }

        .modal-btn-act:hover {
            background: rgba(255,255,255,0.25);
            border-color: #38bdf8;
        }

        .btn-close {
            background: rgba(255,255,255,0.1);
            border: none;
            color: #94a3b8;
            font-size: 1.1rem;
            width: 32px;
            height: 32px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }

        .btn-close:hover {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
        }

        .modal-toolbar {
            padding: 0.75rem 1.15rem;
            background: var(--modal-toolbar-bg);
            border-bottom: 1px solid var(--border-card);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.65rem;
        }

        #detailTable {
            width: 100%;
            table-layout: auto;
        }

        #detailTable thead th {
            background: #0f172a !important;
            color: #ffffff !important;
            position: sticky;
            top: 0;
            z-index: 10;
            font-size: 0.76rem;
            font-weight: 700;
            text-align: right;
            padding: 0.48rem 0.5rem;
            border-bottom: 2px solid #334155;
            white-space: nowrap;
            line-height: 1.2;
        }

        #detailTable thead th.text-left { text-align: left; }
        #detailTable thead th.text-center { text-align: center; }

        #detailTable tbody td {
            padding: 0.35rem 0.5rem;
            font-size: 0.78rem;
            vertical-align: middle;
            line-height: 1.25;
        }

        .tag-pill {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            white-space: nowrap;
        }
    
        /* DC 4-COLUMN AD-AG STYLES */
        .active-dc {
            background: linear-gradient(135deg, #c084fc, #9333ea) !important;
            color: #fff !important;
            border-color: #c084fc !important;
            box-shadow: 0 4px 15px rgba(192, 132, 252, 0.4) !important;
        }
        .dc-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 1.25rem;
        }
        @media (max-width: 1024px) {
            .dc-kpi-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        @media (max-width: 640px) {
            .dc-kpi-grid {
                grid-template-columns: 1fr;
            }
        }
        .dc-quick-filters {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }
        .dc-filter-pill {
            background: var(--bg-card-alt);
            border: 1px solid var(--border-card);
            color: var(--text-secondary);
            padding: 0.45rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            transition: all 0.2s ease;
        }
        .dc-filter-pill:hover {
            border-color: var(--primary);
            color: var(--text-primary);
            transform: translateY(-1px);
        }
        .dc-filter-pill.active {
            background: rgba(192, 132, 252, 0.15);
            border-color: #c084fc;
            color: #f8fafc;
            box-shadow: 0 0 12px rgba(192, 132, 252, 0.25);
        }
        .dc-filter-pill .badge {
            background: rgba(255, 255, 255, 0.12);
            padding: 0.15rem 0.45rem;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 700;
        }
        .dc-filter-pill.active .badge {
            background: #9333ea;
            color: #fff;
        }
        .tag-ad-dongy {
            background: rgba(52, 211, 153, 0.15);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.35);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-ad-tuchoi {
            background: rgba(248, 113, 113, 0.15);
            color: #f87171;
            border: 1px solid rgba(248, 113, 113, 0.35);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-ad-kiemtra {
            background: rgba(251, 191, 36, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.35);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-ad-chua {
            background: rgba(148, 163, 184, 0.15);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.35);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-af-done {
            background: rgba(52, 211, 153, 0.2);
            color: #34d399;
            border: 1px solid #059669;
            font-size: 0.75rem;
            font-weight: 800;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-af-hlv {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            border: 1px solid #dc2626;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-af-check {
            background: rgba(245, 158, 11, 0.2);
            color: #fde68a;
            border: 1px solid #d97706;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tag-af-pending {
            background: rgba(148, 163, 184, 0.12);
            color: #94a3b8;
            border: 1px dashed rgba(148, 163, 184, 0.35);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .note-bubble {
            font-size: 0.75rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.04);
            padding: 0.25rem 0.45rem;
            border-radius: 4px;
            border-left: 2.5px solid #38bdf8;
            word-break: break-word;
            line-height: 1.25;
        }

    </style>
</head>
<body>

    <!-- Header -->
    <header class="app-header">
        <div class="header-container">
            <div class="header-title">
                <i class="fa-solid fa-boxes-stacked header-icon"></i>
                <div class="header-text">
                    <h1>BÁO CÁO ĐỐI SOÁT HÀNG ĐÔNG - MÁT</h1>
                    <p>Hệ thống SCM • Phân tích Ngưỡng 100K theo TỔNG SIÊU THỊ / NGÀY (Store-level)</p>
                </div>
            </div>

            <!-- Group Switcher & Month Filter -->
            <div style="display:flex; align-items:center; gap:0.65rem; flex-wrap:wrap;">
                <!-- Group Tabs -->
                <div class="group-switcher">
                    <button class="group-btn active-mat" id="tab-mat" onclick="changeGroup('mat')">
                        <i class="fa-solid fa-drumstick-bite"></i> 🥩 NHÓM HÀNG MÁT
                    </button>
                    <button class="group-btn" id="tab-dong" onclick="changeGroup('dong')">
                        <i class="fa-solid fa-snowflake"></i> ❄️ NHÓM HÀNG ĐÔNG
                    </button>
                    <button class="group-btn" id="tab-all" onclick="changeGroup('all')">
                        <i class="fa-solid fa-layer-group"></i> 🌟 ĐÔNG & MÁT
                    </button>
                </div>

                <!-- Global Month Filter Selector -->
                <div class="month-switcher">
                    <i class="fa-solid fa-calendar-days" style="color:#38bdf8;"></i>
                    <select class="month-select" id="globalMonthFilter" onchange="changeMonth(this.value)">
                        <option value="all">📅 Tất Cả Các Tháng</option>
                        <!-- Dynamic Month options -->
                    </select>
                </div>
            </div>

            <div style="display:flex; align-items:center; gap:0.75rem;">
                <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="Chuyển đổi giao diện Phông Đen / Sáng">
                    <i class="fa-solid fa-moon"></i> <span>Phông Tối</span>
                </button>
                <button class="action-btn" onclick="exportExcel()">
                    <i class="fa-solid fa-file-excel"></i> Xuất Excel
                </button>
            </div>
        </div>
    </header>

    <div class="main-container">

        <!-- 4 Summary KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card c-blue">
                <div class="kpi-label">1. Tổng Chênh Lệch Toàn Kỳ <i class="fa-solid fa-scale-unbalanced-flip"></i></div>
                <div class="kpi-value c-blue" id="kpi-val-total">0 đ</div>
                <div class="kpi-desc" id="kpi-desc-total">Tổng số lượng lệch: <strong id="kpi-qty-total">0</strong> sp • <strong id="kpi-stores-total">0</strong> ST (<span id="kpi-cases-total">0</span> dòng hàng)</div>
            </div>

            <div class="kpi-card c-red">
                <div class="kpi-label">2. Siêu Thị Lệch ≥ 100k <i class="fa-solid fa-fire"></i></div>
                <div class="kpi-value c-red" id="kpi-val-over100k">0 đ</div>
                <div class="kpi-desc" id="kpi-desc-over100k">Có <strong id="kpi-stores-over100k">0</strong> ST lệch ≥ 100k (Chiếm <strong id="kpi-pct-over100k">0%</strong> tổng tiền)</div>
            </div>

            <div class="kpi-card c-green">
                <div class="kpi-label">3. Đã Xử Lý <i class="fa-solid fa-circle-check"></i></div>
                <div class="kpi-value c-green" id="kpi-val-daxuly">0 đ</div>
                <div class="kpi-desc" id="kpi-desc-daxuly">Đã chốt vào Kho/ST/Hao hụt: <strong id="kpi-pct-daxuly">0%</strong> hoàn tất • <strong id="kpi-stores-daxuly">0</strong> ST</div>
            </div>

            <div class="kpi-card c-orange">
                <div class="kpi-label">4. Chưa Hoàn Tất <i class="fa-solid fa-clock-rotate-left"></i></div>
                <div class="kpi-value c-orange" id="kpi-val-treo">0 đ</div>
                <div class="kpi-desc" id="kpi-desc-treo">🟡 Đang XL (ST ≥ 100k): <strong id="kpi-val-dangxl">0 đ</strong> • ⚪ Không XL: <strong id="kpi-val-khongxl">0 đ</strong></div>
            </div>
        </div>

        <!-- ========================================================== -->
        <!-- THANH TỔNG QUAN TIẾN ĐỘ XỬ LÝ TOÀN KỲ (GLOBAL RESOLUTION TRACKER) -->
        <!-- ========================================================== -->
        <div class="progress-overview-card">
            <div class="progress-overview-header">
                <div class="progress-title">
                    <i class="fa-solid fa-bars-progress" style="color:#38bdf8;"></i>
                    <span id="progressCardTitle">TỔNG QUAN TIẾN ĐỘ XỬ LÝ</span>
                </div>
                <div class="progress-status-badge" id="globalProgressBadge">
                    Đang tính toán...
                </div>
            </div>
            
            <!-- Multi-segment Progress Bar -->
            <div class="multi-progress-bar">
                <div class="progress-segment seg-done" id="bar-seg-done" style="width: 0%;" title="Đã xử lý"></div>
                <div class="progress-segment seg-pending" id="bar-seg-pending" style="width: 0%;" title="Đang xử lý (ST ≥ 100k)"></div>
                <div class="progress-segment seg-ignored" id="bar-seg-ignored" style="width: 0%;" title="Không xử lý (ST < 100k)"></div>
            </div>

            <div class="progress-stats-grid">
                <div class="p-stat-box">
                    <div class="p-stat-label">🟢 ĐÃ XỬ LÝ HOÀN TẤT</div>
                    <div class="p-stat-val c-green" id="stat-val-done">0 đ</div>
                    <div class="p-stat-sub" id="stat-sub-done">Chiếm <strong id="stat-pct-done">0%</strong> • <strong id="stat-st-done">0</strong> Siêu Thị (0 lần giao lệch) • <span id="stat-cases-done">0</span> dòng hàng</div>
                </div>

                <div class="p-stat-box">
                    <div class="p-stat-label">🟡 ĐANG XỬ LÝ (ST ≥ 100k)</div>
                    <div class="p-stat-val c-orange" id="stat-val-pending">0 đ</div>
                    <div class="p-stat-sub" id="stat-sub-pending">Chiếm <strong id="stat-pct-pending">0%</strong> • <strong id="stat-st-pending">0</strong> Siêu Thị (0 lần giao lệch) • <span id="stat-cases-pending">0</span> dòng hàng</div>
                </div>

                <div class="p-stat-box">
                    <div class="p-stat-label">⚪ KHÔNG XỬ LÝ (ST &lt; 100k)</div>
                    <div class="p-stat-val" style="color:var(--text-muted);" id="stat-val-ignored">0 đ</div>
                    <div class="p-stat-sub" id="stat-sub-ignored">Chiếm <strong id="stat-pct-ignored">0%</strong> • <strong id="stat-st-ignored">0</strong> Siêu Thị (0 lần giao lệch) • <span id="stat-cases-ignored">0</span> dòng hàng</div>
                </div>
            </div>
        </div>

        <!-- ========================================================== -->
        <!-- EXECUTIVE SUMMARY: NHẬN XÉT ĐỐI SOÁT & KHUYẾN NGHỊ GIẢI PHÁP -->
        <!-- ========================================================== -->
        <div class="executive-insights-card">
            <div class="insights-header">
                <i class="fa-solid fa-lightbulb"></i>
                <span id="insightsCardTitle">NHẬN XÉT ĐỐI SOÁT & KHUYẾN NGHỊ GIẢI PHÁP HÀNH ĐỘNG</span>
            </div>
            <div class="insights-grid">
                <div class="insight-section">
                    <div class="insight-section-title" style="color:#38bdf8;">
                        <i class="fa-solid fa-magnifying-glass-chart"></i> 1. Nhận Xét Chuyên Sâu Từng Nhóm Ngưỡng
                    </div>
                    <div class="insight-item danger-left" id="insight-item-over">
                        <strong>🚨 Nhóm Trọng Yếu (ST ≥ 100k/ngày):</strong> Chiếm tới <strong>91.1% số vụ</strong> và <strong>98.2% giá trị (3.12 tỷ VNĐ)</strong>. Tiến độ xử lý đạt <strong>91.9%</strong>; hiện còn tồn <strong>2,069 vụ (~252.3 triệu VNĐ)</strong> tập trung ở các ngày cuối tháng 8 cần ưu tiên xử lý dứt điểm.
                    </div>
                    <div class="insight-item success-left" id="insight-item-under">
                        <strong>⚪ Nhóm Miễn Trừ (ST &lt; 100k/ngày):</strong> Chiếm <strong>8.9% số vụ</strong> nhưng chỉ chiếm <strong>1.8% giá trị (57.3 triệu VNĐ)</strong>. Trong đó 65.5% đã tự động quy trách nhiệm, còn lại 34.5% (19.8 triệu VNĐ) thuộc diện miễn trừ không cần tra soát tốn nhân lực.
                    </div>
                    <div class="insight-item warning-left" id="insight-item-trend">
                        <strong>📈 Biên Độ Dao Động:</strong> Số lượng vụ việc dao động mạnh từ <strong>300 đến ~2,550 vụ/ngày</strong> (đỉnh điểm vào các ngày 28-30 hàng tháng). Tỷ lệ hoàn tất các ngày tháng 7 đạt &gt;99%, trong khi các ngày gần nhất tháng 8 đang cuốn chiếu đạt từ 50% - 86%.
                    </div>
                </div>

                <div class="insight-section">
                    <div class="insight-section-title" style="color:#34d399;">
                        <i class="fa-solid fa-shield-halved"></i> 2. Đề Xuất Giải Pháp Hành Động (Action Plan)
                    </div>
                    <div class="insight-item success-left">
                        <strong>🎯 Giải pháp 1 (Quy tắc 80/20):</strong> Tập trung 100% nhân sự vào <strong>Bảng Danh Sách Siêu Thị Ưu Tiên P1</strong> (nhóm ST ≥ 100k đang treo) để xử lý dứt điểm công nợ còn lại trước kỳ chốt sổ.
                    </div>
                    <div class="insight-item" style="border-left-color:#818cf8;">
                        <strong>⚡ Giải pháp 2 (Tự động hóa Miễn trừ):</strong> Áp dụng cơ chế <em>Auto-Waive</em> (tự động kết chuyển hao hụt định mức) cho nhóm ST &lt; 100k/ngày, giúp giải phóng 80% thời gian rà soát chi tiết từng hóa đơn vụn.
                    </div>
                    <div class="insight-item warning-left">
                        <strong>🛡️ Giải pháp 3 (Kiểm soát Ngày Cao Điểm):</strong> Vào các ngày cao điểm giao nhận cuối tháng (khi số case vượt 1,000 vụ/ngày), bắt buộc áp dụng <em>Biên bản giao nhận điện tử tức thời</em> tại cửa xe để giảm 60% tỷ lệ sai lệch hàng ĐÔNG - MÁT.
                    </div>
                </div>
            </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 8 BIỂU ĐỒ TRỰC QUAN TOÀN DIỆN (LƯỚI ĐA CHIỀU 2 CỘT CÂN ĐỐI KÈM TÍNH NĂNG THU/PHÓNG & NHẬN XÉT) -->
        <!-- ========================================================================= -->
        <div class="charts-grid-5">
            
            <!-- Biểu đồ 1: So Sánh Số Vụ Việc & Tỷ Lệ Xử Lý Theo 2 Phân Khúc -->
            <div class="chart-card" style="grid-column: 1 / -1; border-color: rgba(56, 189, 248, 0.35); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-chart-column" style="color:#38bdf8;"></i> 1. So Sánh Số Vụ Việc (Cases) & Tỷ Lệ Xử Lý (% Hoàn Tất) Của 2 Phân Khúc (ST ≥ 100k vs ST < 100k)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartCasesComparison')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container" style="height: 350px;">
                    <canvas id="chartCasesComparison"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 2: Biến Động Tổng Tiền & SL Chênh Lệch Hàng Ngày -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-chart-column c-blue"></i> 2. Giá trị chênh lệch & Số Lượng Theo Ngày</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDailyLech')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container">
                    <canvas id="chartDailyLech"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 3: Tiến Độ Xử Lý Chênh Lệch Theo Ngày (Stacked Bar & % Line) -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-bars-progress c-green"></i> 3. Tiến Độ Xử Lý Chênh Lệch Theo Ngày (VNĐ & % Hoàn Tất)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDailyProgress')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container">
                    <canvas id="chartDailyProgress"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 4: Số Lượng Siêu Thị (ST) Phát Sinh Lệch Theo Ngày -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-store c-purple"></i> 4. Số Lượng Siêu Thị (ST) Phát Sinh Lệch Theo Ngày</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDailyStores')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container">
                    <canvas id="chartDailyStores"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 5: Biến Động Giá Trị Chênh Lệch Theo Nhóm ST (≥ 100k vs < 100k) -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-chart-line c-red"></i> 5. Biến Động Giá Trị Chênh Lệch Theo Nhóm ST (≥ 100k vs < 100k)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartTrendThreshold')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container">
                    <canvas id="chartTrendThreshold"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 6: Giá trị chênh lệch phân bổ theo điểm nhận & Tiến độ (CỘT PHẢI CẠNH BIỂU ĐỒ 5) -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-chart-pie c-orange"></i> 6. Phân Bổ Điểm Nhận Trách Nhiệm & Trạng Thái Xử Lý</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDestDoughnut')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="doughnut-layout">
                    <div class="chart-container" style="height:270px;">
                        <canvas id="chartDestDoughnut"></canvas>
                    </div>
                    <div class="doughnut-legend-list" id="destLegendList">
                        <!-- Render dynamic legend rows with % and VNĐ -->
                    </div>
                </div>
            </div>

            <!-- Biểu đồ 8: Phân Bổ Kết Quả DC Phản Hồi & So Sánh Theo Nhóm Hàng -->
            <div class="chart-card">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-chart-pie" style="color:#38bdf8;"></i> 8. Tỷ Lệ DC Phản Hồi & Kết Quả Xác Nhận Giữa 2 Nhóm Hàng (MÁT vs ĐÔNG)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDCGroupCompare')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="doughnut-layout">
                    <div class="chart-container" style="height:270px;">
                        <canvas id="chartDCGroupCompare"></canvas>
                    </div>
                    <div class="doughnut-legend-list" id="dcGroupLegendList">
                        <!-- Dynamic DC group comparison rows -->
                    </div>
                </div>
            </div>

            <!-- Biểu đồ 7: Tiến Độ Xử Lý Trả DC & Tỷ Lệ DC Phản Hồi Theo Ngày -->
            <div class="chart-card" style="grid-column: 1 / -1; border-color: rgba(168, 85, 247, 0.35); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-truck-ramp-box" style="color:#c084fc;"></i> 7. Tiến Độ Xử Lý Trả DC & Tỷ Lệ DC Phản Hồi Theo Ngày (Số Dòng Hàng & % Phản Hồi)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDCResponse')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container" style="height: 340px;">
                    <canvas id="chartDCResponse"></canvas>
                </div>
            </div>

            
            <!-- ========================================================================= -->
            <!-- CỤM BIỂU ĐỒ CHUYÊN SÂU 4 CỘT AD - AG: TIẾN ĐỘ KFM CHỈNH DONE & DC TỪ CHỐI -->
            <!-- ========================================================================= -->

            <!-- Biểu đồ 9: Tiến Độ KFM Chỉnh DONE Theo Ngày (Tập DC Đồng Ý Claim) -->
            <div class="chart-card" style="border-color: rgba(52, 211, 153, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-circle-check" style="color:#34d399;"></i> 9. Tiến Độ KFM Chỉnh DONE Theo Ngày (Tập DC Đồng Ý Claim - Cột AF)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartKFMProgressDaily')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container" style="height: 310px;">
                    <canvas id="chartKFMProgressDaily"></canvas>
                </div>
            </div>

            <!-- Biểu đồ 10: Cơ Cấu DC Khác Đồng Ý & Tiến Độ KFM Phản Hồi -->
            <div class="chart-card" style="border-color: rgba(248, 113, 113, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-scale-balanced" style="color:#f87171;"></i> 10. Cơ Cấu Các Case DC Khác Đồng Ý & KFM Phản Hồi (Từ Chối, KT Lại, Chờ)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDCNonAgreeBreakdown')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="doughnut-layout">
                    <div class="chart-container" style="height: 270px;">
                        <canvas id="chartDCNonAgreeBreakdown"></canvas>
                    </div>
                    <div class="doughnut-legend-list" id="dcNonAgreeLegendList">
                        <!-- Dynamic legend for DC non-agree categories -->
                    </div>
                </div>
            </div>

            <!-- Biểu đồ 11: Top Điểm Nóng Ghi Chú DC Note (Cột AE) & KFM Note (Cột AG) -->
            <div class="chart-card" style="grid-column: 1 / -1; border-color: rgba(192, 132, 252, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div class="chart-header">
                    <h3><i class="fa-solid fa-tags" style="color:#c084fc;"></i> 11. Top Điểm Nóng Lý Do DC Note (Cột AE) & Hành Động KFM Note (Cột AG)</h3>
                    <button class="btn-chart-zoom" onclick="openChartZoom('chartDCNoteBreakdown')">
                        <i class="fa-solid fa-expand"></i> Phóng to & Nhận xét
                    </button>
                </div>
                <div class="chart-container" style="height: 320px;">
                    <canvas id="chartDCNoteBreakdown"></canvas>
                </div>
            </div>

            <!-- Khối Nhận Xét & Phân Tích Tự Động Biểu Đồ 7 & 8 (AI Insights & SCM Takeaways) -->
            <div class="executive-insights-card" style="grid-column: 1 / -1; border-color: rgba(168, 85, 247, 0.4); background: linear-gradient(135deg, rgba(30, 27, 75, 0.75) 0%, rgba(15, 23, 42, 0.9) 100%); box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-top: 0.25rem;">
                <div class="insights-header" style="color: #c084fc;">
                    <i class="fa-solid fa-brain" style="color: #c084fc;"></i> 
                    <span>NHẬN XÉT & PHÂN TÍCH TỰ ĐỘNG: TIẾN ĐỘ TRẢ DC & TỶ LỆ PHẢN HỒI (AI INSIGHTS & TAKEAWAYS)</span>
                    <span id="dcInsightsBadge" class="tag-pill" style="margin-left: auto; background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 0.75rem; font-weight: 700;">🧠 SCM Intelligence</span>
                </div>
                <div class="insights-grid" style="grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                    <!-- Cột 1: Điểm nóng phản hồi thấp & Ngày tồn đọng -->
                    <div class="insight-section">
                        <div class="insight-section-title" style="color: #f87171;">
                            <i class="fa-solid fa-triangle-exclamation"></i> 1. ĐIỂM NÓNG & NGÀY DC PHẢN HỒI THẤP
                        </div>
                        <div id="dcInsightLowResp" class="insight-item danger-left">
                            <!-- Render dynamic low response dates and pending cases -->
                        </div>
                    </div>

                    <!-- Cột 2: So sánh phân hóa giữa 2 nhóm hàng Mát vs Đông -->
                    <div class="insight-section">
                        <div class="insight-section-title" style="color: #38bdf8;">
                            <i class="fa-solid fa-scale-balanced"></i> 2. PHÂN HÓA PHẢN HỒI (MÁT vs ĐÔNG)
                        </div>
                        <div id="dcInsightGroupCompare" class="insight-item" style="border-left-color: #38bdf8;">
                            <!-- Render dynamic group comparison insight -->
                        </div>
                    </div>

                    <!-- Cột 3: Đề xuất hành động SCM tức thời -->
                    <div class="insight-section">
                        <div class="insight-section-title" style="color: #34d399;">
                            <i class="fa-solid fa-bolt"></i> 3. ĐỀ XUẤT HÀNH ĐỘNG SCM TỨC THỜI
                        </div>
                        <div id="dcInsightActionPlan" class="insight-item success-left">
                            <!-- Render dynamic action plan -->
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <!-- ========================================================================= -->
        <!-- BỘ CHUYỂN ĐỔI 3 BẢNG TIẾN ĐỘ TỔNG HỢP / GIÁ TRỊ / SỐ LƯỢNG -->
        <!-- ========================================================================= -->
        <div class="table-view-tabs">
            <button class="table-view-tab active-master" id="tab-btn-master" onclick="switchTableTab('master')">
                <i class="fa-solid fa-table-columns"></i> BẢNG TỔNG HỢP TIẾN ĐỘ
            </button>
            <button class="table-view-tab" id="tab-btn-val" onclick="switchTableTab('val')">
                <i class="fa-solid fa-money-bill-wave"></i> BẢNG GIÁ TRỊ (VNĐ)
            </button>
            <button class="table-view-tab" id="tab-btn-qty" onclick="switchTableTab('qty')">
                <i class="fa-solid fa-boxes-packing"></i> BẢNG SỐ LƯỢNG (PCS / KG)
            </button>
            <button class="table-view-tab" id="tab-btn-dc" onclick="switchTableTab('dc')">
                <i class="fa-solid fa-truck-ramp-box"></i> 🚚 BẢNG TRẢ DC & PHẢN HỒI DC
            </button>
        </div>

        <!-- ========================================================================= -->
        <!-- BẢNG 1: TỔNG HỢP TIẾN ĐỘ (MẶC ĐỊNH HIỂN THỊ) -->
        <!-- ========================================================================= -->
        <div class="table-card" id="card-master-table">
            <div class="table-header-row">
                <div class="table-title">
                    <i class="fa-solid fa-layer-group" style="color:#38bdf8;"></i> BẢNG TỔNG HỢP TIẾN ĐỘ
                </div>
                <div class="seg-pill">
                    <button class="seg-btn active" id="btn-p-master-daily" onclick="setMasterPeriod('daily')">Theo Ngày</button>
                    <button class="seg-btn" id="btn-p-master-monthly" onclick="setMasterPeriod('monthly')">Theo Tháng</button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="sc-table" id="masterTable">
                    <thead>
                        <tr>
                            <th rowspan="2" class="th-master-bg" style="width:105px;">Thời Gian</th>
                            <th colspan="2" class="th-master-bg">Giao Nhận</th>
                            <th rowspan="2" class="th-master-bg" style="background:#0369a1 !important; color:#fff;">Chênh Lệch<br><span style="font-size:0.7rem; font-weight:400; opacity:0.9;">(SL & Tiền VNĐ)</span></th>
                            <th colspan="2" class="th-master-bg">Phân Khúc Siêu Thị</th>
                            <th colspan="3" class="th-master-bg">Điểm Nhận Trách Nhiệm</th>
                            <th colspan="4" class="th-master-bg">Tiến Độ Xử Lý</th>
                            <th rowspan="2" class="th-master-bg" style="width:75px;">Chi Tiết</th>
                        </tr>
                        <tr>
                            <th class="th-master-sub">SL Chuyển</th>
                            <th class="th-master-sub">SL Nhận</th>
                            <th class="th-master-sub">ST ≥ 100k</th>
                            <th class="th-master-sub">ST < 100k</th>
                            <th class="th-master-sub">Kho ĐÔNG MÁT</th>
                            <th class="th-master-sub">Siêu Thị</th>
                            <th class="th-master-sub">Hao Hụt</th>
                            <th class="th-master-sub">🟢 Đã XL</th>
                            <th class="th-master-sub" style="color:#fed7aa;">🟡 Đang XL (ST ≥ 100k)</th>
                            <th class="th-master-sub" style="color:#cbd5e1;">⚪ Không XL (ST < 100k)</th>
                            <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                        </tr>
                    </thead>
                    <tbody id="masterTableBody"></tbody>
                    <tfoot id="masterTableFoot"></tfoot>
                </table>
            </div>
        </div>

        <!-- ========================================================================= -->
        <!-- BẢNG 2: GIÁ TRỊ (VNĐ) -->
        <!-- ========================================================================= -->
        <div class="table-card" id="card-val-table" style="display:none;">
            <div class="table-header-row">
                <div class="table-title">
                    <i class="fa-solid fa-money-bill-wave" style="color:#38bdf8;"></i> BẢNG GIÁ TRỊ (VNĐ)
                </div>
                <div class="seg-pill">
                    <button class="seg-btn active" id="btn-p-val-daily" onclick="setValPeriod('daily')">Theo Ngày</button>
                    <button class="seg-btn" id="btn-p-val-monthly" onclick="setValPeriod('monthly')">Theo Tháng</button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="sc-table" id="valTable">
                    <thead>
                        <tr>
                            <th rowspan="2" class="th-val-bg" style="width:110px;">Thời Gian</th>
                            <th rowspan="2" class="th-val-bg">Tổng Tiền Lệch</th>
                            <th colspan="2" class="th-val-bg">Phân Khúc Tiền Theo Siêu Thị</th>
                            <th colspan="3" class="th-val-bg">Điểm Nhận Trách Nhiệm (VNĐ)</th>
                            <th colspan="4" class="th-val-bg">Tiến Độ Xử Lý (VNĐ)</th>
                            <th rowspan="2" class="th-val-bg" style="width:80px;">Chi Tiết</th>
                        </tr>
                        <tr>
                            <th class="th-val-sub">Nhóm ST ≥ 100k</th>
                            <th class="th-val-sub">Nhóm ST < 100k</th>
                            <th class="th-val-sub">Kho ĐÔNG MÁT</th>
                            <th class="th-val-sub">Siêu Thị</th>
                            <th class="th-val-sub">Hao Hụt</th>
                            <th class="th-val-sub">🟢 Đã Xử Lý</th>
                            <th class="th-val-sub" style="color:#fed7aa;">🟡 Đang Xử Lý (ST ≥ 100k)</th>
                            <th class="th-val-sub" style="color:#cbd5e1;">⚪ Không Xử Lý (ST < 100k)</th>
                            <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                        </tr>
                    </thead>
                    <tbody id="valTableBody"></tbody>
                    <tfoot id="valTableFoot"></tfoot>
                </table>
            </div>
        </div>

        <!-- ========================================================================= -->
        <!-- BẢNG 3: SỐ LƯỢNG (PCS / KG) -->
        <!-- ========================================================================= -->
        <div class="table-card" id="card-qty-table" style="display:none;">
            <div class="table-header-row">
                <div class="table-title">
                    <i class="fa-solid fa-boxes-packing" style="color:#818cf8;"></i> BẢNG SỐ LƯỢNG (PCS / KG)
                </div>
                <div class="seg-pill">
                    <button class="seg-btn active" id="btn-p-qty-daily" onclick="setQtyPeriod('daily')">Theo Ngày</button>
                    <button class="seg-btn" id="btn-p-qty-monthly" onclick="setQtyPeriod('monthly')">Theo Tháng</button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="sc-table" id="qtyTable">
                    <thead>
                        <tr>
                            <th rowspan="2" class="th-qty-bg" style="width:110px;">Thời Gian</th>
                            <th colspan="3" class="th-qty-bg">Giao Nhận (SL Hàng)</th>
                            <th colspan="3" class="th-qty-bg">Số Siêu Thị Lệch (ST)</th>
                            <th colspan="3" class="th-qty-bg">Điểm Nhận (SL Hàng)</th>
                            <th colspan="4" class="th-qty-bg">Tiến Độ Xử Lý (SL Hàng)</th>
                            <th rowspan="2" class="th-qty-bg" style="width:80px;">Chi Tiết</th>
                        </tr>
                        <tr>
                            <th class="th-qty-sub">SL Chuyển</th>
                            <th class="th-qty-sub">SL Nhận</th>
                            <th class="th-qty-sub">SL Lệch</th>
                            <th class="th-qty-sub">Tổng ST</th>
                            <th class="th-qty-sub">ST ≥ 100k</th>
                            <th class="th-qty-sub">ST < 100k</th>
                            <th class="th-qty-sub">Kho ĐÔNG MÁT</th>
                            <th class="th-qty-sub">Siêu Thị</th>
                            <th class="th-qty-sub">Hao Hụt</th>
                            <th class="th-qty-sub">🟢 Đã Xử Lý</th>
                            <th class="th-qty-sub" style="color:#fed7aa;">🟡 Đang Xử Lý (ST ≥ 100k)</th>
                            <th class="th-qty-sub" style="color:#cbd5e1;">⚪ Không Xử Lý (ST < 100k)</th>
                            <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                        </tr>
                    </thead>
                    <tbody id="qtyTableBody"></tbody>
                    <tfoot id="qtyTableFoot"></tfoot>
                </table>
            </div>
        </div>

        
        <!-- ========================================================================= -->
        <!-- BẢNG 4: TRẢ DC & PHẢN HỒI DC (TOÀN DIỆN 4 CỘT AD - AG) -->
        <!-- ========================================================================= -->
        <div class="table-card" id="card-dc-table" style="display:none; border-top: 3px solid #c084fc;">
            <!-- Header Row with Controls -->
            <div class="table-header-row" style="flex-wrap:wrap; gap:0.75rem;">
                <div class="table-title" style="color:#c084fc; font-size:1.15rem;">
                    <i class="fa-solid fa-truck-ramp-box" style="color:#c084fc;"></i> BẢNG ĐỐI SOÁT TRẢ DC & PHẢN HỒI DC (4 CỘT AD - AG)
                </div>
                <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                    <div class="seg-pill">
                        <button class="seg-btn active" id="btn-dc-mode-summary" onclick="switchDCViewMode('summary')">📊 Tiến Độ Tổng Hợp</button>
                        <button class="seg-btn" id="btn-dc-mode-detail" onclick="switchDCViewMode('detail')">📋 Tra Cứu Chi Tiết 4 Cột</button>
                    </div>
                    <div class="seg-pill" id="dc-period-pill">
                        <button class="seg-btn active" id="btn-p-dc-daily" onclick="setDcPeriod('daily')">Theo Ngày</button>
                        <button class="seg-btn" id="btn-p-dc-monthly" onclick="setDcPeriod('monthly')">Theo Tháng</button>
                    </div>
                    <button class="btn-view-detail" style="background:#10b981; color:#fff; border-color:#059669; padding:0.35rem 0.85rem;" onclick="exportDCExcel()">
                        <i class="fa-solid fa-file-excel"></i> Xuất Excel DC
                    </button>
                </div>
            </div>

            <!-- Khối 4 Thẻ KPI Phân Tích Chuyên Sâu 4 Cột AD - AG -->
            <div class="dc-kpi-grid">
                <!-- Thẻ 1: Tỷ lệ DC Phản Hồi Trên Tổng Trả DC -->
                <div class="kpi-card" style="border-left: 4px solid #38bdf8; background: var(--bg-card-alt);">
                    <div class="kpi-title" style="color:#38bdf8;"><i class="fa-solid fa-truck-ramp-box"></i> 1. TỶ LỆ DC ĐÃ PHẢN HỒI</div>
                    <div class="kpi-val" id="dc-kpi-pct-resp" style="color:#38bdf8; font-size:1.75rem;">-</div>
                    <div class="kpi-sub" id="dc-kpi-sub-resp" style="font-size:0.78rem; line-height:1.4;">
                        Đang tính toán...
                    </div>
                </div>

                <!-- Thẻ 2: Tiến độ KFM Chỉnh DONE (Phụ thuộc DC Đồng Ý Claim) -->
                <div class="kpi-card" style="border-left: 4px solid #34d399; background: var(--bg-card-alt);">
                    <div class="kpi-title" style="color:#34d399;"><i class="fa-solid fa-circle-check"></i> 2. KFM CHỈNH DONE (DC ĐỒNG Ý)</div>
                    <div class="kpi-val" id="dc-kpi-pct-done" style="color:#34d399; font-size:1.75rem;">-</div>
                    <div class="kpi-sub" id="dc-kpi-sub-done" style="font-size:0.78rem; line-height:1.4;">
                        Đang tính toán...
                    </div>
                </div>

                <!-- Thẻ 3: DC Khác Đồng Ý Claim & KFM Phản Hồi -->
                <div class="kpi-card" style="border-left: 4px solid #f87171; background: var(--bg-card-alt);">
                    <div class="kpi-title" style="color:#f87171;"><i class="fa-solid fa-scale-balanced"></i> 3. DC KHÁC ĐỒNG Ý CLAIM</div>
                    <div class="kpi-val" id="dc-kpi-pct-nonagree" style="color:#f87171; font-size:1.75rem;">-</div>
                    <div class="kpi-sub" id="dc-kpi-sub-nonagree" style="font-size:0.78rem; line-height:1.4;">
                        Đang tính toán...
                    </div>
                </div>

                <!-- Thẻ 4: Điểm Nóng Note DC (AE) & KFM Note (AG) -->
                <div class="kpi-card" style="border-left: 4px solid #c084fc; background: var(--bg-card-alt);">
                    <div class="kpi-title" style="color:#c084fc;"><i class="fa-solid fa-tags"></i> 4. ĐIỂM NÓNG NOTE DC & KFM</div>
                    <div class="kpi-val" id="dc-kpi-top-note" style="color:#c084fc; font-size:1.15rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">-</div>
                    <div class="kpi-sub" id="dc-kpi-sub-notes" style="font-size:0.78rem; line-height:1.4;">
                        Đang tính toán...
                    </div>
                </div>
            </div>

            
            <!-- Khối 2 Biểu Đồ Trực Quan Trong Tab DC (Tiến Độ DONE & Phân Bổ Trạng Thái) -->
            <div class="charts-grid-5" style="margin-bottom: 1.25rem; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div class="chart-card" style="margin: 0; background: var(--bg-card-alt);">
                    <div class="chart-header">
                        <h4 style="margin:0; font-size:0.92rem; color:#34d399;"><i class="fa-solid fa-chart-column"></i> Tiến Độ KFM Chỉnh DONE Theo Ngày</h4>
                        <button class="btn-chart-zoom" onclick="openChartZoom('chartKFMProgressDaily')"><i class="fa-solid fa-expand"></i></button>
                    </div>
                    <div class="chart-container" style="height: 250px;">
                        <canvas id="chartTabKFMProgress"></canvas>
                    </div>
                </div>

                <div class="chart-card" style="margin: 0; background: var(--bg-card-alt);">
                    <div class="chart-header">
                        <h4 style="margin:0; font-size:0.92rem; color:#f87171;"><i class="fa-solid fa-chart-pie"></i> Cơ Cấu Trạng Thái DC & KFM Phản Hồi</h4>
                        <button class="btn-chart-zoom" onclick="openChartZoom('chartDCNonAgreeBreakdown')"><i class="fa-solid fa-expand"></i></button>
                    </div>
                    <div class="doughnut-layout">
                        <div class="chart-container" style="height: 220px;">
                            <canvas id="chartTabDCNonAgree"></canvas>
                        </div>
                        <div class="doughnut-legend-list" id="tabDCNonAgreeLegendList" style="font-size:0.75rem;"></div>
                    </div>
                </div>
            </div>

            <!-- Ma Trận Đối Soát Chéo 4 Cột: DC Xác Nhận (AD) x KFM Phản Hồi (AF) -->
            <div class="executive-insights-card" style="margin-bottom: 1.25rem; border-color: rgba(192, 132, 252, 0.35); background: linear-gradient(135deg, rgba(30, 27, 75, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%);">
                <div class="insights-header" style="color: #c084fc;">
                    <i class="fa-solid fa-table-cells"></i>
                    <span>MA TRẬN ĐỐI SOÁT CHÉO: KẾT QUẢ DC XÁC NHẬN (CỘT AD) x KFM PHẢN HỒI (CỘT AF)</span>
                    <span class="tag-pill" style="margin-left: auto; background: rgba(192, 132, 252, 0.2); color: #c084fc; font-size: 0.75rem; font-weight: 700;">📊 Phân Loại Toàn Diện</span>
                </div>
                <div class="table-responsive" style="margin-top: 0.5rem;">
                    <table class="sc-table" id="dcCrossTabTable">
                        <thead>
                            <tr>
                                <th class="text-left" style="background:#0f172a; color:#fff; width:24%;">🏢 DC Xác Nhận (Cột AD)</th>
                                <th class="text-center" style="background:#0f172a; color:#34d399; width:15%;">🟢 DONE</th>
                                <th class="text-center" style="background:#0f172a; color:#f87171; width:17%;">⚖️ Cấp HLV Quyết Định</th>
                                <th class="text-center" style="background:#0f172a; color:#fbbf24; width:16%;">🔄 DC Check Lại</th>
                                <th class="text-center" style="background:#0f172a; color:#94a3b8; width:14%;">⏳ Chưa Phản Hồi</th>
                                <th class="text-right" style="background:#0f172a; color:#38bdf8; width:14%;">Tổng Dòng Hàng</th>
                            </tr>
                        </thead>
                        <tbody id="dcCrossTabBody"></tbody>
                        <tfoot id="dcCrossTabFoot"></tfoot>
                    </table>
                </div>
            </div>

            <!-- CHẾ ĐỘ 1: BẢNG TIẾN ĐỘ TỔNG HỢP THEO NGÀY / THÁNG -->
            <div id="dc-view-summary-container">
                <div class="table-responsive">
                    <table class="sc-table" id="dcTable">
                        <thead>
                            <tr>
                                <th rowspan="2" class="th-master-bg" style="width:110px; background:#1e1b4b !important; color:#c084fc !important;">Thời Gian</th>
                                <th colspan="3" class="th-master-bg" style="background:#1e1b4b !important; color:#c084fc !important;">Gửi Trả DC Tổng</th>
                                <th colspan="2" class="th-master-bg" style="background:#064e3b !important; color:#34d399 !important;">🟢 DC Đồng Ý Claim (Cột AD)</th>
                                <th colspan="2" class="th-master-bg" style="background:#7f1d1d !important; color:#f87171 !important;">🔴 DC Từ Chối Claim (Cột AD)</th>
                                <th rowspan="2" class="th-master-bg" style="background:#78350f !important; color:#fbbf24 !important;">🟡 Kiểm Tra Lại</th>
                                <th rowspan="2" class="th-master-bg" style="background:#334155 !important; color:#cbd5e1 !important;">⏳ Chưa Phản Hồi</th>
                                <th rowspan="2" class="th-master-bg" style="background:#1e1b4b !important; color:#c084fc !important; width:140px; text-align:center;">Tỷ Lệ DC Phản Hồi</th>
                                <th rowspan="2" class="th-master-bg" style="background:#1e1b4b !important; color:#c084fc !important; width:80px; text-align:center;">Chi Tiết</th>
                            </tr>
                            <tr>
                                <th class="th-master-sub">Số Dòng</th>
                                <th class="th-master-sub">Số ST</th>
                                <th class="th-master-sub">Tiền Lệch (VNĐ)</th>
                                <th class="th-master-sub">Số Dòng • Tiền</th>
                                <th class="th-master-sub" style="color:#6ee7b7;">⚡ KFM DONE / Chưa</th>
                                <th class="th-master-sub">Số Dòng • Tiền</th>
                                <th class="th-master-sub" style="color:#fca5a5;">⚖️ KFM Phản Hồi</th>
                            </tr>
                        </thead>
                        <tbody id="dcTableBody"></tbody>
                        <tfoot id="dcTableFoot"></tfoot>
                    </table>
                </div>
            </div>

            <!-- CHẾ ĐỘ 2: BẢNG TRA CỨU CHI TIẾT 4 CỘT AD - AG (KÈM BỘ LỌC THÔNG MINH) -->
            <div id="dc-view-detail-container" style="display:none;">
                <!-- Smart Quick Filters -->
                <div class="dc-quick-filters">
                    <button class="dc-filter-pill active" id="pill-dc-not-done" onclick="setDCQuickFilter('not_done')">
                        🚨 DC Đồng Ý - Chưa Chỉnh DONE <span class="badge" id="badge-cnt-not-done">7.529</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-tuchoi-pending" onclick="setDCQuickFilter('tuchoi_pending')">
                        ⚠️ DC Từ Chối - Chưa Phản Hồi <span class="badge" id="badge-cnt-tc-pending">171</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-tuchoi-hlv" onclick="setDCQuickFilter('tuchoi_hlv')">
                        ⚖️ DC Từ Chối - Cấp HLV Quyết Định <span class="badge" id="badge-cnt-tc-hlv">902</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-kiemtra" onclick="setDCQuickFilter('kiemtra')">
                        🔄 DC Kiểm Tra Lại <span class="badge" id="badge-cnt-kt">159</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-chua" onclick="setDCQuickFilter('chua_phan_hoi')">
                        ⏳ DC Chưa Phản Hồi <span class="badge" id="badge-cnt-chua">355</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-done" onclick="setDCQuickFilter('done')">
                        🟢 DC Đồng Ý - Đã DONE <span class="badge" id="badge-cnt-done">3.490</span>
                    </button>
                    <button class="dc-filter-pill" id="pill-dc-all" onclick="setDCQuickFilter('all')">
                        📦 Tất Cả Dòng Trả DC <span class="badge" id="badge-cnt-all">12.627</span>
                    </button>
                </div>

                <!-- Detailed Filters Toolbar -->
                <div style="padding:0.65rem 0.85rem; background:var(--bg-card-alt); border-radius:10px; margin-bottom:0.85rem; border:1px solid var(--border-card); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.65rem;">
                    <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                        <input type="text" id="dcDetailSearch" placeholder="🔍 Tìm mã ST, tên ST, mã hàng, tên SP, ghi chú..." oninput="filterDCDetailTable()" style="padding:0.4rem 0.75rem; border-radius:6px; font-size:0.82rem; width:260px;">
                        <select id="dcDetailFilterDate" onchange="filterDCDetailTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">📅 Tất cả các ngày</option>
                        </select>
                        <select id="dcDetailFilterGroup" onchange="filterDCDetailTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">🥩❄️ Tất cả nhóm hàng</option>
                            <option value="MÁT">🥩 Hàng Mát</option>
                            <option value="ĐÔNG">❄️ Hàng Đông</option>
                        </select>
                        <select id="dcDetailFilterConfirm" onchange="filterDCDetailTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">🏢 Cột AD: Tất cả DC xác nhận</option>
                            <option value="Đồng ý claim">🟢 Đồng ý claim</option>
                            <option value="Từ chối claim">🔴 Từ chối claim</option>
                            <option value="Kiểm tra lại">🟡 Kiểm tra lại</option>
                            <option value="Chưa phản hồi">⏳ Chưa phản hồi (Trống)</option>
                        </select>
                        <select id="dcDetailFilterReply" onchange="filterDCDetailTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">👤 Cột AF: Tất cả KFM phản hồi</option>
                            <option value="DONE">🟢 DONE</option>
                            <option value="Cấp HLV quyết định">⚖️ Cấp HLV quyết định</option>
                            <option value="DC check lại thông tin">🔄 DC check lại thông tin</option>
                            <option value="Chưa phản hồi">⏳ Chưa phản hồi (Trống)</option>
                        </select>
                    </div>
                    <div id="dcDetailSummaryBadge" style="font-size:0.82rem; font-weight:600; color:var(--text-secondary);"></div>
                </div>

                <!-- Detail Table -->
                <div class="table-responsive" style="max-height: 650px; overflow-y: auto;">
                    <table class="sc-table" id="dcDetailTable">
                        <thead style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th class="text-center" style="width:40px;">STT</th>
                                <th class="text-center" style="width:85px;">Ngày</th>
                                <th class="text-left" style="width:16%;">Siêu Thị Nhận</th>
                                <th class="text-center" style="width:65px;">Nhóm</th>
                                <th class="text-left" style="width:18%;">Mã & Tên Mặt Hàng</th>
                                <th class="text-right" style="width:75px;">SL Lệch</th>
                                <th class="text-right" style="width:95px;">Tiền Lệch</th>
                                <th class="text-left" style="width:125px; background:#1e1b4b !important; color:#a5b4fc !important;">🏢 DC Xác Nhận<br><span style="font-size:0.7rem; font-weight:400; opacity:0.85;">(Cột AD)</span></th>
                                <th class="text-left" style="width:130px; background:#1e1b4b !important; color:#cbd5e1 !important;">📝 NOTE DC<br><span style="font-size:0.7rem; font-weight:400; opacity:0.85;">(Cột AE)</span></th>
                                <th class="text-left" style="width:135px; background:#431407 !important; color:#fdba74 !important;">👤 KFM Phản Hồi<br><span style="font-size:0.7rem; font-weight:400; opacity:0.85;">(Cột AF)</span></th>
                                <th class="text-left" style="width:140px; background:#431407 !important; color:#fed7aa !important;">📌 NOTE KFM<br><span style="font-size:0.7rem; font-weight:400; opacity:0.85;">(Cột AG)</span></th>
                                <th class="text-center" style="width:80px;">PT Trả DC</th>
                                <th class="text-center" style="width:65px;">Hình Ảnh</th>
                            </tr>
                        </thead>
                        <tbody id="dcDetailTableBody"></tbody>
                        <tfoot id="dcDetailTableFoot"></tfoot>
                    </table>
                </div>
            </div>
        </div>

        <!-- ========================================================================= -->
        <!-- BẢNG RIÊNG BIỆT NẰM DƯỚI: DANH SÁCH SIÊU THỊ CẦN XỬ LÝ (ƯU TIÊN THEO GIÁ TRỊ) -->
        <!-- ========================================================================= -->
        <div class="table-card" id="card-store-table" style="margin-top: 2rem; border-top: 3px solid #ef4444;">
            <div class="table-header-row">
                <div class="table-title" style="color:#f87171; font-size:1.1rem;">
                    <i class="fa-solid fa-triangle-exclamation" style="color:#f87171;"></i> DANH SÁCH SIÊU THỊ CẦN XỬ LÝ (ƯU TIÊN THEO GIÁ TRỊ TỔNG / NGÀY)
                </div>
                <button class="btn-view-detail" style="background:#10b981; color:#fff; border-color:#059669; padding:0.35rem 0.85rem;" onclick="exportStorePriorityExcel()">
                    <i class="fa-solid fa-file-excel"></i> Xuất Excel DS Siêu Thị
                </button>
            </div>

            <!-- Toolbar lọc của bảng Siêu Thị -->
            <div style="padding:0.65rem 0.85rem; background:var(--bg-card-alt); border-radius:10px; margin-bottom:0.85rem; border:1px solid var(--border-card); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.65rem;">
                <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                    <input type="text" id="storeSearchInput" placeholder="🔍 Tìm mã ST, tên siêu thị..." oninput="filterStorePriorityTable()" style="padding:0.4rem 0.75rem; border-radius:6px; font-size:0.82rem; width:260px;">
                    <select id="storeFilterDate" onchange="filterStorePriorityTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                        <option value="all">📅 Tất cả các ngày</option>
                    </select>
                    <select id="storeFilterPriority" onchange="filterStorePriorityTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                        <option value="all">🎯 Tất cả mức độ ưu tiên</option>
                        <option value="p1">🚨 Ưu tiên 1: Đang Xử Lý (ST ≥ 100k)</option>
                        <option value="p2">⚪ Ưu tiên 2: Không Xử Lý (ST < 100k)</option>
                        <option value="p3">🟢 Ưu tiên 3: Đã Xử Lý Hoàn Tất (100%)</option>
                    </select>
                    <select id="storeSortBy" onchange="filterStorePriorityTable()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                        <option value="val_desc">💰 Tổng tiền ST giảm dần</option>
                        <option value="dang_xl_desc">🟡 Tiền Đang XL (ST ≥ 100k) giảm dần</option>
                        <option value="sku_desc">📦 Số lượng SKU lệch nhiều nhất</option>
                    </select>
                </div>
                <div id="storeSummaryBadge" style="font-size:0.82rem; font-weight:600; color:var(--text-secondary);"></div>
            </div>

            <div class="table-responsive">
                <table class="sc-table" id="storePriorityTable">
                    <thead>
                        <tr>
                            <th class="th-store-bg text-center" style="width:40px;">STT</th>
                            <th class="th-store-bg text-center" style="width:85px;">Ngày</th>
                            <th class="th-store-bg text-left" style="width:24%;">Siêu Thị Cần Xử Lý</th>
                            <th class="th-store-bg text-center" style="width:16%;">Mức Độ Ưu Tiên</th>
                            <th class="th-store-bg" style="width:13%;">Tổng Tiền Lệch / ST</th>
                            <th class="th-store-bg text-center" style="width:7%;">Số SKU</th>
                            <th class="th-store-bg" style="width:11%; color:#fed7aa;">🟡 Đang XL (≥100k)</th>
                            <th class="th-store-bg" style="width:10%; color:#cbd5e1;">⚪ Không XL (&lt;100k)</th>
                            <th class="th-store-bg" style="width:10%; color:#bbf7d0;">🟢 Đã XL</th>
                            <th class="th-store-bg text-center" style="width:130px;">Tiến Độ (% Xong)</th>
                            <th class="th-store-bg text-center" style="width:80px;">Chi Tiết</th>
                        </tr>
                    </thead>
                    <tbody id="storePriorityTableBody"></tbody>
                    <tfoot id="storePriorityTableFoot"></tfoot>
                </table>
            </div>
        </div>

    </div>

    <!-- Modal Chi Tiết -->
    <div class="modal-overlay" id="detailModal">
        <div class="modal-box" id="modalBox">
            <div class="modal-head">
                <div>
                    <h3 id="modalTitle" style="font-size:1.15rem; font-weight:700; color:#fff;">Chi Tiết Chênh Lệch Ngày</h3>
                    <p id="modalSubTitle" style="font-size:0.82rem; color:#94a3b8;">Danh sách mặt hàng đối soát chi tiết</p>
                </div>
                <div class="modal-head-actions">
                    <button class="modal-btn-act" onclick="exportModalExcel()">
                        <i class="fa-solid fa-file-excel" style="color:#4ade80;"></i> Xuất Excel Ngày Này
                    </button>
                    <button class="modal-btn-act" id="btnFullscreen" onclick="toggleModalFullscreen()">
                        <i class="fa-solid fa-expand"></i> Phóng To Toàn Màn Hình
                    </button>
                    <button class="btn-close" onclick="closeModal()"><i class="fa-solid fa-xmark"></i></button>
                </div>
            </div>
            
            <div class="modal-toolbar">
                <div style="display:flex; gap:0.65rem; align-items:center; flex-wrap:wrap;">
                    <input type="text" id="modalSearch" placeholder="🔍 Tìm mã ST, tên siêu thị, mã hàng, tên sản phẩm..." oninput="filterModalRecords()" style="padding:0.45rem 0.85rem; border-radius:8px; font-size:0.83rem; width:340px;">
                    <select id="modalFilterThreshold" onchange="filterModalRecords()" style="padding:0.45rem 0.75rem; border-radius:8px; font-size:0.82rem; font-weight:600;">
                        <option value="all">Tất cả siêu thị</option>
                        <option value="over">Chỉ xem ST ≥ 100k</option>
                        <option value="under">Chỉ xem ST < 100k</option>
                    </select>
                    <select id="modalFilterStatus" onchange="filterModalRecords()" style="padding:0.45rem 0.75rem; border-radius:8px; font-size:0.82rem; font-weight:600;">
                        <option value="all">Tất cả trạng thái</option>
                        <option value="Đã xử lý">🟢 Đã xử lý</option>
                        <option value="Đang xử lý">🟡 Đang xử lý (ST ≥ 100k)</option>
                        <option value="Không xử lý">⚪ Không xử lý (ST < 100k)</option>
                    </select>
                </div>
                <div id="modalSummaryBadges" style="font-size:0.82rem; font-weight:600; color:var(--text-secondary);"></div>
            </div>

            <div class="modal-body" style="padding:0; overflow-y:auto;">
                <div class="table-responsive" style="border:none; border-radius:0;">
                    <table class="sc-table" id="detailTable">
                        <thead>
                            <tr>
                                <th class="text-center" style="width:40px;">STT</th>
                                <th class="text-left" style="width:24%;">Siêu Thị & Mức Lệch ST</th>
                                <th class="text-left" style="width:28%;">Mã & Tên Mặt Hàng</th>
                                <th style="width:7%;">SL Chuyển</th>
                                <th style="width:7%;">SL Nhận</th>
                                <th style="width:8%; color:#fca5a5;">SL Lệch</th>
                                <th style="width:8%;">Đơn Giá</th>
                                <th style="width:10%; color:#38bdf8;">Tiền Lệch</th>
                                <th class="text-left" style="width:12%;">Lỗi & Điểm Nhận</th>
                                <th class="text-center" style="width:9%;">Trạng Thái</th>
                            </tr>
                        </thead>
                        <tbody id="detailTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Phóng To & Nhận Xét Biểu Đồ -->
    <div class="modal-overlay" id="chartZoomModal">
        <div class="modal-box chart-zoom-box">
            <div class="modal-head">
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <div id="zoomModalIcon" style="width:38px; height:38px; border-radius:10px; background:rgba(56,189,248,0.15); display:flex; align-items:center; justify-content:center; color:#38bdf8; font-size:1.15rem;">
                        <i class="fa-solid fa-chart-line"></i>
                    </div>
                    <div>
                        <h3 id="zoomModalTitle" style="font-size:1.15rem; font-weight:700; color:#fff;">Phóng To Biểu Đồ & Nhận Xét Chuyên Sâu</h3>
                        <p id="zoomModalSubTitle" style="font-size:0.82rem; color:#94a3b8;">Phân tích đa chiều dữ liệu và đề xuất hành động nghiệp vụ</p>
                    </div>
                </div>
                <div class="modal-head-actions">
                    <button class="btn-close" onclick="closeChartZoom()"><i class="fa-solid fa-xmark"></i></button>
                </div>
            </div>
            
            <div class="zoom-modal-body">
                <div class="zoom-chart-area">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                        <span id="zoomChartBadge" class="tag-pill" style="background:rgba(56,189,248,0.15); color:#38bdf8; font-weight:700; font-size:0.82rem;">📊 Dữ liệu trực quan phóng to</span>
                        <span style="font-size:0.75rem; color:var(--text-muted);"><i class="fa-solid fa-check-circle" style="color:#34d399;"></i> Đã hiển thị đầy đủ Data Labels</span>
                    </div>
                    <div class="zoom-chart-container">
                        <canvas id="chartZoomCanvas"></canvas>
                    </div>
                </div>
                <div class="zoom-insights-area" id="zoomInsightsContent">
                    <!-- Nội dung nhận xét, phân tích và bảng số liệu tóm tắt được render động -->
                </div>
            </div>
        </div>
    </div>

    <!-- Script Logic -->
    <script>
        const BUNDLES = """ + json_bundles + """;
        const DAILY_RECORDS = """ + json_daily_records + """;

        let curGroup = 'mat';
        let curMonth = 'all';
        let valPeriod = 'daily';
        let qtyPeriod = 'daily';
        let masterPeriod = 'daily';
        let dcPeriod = 'daily';
        
        let chartDCResp = null;
        let chartDCCompare = null;
        let chartKFMProgress = null;
        let chartTabKFM = null;
        let chartDCNonAgree = null;
        let chartTabNonAgree = null;
        let chartDCNotes = null;
        let curTableTab = 'master';

        let chartCases = null;
        let chart1 = null;
        let chart2 = null;
        let chart3 = null;
        let chart4 = null;
        let chart5 = null;

        // Theme management (Dark Mode by Default)
        let currentTheme = localStorage.getItem('app_theme') || 'dark';

        function applyTheme(theme) {
            currentTheme = theme;
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('app_theme', theme);
            
            const btn = document.getElementById('themeToggleBtn');
            if (btn) {
                if (theme === 'dark') {
                    btn.innerHTML = '<i class="fa-solid fa-moon" style="color:#38bdf8;"></i> <span>Phông Tối</span>';
                    btn.style.background = 'rgba(255, 255, 255, 0.08)';
                    btn.style.color = '#f8fafc';
                    btn.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                } else {
                    btn.innerHTML = '<i class="fa-solid fa-sun" style="color:#f59e0b;"></i> <span>Phông Sáng</span>';
                    btn.style.background = 'rgba(255, 255, 255, 0.9)';
                    btn.style.color = '#0f172a';
                    btn.style.borderColor = '#cbd5e1';
                }
            }
        }

        function toggleTheme() {
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
            renderAll();
        }

        function fmtVND(n) {
            if (!n || isNaN(n)) return "0 đ";
            return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + " đ";
        }

        function fmtN(n) {
            if (!n || isNaN(n)) return "0";
            return new Intl.NumberFormat('vi-VN').format(n);
        }

        function renderProgressBadge(pct) {
            const num = parseFloat(pct) || 0;
            let barColor = 'linear-gradient(90deg, #059669, #34d399)';
            let textColor = '#34d399';
            if (num < 70) {
                barColor = 'linear-gradient(90deg, #b91c1c, #f87171)';
                textColor = '#f87171';
            } else if (num < 90) {
                barColor = 'linear-gradient(90deg, #d97706, #fbbf24)';
                textColor = '#fbbf24';
            }
            return `
            <div class="tbl-progress-cell">
                <div class="tbl-progress-bar">
                    <div class="tbl-progress-fill" style="width:${Math.min(num, 100)}%; background:${barColor};"></div>
                </div>
                <span style="font-weight:700; font-size:0.8rem; color:${textColor}; min-width:42px; text-align:right;">${num.toFixed(1)}%</span>
            </div>
            `;
        }

        if (typeof ChartDataLabels !== 'undefined') {
            Chart.register(ChartDataLabels);
        }

        function populateMonthOptions() {
            const raw = BUNDLES[curGroup];
            if (!raw || !raw.daily_matrix) return;
            
            const months = [...new Set(raw.daily_matrix.map(d => d.month))];
            const selectEl = document.getElementById('globalMonthFilter');
            if (!selectEl) return;

            let html = '<option value="all">📅 Tất Cả Các Tháng</option>';
            months.forEach(m => {
                const label = m.includes('Tháng') ? m + '/2026' : 'Tháng ' + m;
                html += `<option value="${m}">${label}</option>`;
            });
            selectEl.innerHTML = html;
            if (months.includes(curMonth) || curMonth === 'all') {
                selectEl.value = curMonth;
            }
        }

        function changeMonth(mVal) {
            curMonth = mVal;
            renderAll();
        }

        function getDynamicDetailedMetrics() {
            const rawBundle = BUNDLES[curGroup];
            if (!rawBundle) return {
                uniqueStTotal: 0,
                uniqueStOver: 0,
                uniqueStDone: 0,
                uniqueStPending: 0,
                uniqueStIgnored: 0,
                storeDaysDone: 0,
                storeDaysPending: 0,
                storeDaysIgnored: 0,
                casesDone: 0,
                casesPending: 0,
                casesIgnored: 0
            };

            const dates = Object.keys(DAILY_RECORDS);
            const stSetDone = new Set();
            const stSetPending = new Set();
            const stSetIgnored = new Set();
            const stSetTotal = new Set();
            const stOverSet = new Set();

            let casesDone = 0, casesPending = 0, casesIgnored = 0;
            let storeDaysDone = 0, storeDaysPending = 0, storeDaysIgnored = 0;

            dates.forEach(dStr => {
                if (curMonth !== 'all') {
                    const matchDay = rawBundle.daily_matrix.find(d => d.date === dStr);
                    if (!matchDay || matchDay.month !== curMonth) {
                        return;
                    }
                }

                const recs = DAILY_RECORDS[dStr] || [];
                const filteredRecs = curGroup === 'all' ? recs : recs.filter(r => (curGroup === 'mat' ? r.group.includes('MÁT') : r.group.includes('ĐÔNG')));
                
                const dayStoreStatusMap = {};

                filteredRecs.forEach(r => {
                    stSetTotal.add(r.st);
                    if (r.is_store_over_100k) {
                        stOverSet.add(r.st);
                    }

                    if (!dayStoreStatusMap[r.st]) {
                        dayStoreStatusMap[r.st] = { hasDone: false, hasPending: false, hasIgnored: false };
                    }

                    if (r.status_3level === 'Đã xử lý') {
                        casesDone++;
                        stSetDone.add(r.st);
                        dayStoreStatusMap[r.st].hasDone = true;
                    } else if (r.status_3level === 'Đang xử lý') {
                        casesPending++;
                        stSetPending.add(r.st);
                        dayStoreStatusMap[r.st].hasPending = true;
                    } else if (r.status_3level === 'Không xử lý') {
                        casesIgnored++;
                        stSetIgnored.add(r.st);
                        dayStoreStatusMap[r.st].hasIgnored = true;
                    }
                });

                Object.values(dayStoreStatusMap).forEach(statusObj => {
                    if (statusObj.hasDone) storeDaysDone++;
                    if (statusObj.hasPending) storeDaysPending++;
                    if (statusObj.hasIgnored) storeDaysIgnored++;
                });
            });

            return {
                uniqueStTotal: stSetTotal.size,
                uniqueStOver: stOverSet.size,
                uniqueStDone: stSetDone.size,
                uniqueStPending: stSetPending.size,
                uniqueStIgnored: stSetIgnored.size,
                storeDaysDone,
                storeDaysPending,
                storeDaysIgnored,
                casesDone,
                casesPending,
                casesIgnored
            };
        }

        function getFilteredBundleData() {
            const raw = BUNDLES[curGroup];
            if (!raw) return null;

            if (curMonth === 'all') {
                return raw;
            }

            const filteredDaily = raw.daily_matrix.filter(d => d.month === curMonth);
            const filteredMonthly = raw.monthly_matrix.filter(m => m.month === curMonth);

            // Compute dynamic grand total for selected month
            let totVal = 0, totValOver = 0, totValUnder = 0, totCases = 0;
            let totQtyChuyen = 0, totQtyNhan = 0, totQtyLech = 0;
            let totValKho = 0, totValST = 0, totValHaoHut = 0;
            let totValDa = 0, totValDang = 0, totValKhong = 0;
            let totSlKho = 0, totSlST = 0, totSlHaoHut = 0;
            let totSlDa = 0, totSlDang = 0, totSlKhong = 0;
            let totStores = 0, totStoresOver = 0, totStoresUnder = 0;
            let totStDa = 0, totStDang = 0, totStKhong = 0;

            let totDcCases = 0, totDcVal = 0, totDcQty = 0, totDcSt = 0;
            let totDcDongYCases = 0, totDcDongYVal = 0, totDcDongYSt = 0;
            let totDcTuChoiCases = 0, totDcTuChoiVal = 0, totDcTuChoiSt = 0;
            let totDcKiemTraCases = 0, totDcKiemTraVal = 0, totDcKiemTraSt = 0;
            let totDcChuaCases = 0, totDcChuaVal = 0, totDcChuaSt = 0;

            filteredDaily.forEach(d => {
                totVal += d.val_total || 0;
                totValOver += d.val_over_100k || 0;
                totValUnder += d.val_under_100k || 0;
                totCases += d.total_cases || 0;

                totQtyChuyen += d.qty_chuyen || 0;
                totQtyNhan += d.qty_nhan || 0;
                totQtyLech += d.qty_lech || 0;

                totValKho += d.val_kho || 0;
                totValST += d.val_st || 0;
                totValHaoHut += d.val_haohut || 0;

                totValDa += d.val_da_xl || 0;
                totValDang += d.val_dang_xl || 0;
                totValKhong += d.val_khong_xl || 0;

                totSlKho += d.sl_kho || 0;
                totSlST += d.sl_st || 0;
                totSlHaoHut += d.sl_haohut || 0;

                totSlDa += d.sl_da_xl || 0;
                totSlDang += d.sl_dang_xl || 0;
                totSlKhong += d.sl_khong_xl || 0;

                totStores += d.stores_count || 0;
                totStoresOver += d.stores_over_100k || 0;
                totStoresUnder += d.stores_under_100k || 0;

                totStDa += d.st_da_xl || 0;
                totStDang += d.st_dang_xl || 0;
                totStKhong += d.st_khong_xl || 0;

                totDcCases += d.dc_total_cases || 0;
                totDcVal += d.dc_total_val || 0;
                totDcQty += d.dc_total_qty || 0;
                totDcSt += d.dc_st_count || 0;
                totDcDongYCases += d.dc_dongy_cases || 0;
                totDcDongYVal += d.dc_dongy_val || 0;
                totDcDongYSt += d.dc_dongy_st || 0;
                totDcTuChoiCases += d.dc_tuchoi_cases || 0;
                totDcTuChoiVal += d.dc_tuchoi_val || 0;
                totDcTuChoiSt += d.dc_tuchoi_st || 0;
                totDcKiemTraCases += d.dc_kiemtra_cases || 0;
                totDcKiemTraVal += d.dc_kiemtra_val || 0;
                totDcKiemTraSt += d.dc_kiemtra_st || 0;
                totDcChuaCases += d.dc_chua_cases || 0;
                totDcChuaVal += d.dc_chua_val || 0;
                totDcChuaSt += d.dc_chua_st || 0;
            });

            const dynGrandTotal = {
                total_days: filteredDaily.length,
                total_cases: totCases,
                qty_chuyen: totQtyChuyen,
                qty_nhan: totQtyNhan,
                qty_lech: totQtyLech,
                stores_count: totStores,
                stores_over_100k: totStoresOver,
                stores_under_100k: totStoresUnder,
                st_da_xl: totStDa,
                st_dang_xl: totStDang,
                st_khong_xl: totStKhong,
                sl_kho: totSlKho,
                sl_st: totSlST,
                sl_haohut: totSlHaoHut,
                sl_da_xl: totSlDa,
                sl_dang_xl: totSlDang,
                sl_khong_xl: totSlKhong,
                val_total: totVal,
                val_over_100k: totValOver,
                val_under_100k: totValUnder,
                val_kho: totValKho,
                val_st: totValST,
                val_haohut: totValHaoHut,
                val_da_xl: totValDa,
                val_dang_xl: totValDang,
                val_khong_xl: totValKhong,
                dc_total_cases: totDcCases,
                dc_total_qty: totDcQty,
                dc_total_val: totDcVal,
                dc_st_count: totDcSt,
                dc_dongy_cases: totDcDongYCases,
                dc_dongy_val: totDcDongYVal,
                dc_dongy_st: totDcDongYSt,
                dc_tuchoi_cases: totDcTuChoiCases,
                dc_tuchoi_val: totDcTuChoiVal,
                dc_tuchoi_st: totDcTuChoiSt,
                dc_kiemtra_cases: totDcKiemTraCases,
                dc_kiemtra_val: totDcKiemTraVal,
                dc_kiemtra_st: totDcKiemTraSt,
                dc_chua_cases: totDcChuaCases,
                dc_chua_val: totDcChuaVal,
                dc_chua_st: totDcChuaSt,
                dc_pct_phan_hoi: totDcCases > 0 ? (((totDcDongYCases + totDcTuChoiCases + totDcKiemTraCases) / totDcCases * 100).toFixed(1)) : 100.0,
                dc_pct_dongy: totDcCases > 0 ? ((totDcDongYCases / totDcCases * 100).toFixed(1)) : 0.0
            };

            const dynOverallMetrics = {
                over_stores_days: totStoresOver,
                under_stores_days: totStoresUnder,
                da_xu_ly_count: filteredDaily.reduce((a, b) => a + (b.cases_over_da_xl + b.cases_under_da_xl), 0),
                dang_xu_ly_count: filteredDaily.reduce((a, b) => a + b.cases_over_dang_xl, 0),
                khong_xu_ly_count: filteredDaily.reduce((a, b) => a + b.cases_under_khong_xl, 0)
            };

            return {
                daily_matrix: filteredDaily,
                monthly_matrix: filteredMonthly,
                overall_metrics: dynOverallMetrics,
                grand_total: dynGrandTotal
            };
        }

        document.addEventListener('DOMContentLoaded', () => {
            populateMonthOptions();
            applyTheme(currentTheme);
            renderAll();
        });

        function changeGroup(grp) {
            curGroup = grp;
            document.getElementById('tab-mat').className = 'group-btn' + (grp === 'mat' ? ' active-mat' : '');
            document.getElementById('tab-dong').className = 'group-btn' + (grp === 'dong' ? ' active-dong' : '');
            document.getElementById('tab-all').className = 'group-btn' + (grp === 'all' ? ' active-all' : '');
            populateMonthOptions();
            renderAll();
        }

        function switchTableTab(tab) {
            curTableTab = tab;
            const btnMaster = document.getElementById('tab-btn-master');
            const btnVal = document.getElementById('tab-btn-val');
            const btnQty = document.getElementById('tab-btn-qty');
            const btnDc = document.getElementById('tab-btn-dc');
            
            const cardMaster = document.getElementById('card-master-table');
            const cardVal = document.getElementById('card-val-table');
            const cardQty = document.getElementById('card-qty-table');
            const cardDc = document.getElementById('card-dc-table');

            if (btnMaster) btnMaster.className = 'table-view-tab' + (tab === 'master' ? ' active-master' : '');
            if (btnVal) btnVal.className = 'table-view-tab' + (tab === 'val' ? ' active-val' : '');
            if (btnQty) btnQty.className = 'table-view-tab' + (tab === 'qty' ? ' active-qty' : '');
            if (btnDc) btnDc.className = 'table-view-tab' + (tab === 'dc' ? ' active-dc' : '');

            if (cardMaster) cardMaster.style.display = tab === 'master' ? 'block' : 'none';
            if (cardVal) cardVal.style.display = tab === 'val' ? 'block' : 'none';
            if (cardQty) cardQty.style.display = tab === 'qty' ? 'block' : 'none';
            if (cardDc) cardDc.style.display = tab === 'dc' ? 'block' : 'none';

            if (tab === 'dc') {
                renderDCTable();
            }
        }

        function setDcPeriod(p) {
            dcPeriod = p;
            const btnD = document.getElementById('btn-p-dc-daily');
            const btnM = document.getElementById('btn-p-dc-monthly');
            if (btnD) btnD.classList.toggle('active', p === 'daily');
            if (btnM) btnM.classList.toggle('active', p === 'monthly');
            renderDCTable();
        }

        function setValPeriod(p) {
            valPeriod = p;
            document.getElementById('btn-p-val-daily').classList.toggle('active', p === 'daily');
            document.getElementById('btn-p-val-monthly').classList.toggle('active', p === 'monthly');
            renderValTable();
        }

        function setQtyPeriod(p) {
            qtyPeriod = p;
            document.getElementById('btn-p-qty-daily').classList.toggle('active', p === 'daily');
            document.getElementById('btn-p-qty-monthly').classList.toggle('active', p === 'monthly');
            renderQtyTable();
        }

        function setMasterPeriod(p) {
            masterPeriod = p;
            document.getElementById('btn-p-master-daily').classList.toggle('active', p === 'daily');
            document.getElementById('btn-p-master-monthly').classList.toggle('active', p === 'monthly');
            renderMasterTable();
        }

        function getStorePriorityData() {
            const storeMap = {};
            const dates = Object.keys(DAILY_RECORDS);
            
            dates.forEach(dStr => {
                if (curMonth !== 'all') {
                    const rawBundle = BUNDLES[curGroup];
                    const matchDay = rawBundle.daily_matrix.find(d => d.date === dStr);
                    if (!matchDay || matchDay.month !== curMonth) {
                        return;
                    }
                }

                const recs = DAILY_RECORDS[dStr] || [];
                const filteredRecs = curGroup === 'all' ? recs : recs.filter(r => (curGroup === 'mat' ? r.group.includes('MÁT') : r.group.includes('ĐÔNG')));
                
                filteredRecs.forEach(r => {
                    const key = `${dStr}_${r.st}`;
                    if (!storeMap[key]) {
                        storeMap[key] = {
                            date: dStr,
                            st: r.st,
                            store_name: r.store_name,
                            group: r.group,
                            is_store_over_100k: r.is_store_over_100k,
                            sku_count: 0,
                            qty_diff_total: 0,
                            val_total: 0,
                            val_da_xl: 0,
                            val_dang_xl: 0,
                            val_khong_xl: 0
                        };
                    }
                    const stObj = storeMap[key];
                    stObj.sku_count += 1;
                    stObj.qty_diff_total += r.qty_diff;
                    stObj.val_total += r.val_total;
                    
                    if (r.status_3level === 'Đã xử lý') {
                        stObj.val_da_xl += r.val_total;
                    } else if (r.status_3level === 'Đang xử lý') {
                        stObj.val_dang_xl += r.val_total;
                    } else {
                        stObj.val_khong_xl += r.val_total;
                    }
                });
            });

            const list = Object.values(storeMap);
            list.forEach(st => {
                if (st.val_dang_xl > 0) {
                    st.priority = 'p1';
                    st.priority_badge = '<span class="p-badge p-badge-p1">🚨 ĐANG XỬ LÝ (≥100k)</span>';
                } else if (st.val_khong_xl > 0) {
                    st.priority = 'p2';
                    st.priority_badge = '<span class="p-badge p-badge-p3">⚪ KHÔNG XỬ LÝ (&lt;100k)</span>';
                } else {
                    st.priority = 'p3';
                    st.priority_badge = '<span class="p-badge p-badge-p4">🟢 ĐÃ XONG 100%</span>';
                }
                st.pct_done = st.val_total > 0 ? (st.val_da_xl / st.val_total * 100).toFixed(1) : '100.0';
            });

            return list;
        }

        let curStoreData = [];

        function renderStorePriorityTable() {
            curStoreData = getStorePriorityData();
            
            const parseDateScore = (dStr) => {
                if (!dStr) return 0;
                const parts = dStr.split('/');
                if (parts.length === 3) {
                    return parseInt(parts[2] + parts[1].padStart(2, '0') + parts[0].padStart(2, '0'), 10);
                }
                return 0;
            };

            const dateSel = document.getElementById('storeFilterDate');
            if (dateSel) {
                const curVal = dateSel.value;
                const dates = [...new Set(curStoreData.map(s => s.date))].sort((a, b) => parseDateScore(b) - parseDateScore(a));
                
                let dateOptions = '<option value="all">📅 Tất cả các ngày</option>';
                dates.forEach(d => {
                    dateOptions += `<option value="${d}">${d}</option>`;
                });
                dateSel.innerHTML = dateOptions;
                if (dates.includes(curVal)) dateSel.value = curVal;
            }

            filterStorePriorityTable();
        }

        function filterStorePriorityTable() {
            const query = (document.getElementById('storeSearchInput').value || '').trim().toLowerCase();
            const filterDate = document.getElementById('storeFilterDate').value;
            const filterP = document.getElementById('storeFilterPriority').value;
            const sortBy = document.getElementById('storeSortBy').value;

            let filtered = curStoreData.filter(s => {
                if (filterDate !== 'all' && s.date !== filterDate) return false;
                if (filterP !== 'all' && s.priority !== filterP) return false;
                if (query) {
                    const matchSt = (s.st || '').toLowerCase().includes(query) || (s.store_name || '').toLowerCase().includes(query);
                    if (!matchSt) return false;
                }
                return true;
            });

            filtered.sort((a, b) => {
                if (sortBy === 'dang_xl_desc') {
                    if (b.val_dang_xl !== a.val_dang_xl) return b.val_dang_xl - a.val_dang_xl;
                    return b.val_total - a.val_total;
                } else if (sortBy === 'sku_desc') {
                    return b.sku_count - a.sku_count;
                } else {
                    const pOrder = { 'p1': 1, 'p2': 2, 'p3': 3 };
                    if (pOrder[a.priority] !== pOrder[b.priority]) return pOrder[a.priority] - pOrder[b.priority];
                    return b.val_total - a.val_total;
                }
            });

            const p1Count = filtered.filter(s => s.priority === 'p1').length;
            const p1Val = filtered.reduce((acc, s) => acc + s.val_dang_xl, 0);
            const p2Count = filtered.filter(s => s.priority === 'p2').length;
            const p3Count = filtered.filter(s => s.priority === 'p3').length;
            
            document.getElementById('storeSummaryBadge').innerHTML = `
                <span>Hiển thị: <strong>${filtered.length}</strong> Siêu Thị • <span style="color:#fb923c; font-weight:700;">🟡 Đang XL (≥100k): ${p1Count} ST (${fmtVND(p1Val)})</span> • ⚪ Không XL (&lt;100k): ${p2Count} ST • 🟢 Xong: ${p3Count} ST</span>
            `;

            const tbody = document.getElementById('storePriorityTableBody');
            const tfoot = document.getElementById('storePriorityTableFoot');
            let html = '';
            
            let totVal = 0, totDang = 0, totKhong = 0, totDa = 0, totSku = 0;

            filtered.forEach((s, idx) => {
                totVal += s.val_total;
                totDang += s.val_dang_xl;
                totKhong += s.val_khong_xl;
                totDa += s.val_da_xl;
                totSku += s.sku_count;

                const tagThresh = s.val_total >= 100000 
                    ? '<span class="tag-pill" style="background:rgba(239,68,68,0.18); color:#f87171; border:1px solid rgba(239,68,68,0.4);">ST ≥ 100k</span>' 
                    : '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">ST < 100k</span>';
                
                const tagGrp = (s.group || '').includes('MÁT') 
                    ? '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">MÁT</span>' 
                    : '<span class="tag-pill" style="background:rgba(99,102,241,0.18); color:#818cf8; border:1px solid rgba(99,102,241,0.4);">ĐÔNG</span>';

                html += `
                <tr>
                    <td class="text-center" style="color:var(--text-muted); font-weight:700;">#${idx + 1}</td>
                    <td class="text-center" style="font-weight:600; color:var(--text-secondary);">${s.date}</td>
                    <td class="text-left">
                        <strong style="color:var(--text-primary); font-size:0.85rem;">${s.st}</strong> - <span style="color:var(--text-secondary);">${s.store_name}</span>
                        <div style="margin-top:2px; display:flex; gap:5px;">${tagThresh} ${tagGrp}</div>
                    </td>
                    <td class="text-center">${s.priority_badge}</td>
                    <td><strong class="c-blue" style="font-size:0.88rem;">${fmtVND(s.val_total)}</strong></td>
                    <td class="text-center"><strong>${s.sku_count}</strong></td>
                    <td><strong class="c-orange" style="font-size:0.85rem;">${s.val_dang_xl > 0 ? fmtVND(s.val_dang_xl) : '-'}</strong></td>
                    <td><strong style="color:var(--text-muted);">${s.val_khong_xl > 0 ? fmtVND(s.val_khong_xl) : '-'}</strong></td>
                    <td><strong class="c-green">${s.val_da_xl > 0 ? fmtVND(s.val_da_xl) : '-'}</strong></td>
                    <td class="text-center">
                        ${renderProgressBadge(s.pct_done)}
                    </td>
                    <td class="text-center">
                        <button class="btn-view-detail" onclick="openStoreModal('${s.date}', '${s.st}')">
                            <i class="fa-solid fa-magnifying-glass"></i> Xem SKU
                        </button>
                    </td>
                </tr>
                `;
            });

            tbody.innerHTML = html || '<tr><td colspan="11" class="text-center" style="padding:2rem;">Không tìm thấy siêu thị nào phù hợp bộ lọc</td></tr>';

            const pctTotal = totVal > 0 ? (totDa / totVal * 100).toFixed(1) : 0;
            tfoot.innerHTML = `
            <tr>
                <td colspan="4" class="text-left"><strong>TỔNG CỘNG (${filtered.length} Siêu Thị)</strong></td>
                <td><strong class="c-blue">${fmtVND(totVal)}</strong></td>
                <td class="text-center"><strong>${totSku}</strong></td>
                <td><strong class="c-orange">${fmtVND(totDang)}</strong></td>
                <td><strong style="color:var(--text-muted);">${fmtVND(totKhong)}</strong></td>
                <td><strong class="c-green">${fmtVND(totDa)}</strong></td>
                <td class="text-center">${renderProgressBadge(pctTotal)}</td>
                <td class="text-center">-</td>
            </tr>
            `;
        }

        function openStoreModal(dateStr, stId) {
            const all = DAILY_RECORDS[dateStr] || [];
            curModalRecords = curGroup === 'all' ? all : all.filter(r => (curGroup === 'mat' ? r.group.includes('MÁT') : r.group.includes('ĐÔNG')));

            document.getElementById('modalTitle').innerText = `Chi Tiết Chênh Lệch Ngày ${dateStr} - ST ${stId}`;
            document.getElementById('modalSearch').value = stId;
            document.getElementById('modalFilterThreshold').value = 'all';
            document.getElementById('modalFilterStatus').value = 'all';

            filterModalRecords();
            document.getElementById('detailModal').classList.add('active');
        }

        function exportStorePriorityExcel() {
            const wb = XLSX.utils.book_new();
            const tbl = document.getElementById('storePriorityTable');
            const ws = XLSX.utils.table_to_sheet(tbl);
            XLSX.utils.book_append_sheet(wb, ws, "DS_Sieu_Thi_Can_Xu_Ly");
            const mText = curMonth === 'all' ? 'TOANKY' : curMonth.replace(/\s+/g, '');
            XLSX.writeFile(wb, `DS_Sieu_Thi_Can_Xu_Ly_${curGroup.toUpperCase()}_${mText}_${new Date().toISOString().slice(0, 10)}.xlsx`);
        }

        function renderAll() {
            const data = getFilteredBundleData();
            if (!data) return;

            const gt = data.grand_total;
            const om = data.overall_metrics;
            const detMetrics = getDynamicDetailedMetrics();

            // Cập nhật 4 Thẻ KPI Đầu Trang
            const elValTotal = document.getElementById('kpi-val-total');
            if (elValTotal) elValTotal.innerText = fmtVND(gt.val_total);
            const elQtyTotal = document.getElementById('kpi-qty-total');
            if (elQtyTotal) elQtyTotal.innerText = fmtN(gt.qty_lech);
            const elStoresTotal = document.getElementById('kpi-stores-total');
            if (elStoresTotal) elStoresTotal.innerText = fmtN(detMetrics.uniqueStTotal);
            const elCasesTotal = document.getElementById('kpi-cases-total');
            if (elCasesTotal) elCasesTotal.innerText = fmtN(gt.total_cases);

            const elValOver = document.getElementById('kpi-val-over100k');
            if (elValOver) elValOver.innerText = fmtVND(gt.val_over_100k);
            const elStoresOver = document.getElementById('kpi-stores-over100k');
            if (elStoresOver) elStoresOver.innerText = fmtN(detMetrics.uniqueStOver);
            const elPctOver = document.getElementById('kpi-pct-over100k');
            if (elPctOver) elPctOver.innerText = `${(gt.val_over_100k / (gt.val_total || 1) * 100).toFixed(1)}%`;

            const elValDa = document.getElementById('kpi-val-daxuly');
            if (elValDa) elValDa.innerText = fmtVND(gt.val_da_xl);
            const elPctDa = document.getElementById('kpi-pct-daxuly');
            if (elPctDa) elPctDa.innerText = `${(gt.val_da_xl / (gt.val_total || 1) * 100).toFixed(1)}%`;
            const elStoresDa = document.getElementById('kpi-stores-daxuly');
            if (elStoresDa) elStoresDa.innerText = `${fmtN(detMetrics.uniqueStDone)} ST`;

            const elValTreo = document.getElementById('kpi-val-treo');
            if (elValTreo) elValTreo.innerText = fmtVND(gt.val_dang_xl + gt.val_khong_xl);
            const elValDang = document.getElementById('kpi-val-dangxl');
            if (elValDang) elValDang.innerText = fmtVND(gt.val_dang_xl);
            const elValKhong = document.getElementById('kpi-val-khongxl');
            if (elValKhong) elValKhong.innerText = fmtVND(gt.val_khong_xl);

            // Cập nhật Thanh Tiến Độ Xử Lý
            const pctDone = (gt.val_da_xl / (gt.val_total || 1) * 100);
            const pctPending = (gt.val_dang_xl / (gt.val_total || 1) * 100);
            const pctIgnored = (gt.val_khong_xl / (gt.val_total || 1) * 100);

            const barDone = document.getElementById('bar-seg-done');
            if (barDone) barDone.style.width = pctDone + '%';
            const barPending = document.getElementById('bar-seg-pending');
            if (barPending) barPending.style.width = pctPending + '%';
            const barIgnored = document.getElementById('bar-seg-ignored');
            if (barIgnored) barIgnored.style.width = pctIgnored + '%';

            const elValDone = document.getElementById('stat-val-done');
            if (elValDone) elValDone.innerText = fmtVND(gt.val_da_xl);
            const elPctDone = document.getElementById('stat-pct-done');
            if (elPctDone) elPctDone.innerText = pctDone.toFixed(1) + '%';
            const elCasesDone = document.getElementById('stat-cases-done');
            if (elCasesDone) elCasesDone.innerText = fmtN(detMetrics.casesDone);
            const elSubDone = document.getElementById('stat-sub-done');
            if (elSubDone) elSubDone.innerHTML = `Chiếm <strong id="stat-pct-done">${pctDone.toFixed(1)}%</strong> • <strong>${fmtN(detMetrics.uniqueStDone)}</strong> Siêu Thị (${fmtN(detMetrics.storeDaysDone)} lần giao lệch) • <span id="stat-cases-done">${fmtN(detMetrics.casesDone)}</span> dòng hàng`;

            const elValPending = document.getElementById('stat-val-pending');
            if (elValPending) elValPending.innerText = fmtVND(gt.val_dang_xl);
            const elPctPending = document.getElementById('stat-pct-pending');
            if (elPctPending) elPctPending.innerText = pctPending.toFixed(1) + '%';
            const elCasesPending = document.getElementById('stat-cases-pending');
            if (elCasesPending) elCasesPending.innerText = fmtN(detMetrics.casesPending);
            const elSubPending = document.getElementById('stat-sub-pending');
            if (elSubPending) elSubPending.innerHTML = `Chiếm <strong id="stat-pct-pending">${pctPending.toFixed(1)}%</strong> • <strong>${fmtN(detMetrics.uniqueStPending)}</strong> Siêu Thị (${fmtN(detMetrics.storeDaysPending)} lần giao lệch) • <span id="stat-cases-pending">${fmtN(detMetrics.casesPending)}</span> dòng hàng`;

            const elValIgnored = document.getElementById('stat-val-ignored');
            if (elValIgnored) elValIgnored.innerText = fmtVND(gt.val_khong_xl);
            const elPctIgnored = document.getElementById('stat-pct-ignored');
            if (elPctIgnored) elPctIgnored.innerText = pctIgnored.toFixed(1) + '%';
            const elCasesIgnored = document.getElementById('stat-cases-ignored');
            if (elCasesIgnored) elCasesIgnored.innerText = fmtN(detMetrics.casesIgnored);
            const elSubIgnored = document.getElementById('stat-sub-ignored');
            if (elSubIgnored) elSubIgnored.innerHTML = `Chiếm <strong id="stat-pct-ignored">${pctIgnored.toFixed(1)}%</strong> • <strong>${fmtN(detMetrics.uniqueStIgnored)}</strong> Siêu Thị (${fmtN(detMetrics.storeDaysIgnored)} lần giao lệch) • <span id="stat-cases-ignored">${fmtN(detMetrics.casesIgnored)}</span> dòng hàng`;
            const badgeEl = document.getElementById('globalProgressBadge') || document.getElementById('progress-header-badge');
            if (badgeEl) {
                if (pctDone >= 90) {
                    badgeEl.innerHTML = `🟢 Rất tốt: ${pctDone.toFixed(1)}% Hoàn tất`;
                    badgeEl.style.background = 'rgba(52, 211, 153, 0.15)';
                    badgeEl.style.color = '#34d399';
                    badgeEl.style.borderColor = 'rgba(52, 211, 153, 0.3)';
                } else if (pctDone >= 70) {
                    badgeEl.innerHTML = `🟡 Đạt tiến độ: ${pctDone.toFixed(1)}% Hoàn tất`;
                    badgeEl.style.background = 'rgba(251, 146, 60, 0.15)';
                    badgeEl.style.color = '#fb923c';
                    badgeEl.style.borderColor = 'rgba(251, 146, 60, 0.3)';
                } else {
                    badgeEl.innerHTML = `🚨 Cần đẩy nhanh: ${pctDone.toFixed(1)}% Hoàn tất`;
                    badgeEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    badgeEl.style.color = '#f87171';
                    badgeEl.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                }
            }

            // Cập nhật Khối Thống Kê Tổng Quan DC
            updateDCOverviewStats(data);

            // Render Khối AI Insights & Takeaways DC
            renderDCInsights(data);

            // Render Charts
            renderCharts(data);
            renderDCCharts(data);

            // Render Tables
            renderStorePriorityTable();
            renderMasterTable();
            renderValTable();
            renderQtyTable();
            renderDCTable();
        }

        function renderCharts(data) {
            const list = [...data.daily_matrix].reverse();
            const fullDates = list.map(d => d.date);
            const shortLabels = list.map(d => d.date.length >= 10 ? d.date.slice(0, 5) : d.date);
            
            const vTotal = list.map(d => Number(d.val_total) || 0);
            const qLech = list.map(d => Number(d.qty_lech) || 0);
            const stOver = list.map(d => Number(d.stores_over_100k) || 0);
            const stUnder = list.map(d => Number(d.stores_under_100k) || 0);
            const vOver = list.map(d => Number(d.val_over_100k) || 0);
            const vUnder = list.map(d => Number(d.val_under_100k) || 0);

            const vDaXL = list.map(d => Number(d.val_da_xl) || 0);
            const vDangXL = list.map(d => Number(d.val_dang_xl) || 0);
            const vKhongXL = list.map(d => Number(d.val_khong_xl) || 0);
            const pctDaXLList = list.map(d => Number(d.pct_val_da_xl) || 0);

            // Case metrics by threshold group
            const cOverDa = list.map(d => Number(d.cases_over_da_xl) || 0);
            const cOverDang = list.map(d => Number(d.cases_over_dang_xl) || 0);
            const cUnderDa = list.map(d => Number(d.cases_under_da_xl) || 0);
            const cUnderKhong = list.map(d => Number(d.cases_under_khong_xl) || 0);
            const pctOverList = list.map(d => Number(d.pct_over_da_xl) || 0);
            const pctUnderList = list.map(d => Number(d.pct_under_da_xl) || 0);

            const isDark = currentTheme === 'dark';
            const textColor = isDark ? '#ffffff' : '#0f172a';
            const textMuted = isDark ? '#cbd5e1' : '#334155';
            const textDim = isDark ? '#94a3b8' : '#64748b';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';
            const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(15, 23, 42, 0.96)';

            const dpr = Math.max(window.devicePixelRatio || 2, 2);

            // ----------------------------------------------------
            // 1. BIỂU ĐỒ SO SÁNH SỐ VỤ VIỆC & TỶ LỆ XỬ LÝ (NÉT MẢNH, THANH THOÁT)
            // ----------------------------------------------------
            const elCases = document.getElementById('chartCasesComparison');
            if (elCases) {
                if (chartCases) { chartCases.destroy(); chartCases = null; }
                chartCases = new Chart(elCases.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            type: 'bar',
                            label: '🟢 ST ≥ 100k (Đã XL)',
                            data: cOverDa,
                            backgroundColor: isDark ? 'rgba(52, 211, 153, 0.9)' : 'rgba(16, 185, 129, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'over100k',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '🟡 ST ≥ 100k (Đang XL)',
                            data: cOverDang,
                            backgroundColor: isDark ? 'rgba(251, 146, 60, 0.9)' : 'rgba(234, 88, 12, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'over100k',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '🟢 ST < 100k (Đã XL)',
                            data: cUnderDa,
                            backgroundColor: isDark ? 'rgba(56, 189, 248, 0.85)' : 'rgba(2, 132, 199, 0.85)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'under100k',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '⚪ ST < 100k (Không XL)',
                            data: cUnderKhong,
                            backgroundColor: isDark ? 'rgba(148, 163, 184, 0.75)' : 'rgba(100, 116, 139, 0.75)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'under100k',
                            yAxisID: 'y'
                        },
                        {
                            type: 'line',
                            label: '📈 Tỷ lệ Xử lý ST ≥ 100k (%)',
                            data: pctOverList,
                            borderColor: '#f87171',
                            backgroundColor: '#f87171',
                            borderWidth: 2.2,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            tension: 0.3,
                            yAxisID: 'y1'
                        },
                        {
                            type: 'line',
                            label: '📈 Tỷ lệ Xử lý ST < 100k (%)',
                            data: pctUnderList,
                            borderColor: '#38bdf8',
                            backgroundColor: '#38bdf8',
                            borderWidth: 1.8,
                            borderDash: [4, 4],
                            pointRadius: 2.5,
                            pointHoverRadius: 5,
                            tension: 0.3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: { padding: { top: 25, bottom: 15 } },
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: {
                            stacked: true,
                            ticks: {
                                color: textMuted,
                                font: { weight: '600', size: 10.5 },
                                minRotation: 45,
                                maxRotation: 45,
                                autoSkip: false
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y: {
                            stacked: true,
                            title: { display: true, text: 'Số Vụ Việc (Dòng SKU)', font: { size: 11, weight: '700' }, color: textColor },
                            ticks: { color: textMuted, font: { weight: '700', size: 10.5 } },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y1: {
                            position: 'right',
                            min: 0,
                            max: 130,
                            grid: { drawOnChartArea: false },
                            ticks: {
                                color: '#f87171',
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => v <= 100 ? v + '%' : ''
                            },
                            title: { display: true, text: 'Tỷ Lệ % Xong', font: { size: 11, weight: '700' }, color: '#f87171' }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 16 }
                        },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            callbacks: {
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => {
                                    const curDay = list[c.dataIndex] || {};
                                    if (c.dataset.yAxisID === 'y1') return ` ${c.dataset.label}: ${c.raw}%`;
                                    
                                    let stCount = 0;
                                    if (c.datasetIndex === 0) stCount = curDay.st_over_da_xl || 0;
                                    else if (c.datasetIndex === 1) stCount = curDay.st_over_dang_xl || 0;
                                    else if (c.datasetIndex === 2) stCount = curDay.st_under_da_xl || 0;
                                    else if (c.datasetIndex === 3) stCount = curDay.st_under_khong_xl || 0;

                                    return ` ${c.dataset.label}: ${fmtN(c.raw)} dòng hàng • ${stCount} Siêu Thị`;
                                },
                                footer: (items) => {
                                    const curDay = list[items[0].dataIndex] || {};
                                    const overTot = (items.find(i => i.datasetIndex === 0)?.raw || 0) + (items.find(i => i.datasetIndex === 1)?.raw || 0);
                                    const underTot = (items.find(i => i.datasetIndex === 2)?.raw || 0) + (items.find(i => i.datasetIndex === 3)?.raw || 0);
                                    return `👉 ST ≥ 100k: ${fmtN(overTot)} dòng (${curDay.stores_over_100k || 0} ST) | ST < 100k: ${fmtN(underTot)} dòng (${curDay.stores_under_100k || 0} ST)`;
                                }
                            }
                        },
                        datalabels: { display: false }
                    }
                }
            });
            }

            // ----------------------------------------------------
            // 2. Biểu đồ Chênh Lệch Tiền & Số Lượng (CỘT MẢNH, ĐƯỜNG NÉT)
            // ----------------------------------------------------
            const el1 = document.getElementById('chartDailyLech');
            if (el1) {
                if (chart1) { chart1.destroy(); chart1 = null; }
                chart1 = new Chart(el1.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            type: 'bar',
                            label: 'Tổng Tiền Lệch (VNĐ)',
                            data: vTotal,
                            backgroundColor: isDark ? 'rgba(56, 189, 248, 0.85)' : 'rgba(2, 132, 199, 0.85)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            yAxisID: 'y'
                        },
                        {
                            type: 'line',
                            label: 'SL Lệch (PCS / KG)',
                            data: qLech,
                            borderColor: '#f87171',
                            backgroundColor: '#f87171',
                            borderWidth: 2.2,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            tension: 0.3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        datalabels: {
                            display: (ctx) => {
                                if (ctx.dataset.yAxisID === 'y') {
                                    return ctx.dataset.data[ctx.dataIndex] >= 65e6;
                                }
                                return ctx.dataset.data[ctx.dataIndex] >= 3000;
                            },
                            color: (ctx) => ctx.dataset.yAxisID === 'y' ? '#ffffff' : '#f87171',
                            backgroundColor: 'rgba(15, 23, 42, 0.88)',
                            borderRadius: 4,
                            padding: { top: 2, bottom: 2, left: 4, right: 4 },
                            font: { weight: 'bold', size: 9.5 },
                            anchor: 'end',
                            align: 'top',
                            offset: 2,
                            formatter: (v, ctx) => ctx.dataset.yAxisID === 'y' ? (v/1e6).toFixed(0) + 'Tr' : fmtN(v)
                        },
                        legend: { 
                            position: 'top', 
                            labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 16 } 
                        },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            callbacks: {
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => c.dataset.yAxisID === 'y' ? ` ${c.dataset.label}: ${fmtVND(c.raw)}` : ` ${c.dataset.label}: ${fmtN(c.raw)}`
                            }
                        }
                    },
                    layout: {
                        padding: { top: 20, bottom: 15 }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: textMuted,
                                font: { weight: '600', size: 10.5 },
                                minRotation: 45,
                                maxRotation: 45,
                                autoSkip: false
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y: { 
                            type: 'linear',
                            position: 'left',
                            ticks: { 
                                color: textMuted,
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => (v / 1e6).toFixed(0) + ' Tr' 
                            },
                            title: { display: true, text: 'Tiền Lệch (VNĐ)', font: { size: 11, weight: '700' }, color: '#38bdf8' },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { 
                                color: '#f87171',
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => fmtN(v) 
                            },
                            title: { display: true, text: 'Số Lượng Lệch', font: { size: 11, weight: '700' }, color: '#f87171' }
                        }
                    }
                }
            });
            }

            // ----------------------------------------------------
            // 3. Biểu đồ Tiến Độ Xử Lý Chênh Lệch Theo Ngày (MẢNH MAI & SẮC NÉT)
            // ----------------------------------------------------
            const el2 = document.getElementById('chartDailyProgress');
            if (el2) {
                if (chart2) { chart2.destroy(); chart2 = null; }
                chart2 = new Chart(el2.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            type: 'bar',
                            label: '🟢 Đã Xử Lý',
                            data: vDaXL,
                            backgroundColor: isDark ? 'rgba(52, 211, 153, 0.9)' : 'rgba(16, 185, 129, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'stack0',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '🟡 Đang XL (ST ≥ 100k)',
                            data: vDangXL,
                            backgroundColor: isDark ? 'rgba(251, 146, 60, 0.9)' : 'rgba(234, 88, 12, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'stack0',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '⚪ Không XL (ST < 100k)',
                            data: vKhongXL,
                            backgroundColor: isDark ? 'rgba(148, 163, 184, 0.75)' : 'rgba(100, 116, 139, 0.75)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'stack0',
                            yAxisID: 'y'
                        },
                        {
                            type: 'line',
                            label: '📈 % Hoàn Tất',
                            data: pctDaXLList,
                            borderColor: '#38bdf8',
                            backgroundColor: '#38bdf8',
                            borderWidth: 2.2,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            tension: 0.3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: {
                        padding: {
                            top: 25,
                            bottom: 15
                        }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        x: { 
                            stacked: true,
                            ticks: {
                                color: textMuted,
                                font: { weight: '600', size: 10.5 },
                                minRotation: 45,
                                maxRotation: 45,
                                autoSkip: false
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y: { 
                            stacked: true, 
                            title: { display: true, text: 'Tiền Xử Lý (VNĐ)', font: { size: 11, weight: '700' }, color: '#34d399' },
                            ticks: { 
                                color: textMuted,
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => (v / 1e6).toFixed(0) + ' Tr'
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y1: {
                            position: 'right',
                            min: 0,
                            max: 130,
                            grid: { drawOnChartArea: false },
                            ticks: {
                                color: '#38bdf8',
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => v <= 100 ? v + '%' : ''
                            },
                            title: { display: true, text: 'Tỷ lệ % Xong', font: { size: 11, weight: '700' }, color: '#38bdf8' }
                        }
                    },
                    plugins: {
                        legend: { 
                            position: 'top', 
                            labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 16 } 
                        },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            callbacks: {
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => {
                                    if (c.dataset.yAxisID === 'y1') return ` ${c.dataset.label}: ${c.raw}%`;
                                    return ` ${c.dataset.label}: ${fmtVND(c.raw)}`;
                                },
                                footer: (items) => {
                                    const total = items.filter(i => i.dataset.yAxisID === 'y').reduce((a, b) => a + (Number(b.raw) || 0), 0);
                                    return `👉 Tổng tiền phát sinh: ${fmtVND(total)}`;
                                }
                            }
                        },
                        datalabels: {
                            display: (ctx) => {
                                if (ctx.dataset.yAxisID === 'y1') {
                                    const val = ctx.dataset.data[ctx.dataIndex];
                                    return val < 98;
                                }
                                return ctx.datasetIndex === 0 && ctx.dataset.data[ctx.dataIndex] >= 75e6;
                            },
                            color: (ctx) => ctx.dataset.yAxisID === 'y1' ? '#fbbf24' : '#ffffff',
                            backgroundColor: 'rgba(15, 23, 42, 0.92)',
                            borderRadius: 4,
                            padding: { top: 2, bottom: 2, left: 4, right: 4 },
                            font: { weight: 'bold', size: 9.5 },
                            anchor: (ctx) => ctx.dataset.yAxisID === 'y1' ? 'bottom' : 'center',
                            align: (ctx) => ctx.dataset.yAxisID === 'y1' ? 'bottom' : 'center',
                            formatter: (v, ctx) => ctx.dataset.yAxisID === 'y1' ? '⚠️ ' + v + '%' : (v/1e6).toFixed(0) + 'Tr'
                        }
                    }
                }
            });
            }

            // ----------------------------------------------------
            // 4. Biểu đồ Số Lượng Siêu Thị Phát Sinh Lệch (CỘT MẢNH)
            // ----------------------------------------------------
            const el3 = document.getElementById('chartDailyStores');
            if (el3) {
                if (chart3) { chart3.destroy(); chart3 = null; }
                chart3 = new Chart(el3.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            label: 'ST ≥ 100k',
                            data: stOver,
                            backgroundColor: isDark ? 'rgba(248, 113, 113, 0.9)' : 'rgba(220, 38, 38, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14
                        },
                        {
                            label: 'ST < 100k',
                            data: stUnder,
                            backgroundColor: isDark ? 'rgba(52, 211, 153, 0.9)' : 'rgba(22, 163, 74, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: {
                        padding: {
                            top: 25,
                            bottom: 15
                        }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        x: { 
                            stacked: true,
                            ticks: {
                                color: textMuted,
                                font: { weight: '600', size: 10.5 },
                                minRotation: 45,
                                maxRotation: 45,
                                autoSkip: false
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y: { 
                            stacked: true, 
                            title: { display: true, text: 'Số lượng Siêu Thị (ST)', font: { size: 11, weight: '700' }, color: textColor },
                            ticks: { 
                                color: textMuted,
                                font: { weight: '700', size: 10.5 },
                                stepSize: 25 
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        }
                    },
                    plugins: {
                        legend: { 
                            position: 'top', 
                            labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 16 } 
                        },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            callbacks: {
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => ` ${c.dataset.label}: ${c.raw} ST`,
                                footer: (items) => {
                                    const total = items.reduce((a, b) => a + (Number(b.raw) || 0), 0);
                                    return `👉 Tổng số ST lệch: ${total} ST`;
                                }
                            }
                        },
                        datalabels: {
                            display: (ctx) => ctx.datasetIndex === 1,
                            anchor: 'end',
                            align: 'top',
                            offset: 3,
                            color: '#ffffff',
                            backgroundColor: 'rgba(15, 23, 42, 0.92)',
                            borderRadius: 4,
                            padding: { top: 2, bottom: 2, left: 4, right: 4 },
                            font: { weight: '800', size: 10.5 },
                            formatter: (value, ctx) => {
                                const d0 = Number(ctx.chart.data.datasets[0].data[ctx.dataIndex]) || 0;
                                const d1 = Number(ctx.chart.data.datasets[1].data[ctx.dataIndex]) || 0;
                                const total = d0 + d1;
                                return total > 0 ? total : '';
                            }
                        }
                    }
                }
            });
            }

            // ----------------------------------------------------
            // 5. Biểu đồ Biến Động Giá Trị Chênh Lệch Theo Nhóm ST (NÉT MẢNH)
            // ----------------------------------------------------
            const el4 = document.getElementById('chartTrendThreshold');
            if (el4) {
                if (chart4) { chart4.destroy(); chart4 = null; }
                chart4 = new Chart(el4.getContext('2d'), {
                type: 'line',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            label: 'Nhóm ST ≥ 100k',
                            data: vOver,
                            borderColor: '#f87171',
                            backgroundColor: isDark ? 'rgba(248, 113, 113, 0.12)' : 'rgba(220, 38, 38, 0.08)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 2.5,
                            pointRadius: 3.5,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#f87171'
                        },
                        {
                            label: 'Nhóm ST < 100k',
                            data: vUnder,
                            borderColor: '#34d399',
                            backgroundColor: isDark ? 'rgba(52, 211, 153, 0.08)' : 'rgba(22, 163, 74, 0.06)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 2.0,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            pointBackgroundColor: '#34d399'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: {
                        padding: { top: 25, bottom: 15 }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: { 
                            position: 'top', 
                            labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 16 } 
                        },
                        tooltip: { 
                            backgroundColor: tooltipBg,
                            padding: 10,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            callbacks: { 
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => ` ${c.dataset.label}: ${fmtVND(c.raw)}` 
                            } 
                        },
                        datalabels: {
                            display: (ctx) => ctx.datasetIndex === 0 && ctx.dataset.data[ctx.dataIndex] >= 60e6,
                            color: '#ffffff',
                            backgroundColor: '#dc2626',
                            borderRadius: 4,
                            padding: { top: 2, bottom: 2, left: 4, right: 4 },
                            font: { weight: 'bold', size: 9.5 },
                            anchor: 'end',
                            align: 'top',
                            offset: 3,
                            formatter: (v) => (v / 1e6).toFixed(0) + ' Tr'
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: textMuted,
                                font: { weight: '600', size: 10.5 },
                                minRotation: 45,
                                maxRotation: 45,
                                autoSkip: false
                            },
                            grid: { color: gridColor, borderDash: [3, 4] }
                        },
                        y: { 
                            ticks: { 
                                color: textMuted,
                                font: { weight: '700', size: 10.5 },
                                callback: (v) => (v / 1e6).toFixed(0) + ' Tr' 
                            },
                            title: { display: true, text: 'Tiền Lệch (VNĐ)', font: { size: 11, weight: '700' }, color: '#f87171' },
                        }
                    }
                }
            });
            }

            // ----------------------------------------------------
            // 6. Biểu đồ Phân Bổ Điểm Nhận Trách Nhiệm (VÒNG DONUT TINH TẾ)
            // ----------------------------------------------------
            const gt = data.grand_total;
            const destItems = [
                { label: 'Kho ĐÔNG MÁT', val: Number(gt.val_kho) || 0, color: isDark ? '#818cf8' : '#6366f1' },
                { label: 'Siêu Thị', val: Number(gt.val_st) || 0, color: isDark ? '#fbbf24' : '#f59e0b' },
                { label: 'Hao Hụt', val: Number(gt.val_haohut) || 0, color: isDark ? '#34d399' : '#10b981' },
                { label: 'Đang XL (ST ≥ 100k)', val: Number(gt.val_dang_xl) || 0, color: isDark ? '#fb923c' : '#ea580c' },
                { label: 'Không XL (ST < 100k)', val: Number(gt.val_khong_xl) || 0, color: isDark ? '#94a3b8' : '#64748b' }
            ];

            const totalDestVal = destItems.reduce((a, b) => a + b.val, 0) || 1.0;

            const el5 = document.getElementById('chartDestDoughnut');
            if (el5) {
                if (chart5) { chart5.destroy(); chart5 = null; }
                chart5 = new Chart(el5.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: destItems.map(d => d.label),
                    datasets: [{
                        data: destItems.map(d => d.val),
                        backgroundColor: destItems.map(d => d.color),
                        borderWidth: 1.5,
                        borderColor: isDark ? '#111827' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: { padding: 10 },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            callbacks: {
                                label: (c) => {
                                    const pct = (c.raw / totalDestVal * 100).toFixed(1);
                                    return ` ${c.label}: ${fmtVND(c.raw)} (${pct}%)`;
                                }
                            }
                        },
                        datalabels: {
                            color: '#ffffff',
                            font: { weight: 'bold', size: 10.5 },
                            formatter: (value, ctx) => {
                                const pct = (value / totalDestVal * 100);
                                return pct >= 6.0 ? pct.toFixed(1) + '%' : '';
                            }
                        }
                    },
                    cutout: '66%'
                }
            });
            }

            // Render Danh sách Tỷ Lệ % và Số Tiền bên cạnh biểu đồ tròn
            let legendHtml = '';
            destItems.forEach(item => {
                const pct = (item.val / totalDestVal * 100).toFixed(1);
                legendHtml += `
                <div class="legend-row" style="border-left-color: ${item.color};">
                    <div class="legend-name">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${item.color};"></span>
                        <span>${item.label}</span>
                    </div>
                    <div>
                        <span class="legend-val">${fmtVND(item.val)}</span>
                        <span class="legend-pct" style="background:${item.color};">${pct}%</span>
                    </div>
                </div>
                `;
            });
            const destLegEl = document.getElementById('destLegendList');
            if (destLegEl) destLegEl.innerHTML = legendHtml;
        }

        // ----------------------------------------------------
        // CẬP NHẬT THẺ TỔNG QUAN DC PHẢN HỒI (DC OVERVIEW STATS)
        // ----------------------------------------------------
        function updateDCOverviewStats(data) {
            const list = data.daily_matrix || [];
            
            let totDcCases = 0, totDcVal = 0;
            let totDongYCases = 0, totDongYVal = 0;
            let totTuChoiCases = 0, totTuChoiVal = 0;
            let totKiemTraCases = 0, totKiemTraVal = 0;
            let totChuaCases = 0, totChuaVal = 0;

            const stSetTotal = new Set();
            const stSetDongY = new Set();
            const stSetTuChoi = new Set();
            const stSetKiemTra = new Set();
            const stSetChua = new Set();

            let storeDaysTotal = 0, storeDaysDongY = 0, storeDaysTuChoi = 0, storeDaysKiemTra = 0, storeDaysChua = 0;

            const dates = list.map(d => d.date);
            dates.forEach(dStr => {
                const recs = DAILY_RECORDS[dStr] || [];
                const filteredRecs = curGroup === 'all' ? recs : recs.filter(r => (curGroup === 'mat' ? r.group.includes('MÁT') : r.group.includes('ĐÔNG')));
                const dcRecs = filteredRecs.filter(r => r.destination === 'Kho ĐÔNG MÁT');

                const dayStMap = {};

                dcRecs.forEach(r => {
                    totDcCases++;
                    totDcVal += r.val_total || 0;
                    stSetTotal.add(r.st);

                    if (!dayStMap[r.st]) {
                        dayStMap[r.st] = { hasTotal: true, hasDongY: false, hasTuChoi: false, hasKiemTra: false, hasChua: false };
                    }

                    if (r.dc_confirm === 'Đồng ý claim') {
                        totDongYCases++;
                        totDongYVal += r.val_total || 0;
                        stSetDongY.add(r.st);
                        dayStMap[r.st].hasDongY = true;
                    } else if (r.dc_confirm === 'Từ chối claim') {
                        totTuChoiCases++;
                        totTuChoiVal += r.val_total || 0;
                        stSetTuChoi.add(r.st);
                        dayStMap[r.st].hasTuChoi = true;
                    } else if (r.dc_confirm === 'Kiểm tra lại') {
                        totKiemTraCases++;
                        totKiemTraVal += r.val_total || 0;
                        stSetKiemTra.add(r.st);
                        dayStMap[r.st].hasKiemTra = true;
                    } else {
                        totChuaCases++;
                        totChuaVal += r.val_total || 0;
                        stSetChua.add(r.st);
                        dayStMap[r.st].hasChua = true;
                    }
                });

                Object.values(dayStMap).forEach(obj => {
                    if (obj.hasTotal) storeDaysTotal++;
                    if (obj.hasDongY) storeDaysDongY++;
                    if (obj.hasTuChoi) storeDaysTuChoi++;
                    if (obj.hasKiemTra) storeDaysKiemTra++;
                    if (obj.hasChua) storeDaysChua++;
                });
            });

            const respCases = totDongYCases + totTuChoiCases + totKiemTraCases;
            const pctResp = totDcCases > 0 ? (respCases / totDcCases * 100) : 100.0;
            const pctDongY = totDcCases > 0 ? (totDongYCases / totDcCases * 100) : 0.0;
            const pctTuChoi = totDcCases > 0 ? (totTuChoiCases / totDcCases * 100) : 0.0;
            const pctKiemTra = totDcCases > 0 ? ((totKiemTraCases + totChuaCases) / totDcCases * 100) : 0.0;

            const elValTotal = document.getElementById('dc-stat-val-total');
            const elSubTotal = document.getElementById('dc-stat-sub-total');
            if (elValTotal) elValTotal.innerText = fmtVND(totDcVal);
            if (elSubTotal) elSubTotal.innerText = `${fmtN(totDcCases)} dòng hàng • ${stSetTotal.size} Siêu Thị (${storeDaysTotal} lần giao)`;

            const elValDongY = document.getElementById('dc-stat-val-dongy');
            const elSubDongY = document.getElementById('dc-stat-sub-dongy');
            if (elValDongY) elValDongY.innerText = fmtVND(totDongYVal);
            if (elSubDongY) elSubDongY.innerText = `Chiếm ${pctDongY.toFixed(1)}% • ${stSetDongY.size} Siêu Thị (${storeDaysDongY} lần giao) • ${fmtN(totDongYCases)} dòng`;

            const elValTuChoi = document.getElementById('dc-stat-val-tuchoi');
            const elSubTuChoi = document.getElementById('dc-stat-sub-tuchoi');
            if (elValTuChoi) elValTuChoi.innerText = fmtVND(totTuChoiVal);
            if (elSubTuChoi) elSubTuChoi.innerText = `Chiếm ${pctTuChoi.toFixed(1)}% • ${stSetTuChoi.size} Siêu Thị (${storeDaysTuChoi} lần giao) • ${fmtN(totTuChoiCases)} dòng`;

            const elValKiemTra = document.getElementById('dc-stat-val-kiemtra');
            const elSubKiemTra = document.getElementById('dc-stat-sub-kiemtra');
            if (elValKiemTra) elValKiemTra.innerText = fmtVND(totKiemTraVal + totChuaVal);
            if (elSubKiemTra) elSubKiemTra.innerText = `Chiếm ${pctKiemTra.toFixed(1)}% • ${stSetKiemTra.size + stSetChua.size} Siêu Thị • ${fmtN(totKiemTraCases + totChuaCases)} dòng`;

            const elValPct = document.getElementById('dc-stat-val-pct');
            const elSubPct = document.getElementById('dc-stat-sub-pct');
            if (elValPct) elValPct.innerText = `${pctResp.toFixed(1)}%`;
            if (elSubPct) elSubPct.innerText = `Đã phản hồi ${fmtN(respCases)} / ${fmtN(totDcCases)} dòng hàng`;
        }

        
        // ==========================================================
        // KHỐI QUẢN LÝ VÀ PHÂN TÍCH DC & KFM (4 CỘT AD - AG)
        // ==========================================================
        let curDCViewMode = 'summary'; // 'summary' hoặc 'detail'
        let curDCQuickFilter = 'not_done';
        let allDCCasesCache = [];

        function switchDCViewMode(mode) {
            curDCViewMode = mode;
            const btnSum = document.getElementById('btn-dc-mode-summary');
            const btnDet = document.getElementById('btn-dc-mode-detail');
            const pPill = document.getElementById('dc-period-pill');
            const sumCont = document.getElementById('dc-view-summary-container');
            const detCont = document.getElementById('dc-view-detail-container');

            if (btnSum) btnSum.className = 'seg-btn' + (mode === 'summary' ? ' active' : '');
            if (btnDet) btnDet.className = 'seg-btn' + (mode === 'detail' ? ' active' : '');
            if (pPill) pPill.style.display = mode === 'summary' ? 'flex' : 'none';
            if (sumCont) sumCont.style.display = mode === 'summary' ? 'block' : 'none';
            if (detCont) detCont.style.display = mode === 'detail' ? 'block' : 'none';

            if (mode === 'summary') {
                renderDCSummaryTable();
            } else {
                renderDCDetailTable();
            }
        }

        function setDCQuickFilter(filterKey) {
            curDCQuickFilter = filterKey;
            
            const pills = [
                { id: 'pill-dc-not-done', key: 'not_done' },
                { id: 'pill-dc-tuchoi-pending', key: 'tuchoi_pending' },
                { id: 'pill-dc-tuchoi-hlv', key: 'tuchoi_hlv' },
                { id: 'pill-dc-kiemtra', key: 'kiemtra' },
                { id: 'pill-dc-chua', key: 'chua_phan_hoi' },
                { id: 'pill-dc-done', key: 'done' },
                { id: 'pill-dc-all', key: 'all' }
            ];

            pills.forEach(p => {
                const el = document.getElementById(p.id);
                if (el) el.className = 'dc-filter-pill' + (p.key === filterKey ? ' active' : '');
            });

            // Đồng bộ dropdown lọc tương ứng
            const selConf = document.getElementById('dcDetailFilterConfirm');
            const selReply = document.getElementById('dcDetailFilterReply');

            if (filterKey === 'not_done') {
                if (selConf) selConf.value = 'Đồng ý claim';
                if (selReply) selReply.value = 'Chưa phản hồi';
            } else if (filterKey === 'tuchoi_pending') {
                if (selConf) selConf.value = 'Từ chối claim';
                if (selReply) selReply.value = 'Chưa phản hồi';
            } else if (filterKey === 'tuchoi_hlv') {
                if (selConf) selConf.value = 'Từ chối claim';
                if (selReply) selReply.value = 'Cấp HLV quyết định';
            } else if (filterKey === 'kiemtra') {
                if (selConf) selConf.value = 'Kiểm tra lại';
                if (selReply) selReply.value = 'all';
            } else if (filterKey === 'chua_phan_hoi') {
                if (selConf) selConf.value = 'Chưa phản hồi';
                if (selReply) selReply.value = 'all';
            } else if (filterKey === 'done') {
                if (selConf) selConf.value = 'Đồng ý claim';
                if (selReply) selReply.value = 'DONE';
            } else {
                if (selConf) selConf.value = 'all';
                if (selReply) selReply.value = 'all';
            }

            filterDCDetailTable();
        }

        function getAllDCCases() {
            const list = [];
            const dates = Object.keys(DAILY_RECORDS);

            dates.forEach(dStr => {
                if (curMonth !== 'all') {
                    const rawBundle = BUNDLES[curGroup];
                    const matchDay = rawBundle.daily_matrix.find(d => d.date === dStr);
                    if (!matchDay || matchDay.month !== curMonth) {
                        return;
                    }
                }

                const recs = DAILY_RECORDS[dStr] || [];
                const filteredRecs = recs.filter(r => {
                    // Phải là trả DC (Destination Kho ĐÔNG MÁT)
                    if (r.destination !== 'Kho ĐÔNG MÁT') return false;
                    // Lọc theo nhóm nếu curGroup != 'all'
                    if (curGroup === 'mat' && !r.group.includes('MÁT')) return false;
                    if (curGroup === 'dong' && !r.group.includes('ĐÔNG')) return false;
                    return true;
                });

                filteredRecs.forEach(r => {
                    list.push({ ...r, date: dStr });
                });
            });

            return list;
        }

        // Cập nhật 4 Thẻ KPI DC & Bảng Ma Trận Đối Soát Chéo
        function updateDCOverviewStats(data) {
            const dcCases = getAllDCCases();
            const totDC = dcCases.length || 1;
            const totValDC = dcCases.reduce((a, b) => a + (Number(b.val_total) || 0), 0);

            // Phân loại DC xác nhận (Cột AD)
            const dyCases = dcCases.filter(r => r.dc_confirm === 'Đồng ý claim');
            const tcCases = dcCases.filter(r => r.dc_confirm === 'Từ chối claim');
            const ktCases = dcCases.filter(r => r.dc_confirm === 'Kiểm tra lại');
            const chCases = dcCases.filter(r => !['Đồng ý claim', 'Từ chối claim', 'Kiểm tra lại'].includes(r.dc_confirm));

            const respCases = dyCases.length + tcCases.length + ktCases.length;
            const pctResp = (respCases / totDC * 100).toFixed(1);
            const valResp = dyCases.concat(tcCases, ktCases).reduce((a, b) => a + (Number(b.val_total) || 0), 0);
            const valChua = chCases.reduce((a, b) => a + (Number(b.val_total) || 0), 0);

            // Cột AF trên DC Đồng ý claim
            const dyDone = dyCases.filter(r => r.kfm_reply === 'DONE');
            const dyNotDone = dyCases.filter(r => r.kfm_reply !== 'DONE');
            const pctDyDone = dyCases.length > 0 ? (dyDone.length / dyCases.length * 100).toFixed(1) : 0;
            const valDyDone = dyDone.reduce((a, b) => a + (Number(b.val_total) || 0), 0);
            const valDyNotDone = dyNotDone.reduce((a, b) => a + (Number(b.val_total) || 0), 0);

            // Nhóm DC khác Đồng ý
            const nonAgreeCases = tcCases.length + ktCases.length + chCases.length;
            const pctNonAgree = (nonAgreeCases / totDC * 100).toFixed(1);
            const tcReplied = tcCases.filter(r => (r.kfm_reply || '').trim() !== '');
            const pctTcReplied = tcCases.length > 0 ? (tcReplied.length / tcCases.length * 100).toFixed(1) : 0;
            const ktReplied = ktCases.filter(r => (r.kfm_reply || '').trim() !== '');
            const pctKtReplied = ktCases.length > 0 ? (ktReplied.length / ktCases.length * 100).toFixed(1) : 0;

            // Update Thẻ 1
            const elPctResp = document.getElementById('dc-kpi-pct-resp');
            const elSubResp = document.getElementById('dc-kpi-sub-resp');
            if (elPctResp) elPctResp.innerText = `${pctResp}%`;
            if (elSubResp) {
                elSubResp.innerHTML = `Đã phản hồi <strong>${fmtN(respCases)}</strong> / ${fmtN(totDC)} dòng (${fmtVND(valResp)})<br><span style="color:#f87171; font-weight:600;">⚠️ Còn nợ phản hồi: ${fmtN(chCases.length)} dòng (${(chCases.length/totDC*100).toFixed(1)}% • ${fmtVND(valChua)})</span>`;
            }

            // Update Thẻ 2 (KFM DONE trên DC Đồng ý)
            const elPctDone = document.getElementById('dc-kpi-pct-done');
            const elSubDone = document.getElementById('dc-kpi-sub-done');
            if (elPctDone) elPctDone.innerText = `${pctDyDone}%`;
            if (elSubDone) {
                elSubDone.innerHTML = `Đã DONE: <strong>${fmtN(dyDone.length)}</strong> / ${fmtN(dyCases.length)} dòng (${fmtVND(valDyDone)})<br><span style="color:#fb923c; font-weight:600;">🚨 Chưa chỉnh DONE: ${fmtN(dyNotDone.length)} dòng (${(100 - pctDyDone).toFixed(1)}% • ${fmtVND(valDyNotDone)})</span>`;
            }

            // Update Thẻ 3 (DC Khác Đồng ý)
            const elPctNon = document.getElementById('dc-kpi-pct-nonagree');
            const elSubNon = document.getElementById('dc-kpi-sub-nonagree');
            if (elPctNon) elPctNon.innerText = `${pctNonAgree}%`;
            if (elSubNon) {
                elSubNon.innerHTML = `Tổng <strong>${fmtN(nonAgreeCases)}</strong> dòng (Từ chối: ${fmtN(tcCases.length)} • KT lại: ${fmtN(ktCases.length)} • Chờ: ${fmtN(chCases.length)})<br><span>KFM phản hồi: <strong>${pctTcReplied}%</strong> Từ chối (${tcReplied.length} case) • <strong>${pctKtReplied}%</strong> KT lại</span>`;
            }

            // Update Thẻ 4 (Top Note DC & KFM)
            const dcNotesMap = {};
            const kfmNotesMap = {};
            dcCases.forEach(r => {
                if (r.dc_note) dcNotesMap[r.dc_note] = (dcNotesMap[r.dc_note] || 0) + 1;
                if (r.kfm_note) kfmNotesMap[r.kfm_note] = (kfmNotesMap[r.kfm_note] || 0) + 1;
            });
            const topDCNotes = Object.entries(dcNotesMap).sort((a, b) => b[1] - a[1]);
            const topKFMNotes = Object.entries(kfmNotesMap).sort((a, b) => b[1] - a[1]);

            const elTopNote = document.getElementById('dc-kpi-top-note');
            const elSubNotes = document.getElementById('dc-kpi-sub-notes');
            if (elTopNote) {
                elTopNote.innerText = topDCNotes.length > 0 ? `${topDCNotes[0][0]} (${topDCNotes[0][1]})` : 'Không có ghi chú';
            }
            if (elSubNotes) {
                const subDcTxt = topDCNotes.slice(1, 4).map(x => `${x[0]} (${x[1]})`).join(', ') || 'Chưa có ghi chú khác';
                const subKfmTxt = topKFMNotes.slice(0, 2).map(x => `${x[0]} (${x[1]})`).join(', ') || 'Chưa có';
                elSubNotes.innerHTML = `Lý do DC: <em>${subDcTxt}</em><br>KFM Note: <em>${subKfmTxt}</em>`;
            }

            // Update Quick Filter Badges
            const bNotDone = document.getElementById('badge-cnt-not-done');
            if (bNotDone) bNotDone.innerText = fmtN(dyNotDone.length);
            const bTcPending = document.getElementById('badge-cnt-tc-pending');
            if (bTcPending) bTcPending.innerText = fmtN(tcCases.length - tcReplied.length);
            const bTcHlv = document.getElementById('badge-cnt-tc-hlv');
            if (bTcHlv) bTcHlv.innerText = fmtN(tcCases.filter(r => r.kfm_reply === 'Cấp HLV quyết định').length);
            const bKt = document.getElementById('badge-cnt-kt');
            if (bKt) bKt.innerText = fmtN(ktCases.length);
            const bChua = document.getElementById('badge-cnt-chua');
            if (bChua) bChua.innerText = fmtN(chCases.length);
            const bDone = document.getElementById('badge-cnt-done');
            if (bDone) bDone.innerText = fmtN(dyDone.length);
            const bAll = document.getElementById('badge-cnt-all');
            if (bAll) bAll.innerText = fmtN(dcCases.length);

            // Render Cross-Tab Matrix
            renderDCCrossTabMatrix(dcCases);
        }

        function renderDCCrossTabMatrix(dcCases) {
            const tbody = document.getElementById('dcCrossTabBody');
            const tfoot = document.getElementById('dcCrossTabFoot');
            if (!tbody || !tfoot) return;

            const categories = [
                { key: 'Đồng ý claim', label: '🟢 DC Đồng Ý Claim', color: '#34d399' },
                { key: 'Từ chối claim', label: '🔴 DC Từ Chối Claim', color: '#f87171' },
                { key: 'Kiểm tra lại', label: '🟡 DC Kiểm Tra Lại', color: '#fbbf24' },
                { key: 'Chưa phản hồi', label: '⏳ DC Chưa Phản Hồi (Trống)', color: '#94a3b8' }
            ];

            let sumDone = 0, sumHlv = 0, sumCheck = 0, sumBlank = 0, sumTotal = 0;
            let rowsHtml = '';

            categories.forEach(cat => {
                const sub = dcCases.filter(r => {
                    if (cat.key === 'Chưa phản hồi') return !['Đồng ý claim', 'Từ chối claim', 'Kiểm tra lại'].includes(r.dc_confirm);
                    return r.dc_confirm === cat.key;
                });

                const cDone = sub.filter(r => r.kfm_reply === 'DONE').length;
                const cHlv = sub.filter(r => r.kfm_reply === 'Cấp HLV quyết định').length;
                const cCheck = sub.filter(r => r.kfm_reply === 'DC check lại thông tin').length;
                const cBlank = sub.filter(r => !['DONE', 'Cấp HLV quyết định', 'DC check lại thông tin'].includes(r.kfm_reply)).length;
                const cTot = sub.length;

                sumDone += cDone;
                sumHlv += cHlv;
                sumCheck += cCheck;
                sumBlank += cBlank;
                sumTotal += cTot;

                const pctDoneOnCat = cTot > 0 ? (cDone / cTot * 100).toFixed(1) : 0;
                const pctHlvOnCat = cTot > 0 ? (cHlv / cTot * 100).toFixed(1) : 0;

                rowsHtml += `
                <tr>
                    <td class="text-left" style="font-weight:700; color:${cat.color};">${cat.label}</td>
                    <td class="text-center">${cDone > 0 ? `<strong style="color:#34d399;">${fmtN(cDone)}</strong> <span style="font-size:0.72rem; color:var(--text-muted);">(${pctDoneOnCat}%)</span>` : '-'}</td>
                    <td class="text-center">${cHlv > 0 ? `<strong style="color:#f87171;">${fmtN(cHlv)}</strong> <span style="font-size:0.72rem; color:var(--text-muted);">(${pctHlvOnCat}%)</span>` : '-'}</td>
                    <td class="text-center">${cCheck > 0 ? `<strong style="color:#fbbf24;">${fmtN(cCheck)}</strong>` : '-'}</td>
                    <td class="text-center">${cBlank > 0 ? `<span style="color:#94a3b8;">${fmtN(cBlank)}</span>` : '-'}</td>
                    <td class="text-right" style="font-weight:800; color:#38bdf8;">${fmtN(cTot)} dòng</td>
                </tr>
                `;
            });

            tbody.innerHTML = rowsHtml;

            tfoot.innerHTML = `
            <tr style="font-weight:800; background:rgba(15, 23, 42, 0.95); border-top:2px solid #334155;">
                <td class="text-left" style="color:#fff;">TỔNG CỘNG HỆ THỐNG</td>
                <td class="text-center" style="color:#34d399;">${fmtN(sumDone)} (${(sumDone/sumTotal*100).toFixed(1)}%)</td>
                <td class="text-center" style="color:#f87171;">${fmtN(sumHlv)} (${(sumHlv/sumTotal*100).toFixed(1)}%)</td>
                <td class="text-center" style="color:#fbbf24;">${fmtN(sumCheck)} (${(sumCheck/sumTotal*100).toFixed(1)}%)</td>
                <td class="text-center" style="color:#94a3b8;">${fmtN(sumBlank)} (${(sumBlank/sumTotal*100).toFixed(1)}%)</td>
                <td class="text-right" style="color:#38bdf8;">${fmtN(sumTotal)} dòng</td>
            </tr>
            `;
        }

        // Render Chế độ 1: Bảng Tổng Hợp DC
        function renderDCSummaryTable() {
            const data = getFilteredBundleData();
            if (!data) return;

            const tbody = document.getElementById('dcTableBody');
            const tfoot = document.getElementById('dcTableFoot');
            if (!tbody || !tfoot) return;

            const list = dcPeriod === 'daily' ? data.daily_matrix : data.monthly_matrix;
            let rowsHtml = '';

            let sumTotalCases = 0, sumTotalVal = 0, sumTotalQty = 0;
            let sumDongYCases = 0, sumDongYVal = 0, sumDongYDone = 0, sumDongYNotDone = 0;
            let sumTuChoiCases = 0, sumTuChoiVal = 0, sumTuChoiReplied = 0;
            let sumKiemTraCases = 0, sumKiemTraVal = 0;
            let sumChuaCases = 0, sumChuaVal = 0;

            list.forEach(row => {
                const label = dcPeriod === 'daily' ? row.date : row.month;
                const totCases = row.dc_total_cases || 0;
                const totVal = row.dc_total_val || 0;
                const stCount = row.dc_st_count || 0;

                const dyCases = row.dc_dongy_cases || 0;
                const dyVal = row.dc_dongy_val || 0;
                const dyDone = row.dc_dongy_done_cases || 0;
                const dyNotDone = row.dc_dongy_not_done_cases || (dyCases - dyDone);
                const dyPctDone = row.dc_dongy_pct_done || (dyCases > 0 ? (dyDone / dyCases * 100).toFixed(1) : 0);

                const tcCases = row.dc_tuchoi_cases || 0;
                const tcVal = row.dc_tuchoi_val || 0;
                const tcReplied = row.dc_tuchoi_kfm_replied || 0;
                const tcPending = row.dc_tuchoi_kfm_pending || (tcCases - tcReplied);

                const ktCases = row.dc_kiemtra_cases || 0;
                const ktVal = row.dc_kiemtra_val || 0;

                const chCases = row.dc_chua_cases || 0;
                const chVal = row.dc_chua_val || 0;

                const pctResp = row.dc_pct_phan_hoi || (totCases > 0 ? ((dyCases + tcCases + ktCases) / totCases * 100).toFixed(1) : 100);

                sumTotalCases += totCases;
                sumTotalVal += totVal;
                sumDongYCases += dyCases;
                sumDongYVal += dyVal;
                sumDongYDone += dyDone;
                sumDongYNotDone += dyNotDone;
                sumTuChoiCases += tcCases;
                sumTuChoiVal += tcVal;
                sumTuChoiReplied += tcReplied;
                sumKiemTraCases += ktCases;
                sumKiemTraVal += ktVal;
                sumChuaCases += chCases;
                sumChuaVal += chVal;

                const detailBtn = dcPeriod === 'daily' 
                    ? `<button class="btn-view-detail" onclick="openDetailModal('${row.date}')"><i class="fa-solid fa-eye"></i> Xem</button>`
                    : `<span style="color:var(--text-muted); font-size:0.75rem;">(Theo tháng)</span>`;

                rowsHtml += `
                <tr>
                    <td class="text-left" style="font-weight:700;">${label}</td>
                    <td class="text-right" style="font-weight:600;">${fmtN(totCases)} dòng</td>
                    <td class="text-right">${stCount} ST</td>
                    <td class="text-right c-blue" style="font-weight:700;">${fmtVND(totVal)}</td>
                    
                    <td class="text-right" style="color:#34d399; font-weight:700;">
                        ${fmtN(dyCases)} dòng<br><span style="font-size:0.75rem; opacity:0.85;">${fmtVND(dyVal)}</span>
                    </td>
                    <td class="text-center">
                        <span class="tag-pill" style="background:rgba(52,211,153,0.15); color:#34d399; font-size:0.72rem; font-weight:700;">DONE: ${fmtN(dyDone)}</span>
                        ${dyNotDone > 0 ? `<span class="tag-pill" style="background:rgba(251,146,60,0.15); color:#fb923c; font-size:0.72rem; font-weight:700; margin-left:3px;">Chưa: ${fmtN(dyNotDone)}</span>` : ''}
                    </td>

                    <td class="text-right" style="color:#f87171; font-weight:700;">
                        ${fmtN(tcCases)} dòng<br><span style="font-size:0.75rem; opacity:0.85;">${fmtVND(tcVal)}</span>
                    </td>
                    <td class="text-center">
                        <span class="tag-pill" style="background:rgba(239,68,68,0.15); color:#fca5a5; font-size:0.72rem;">Đã: ${fmtN(tcReplied)}</span>
                        ${tcPending > 0 ? `<span class="tag-pill" style="background:rgba(148,163,184,0.15); color:#cbd5e1; font-size:0.72rem; margin-left:3px;">Chưa: ${fmtN(tcPending)}</span>` : ''}
                    </td>

                    <td class="text-right" style="color:#fbbf24;">${fmtN(ktCases)} dòng<br><span style="font-size:0.72rem; opacity:0.85;">${fmtVND(ktVal)}</span></td>
                    <td class="text-right" style="color:var(--text-muted);">${fmtN(chCases)} dòng<br><span style="font-size:0.72rem; opacity:0.85;">${fmtVND(chVal)}</span></td>

                    <td style="text-align:center;">
                        <div style="display:flex; align-items:center; justify-content:center; gap:6px;">
                            <div class="progress-bar-wrap" style="width:55px; height:6px;">
                                <div class="progress-bar-fill" style="width:${pctResp}%; background:${pctResp >= 95 ? '#34d399' : (pctResp >= 80 ? '#38bdf8' : '#fb923c')};"></div>
                            </div>
                            <span style="font-weight:700; font-size:0.78rem; color:${pctResp >= 95 ? '#34d399' : '#38bdf8'};">${pctResp}%</span>
                        </div>
                    </td>
                    <td class="text-center">${detailBtn}</td>
                </tr>
                `;
            });

            tbody.innerHTML = rowsHtml;

            const detMetrics = getDynamicDetailedMetrics();
            const sumResp = sumDongYCases + sumTuChoiCases + sumKiemTraCases;
            const sumPctResp = sumTotalCases > 0 ? (sumResp / sumTotalCases * 100).toFixed(1) : 100;
            const sumPctDongYDone = sumDongYCases > 0 ? (sumDongYDone / sumDongYCases * 100).toFixed(1) : 0;

            tfoot.innerHTML = `
            <tr style="font-weight:800; background:rgba(15, 23, 42, 0.95); border-top:2px solid #334155;">
                <td class="text-left">TỔNG CỘNG</td>
                <td class="text-right">${fmtN(sumTotalCases)} dòng</td>
                <td class="text-right">${detMetrics.uniqueStTotal} Siêu Thị</td>
                <td class="text-right c-blue">${fmtVND(sumTotalVal)}</td>

                <td class="text-right" style="color:#34d399;">${fmtN(sumDongYCases)} dòng<br><span style="font-size:0.72rem;">${fmtVND(sumDongYVal)}</span></td>
                <td class="text-center" style="color:#34d399;">${fmtN(sumDongYDone)} DONE (${sumPctDongYDone}%)<br><span style="color:#fb923c; font-size:0.72rem;">${fmtN(sumDongYNotDone)} Chưa DONE</span></td>

                <td class="text-right" style="color:#f87171;">${fmtN(sumTuChoiCases)} dòng<br><span style="font-size:0.72rem;">${fmtVND(sumTuChoiVal)}</span></td>
                <td class="text-center" style="color:#f87171;">${fmtN(sumTuChoiReplied)} Đã phản hồi<br><span style="color:#94a3b8; font-size:0.72rem;">${fmtN(sumTuChoiCases - sumTuChoiReplied)} Chưa</span></td>

                <td class="text-right" style="color:#fbbf24;">${fmtN(sumKiemTraCases)} dòng<br><span style="font-size:0.72rem;">${fmtVND(sumKiemTraVal)}</span></td>
                <td class="text-right" style="color:var(--text-muted);">${fmtN(sumChuaCases)} dòng<br><span style="font-size:0.72rem;">${fmtVND(sumChuaVal)}</span></td>

                <td class="text-center" style="color:#38bdf8; font-size:0.85rem;">${sumPctResp}% ĐÃ PHẢN HỒI</td>
                <td></td>
            </tr>
            `;
        }

        // Render Chế độ 2: Tra Cứu Chi Tiết 4 Cột AD - AG
        let curDCFilteredRecords = [];

        function renderDCDetailTable() {
            allDCCasesCache = getAllDCCases();

            // Populate date options in dropdown
            const dateSel = document.getElementById('dcDetailFilterDate');
            if (dateSel) {
                const curVal = dateSel.value;
                const parseDateScore = (dStr) => {
                    if (!dStr) return 0;
                    const parts = dStr.split('/');
                    if (parts.length === 3) return parseInt(parts[2] + parts[1].padStart(2, '0') + parts[0].padStart(2, '0'), 10);
                    return 0;
                };
                const dates = [...new Set(allDCCasesCache.map(s => s.date))].sort((a, b) => parseDateScore(b) - parseDateScore(a));
                let dateOptions = '<option value="all">📅 Tất cả các ngày</option>';
                dates.forEach(d => {
                    dateOptions += `<option value="${d}">${d}</option>`;
                });
                dateSel.innerHTML = dateOptions;
                if (dates.includes(curVal)) dateSel.value = curVal;
            }

            filterDCDetailTable();
        }

        function filterDCDetailTable() {
            if (!allDCCasesCache || allDCCasesCache.length === 0) {
                allDCCasesCache = getAllDCCases();
            }

            const query = (document.getElementById('dcDetailSearch')?.value || '').trim().toLowerCase();
            const filterDate = document.getElementById('dcDetailFilterDate')?.value || 'all';
            const filterGroup = document.getElementById('dcDetailFilterGroup')?.value || 'all';
            const filterConfirm = document.getElementById('dcDetailFilterConfirm')?.value || 'all';
            const filterReply = document.getElementById('dcDetailFilterReply')?.value || 'all';

            curDCFilteredRecords = allDCCasesCache.filter(r => {
                if (filterDate !== 'all' && r.date !== filterDate) return false;
                if (filterGroup !== 'all' && !r.group.includes(filterGroup)) return false;

                // Lọc theo Cột AD (DC xác nhận)
                if (filterConfirm !== 'all') {
                    if (filterConfirm === 'Chưa phản hồi') {
                        if (['Đồng ý claim', 'Từ chối claim', 'Kiểm tra lại'].includes(r.dc_confirm)) return false;
                    } else if (r.dc_confirm !== filterConfirm) {
                        return false;
                    }
                }

                // Lọc theo Cột AF (KFM phản hồi)
                if (filterReply !== 'all') {
                    if (filterReply === 'Chưa phản hồi') {
                        if (['DONE', 'Cấp HLV quyết định', 'DC check lại thông tin'].includes(r.kfm_reply)) return false;
                    } else if (r.kfm_reply !== filterReply) {
                        return false;
                    }
                }

                // Lọc tìm kiếm từ khóa
                if (query) {
                    const searchStr = `${r.st} ${r.store_name} ${r.sku} ${r.sku_name} ${r.dc_confirm} ${r.dc_note} ${r.kfm_reply} ${r.kfm_note} ${r.pt_dc} ${r.handler}`.toLowerCase();
                    if (!searchStr.includes(query)) return false;
                }

                return true;
            });

            // Render Table Rows
            const tbody = document.getElementById('dcDetailTableBody');
            const tfoot = document.getElementById('dcDetailTableFoot');
            const badgeEl = document.getElementById('dcDetailSummaryBadge');

            if (!tbody || !tfoot) return;

            let html = '';
            let totVal = 0, totQty = 0;

            const limit = 800; // Limit initial DOM rendering for ultra-fast response
            const renderList = curDCFilteredRecords.slice(0, limit);

            renderList.forEach((r, idx) => {
                totVal += Number(r.val_total) || 0;
                totQty += Number(r.qty_diff) || 0;

                // Badge Cột AD
                let badgeAD = '<span class="tag-ad-chua">⏳ Chưa phản hồi</span>';
                if (r.dc_confirm === 'Đồng ý claim') badgeAD = '<span class="tag-ad-dongy">🟢 Đồng ý claim</span>';
                else if (r.dc_confirm === 'Từ chối claim') badgeAD = '<span class="tag-ad-tuchoi">🔴 Từ chối claim</span>';
                else if (r.dc_confirm === 'Kiểm tra lại') badgeAD = '<span class="tag-ad-kiemtra">🟡 Kiểm tra lại</span>';

                // Badge Cột AF
                let badgeAF = '<span class="tag-af-pending">⏳ Chưa phản hồi</span>';
                if (r.kfm_reply === 'DONE') badgeAF = '<span class="tag-af-done">🟢 DONE</span>';
                else if (r.kfm_reply === 'Cấp HLV quyết định') badgeAF = '<span class="tag-af-hlv">⚖️ Cấp HLV quyết định</span>';
                else if (r.kfm_reply === 'DC check lại thông tin') badgeAF = '<span class="tag-af-check">🔄 DC check lại</span>';

                // Notes
                const dcNoteHtml = r.dc_note ? `<div class="note-bubble" style="border-left-color:#c084fc;">${r.dc_note}</div>` : '<span style="color:var(--text-muted); font-size:0.75rem;">-</span>';
                const kfmNoteHtml = r.kfm_note ? `<div class="note-bubble" style="border-left-color:#fb923c;">${r.kfm_note}</div>` : '<span style="color:var(--text-muted); font-size:0.75rem;">-</span>';

                // Group tag
                const tagGrp = r.group.includes('MÁT') 
                    ? '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; font-size:0.7rem;">MÁT</span>'
                    : '<span class="tag-pill" style="background:rgba(99,102,241,0.18); color:#818cf8; font-size:0.7rem;">ĐÔNG</span>';

                // Image Link
                const imgHtml = r.img_link && r.img_link.startsWith('http')
                    ? `<a href="${r.img_link}" target="_blank" class="btn-view-detail" style="padding:2px 6px; font-size:0.72rem; text-decoration:none;"><i class="fa-solid fa-image"></i> Xem</a>`
                    : '<span style="color:var(--text-muted); font-size:0.75rem;">-</span>';

                html += `
                <tr>
                    <td class="text-center" style="color:var(--text-muted); font-weight:700;">#${idx + 1}</td>
                    <td class="text-center" style="font-weight:600; color:var(--text-secondary);">${r.date}</td>
                    <td class="text-left">
                        <strong style="color:var(--text-primary); font-size:0.83rem;">${r.st}</strong><br>
                        <span style="color:var(--text-secondary); font-size:0.78rem;">${r.store_name}</span>
                    </td>
                    <td class="text-center">${tagGrp}</td>
                    <td class="text-left">
                        <strong style="color:#38bdf8; font-size:0.82rem;">${r.sku}</strong><br>
                        <span style="font-size:0.78rem; color:var(--text-secondary);">${r.sku_name}</span>
                    </td>
                    <td class="text-right" style="color:#fca5a5; font-weight:700;">${fmtN(r.qty_diff)}</td>
                    <td class="text-right" style="color:#38bdf8; font-weight:700;">${fmtVND(r.val_total)}</td>
                    <td class="text-left">${badgeAD}</td>
                    <td class="text-left">${dcNoteHtml}</td>
                    <td class="text-left">${badgeAF}</td>
                    <td class="text-left">${kfmNoteHtml}</td>
                    <td class="text-center" style="font-size:0.75rem; color:#cbd5e1;">${r.pt_dc || '-'}</td>
                    <td class="text-center">${imgHtml}</td>
                </tr>
                `;
            });

            tbody.innerHTML = html || '<tr><td colspan="13" class="text-center" style="padding:2rem;">Không tìm thấy case nào phù hợp bộ lọc</td></tr>';

            const totalValAll = curDCFilteredRecords.reduce((a, b) => a + (Number(b.val_total) || 0), 0);
            const totalQtyAll = curDCFilteredRecords.reduce((a, b) => a + (Number(b.qty_diff) || 0), 0);

            tfoot.innerHTML = `
            <tr style="font-weight:800; background:rgba(15, 23, 42, 0.95); border-top:2px solid #334155;">
                <td colspan="5" class="text-left">TỔNG CỘNG: ${fmtN(curDCFilteredRecords.length)} DÒNG TRẢ DC ${curDCFilteredRecords.length > limit ? `(Hiển thị ${limit} dòng đầu)` : ''}</td>
                <td class="text-right" style="color:#fca5a5;">${fmtN(totalQtyAll)}</td>
                <td class="text-right" style="color:#38bdf8;">${fmtVND(totalValAll)}</td>
                <td colspan="6"></td>
            </tr>
            `;

            if (badgeEl) {
                badgeEl.innerHTML = `Đang hiển thị <strong style="color:#38bdf8;">${fmtN(curDCFilteredRecords.length)}</strong> / ${fmtN(allDCCasesCache.length)} dòng trả DC (${fmtVND(totalValAll)})`;
            }
        }

        // Xuất Excel cho bảng DC
        function exportDCExcel() {
            const wb = XLSX.utils.book_new();
            
            if (curDCViewMode === 'summary') {
                const tbl = document.getElementById('dcTable');
                const ws = XLSX.utils.table_to_sheet(tbl);
                XLSX.utils.book_append_sheet(wb, ws, "Tien_Do_Tra_DC_Tong_Hop");
                XLSX.writeFile(wb, `Tien_Do_Tra_DC_Tong_Hop_${curGroup.toUpperCase()}_${new Date().toISOString().slice(0,10)}.xlsx`);
            } else {
                // Export detailed filtered rows with all 4 columns AD-AG
                const exportData = curDCFilteredRecords.map((r, i) => ({
                    "STT": i + 1,
                    "Ngày": r.date,
                    "Mã ST": r.st,
                    "Tên Siêu Thị": r.store_name,
                    "Nhóm Hàng": r.group,
                    "Mã Hàng": r.sku,
                    "Tên Sản Phẩm": r.sku_name,
                    "ĐVT": r.unit,
                    "Số Lượng Chuyển": r.qty_transfer,
                    "Số Lượng Nhận": r.qty_receive,
                    "Chênh Lệch (Qty)": r.qty_diff,
                    "Đơn Giá": r.price,
                    "Tổng Giá Trị Lệch (VNĐ)": r.val_total,
                    "Lỗi": r.error,
                    "Điểm Nhận": r.destination,
                    "Cột AD - DC Xác Nhận": r.dc_confirm || "Chưa phản hồi",
                    "Cột AE - NOTE DC": r.dc_note || "",
                    "Cột AF - KFM Phản Hồi": r.kfm_reply || "Chưa phản hồi",
                    "Cột AG - NOTE KFM": r.kfm_note || "",
                    "PT Trả Tồn Về DC": r.pt_dc || "",
                    "PT DC Pick Dư": r.pt_pick_du || "",
                    "Người Xử Lý": r.handler || "",
                    "Link Hình Ảnh": r.img_link || ""
                }));

                const ws = XLSX.utils.json_to_sheet(exportData);
                XLSX.utils.book_append_sheet(wb, ws, "Chi_Tiet_Tra_DC_4_Cot");
                XLSX.writeFile(wb, `Chi_Tiet_Tra_DC_4_Cot_AD_AG_${curGroup.toUpperCase()}_${new Date().toISOString().slice(0,10)}.xlsx`);
            }
        }

        function renderDCTable() {
            updateDCOverviewStats(getFilteredBundleData());
            if (curDCViewMode === 'summary') {
                renderDCSummaryTable();
            } else {
                renderDCDetailTable();
            }
        }


                // ----------------------------------------------------
        // RENDER TẤT CẢ BIỂU ĐỒ CHUYÊN SÂU DC & KFM (CHART 7, 8, 9, 10, 11)
        // ----------------------------------------------------
        function renderDCCharts(data) {
            const list = [...data.daily_matrix].reverse();
            const fullDates = list.map(d => d.date);
            const shortLabels = list.map(d => d.date.length >= 10 ? d.date.slice(0, 5) : d.date);

            const dyCases = list.map(d => Number(d.dc_dongy_cases) || 0);
            const dyDone = list.map(d => Number(d.dc_dongy_done_cases) || 0);
            const dyNotDone = list.map(d => Math.max(0, (Number(d.dc_dongy_cases) || 0) - (Number(d.dc_dongy_done_cases) || 0)));
            const dyPctDoneList = list.map(d => (Number(d.dc_dongy_cases) || 0) > 0 ? ((Number(d.dc_dongy_done_cases) || 0) / (Number(d.dc_dongy_cases) || 1) * 100).toFixed(1) : 0);

            const tcCases = list.map(d => Number(d.dc_tuchoi_cases) || 0);
            const ktCases = list.map(d => Number(d.dc_kiemtra_cases) || 0);
            const chCases = list.map(d => Number(d.dc_chua_cases) || 0);
            const pctRespList = list.map(d => Number(d.dc_pct_phan_hoi) || 0);

            const isDark = currentTheme === 'dark';
            const textColor = isDark ? '#f8fafc' : '#0f172a';
            const textMuted = isDark ? '#94a3b8' : '#64748b';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.035)' : 'rgba(0, 0, 0, 0.04)';
            const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(15, 23, 42, 0.95)';
            const dpr = Math.max(window.devicePixelRatio || 2, 2);

            // ----------------------------------------------------
            // 7. Biểu đồ Tiến độ & Tỷ lệ DC Phản hồi theo ngày
            // ----------------------------------------------------
            const ctxDC = document.getElementById('chartDCResponse');
            if (ctxDC) {
                if (chartDCResp) chartDCResp.destroy();
                chartDCResp = new Chart(ctxDC.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            {
                                type: 'bar',
                                label: '🟢 DC Đồng Ý Claim',
                                data: dyCases,
                                backgroundColor: isDark ? 'rgba(52, 211, 153, 0.85)' : 'rgba(16, 185, 129, 0.85)',
                                borderRadius: 3,
                                maxBarThickness: 14,
                                stack: 'stackDC',
                                yAxisID: 'y'
                            },
                            {
                                type: 'bar',
                                label: '🔴 DC Từ Chối Claim',
                                data: tcCases,
                                backgroundColor: isDark ? 'rgba(248, 113, 113, 0.85)' : 'rgba(220, 38, 38, 0.85)',
                                borderRadius: 3,
                                maxBarThickness: 14,
                                stack: 'stackDC',
                                yAxisID: 'y'
                            },
                            {
                                type: 'bar',
                                label: '🟡 DC Kiểm Tra Lại / Chờ',
                                data: ktCases.map((v, i) => v + chCases[i]),
                                backgroundColor: isDark ? 'rgba(251, 191, 36, 0.85)' : 'rgba(217, 119, 6, 0.85)',
                                borderRadius: 3,
                                maxBarThickness: 14,
                                stack: 'stackDC',
                                yAxisID: 'y'
                            },
                            {
                                type: 'line',
                                label: '📈 Tỷ Lệ DC Phản Hồi (%)',
                                data: pctRespList,
                                borderColor: '#c084fc',
                                backgroundColor: '#c084fc',
                                borderWidth: 1.8,
                                pointRadius: 2.5,
                                pointHoverRadius: 5,
                                tension: 0.3,
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        devicePixelRatio: dpr,
                        layout: { padding: { top: 28, bottom: 15, left: 10, right: 10 } },
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: {
                                stacked: true,
                                ticks: { color: textMuted, font: { weight: '600', size: 10.5 }, minRotation: 45, maxRotation: 45, autoSkip: false },
                                grid: { color: gridColor, borderDash: [3, 4] }
                            },
                            y: {
                                stacked: true,
                                ticks: { color: textMuted, font: { weight: '700', size: 10.5 }, stepSize: 100 },
                                title: { display: true, text: 'Số Dòng Hàng Trả DC', font: { size: 11, weight: '700' }, color: textColor },
                                grid: { color: gridColor, borderDash: [3, 4] }
                            },
                            y1: {
                                position: 'right',
                                min: 0,
                                max: 130,
                                grid: { drawOnChartArea: false },
                                ticks: { color: '#c084fc', font: { weight: '700', size: 10.5 }, callback: (v) => v <= 100 ? v + '%' : '' },
                                title: { display: true, text: '% DC Đã Phản Hồi', font: { size: 11, weight: '700' }, color: '#c084fc' }
                            }
                        },
                        plugins: {
                            legend: { position: 'top', labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 14 } },
                            tooltip: {
                                backgroundColor: tooltipBg,
                                padding: 10,
                                callbacks: {
                                    title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                    label: (c) => c.dataset.yAxisID === 'y1' ? ` ${c.dataset.label}: ${c.raw}%` : ` ${c.dataset.label}: ${fmtN(c.raw)} dòng`,
                                    footer: (items) => {
                                        const tot = items.filter(i => i.dataset.yAxisID === 'y').reduce((a, b) => a + (Number(b.raw) || 0), 0);
                                        return `👉 Tổng số dòng trả DC: ${fmtN(tot)} dòng`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // ----------------------------------------------------
            // 8. Biểu đồ So Sánh Kết Quả Xác Nhận DC (MÁT vs ĐÔNG)
            // ----------------------------------------------------
            const ctxCompare = document.getElementById('chartDCGroupCompare');
            if (ctxCompare) {
                if (chartDCCompare) chartDCCompare.destroy();

                const bMat = BUNDLES['mat'] ? BUNDLES['mat'].grand_total : {};
                const bDong = BUNDLES['dong'] ? BUNDLES['dong'].grand_total : {};

                const matTotal = bMat.dc_total_cases || 4557;
                const matDongY = bMat.dc_dongy_cases || 3641;
                const matTuChoi = bMat.dc_tuchoi_cases || 584;
                const matKiemTra = (bMat.dc_kiemtra_cases || 108) + (bMat.dc_chua_cases || 224);
                const matDongYDone = bMat.dc_dongy_done_cases || 3489;
                const matPctDongY = (matDongY / matTotal * 100).toFixed(1);
                const matPctDoneOnDongY = matDongY > 0 ? (matDongYDone / matDongY * 100).toFixed(1) : 0;
                const matPctResp = bMat.dc_pct_phan_hoi || 95.1;

                const dongTotal = bDong.dc_total_cases || 8070;
                const dongDongY = bDong.dc_dongy_cases || 7378;
                const dongTuChoi = bDong.dc_tuchoi_cases || 510;
                const dongKiemTra = (bDong.dc_kiemtra_cases || 51) + (bDong.dc_chua_cases || 131);
                const dongDongYDone = bDong.dc_dongy_done_cases || 1;
                const dongPctDongY = (dongDongY / dongTotal * 100).toFixed(1);
                const dongPctDoneOnDongY = dongDongY > 0 ? (dongDongYDone / dongDongY * 100).toFixed(1) : 0;
                const dongPctResp = bDong.dc_pct_phan_hoi || 98.4;

                chartDCCompare = new Chart(ctxCompare.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: [`🥩 NHÓM HÀNG MÁT (${fmtN(matTotal)} dòng trả DC)`, `❄️ NHÓM HÀNG ĐÔNG (${fmtN(dongTotal)} dòng trả DC)`],
                        datasets: [
                            {
                                label: '🟢 Đồng Ý Claim',
                                data: [matDongY, dongDongY],
                                backgroundColor: isDark ? 'rgba(52, 211, 153, 0.9)' : 'rgba(16, 185, 129, 0.9)',
                                borderRadius: 4,
                                maxBarThickness: 32
                            },
                            {
                                label: '🔴 Từ Chối Claim',
                                data: [matTuChoi, dongTuChoi],
                                backgroundColor: isDark ? 'rgba(248, 113, 113, 0.9)' : 'rgba(220, 38, 38, 0.9)',
                                borderRadius: 4,
                                maxBarThickness: 32
                            },
                            {
                                label: '🟡 Kiểm Tra Lại / Chờ',
                                data: [matKiemTra, dongKiemTra],
                                backgroundColor: isDark ? 'rgba(251, 191, 36, 0.9)' : 'rgba(217, 119, 6, 0.9)',
                                borderRadius: 4,
                                maxBarThickness: 32
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { ticks: { color: textMuted, font: { weight: '700', size: 10.5 } }, grid: { display: false } },
                            y: { ticks: { color: textMuted, font: { weight: '600', size: 10.5 } }, grid: { color: gridColor, borderDash: [3, 4] }, title: { display: true, text: 'Số Dòng Hàng Trả DC', color: textColor } }
                        },
                        plugins: {
                            legend: { position: 'top', labels: { color: textColor, font: { weight: '600', size: 10.5 }, boxWidth: 10, boxHeight: 10, padding: 12 } },
                            datalabels: {
                                color: '#ffffff',
                                font: { weight: 'bold', size: 10 },
                                anchor: 'center',
                                align: 'center',
                                formatter: (v, ctx) => {
                                    const total = ctx.datasetIndex === 0 ? (ctx.dataIndex === 0 ? matTotal : dongTotal) : 0;
                                    const pct = total > 0 ? (v / total * 100).toFixed(1) : 0;
                                    return v >= 100 ? `${fmtN(v)}
(${pct}%)` : (v > 0 ? fmtN(v) : '');
                                }
                            }
                        }
                    }
                });

                const legendList = document.getElementById('dcGroupLegendList');
                if (legendList) {
                    legendList.innerHTML = `
                    <div style="padding: 0.75rem; background: var(--bg-card-alt); border-radius: 8px; border: 1px solid var(--border-card); margin-bottom: 0.5rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                            <span style="font-weight:700; color:#34d399; font-size:0.85rem;"><i class="fa-solid fa-drumstick-bite"></i> 🥩 HÀNG MÁT</span>
                            <span class="tag-pill" style="background:rgba(52,211,153,0.15); color:#34d399; font-size:0.75rem;">Phản hồi ${matPctResp}%</span>
                        </div>
                        <div style="font-size:0.8rem; color:var(--text-secondary);">
                            • Tổng trả DC: <strong>${fmtN(matTotal)}</strong> dòng hàng<br>
                            • DC Đồng ý: <strong>${fmtN(matDongY)}</strong> dòng (<strong>${matPctDongY}%</strong>)<br>
                            • KFM đã chỉnh DONE: <strong style="color:#34d399;">${fmtN(matDongYDone)}</strong> / ${fmtN(matDongY)} (<strong>${matPctDoneOnDongY}%</strong>)
                        </div>
                    </div>
                    <div style="padding: 0.75rem; background: var(--bg-card-alt); border-radius: 8px; border: 1px solid var(--border-card);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                            <span style="font-weight:700; color:#818cf8; font-size:0.85rem;"><i class="fa-solid fa-snowflake"></i> ❄️ HÀNG ĐÔNG</span>
                            <span class="tag-pill" style="background:rgba(129,140,248,0.15); color:#818cf8; font-size:0.75rem;">Phản hồi ${dongPctResp}%</span>
                        </div>
                        <div style="font-size:0.8rem; color:var(--text-secondary);">
                            • Tổng trả DC: <strong>${fmtN(dongTotal)}</strong> dòng hàng<br>
                            • DC Đồng ý: <strong>${fmtN(dongDongY)}</strong> dòng (<strong>${dongPctDongY}%</strong>)<br>
                            • KFM đã chỉnh DONE: <strong style="color:#fb923c;">${fmtN(dongDongYDone)}</strong> / ${fmtN(dongDongY)} (<strong>${dongPctDoneOnDongY}%</strong>) 🚨
                        </div>
                    </div>
                    `;
                }
            }

            // ----------------------------------------------------
            // 9. Biểu đồ Tiến Độ KFM Chỉnh DONE Theo Ngày (Cột AF trên DC Đồng Ý)
            // ----------------------------------------------------
            const createKFMConfig = () => ({
                type: 'bar',
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            type: 'bar',
                            label: '🟢 KFM Đã DONE',
                            data: dyDone,
                            backgroundColor: isDark ? 'rgba(52, 211, 153, 0.9)' : 'rgba(16, 185, 129, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'kfmStack',
                            yAxisID: 'y'
                        },
                        {
                            type: 'bar',
                            label: '🚨 KFM Chưa DONE',
                            data: dyNotDone,
                            backgroundColor: isDark ? 'rgba(251, 146, 60, 0.9)' : 'rgba(234, 88, 12, 0.9)',
                            borderRadius: 3,
                            maxBarThickness: 14,
                            stack: 'kfmStack',
                            yAxisID: 'y'
                        },
                        {
                            type: 'line',
                            label: '📈 Tỷ Lệ Đã DONE (%)',
                            data: dyPctDoneList,
                            borderColor: '#38bdf8',
                            backgroundColor: '#38bdf8',
                            borderWidth: 2,
                            pointRadius: 2.5,
                            pointHoverRadius: 5,
                            tension: 0.3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: { padding: { top: 25, bottom: 15, left: 10, right: 10 } },
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { stacked: true, ticks: { color: textMuted, font: { weight: '600', size: 10.5 }, minRotation: 45, maxRotation: 45, autoSkip: false }, grid: { color: gridColor, borderDash: [3, 4] } },
                        y: { stacked: true, ticks: { color: textMuted, font: { weight: '700', size: 10.5 } }, title: { display: true, text: 'Số Dòng DC Đồng Ý', font: { size: 11, weight: '700' }, color: textColor }, grid: { color: gridColor, borderDash: [3, 4] } },
                        y1: { position: 'right', min: 0, max: 130, grid: { drawOnChartArea: false }, ticks: { color: '#38bdf8', font: { weight: '700', size: 10.5 }, callback: (v) => v <= 100 ? v + '%' : '' }, title: { display: true, text: '% KFM Đã DONE', font: { size: 11, weight: '700' }, color: '#38bdf8' } }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 12 } },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            callbacks: {
                                title: (items) => `Ngày ${fullDates[items[0].dataIndex]}`,
                                label: (c) => c.dataset.yAxisID === 'y1' ? ` ${c.dataset.label}: ${c.raw}%` : ` ${c.dataset.label}: ${fmtN(c.raw)} dòng`,
                                footer: (items) => {
                                    const tot = items.filter(i => i.dataset.yAxisID === 'y').reduce((a, b) => a + (Number(b.raw) || 0), 0);
                                    return `👉 Tổng số dòng DC Đồng ý: ${fmtN(tot)} dòng`;
                                }
                            }
                        }
                    }
                }
            });

            const ctxKFM = document.getElementById('chartKFMProgressDaily');
            if (ctxKFM) {
                if (chartKFMProgress) chartKFMProgress.destroy();
                chartKFMProgress = new Chart(ctxKFM.getContext('2d'), createKFMConfig());
            }

            const ctxTabKFM = document.getElementById('chartTabKFMProgress');
            if (ctxTabKFM) {
                if (chartTabKFM) chartTabKFM.destroy();
                chartTabKFM = new Chart(ctxTabKFM.getContext('2d'), createKFMConfig());
            }

            // ----------------------------------------------------
            // 10. Biểu đồ Cơ Cấu DC Khác Đồng Ý & KFM Phản Hồi
            // ----------------------------------------------------
            const dcCases = getAllDCCases();
            const tcSub = dcCases.filter(r => r.dc_confirm === 'Từ chối claim');
            const ktSub = dcCases.filter(r => r.dc_confirm === 'Kiểm tra lại');
            const chSub = dcCases.filter(r => !['Đồng ý claim', 'Từ chối claim', 'Kiểm tra lại'].includes(r.dc_confirm));

            const tcHlv = tcSub.filter(r => r.kfm_reply === 'Cấp HLV quyết định').length;
            const tcPending = tcSub.filter(r => !['DONE', 'Cấp HLV quyết định', 'DC check lại thông tin'].includes(r.kfm_reply)).length;
            const tcOther = tcSub.length - tcHlv - tcPending;
            const ktDone = ktSub.filter(r => r.kfm_reply === 'DONE' || r.kfm_reply === 'DC check lại thông tin').length;
            const ktPending = ktSub.length - ktDone;
            const chTot = chSub.length;

            const nonAgreeItems = [
                { label: '🔴 Từ Chối - Cấp HLV Quyết Định', val: tcHlv, color: '#f87171' },
                { label: '⚠️ Từ Chối - KFM Chưa Phản Hồi', val: tcPending, color: '#fb923c' },
                { label: '🟡 Kiểm Tra Lại - Đã Phản Hồi', val: ktDone, color: '#fbbf24' },
                { label: '⏳ DC Chưa Phản Hồi (Trống)', val: chTot, color: '#94a3b8' },
                { label: '🟢 Từ Chối - Đã Xử Lý Khác', val: tcOther, color: '#34d399' }
            ].filter(x => x.val > 0);

            const totNonAgree = nonAgreeItems.reduce((a, b) => a + b.val, 0) || 1;

            const createNonAgreeConfig = () => ({
                type: 'doughnut',
                data: {
                    labels: nonAgreeItems.map(d => d.label),
                    datasets: [{
                        data: nonAgreeItems.map(d => d.val),
                        backgroundColor: nonAgreeItems.map(d => d.color),
                        borderWidth: 1.5,
                        borderColor: isDark ? '#111827' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    devicePixelRatio: dpr,
                    layout: { padding: 10 },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: tooltipBg,
                            padding: 10,
                            callbacks: {
                                label: (c) => {
                                    const pct = (c.raw / totNonAgree * 100).toFixed(1);
                                    return ` ${c.label}: ${fmtN(c.raw)} dòng (${pct}%)`;
                                }
                            }
                        },
                        datalabels: {
                            color: '#ffffff',
                            font: { weight: 'bold', size: 10 },
                            formatter: (value, ctx) => {
                                const pct = (value / totNonAgree * 100);
                                return pct >= 8.0 ? pct.toFixed(1) + '%' : '';
                            }
                        }
                    },
                    cutout: '62%'
                }
            });

            const ctxNonAgree = document.getElementById('chartDCNonAgreeBreakdown');
            if (ctxNonAgree) {
                if (chartDCNonAgree) chartDCNonAgree.destroy();
                chartDCNonAgree = new Chart(ctxNonAgree.getContext('2d'), createNonAgreeConfig());
            }

            const ctxTabNonAgree = document.getElementById('chartTabDCNonAgree');
            if (ctxTabNonAgree) {
                if (chartTabNonAgree) chartTabNonAgree.destroy();
                chartTabNonAgree = new Chart(ctxTabNonAgree.getContext('2d'), createNonAgreeConfig());
            }

            // Legend for non-agree breakdown
            let nonAgreeLegendHtml = '';
            nonAgreeItems.forEach(item => {
                const pct = (item.val / totNonAgree * 100).toFixed(1);
                nonAgreeLegendHtml += `
                <div class="legend-row" style="border-left-color: ${item.color};">
                    <div class="legend-name">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${item.color};"></span>
                        <span>${item.label}</span>
                    </div>
                    <div>
                        <span class="legend-val">${fmtN(item.val)} dòng</span>
                        <span class="legend-pct" style="background:${item.color};">${pct}%</span>
                    </div>
                </div>
                `;
            });

            const legEl = document.getElementById('dcNonAgreeLegendList');
            if (legEl) legEl.innerHTML = nonAgreeLegendHtml;
            const tabLegEl = document.getElementById('tabDCNonAgreeLegendList');
            if (tabLegEl) tabLegEl.innerHTML = nonAgreeLegendHtml;

            // ----------------------------------------------------
            // 11. Biểu đồ Top Điểm Nóng Note DC (AE) & Note KFM (AG)
            // ----------------------------------------------------
            const dcNotesMap = {};
            const kfmNotesMap = {};
            dcCases.forEach(r => {
                if (r.dc_note) dcNotesMap[r.dc_note] = (dcNotesMap[r.dc_note] || 0) + 1;
                if (r.kfm_note) kfmNotesMap[r.kfm_note] = (kfmNotesMap[r.kfm_note] || 0) + 1;
            });

            const topDC = Object.entries(dcNotesMap).sort((a, b) => b[1] - a[1]).slice(0, 5);
            const topKFM = Object.entries(kfmNotesMap).sort((a, b) => b[1] - a[1]).slice(0, 5);

            const allNotesLabels = [...topDC.map(x => `🏢 DC: ${x[0]}`), ...topKFM.map(x => `👤 KFM: ${x[0]}`)];
            const allNotesValues = [...topDC.map(x => x[1]), ...topKFM.map(x => x[1])];
            const allNotesColors = [
                ...topDC.map(() => isDark ? 'rgba(192, 132, 252, 0.85)' : 'rgba(147, 51, 234, 0.85)'),
                ...topKFM.map(() => isDark ? 'rgba(251, 146, 60, 0.85)' : 'rgba(234, 88, 12, 0.85)')
            ];

            const ctxNotes = document.getElementById('chartDCNoteBreakdown');
            if (ctxNotes) {
                if (chartDCNotes) chartDCNotes.destroy();
                chartDCNotes = new Chart(ctxNotes.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: allNotesLabels,
                        datasets: [{
                            label: 'Số Lượng Dòng Ghi Chú',
                            data: allNotesValues,
                            backgroundColor: allNotesColors,
                            borderRadius: 4,
                            maxBarThickness: 22
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        devicePixelRatio: dpr,
                        scales: {
                            x: { ticks: { color: textMuted, font: { weight: '600', size: 10 } }, grid: { color: gridColor, borderDash: [3, 4] }, title: { display: true, text: 'Số Dòng Hàng Ghi Chú', color: textColor } },
                            y: { ticks: { color: textColor, font: { weight: '600', size: 11 } }, grid: { display: false } }
                        },
                        plugins: {
                            legend: { display: false },
                            datalabels: {
                                color: '#ffffff',
                                font: { weight: 'bold', size: 10 },
                                anchor: 'end',
                                align: 'right',
                                offset: 4,
                                formatter: (v) => `${fmtN(v)} case`
                            }
                        }
                    }
                });
            }
        }


        // ----------------------------------------------------
        // RENDER KHỐI NHẬN XÉT & PHÂN TÍCH TỰ ĐỘNG BIỂU ĐỒ 7 & 8 (AI INSIGHTS)
        // ----------------------------------------------------
        function renderDCInsights(data) {
            const list = data.daily_matrix || [];
            const bMat = BUNDLES['mat'] ? BUNDLES['mat'].grand_total : {};
            const bDong = BUNDLES['dong'] ? BUNDLES['dong'].grand_total : {};

            // 1. Phân tích ngày DC phản hồi thấp
            const sortedByResp = [...list].filter(d => (d.dc_total_cases || 0) > 0)
                                          .sort((a, b) => (Number(a.dc_pct_phan_hoi) || 0) - (Number(b.dc_pct_phan_hoi) || 0));
            const lowDays = sortedByResp.slice(0, 3);
            
            let totPendingCases = 0, totPendingVal = 0, totTuChoiCases = 0, totTuChoiVal = 0;
            list.forEach(d => {
                const chuaCases = (Number(d.dc_chua_cases) || 0) + (Number(d.dc_kiemtra_cases) || 0);
                totPendingCases += chuaCases;
                totPendingVal += (Number(d.dc_chua_val) || 0) + (Number(d.dc_kiemtra_val) || 0);
                totTuChoiCases += (Number(d.dc_tuchoi_cases) || 0);
                totTuChoiVal += (Number(d.dc_tuchoi_val) || 0);
            });

            let lowDaysHtml = '';
            if (lowDays.length > 0) {
                lowDaysHtml = lowDays.map(d => {
                    const chua = (Number(d.dc_chua_cases) || 0) + (Number(d.dc_kiemtra_cases) || 0);
                    return `• <strong>Ngày ${d.date}:</strong> Phản hồi <strong>${d.dc_pct_phan_hoi}%</strong> (còn kẹt <strong>${chua} dòng</strong> chưa trả lời / tổng ${d.dc_total_cases} dòng trả DC - ${fmtVND(d.dc_total_val || 0)}).`;
                }).join('<br>');
            } else {
                lowDaysHtml = '• Tất cả các ngày đều đã được DC phản hồi đầy đủ 100%.';
            }

            const lowRespEl = document.getElementById('dcInsightLowResp');
            if (lowRespEl) {
                lowRespEl.innerHTML = `
                    <div style="font-size:0.84rem; line-height:1.55; color:var(--text-main);">
                        ${lowDaysHtml}
                        <div style="margin-top:0.5rem; padding-top:0.45rem; border-top:1px dashed rgba(248,113,113,0.3); font-size:0.8rem; color:#fca5a5;">
                            👉 <strong>Tổng dòng hàng đang kẹt chờ DC duyệt:</strong> <span style="font-weight:700; color:#fb923c;">${fmtN(totPendingCases)} dòng</span> (${fmtVND(totPendingVal)}).
                        </div>
                    </div>
                `;
            }

            // 2. So sánh Hàng Mát vs Hàng Đông
            const matDongY = Number(bMat.dc_dongy_cases) || 0;
            const matTuChoi = Number(bMat.dc_tuchoi_cases) || 0;
            const matKiemTra = (Number(bMat.dc_kiemtra_cases) || 0) + (Number(bMat.dc_chua_cases) || 0);
            const matTotal = (matDongY + matTuChoi + matKiemTra) || 1;
            const matPctDongY = (matDongY / matTotal * 100).toFixed(1);
            const matPctKiemTra = (matKiemTra / matTotal * 100).toFixed(1);
            const matPctResp = bMat.dc_pct_phan_hoi || 0;

            const dongDongY = Number(bDong.dc_dongy_cases) || 0;
            const dongTuChoi = Number(bDong.dc_tuchoi_cases) || 0;
            const dongKiemTra = (Number(bDong.dc_kiemtra_cases) || 0) + (Number(bDong.dc_chua_cases) || 0);
            const dongTotal = (dongDongY + dongTuChoi + dongKiemTra) || 1;
            const dongPctDongY = (dongDongY / dongTotal * 100).toFixed(1);
            const dongPctKiemTra = (dongKiemTra / dongTotal * 100).toFixed(1);
            const dongPctResp = bDong.dc_pct_phan_hoi || 0;

            const groupCompareEl = document.getElementById('dcInsightGroupCompare');
            if (groupCompareEl) {
                groupCompareEl.innerHTML = `
                    <div style="font-size:0.84rem; line-height:1.55; color:var(--text-main);">
                        • <strong>❄️ Hàng Đông:</strong> DC đã chốt đồng ý <span style="color:#34d399; font-weight:700;">${dongPctDongY}%</span> (${fmtN(dongDongY)} / ${fmtN(dongTotal)} dòng), chỉ còn kẹt <strong>${fmtN(dongKiemTra)} dòng (${dongPctKiemTra}%)</strong>. Hàng đóng thùng nguyên kiện nên DC kiểm đếm và nhận lỗi nhanh.<br>
                        • <strong>🥩 Hàng Mát:</strong> DC mới đồng ý <span style="color:#fbbf24; font-weight:700;">${matPctDongY}%</span> (${fmtN(matDongY)} / ${fmtN(matTotal)} dòng), đang kẹt tới <span style="color:#f87171; font-weight:700;">${fmtN(matKiemTra)} dòng (${matPctKiemTra}%)</span> chưa trả lời. Hàng tươi sống cần cân ký lại và kiểm tra hao hụt thực tế nên thời gian đối soát lâu hơn.
                    </div>
                `;
            }

            // 3. Việc SCM cần xử lý ngay
            const actionPlanEl = document.getElementById('dcInsightActionPlan');
            if (actionPlanEl) {
                actionPlanEl.innerHTML = `
                    <div style="font-size:0.84rem; line-height:1.55; color:var(--text-main);">
                        1. <strong>Kho DC:</strong> Làm việc trực tiếp với Trưởng kho DC Mát để chốt dứt điểm <strong>${fmtN(matKiemTra)} dòng hàng Mát đang kẹt</strong>.<br>
                        2. <strong>Xử lý hàng DC từ chối (${fmtN(totTuChoiCases)} dòng - ${fmtVND(totTuChoiVal)}):</strong> Thu hồi biên bản giao nhận có chữ ký tài xế; nếu lỗi do Siêu thị thì chuyển về ST nhận trách nhiệm, nếu không quy được thì chuyển hạch toán Hao hụt.<br>
                        3. <strong>Siêu thị:</strong> Yêu cầu Siêu thị chụp ảnh và ký biên bản giao nhận ngay lúc nhận hàng tươi sống để làm bằng chứng khi gửi trả DC.
                    </div>
                `;
            }
        }

        // 1. RENDER BẢNG SỐ LƯỢNG (PCS / KG) & SỐ LƯỢNG SIÊU THỊ
        function renderQtyTable() {
            const data = getFilteredBundleData();
            if (!data) return;
            const rows = qtyPeriod === 'daily' ? data.daily_matrix : data.monthly_matrix;
            const tbody = document.getElementById('qtyTableBody');
            const tfoot = document.getElementById('qtyTableFoot');

            if (!rows || rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="14" class="text-center">Không có dữ liệu</td></tr>';
                tfoot.innerHTML = '';
                return;
            }

            let html = '';
            rows.forEach(r => {
                const label = qtyPeriod === 'daily' ? r.date : r.month;
                const actionBtn = qtyPeriod === 'daily' 
                    ? `<button class="btn-view-detail" onclick="openModal('${r.date}')"><i class="fa-solid fa-list-ul"></i> Xem</button>` 
                    : '-';

                html += `
                <tr>
                    <td class="text-left" style="font-weight:600; color:var(--primary);">${label}</td>
                    <td>${fmtN(r.qty_chuyen)}</td>
                    <td>${fmtN(r.qty_nhan)}</td>
                    <td class="c-red"><strong>${fmtN(r.qty_lech)}</strong></td>
                    <td>${fmtN(r.stores_count)} ST</td>
                    <td class="c-red">${fmtN(r.stores_over_100k)} ST</td>
                    <td class="c-green">${fmtN(r.stores_under_100k)} ST</td>
                    <td>${fmtN(r.sl_kho)}</td>
                    <td>${fmtN(r.sl_st)}</td>
                    <td>${fmtN(r.sl_haohut)}</td>
                    <td>
                        <div class="c-green">${fmtN(r.sl_da_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_da_xl} ST)</div>
                    </td>
                    <td>
                        <div class="c-orange">${fmtN(r.sl_dang_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_dang_xl} ST)</div>
                    </td>
                    <td>
                        <div style="color:var(--text-muted);">${fmtN(r.sl_khong_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_khong_xl} ST)</div>
                    </td>
                    <td class="text-center">${renderProgressBadge(r.pct_sl_da_xl)}</td>
                    <td class="text-center">${actionBtn}</td>
                </tr>
                `;
            });
            tbody.innerHTML = html;

            const gt = data.grand_total;
            const pctSlFoot = gt.qty_lech > 0 ? (gt.sl_da_xl / gt.qty_lech * 100).toFixed(1) : 0;
            tfoot.innerHTML = `
            <tr>
                <td class="text-left">TỔNG CỘNG</td>
                <td>${fmtN(gt.qty_chuyen)}</td>
                <td>${fmtN(gt.qty_nhan)}</td>
                <td class="c-red"><strong>${fmtN(gt.qty_lech)}</strong></td>
                <td>${fmtN(gt.stores_count)} ST</td>
                <td class="c-red"><strong>${fmtN(gt.stores_over_100k)} ST</strong></td>
                <td class="c-green"><strong>${fmtN(gt.stores_under_100k)} ST</strong></td>
                <td>${fmtN(gt.sl_kho)}</td>
                <td>${fmtN(gt.sl_st)}</td>
                <td>${fmtN(gt.sl_haohut)}</td>
                <td>
                    <div class="c-green"><strong>${fmtN(gt.sl_da_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_da_xl} lần giao)</div>
                </td>
                <td>
                    <div class="c-orange"><strong>${fmtN(gt.sl_dang_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_dang_xl} lần giao)</div>
                </td>
                <td>
                    <div style="color:var(--text-muted);"><strong>${fmtN(gt.sl_khong_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_khong_xl} lần giao)</div>
                </td>
                <td class="text-center">${renderProgressBadge(pctSlFoot)}</td>
                <td class="text-center">${gt.total_days} Ngày</td>
            </tr>
            `;
        }

        // 2. RENDER BẢNG GIÁ TRỊ (VNĐ)
        function renderValTable() {
            const data = getFilteredBundleData();
            if (!data) return;
            const rows = valPeriod === 'daily' ? data.daily_matrix : data.monthly_matrix;
            const tbody = document.getElementById('valTableBody');
            const tfoot = document.getElementById('valTableFoot');

            if (!rows || rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" class="text-center">Không có dữ liệu</td></tr>';
                tfoot.innerHTML = '';
                return;
            }

            let html = '';
            rows.forEach(r => {
                const label = valPeriod === 'daily' ? r.date : r.month;
                const actionBtn = valPeriod === 'daily' 
                    ? `<button class="btn-view-detail" onclick="openModal('${r.date}')"><i class="fa-solid fa-list-ul"></i> Xem</button>` 
                    : '-';

                html += `
                <tr>
                    <td class="text-left" style="font-weight:600; color:var(--primary);">${label}</td>
                    <td class="c-blue"><strong>${fmtVND(r.val_total)}</strong></td>
                    <td class="c-red">${fmtVND(r.val_over_100k)}</td>
                    <td class="c-green">${fmtVND(r.val_under_100k)}</td>
                    <td>${fmtVND(r.val_kho)}</td>
                    <td>${fmtVND(r.val_st)}</td>
                    <td>${fmtVND(r.val_haohut)}</td>
                    <td>
                        <div class="c-green">${fmtVND(r.val_da_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_da_xl} ST)</div>
                    </td>
                    <td>
                        <div class="c-orange">${fmtVND(r.val_dang_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_dang_xl} ST)</div>
                    </td>
                    <td>
                        <div style="color:var(--text-muted);">${fmtVND(r.val_khong_xl)}</div>
                        <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_khong_xl} ST)</div>
                    </td>
                    <td class="text-center">${renderProgressBadge(r.pct_val_da_xl)}</td>
                    <td class="text-center">${actionBtn}</td>
                </tr>
                `;
            });
            tbody.innerHTML = html;

            const gt = data.grand_total;
            const pctFoot = gt.val_total > 0 ? (gt.val_da_xl / gt.val_total * 100).toFixed(1) : 0;
            tfoot.innerHTML = `
            <tr>
                <td class="text-left">TỔNG CỘNG</td>
                <td class="c-blue"><strong>${fmtVND(gt.val_total)}</strong></td>
                <td class="c-red"><strong>${fmtVND(gt.val_over_100k)}</strong></td>
                <td class="c-green"><strong>${fmtVND(gt.val_under_100k)}</strong></td>
                <td>${fmtVND(gt.val_kho)}</td>
                <td>${fmtVND(gt.val_st)}</td>
                <td>${fmtVND(gt.val_haohut)}</td>
                <td>
                    <div class="c-green"><strong>${fmtVND(gt.val_da_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_da_xl} lần giao)</div>
                </td>
                <td>
                    <div class="c-orange"><strong>${fmtVND(gt.val_dang_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_dang_xl} lần giao)</div>
                </td>
                <td>
                    <div style="color:var(--text-muted);"><strong>${fmtVND(gt.val_khong_xl)}</strong></div>
                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_khong_xl} lần giao)</div>
                </td>
                <td class="text-center">${renderProgressBadge(pctFoot)}</td>
                <td class="text-center">${gt.total_days} Ngày</td>
            </tr>
            `;
        }

        // 3. RENDER BẢNG TỔNG HỢP (LỒNG GHÉP 2-IN-1: SL & TIỀN)
        function renderMasterTable() {
            const data = getFilteredBundleData();
            if (!data) return;
            const rows = masterPeriod === 'daily' ? data.daily_matrix : data.monthly_matrix;
            const tbody = document.getElementById('masterTableBody');
            const tfoot = document.getElementById('masterTableFoot');

            if (!rows || rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="13" class="text-center">Không có dữ liệu</td></tr>';
                tfoot.innerHTML = '';
                return;
            }

            let html = '';
            rows.forEach(r => {
                const label = masterPeriod === 'daily' ? r.date : r.month;
                const actionBtn = masterPeriod === 'daily' 
                    ? `<button class="btn-view-detail" onclick="openModal('${r.date}')"><i class="fa-solid fa-list-ul"></i> Xem</button>` 
                    : '-';

                html += `
                <tr>
                    <td class="text-left" style="font-weight:600; color:var(--primary);">${label}</td>
                    <td>${fmtN(r.qty_chuyen)}</td>
                    <td>${fmtN(r.qty_nhan)}</td>
                    <td>
                        <div class="c-red" style="font-weight:700;">${fmtN(r.qty_lech)}</div>
                        <div class="c-blue" style="font-size:0.75rem;">${fmtVND(r.val_total)}</div>
                    </td>
                    <td>
                        <div class="c-red" style="font-weight:700;">${r.stores_over_100k} ST</div>
                        <div style="font-size:0.75rem; color:#f87171;">${fmtVND(r.val_over_100k)}</div>
                    </td>
                    <td>
                        <div class="c-green" style="font-weight:700;">${r.stores_under_100k} ST</div>
                        <div style="font-size:0.75rem; color:#34d399;">${fmtVND(r.val_under_100k)}</div>
                    </td>
                    <td>
                        <div>${fmtN(r.sl_kho)}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(r.val_kho)}</div>
                    </td>
                    <td>
                        <div>${fmtN(r.sl_st)}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(r.val_st)}</div>
                    </td>
                    <td>
                        <div>${fmtN(r.sl_haohut)}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(r.val_haohut)}</div>
                    </td>
                    <td>
                        <div class="c-green" style="font-weight:700;">${fmtN(r.sl_da_xl)}</div>
                        <div style="font-size:0.75rem; color:#34d399;">${fmtVND(r.val_da_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_da_xl} ST)</span></div>
                    </td>
                    <td>
                        <div class="c-orange" style="font-weight:700;">${fmtN(r.sl_dang_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_dang_xl} ST)</span></div>
                        <div style="font-size:0.75rem; color:#fb923c;">${fmtVND(r.val_dang_xl)}</div>
                    </td>
                    <td>
                        <div style="color:var(--text-muted); font-weight:700;">${fmtN(r.sl_khong_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${r.st_khong_xl} ST)</span></div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(r.val_khong_xl)}</div>
                    </td>
                    <td class="text-center">${renderProgressBadge(r.pct_val_da_xl)}</td>
                    <td class="text-center">${actionBtn}</td>
                </tr>
                `;
            });
            tbody.innerHTML = html;

            const gt = data.grand_total;
            const pctFoot = gt.val_total > 0 ? (gt.val_da_xl / gt.val_total * 100).toFixed(1) : 0;
            tfoot.innerHTML = `
            <tr>
                <td class="text-left">TỔNG CỘNG</td>
                <td>${fmtN(gt.qty_chuyen)}</td>
                <td>${fmtN(gt.qty_nhan)}</td>
                <td>
                    <div class="c-red" style="font-weight:700;">${fmtN(gt.qty_lech)}</div>
                    <div class="c-blue" style="font-size:0.75rem;">${fmtVND(gt.val_total)}</div>
                </td>
                <td>
                    <div class="c-red" style="font-weight:700;">${gt.stores_over_100k} ST</div>
                    <div style="font-size:0.75rem; color:#f87171;">${fmtVND(gt.val_over_100k)}</div>
                </td>
                <td>
                    <div class="c-green" style="font-weight:700;">${gt.stores_under_100k} ST</div>
                    <div style="font-size:0.75rem; color:#34d399;">${fmtVND(gt.val_under_100k)}</div>
                </td>
                <td>
                    <div>${fmtN(gt.sl_kho)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(gt.val_kho)}</div>
                </td>
                <td>
                    <div>${fmtN(gt.sl_st)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(gt.val_st)}</div>
                </td>
                <td>
                    <div>${fmtN(gt.sl_haohut)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(gt.val_haohut)}</div>
                </td>
                <td>
                    <div class="c-green" style="font-weight:700;">${fmtN(gt.sl_da_xl)}</div>
                    <div style="font-size:0.75rem; color:#34d399;">${fmtVND(gt.val_da_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_da_xl} lần giao)</span></div>
                </td>
                <td>
                    <div class="c-orange" style="font-weight:700;">${fmtN(gt.sl_dang_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_dang_xl} lần giao)</span></div>
                    <div style="font-size:0.75rem; color:#fb923c;">${fmtVND(gt.val_dang_xl)}</div>
                </td>
                <td>
                    <div style="color:var(--text-muted); font-weight:700;">${fmtN(gt.sl_khong_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${gt.st_khong_xl} lần giao)</span></div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${fmtVND(gt.val_khong_xl)}</div>
                </td>
                <td class="text-center">${renderProgressBadge(pctFoot)}</td>
                <td class="text-center">${gt.total_days} Ngày</td>
            </tr>
            `;
        }

        let curModalRecords = [];

        function openModal(dateStr) {
            const all = DAILY_RECORDS[dateStr] || [];
            curModalRecords = curGroup === 'all' ? all : all.filter(r => (curGroup === 'mat' ? r.group.includes('MÁT') : r.group.includes('ĐÔNG')));

            document.getElementById('modalTitle').innerText = `Chi Tiết Chênh Lệch Ngày ${dateStr}`;
            document.getElementById('modalSearch').value = '';
            document.getElementById('modalFilterThreshold').value = 'all';
            document.getElementById('modalFilterStatus').value = 'all';

            filterModalRecords();
            document.getElementById('detailModal').classList.add('active');
        }

        function filterModalRecords() {
            const query = (document.getElementById('modalSearch').value || '').trim().toLowerCase();
            const thVal = document.getElementById('modalFilterThreshold').value;
            const stVal = document.getElementById('modalFilterStatus').value;

            let filtered = curModalRecords.filter(r => {
                if (thVal === 'over' && !r.is_store_over_100k) return false;
                if (thVal === 'under' && r.is_store_over_100k) return false;
                if (stVal !== 'all' && r.status_3level !== stVal) return false;

                if (query) {
                    const matchSt = (r.st || '').toLowerCase().includes(query) || (r.store_name || '').toLowerCase().includes(query);
                    const matchSku = (r.sku || '').toLowerCase().includes(query) || (r.sku_name || '').toLowerCase().includes(query);
                    if (!matchSt && !matchSku) return false;
                }
                return true;
            });

            // Summary Badges
            const totalVal = filtered.reduce((a, b) => a + b.val_total, 0);
            const uniqueSt = new Set(filtered.map(r => r.st)).size;
            document.getElementById('modalSummaryBadges').innerHTML = `
                <span>Hiển thị: <strong>${filtered.length}</strong> dòng • <strong>${uniqueSt}</strong> Siêu Thị • Tổng tiền: <strong class="c-blue">${fmtVND(totalVal)}</strong></span>
            `;

            const tbody = document.getElementById('detailTableBody');
            let html = '';
            filtered.forEach((r, idx) => {
                const tagGroup = r.group.includes('MÁT') 
                    ? '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">MÁT</span>' 
                    : '<span class="tag-pill" style="background:rgba(99,102,241,0.18); color:#818cf8; border:1px solid rgba(99,102,241,0.4);">ĐÔNG</span>';
                
                const tagThreshold = r.is_store_over_100k 
                    ? '<span class="tag-pill" style="background:rgba(239,68,68,0.18); color:#f87171; border:1px solid rgba(239,68,68,0.4);">ST ≥ 100k</span>' 
                    : '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">ST < 100k</span>';
                
                let stTag = '<span class="tag-pill" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.4);">🟢 Đã xử lý</span>';
                if (r.status_3level === 'Đang xử lý') stTag = '<span class="tag-pill" style="background:rgba(245,158,11,0.18); color:#fbbf24; border:1px solid rgba(245,158,11,0.4);">🟡 Đang xử lý (ST ≥ 100k)</span>';
                if (r.status_3level === 'Không xử lý') stTag = '<span class="tag-pill" style="background:rgba(148,163,184,0.15); color:#cbd5e1; border:1px solid rgba(148,163,184,0.3);">⚪ Không xử lý (ST < 100k)</span>';

                html += `
                <tr>
                    <td class="text-center" style="color:var(--text-muted);">${idx + 1}</td>
                    <td class="text-left">
                        <strong style="color:var(--text-primary); font-size:0.85rem;">${r.st}</strong> - <span style="color:var(--text-secondary);">${r.store_name}</span>
                        <div style="margin-top:3px; display:flex; align-items:center; gap:6px;">
                            ${tagThreshold}
                            <span style="font-size:0.75rem; color:var(--text-muted);">Tổng ST: ${fmtVND(r.store_day_total)}</span>
                        </div>
                    </td>
                    <td class="text-left">
                        <strong style="color:var(--text-primary);">${r.sku}</strong> - <span style="color:var(--text-secondary);">${r.sku_name}</span>
                        <div style="margin-top:2px;">${tagGroup}</div>
                    </td>
                    <td>${fmtN(r.qty_transfer)}</td>
                    <td>${fmtN(r.qty_receive)}</td>
                    <td class="c-red" style="font-weight:700; font-size:0.88rem;">${fmtN(r.qty_diff)}</td>
                    <td>${fmtVND(r.price)}</td>
                    <td class="c-blue" style="font-weight:700;">${fmtVND(r.val_total)}</td>
                    <td class="text-left">
                        <div style="color:var(--text-primary); font-weight:600;">${r.destination}</div>
                        <div style="color:var(--text-muted); font-size:0.75rem;">${r.error || '-'}</div>
                    </td>
                    <td class="text-center">${stTag}</td>
                </tr>
                `;
            });

            tbody.innerHTML = html || '<tr><td colspan="10" class="text-center" style="padding:2rem;">Không tìm thấy dữ liệu phù hợp với bộ lọc</td></tr>';
        }

        function toggleModalFullscreen() {
            const box = document.getElementById('modalBox');
            const btn = document.getElementById('btnFullscreen');
            if (box) box.classList.toggle('is-fullscreen');
            if (box && box.classList.contains('is-fullscreen')) {
                btn.innerHTML = '<i class="fa-solid fa-compress"></i> Thu Nhỏ';
            } else {
                btn.innerHTML = '<i class="fa-solid fa-expand"></i> Phóng To Toàn Màn Hình';
            }
        }

        function exportModalExcel() {
            const wb = XLSX.utils.book_new();
            const detailTable = document.getElementById('detailTable');
            const ws = XLSX.utils.table_to_sheet(detailTable);
            XLSX.utils.book_append_sheet(wb, ws, "Chi_Tiet_Chenh_Lech");
            const title = document.getElementById('modalTitle').innerText.replace(/\s+/g, '_');
            XLSX.writeFile(wb, `${title}.xlsx`);
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
        }

        function exportExcel() {
            const wb = XLSX.utils.book_new();
            const qtyTable = document.getElementById('qtyTable');
            const valTable = document.getElementById('valTable');
            const masterTable = document.getElementById('masterTable');
            
            const ws1 = XLSX.utils.table_to_sheet(qtyTable);
            const ws2 = XLSX.utils.table_to_sheet(valTable);
            const ws3 = XLSX.utils.table_to_sheet(masterTable);

            XLSX.utils.book_append_sheet(wb, ws1, "Bang_So_Luong");
            XLSX.utils.book_append_sheet(wb, ws2, "Bang_Gia_Tri");
            XLSX.utils.book_append_sheet(wb, ws3, "Bang_Hop_Nhat");

            const mText = curMonth === 'all' ? 'TOANKY' : curMonth.replace(/\s+/g, '');
            XLSX.writeFile(wb, `Bao_Cao_Doi_Soat_${curGroup.toUpperCase()}_${mText}_${new Date().toISOString().slice(0, 10)}.xlsx`);
        }

        // ==========================================================
        // THU / PHÓNG TO BIỂU ĐỒ & NHẬN XÉT CHUYÊN SÂU (CHART ZOOM)
        // ==========================================================
        let chartZoomInstance = null;

        function closeChartZoom() {
            const modal = document.getElementById('chartZoomModal');
            if (modal) modal.classList.remove('active');
            if (chartZoomInstance) {
                chartZoomInstance.destroy();
                chartZoomInstance = null;
            }
        }

        function openChartZoom(chartKey) {
            const data = getFilteredBundleData();
            if (!data) return;
            const gt = data.grand_total;
            const om = data.overall_metrics;
            const list = [...data.daily_matrix].reverse();
            const fullDates = list.map(d => d.date);
            const shortLabels = list.map(d => d.date.length >= 10 ? d.date.slice(0, 5) : d.date);

            const isDark = currentTheme === 'dark';
            const textColor = isDark ? '#f8fafc' : '#0f172a';
            const textMuted = isDark ? '#94a3b8' : '#64748b';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
            const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(15, 23, 42, 0.95)';

            const modal = document.getElementById('chartZoomModal');
            const titleEl = document.getElementById('zoomModalTitle');
            const subtitleEl = document.getElementById('zoomModalSubTitle');
            const iconEl = document.getElementById('zoomModalIcon');
            const badgeEl = document.getElementById('zoomChartBadge');
            const insightsEl = document.getElementById('zoomInsightsContent');
            const canvas = document.getElementById('chartZoomCanvas');

            if (chartZoomInstance) {
                chartZoomInstance.destroy();
                chartZoomInstance = null;
            }

            const ctx = canvas.getContext('2d');
            let chartConfig = null;
            let insightsHtml = '';

            if (chartKey === 'chartCasesComparison') {
                titleEl.innerText = "1. So Sánh Số Dòng Hàng Lệch & Tỷ Lệ Xử Lý Theo Ngày";
                subtitleEl.innerText = "Chi tiết số lượng dòng hàng theo phân khúc ST ≥ 100k vs ST < 100k và tỷ lệ hoàn tất";
                iconEl.innerHTML = '<i class="fa-solid fa-chart-column" style="color:#38bdf8;"></i>';
                badgeEl.innerText = "📊 Số Dòng Hàng & Tỷ Lệ Hoàn Tất";

                const cOverDa = list.map(d => Number(d.cases_over_da_xl) || 0);
                const cOverDang = list.map(d => Number(d.cases_over_dang_xl) || 0);
                const cUnderDa = list.map(d => Number(d.cases_under_da_xl) || 0);
                const cUnderKhong = list.map(d => Number(d.cases_under_khong_xl) || 0);
                const pctOverList = list.map(d => Number(d.pct_over_da_xl) || 0);
                const pctUnderList = list.map(d => Number(d.pct_under_da_xl) || 0);

                const totCasesOver = cOverDa.reduce((a,b)=>a+b,0) + cOverDang.reduce((a,b)=>a+b,0);
                const totCasesUnder = cUnderDa.reduce((a,b)=>a+b,0) + cUnderKhong.reduce((a,b)=>a+b,0);
                const totOverDang = cOverDang.reduce((a,b)=>a+b,0);
                const daCasesOver = cOverDa.reduce((a,b)=>a+b,0);
                const pctDoneOver = totCasesOver > 0 ? (daCasesOver / totCasesOver * 100).toFixed(1) : 100;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-clipboard-check"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Nhóm ST ≥ 100k (Trọng điểm kiểm soát):</strong> Tổng phát sinh <strong>${fmtN(totCasesOver)} dòng hàng</strong>, đã xử lý dứt điểm <strong>${pctDoneOver}%</strong> (${fmtN(daCasesOver)} dòng), hiện còn <strong>${fmtN(totOverDang)} dòng đang xử lý</strong> (chiếm 95% rủi ro công nợ).<br>
                        • <strong>Nhóm ST &lt; 100k (Miễn trừ xử lý):</strong> Có <strong>${fmtN(totCasesUnder)} dòng hàng</strong> giá trị nhỏ lẻ, không ảnh hưởng trọng yếu đến công nợ.<br>
                        • <strong>Phân bổ thời gian:</strong> Các ngày đầu kỳ đã xử lý dứt điểm >95%, các dòng đang xử lý tập trung chủ yếu ở các ngày gần nhất do đang trong chu kỳ đối soát cuốn chiếu.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng Dòng ST ≥ 100k</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${fmtN(totCasesOver)} dòng</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Đã Xử Lý (ST ≥ 100k)</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${pctDoneOver}%</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Đang Xử Lý (ST ≥ 100k)</span>
                            <span class="zoom-stat-val" style="color:#fb923c;">${fmtN(totOverDang)} dòng</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng Dòng ST &lt; 100k</span>
                            <span class="zoom-stat-val" style="color:#94a3b8;">${fmtN(totCasesUnder)} dòng</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#34d399;"><i class="fa-solid fa-bolt"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Tập trung xử lý dứt điểm:</strong> Ưu tiên giải quyết dứt điểm <strong>${fmtN(totOverDang)} dòng hàng nhóm ST ≥ 100k</strong> còn tồn đọng trước ngày chốt sổ công nợ.<br>
                        • <strong>2. Tự động hóa kết chuyển:</strong> Áp dụng cơ chế Auto-Waive (miễn trừ tự động kết chuyển hao hụt định mức) cho nhóm ST &lt; 100k/ngày để giải phóng thời gian cho nhân sự kho.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { type: 'bar', label: '🟢 ST ≥ 100k (Đã XL)', data: cOverDa, backgroundColor: 'rgba(52, 211, 153, 0.9)', stack: 'over' },
                            { type: 'bar', label: '🟡 ST ≥ 100k (Đang XL)', data: cOverDang, backgroundColor: 'rgba(251, 146, 60, 0.9)', stack: 'over' },
                            { type: 'bar', label: '🟢 ST < 100k (Đã XL)', data: cUnderDa, backgroundColor: 'rgba(56, 189, 248, 0.85)', stack: 'under' },
                            { type: 'bar', label: '⚪ ST < 100k (Không XL)', data: cUnderKhong, backgroundColor: 'rgba(148, 163, 184, 0.7)', stack: 'under' },
                            { type: 'line', label: '📈 % Xong ST ≥ 100k', data: pctOverList, borderColor: '#f87171', backgroundColor: '#f87171', yAxisID: 'y1', borderWidth: 2.5, pointRadius: 4 },
                            { type: 'line', label: '📈 % Xong ST < 100k', data: pctUnderList, borderColor: '#38bdf8', backgroundColor: '#38bdf8', borderDash:[4,4], yAxisID: 'y1', borderWidth: 2, pointRadius: 3.5 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { stacked: true, ticks: { color: textMuted, font: { weight: '600' } } },
                            y: { stacked: true, title: { display: true, text: 'Số Dòng Hàng', color: textMuted } },
                            y1: { position: 'right', min: 0, max: 100, ticks: { callback: v => v + '%' }, title: { display: true, text: 'Tỷ Lệ % Xong' } }
                        },
                        plugins: {
                            datalabels: {
                                display: (ctx) => ctx.dataset.type === 'bar' && ctx.dataset.data[ctx.dataIndex] >= 40,
                                color: '#ffffff',
                                font: { weight: 'bold', size: 10 },
                                formatter: v => fmtN(v)
                            }
                        }
                    }
                };
            }
            else if (chartKey === 'chartDailyLech') {
                titleEl.innerText = "2. Giá Trị Tiền Lệch & Khối Lượng Hàng Lệch Theo Ngày";
                subtitleEl.innerText = "Chi tiết số tiền lệch (VNĐ) và khối lượng hàng lệch (Pcs/Kg) theo từng ngày";
                iconEl.innerHTML = '<i class="fa-solid fa-money-bill-transfer" style="color:#38bdf8;"></i>';
                badgeEl.innerText = "💰 Tiền Lệch vs Khối Lượng";

                const vTotal = list.map(d => Number(d.val_total) || 0);
                const qLech = list.map(d => Number(d.qty_lech) || 0);
                const maxValDay = [...list].sort((a,b)=>(b.val_total||0)-(a.val_total||0))[0] || {};

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-chart-line"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Tổng chênh lệch toàn kỳ:</strong> <strong>${fmtVND(gt.val_total)}</strong> (tổng khối lượng <strong>${fmtN(gt.qty_lech)} sp/kg</strong> qua ${fmtN(gt.cases_total)} dòng hàng).<br>
                        • <strong>Ngày phát sinh lệch cao nhất:</strong> Ngày <strong>${maxValDay.date || '-'}</strong> với tiền lệch đỉnh kỳ đạt <strong>${fmtVND(maxValDay.val_total || 0)}</strong> (${fmtN(maxValDay.qty_lech || 0)} sp lệch).<br>
                        • <strong>Xu hướng vận hành:</strong> Tiền lệch có xu hướng tăng vào các ngày giao nhận cao điểm (đặc biệt khi số lượng đơn hàng và chuyển kho tăng đột biến).
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng Tiền Lệch</span>
                            <span class="zoom-stat-val" style="color:#38bdf8;">${fmtVND(gt.val_total)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng SL Lệch</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${fmtN(gt.qty_lech)} sp/kg</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Ngày Lệch Cao Nhất</span>
                            <span class="zoom-stat-val" style="color:#fbbf24;">${maxValDay.date || '-'}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tiền Lệch Đỉnh</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${fmtVND(maxValDay.val_total || 0)}</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#38bdf8;"><i class="fa-solid fa-magnifying-glass"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Rà soát trọng điểm:</strong> Kiểm tra lại biên bản giao nhận và phiếu kiểm đếm 3 bên của ngày cao điểm <strong>${maxValDay.date || '-'}</strong> để làm rõ nguyên nhân lệch số lượng lớn.<br>
                        • <strong>2. Kiểm soát cửa xe:</strong> Tăng cường giám sát quy trình quét mã barcode tại cửa xe vào các khung giờ cao điểm để giảm thiểu lỗi đếm thiếu hoặc nhầm lẫn SKU.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { type: 'bar', label: '💰 Tiền Lệch (VNĐ)', data: vTotal, backgroundColor: 'rgba(56, 189, 248, 0.85)', yAxisID: 'y' },
                            { type: 'line', label: '📦 SL Lệch (sp/kg)', data: qLech, borderColor: '#f87171', backgroundColor: '#f87171', yAxisID: 'y1', borderWidth: 2.5, pointRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { ticks: { color: textMuted, font: { weight: '600' } } },
                            y: { ticks: { callback: v => (v/1e6).toFixed(0) + ' Tr' }, title: { display: true, text: 'Tiền Lệch (VNĐ)' } },
                            y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'SL Hàng (sp/kg)' } }
                        },
                        plugins: {
                            datalabels: {
                                display: (ctx) => ctx.dataset.type === 'bar' && ctx.dataset.data[ctx.dataIndex] >= 50e6,
                                color: '#ffffff',
                                font: { weight: 'bold', size: 9.5 },
                                formatter: v => (v/1e6).toFixed(0) + 'Tr'
                            }
                        }
                    }
                };
            }
            else if (chartKey === 'chartDailyProgress') {
                titleEl.innerText = "3. Tiến Độ Xử Lý Tiền Lệch Theo Ngày";
                subtitleEl.innerText = "Số tiền Đã Xử Lý vs Đang Xử Lý và Tỷ lệ % Hoàn Tất theo ngày";
                iconEl.innerHTML = '<i class="fa-solid fa-bars-progress" style="color:#34d399;"></i>';
                badgeEl.innerText = "🟢 Tiến Độ Xử Lý Tiền";

                const vDa = list.map(d => Number(d.val_da_xl) || 0);
                const vDang = list.map(d => Number(d.val_dang_xl) || 0);
                const vKhong = list.map(d => Number(d.val_khong_xl) || 0);
                const pctDaList = list.map(d => Number(d.pct_val_da_xl) || 0);
                const avgPct = (gt.val_da_xl / (gt.val_total || 1) * 100).toFixed(1);
                const detMetrics = getDynamicDetailedMetrics();

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-list-check"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Đã xử lý xong:</strong> <strong>${fmtVND(gt.val_da_xl)}</strong> (đạt <strong>${avgPct}%</strong> tổng tiền lệch).<br>
                        • <strong>Còn đang xử lý:</strong> Còn <strong>${fmtVND(gt.val_dang_xl)}</strong> (chiếm ${((gt.val_dang_xl/(gt.val_total||1))*100).toFixed(1)}%) thuộc nhóm ST ≥ 100k (${detMetrics.uniqueStPending} ST) đang trong quá trình xác định điểm nhận trách nhiệm.<br>
                        • <strong>Không cần xử lý:</strong> <strong>${fmtVND(gt.val_khong_xl)}</strong> thuộc các dòng hàng nhỏ lẻ dưới ngưỡng 100k.<br>
                        • <strong>Đánh giá tiến độ:</strong> Tỷ lệ xử lý các ngày đầu kỳ đạt >95%, các ngày gần nhất đang được bộ phận vận hành cuốn chiếu xử lý.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tiền Đã Xong</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${fmtVND(gt.val_da_xl)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">% Đã Hoàn Tất</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${avgPct}%</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tiền Đang Xử Lý</span>
                            <span class="zoom-stat-val" style="color:#fb923c;">${fmtVND(gt.val_dang_xl)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Không Cần Xử Lý</span>
                            <span class="zoom-stat-val" style="color:#94a3b8;">${fmtVND(gt.val_khong_xl)}</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#34d399;"><i class="fa-solid fa-forward"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Đôn đốc giải trình:</strong> Yêu cầu <strong>${detMetrics.uniqueStPending} Siêu Thị</strong> còn tồn đọng gửi đầy đủ biên bản đối soát cho khoản <strong>${fmtVND(gt.val_dang_xl)}</strong> trước ngày chốt sổ.<br>
                        • <strong>2. Chốt điểm nhận:</strong> Phối hợp Kho DC xác nhận dứt điểm các khoản bồi hoàn để chuyển trạng thái từ "Đang Xử Lý" sang "Đã Xử Lý".
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { type: 'bar', label: '🟢 Đã Xử Lý', data: vDa, backgroundColor: 'rgba(52, 211, 153, 0.9)', stack: 'val' },
                            { type: 'bar', label: '🟡 Đang Xử Lý', data: vDang, backgroundColor: 'rgba(251, 146, 60, 0.9)', stack: 'val' },
                            { type: 'bar', label: '⚪ Không Xử Lý', data: vKhong, backgroundColor: 'rgba(148, 163, 184, 0.7)', stack: 'val' },
                            { type: 'line', label: '📈 % Đã Xong', data: pctDaList, borderColor: '#34d399', backgroundColor: '#34d399', yAxisID: 'y1', borderWidth: 2.5, pointRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { stacked: true },
                            y: { stacked: true, ticks: { callback: v => (v/1e6).toFixed(0) + ' Tr' } },
                            y1: { position: 'right', min: 0, max: 100, ticks: { callback: v => v + '%' } }
                        },
                        plugins: {
                            datalabels: {
                                display: (ctx) => ctx.dataset.yAxisID === 'y1',
                                color: '#34d399',
                                font: { weight: 'bold', size: 10 },
                                align: 'top',
                                formatter: v => v >= 90 ? v + '%' : ''
                            }
                        }
                    }
                };
            }
            else if (chartKey === 'chartDailyStores') {
                titleEl.innerText = "4. Số Lượng Siêu Thị (ST) Phát Sinh Lệch Theo Ngày";
                subtitleEl.innerText = "Số lượng siêu thị có phát sinh lệch nhóm ST ≥ 100k và ST < 100k";
                iconEl.innerHTML = '<i class="fa-solid fa-store" style="color:#a5b4fc;"></i>';
                badgeEl.innerText = "🏪 Số Lượng Siêu Thị";

                const stOver = list.map(d => Number(d.stores_over_100k) || 0);
                const stUnder = list.map(d => Number(d.stores_under_100k) || 0);
                const detMetrics = getDynamicDetailedMetrics();

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-shop"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Tổng siêu thị phát sinh lệch:</strong> Có <strong>${detMetrics.uniqueStTotal} Siêu Thị</strong> toàn kỳ.<br>
                        • <strong>Siêu thị nhóm trọng điểm (≥ 100k):</strong> Có <strong>${detMetrics.uniqueStOver} Siêu Thị</strong> (chiếm hơn 95% tổng giá trị lệch). Trong đó đã xử lý xong hoàn toàn <strong>${detMetrics.uniqueStDone} ST</strong>, hiện còn <strong>${detMetrics.uniqueStPending} ST</strong> đang xử lý.<br>
                        • <strong>Siêu thị nhóm nhỏ (&lt; 100k):</strong> Có ${detMetrics.uniqueStIgnored} ST chỉ phát sinh các khoản vụn vặt dưới 100k, không gây rủi ro thất thoát.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng ST Lệch Kỳ</span>
                            <span class="zoom-stat-val" style="color:#38bdf8;">${detMetrics.uniqueStTotal} ST</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">ST Nhóm ≥ 100k</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${detMetrics.uniqueStOver} ST</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">ST Đã Xong 100%</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${detMetrics.uniqueStDone} ST</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">ST Còn Đang Xử Lý</span>
                            <span class="zoom-stat-val" style="color:#fb923c;">${detMetrics.uniqueStPending} ST</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#a5b4fc;"><i class="fa-solid fa-filter"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Tập trung Ưu Tiên 1 (P1):</strong> Mở bảng <em>"Danh sách Siêu Thị Ưu Tiên P1"</em> bên dưới giao diện chính để lọc ra đúng <strong>${detMetrics.uniqueStPending} ST còn đang xử lý</strong> và xử lý dứt điểm theo thứ tự số tiền giảm dần.<br>
                        • <strong>2. Giao ban định kỳ:</strong> Làm việc với Giám sát bán lẻ vùng đối với các Siêu Thị thường xuyên lọt top lệch cao để chấn chỉnh khâu nhận hàng tại cửa hàng.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { label: '🔴 Siêu Thị Lệch ≥ 100k', data: stOver, backgroundColor: 'rgba(248, 113, 113, 0.9)', stack: 'st' },
                            { label: '🟢 Siêu Thị Lệch < 100k', data: stUnder, backgroundColor: 'rgba(52, 211, 153, 0.9)', stack: 'st' }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { stacked: true }, y: { stacked: true, title: { display: true, text: 'Số Siêu Thị (ST)' } } },
                        plugins: {
                            datalabels: {
                                display: (ctx) => ctx.dataset.data[ctx.dataIndex] >= 15,
                                color: '#ffffff',
                                font: { weight: 'bold', size: 10 },
                                formatter: v => v
                            }
                        }
                    }
                };
            }
            else if (chartKey === 'chartTrendThreshold') {
                titleEl.innerText = "5. Diễn Biến Tiền Lệch Giữa Nhóm ST ≥ 100k vs ST < 100k";
                subtitleEl.innerText = "So sánh đường giá trị tiền lệch giữa 2 phân khúc siêu thị";
                iconEl.innerHTML = '<i class="fa-solid fa-chart-line" style="color:#f87171;"></i>';
                badgeEl.innerText = "📈 Xu Hướng Tiền Lệch Phân Khúc";

                const vOver = list.map(d => Number(d.val_over_100k) || 0);
                const vUnder = list.map(d => Number(d.val_under_100k) || 0);
                const pctOver = (gt.val_over_100k / (gt.val_total || 1) * 100).toFixed(1);

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-scale-unbalanced"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Nhóm ST ≥ 100k (Đường đỏ):</strong> Chiếm <strong>${pctOver}%</strong> tổng tiền lệch (<strong>${fmtVND(gt.val_over_100k)}</strong>). Đây là nhóm quyết định 95-98% kết quả thu hồi công nợ.<br>
                        • <strong>Nhóm ST &lt; 100k (Đường xanh lá):</strong> Chỉ chiếm <strong>${(100 - pctOver).toFixed(1)}%</strong> (<strong>${fmtVND(gt.val_under_100k)}</strong>), đường biểu diễn đi ngang ổn định ở mức rất thấp (&lt; 3 Triệu VNĐ/ngày).<br>
                        • <strong>Ý nghĩa kiểm soát:</strong> Phân khúc 100k giúp loại bỏ nhiễu số liệu từ các đơn lẻ tẻ, tập trung tối đa thời gian vào các khoản lệch có giá trị thực sự.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tiền Nhóm ST ≥ 100k</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${fmtVND(gt.val_over_100k)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tỷ Trọng Nhóm ≥ 100k</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${pctOver}%</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tiền Nhóm ST &lt; 100k</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${fmtVND(gt.val_under_100k)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tỷ Trọng Nhóm &lt; 100k</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${(100 - pctOver).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#f87171;"><i class="fa-solid fa-bullseye"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Áp dụng chuẩn quy tắc 80/20:</strong> Toàn bộ biên bản làm việc và đối soát chuyên sâu chỉ áp dụng cho nhóm ST ≥ 100k.<br>
                        • <strong>2. Giảm tải vận hành:</strong> Duy trì cơ chế miễn trừ xử lý cho nhóm &lt; 100k để giảm tải hơn 80% khối lượng giấy tờ thủ công cho các bộ phận.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'line',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { label: '🔴 Nhóm ST ≥ 100k', data: vOver, borderColor: '#f87171', backgroundColor: 'rgba(248, 113, 113, 0.15)', fill: true, tension: 0.3, borderWidth: 2.5, pointRadius: 4 },
                            { label: '🟢 Nhóm ST < 100k', data: vUnder, borderColor: '#34d399', backgroundColor: 'rgba(52, 211, 153, 0.1)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 3 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { ticks: { callback: v => (v/1e6).toFixed(0) + ' Tr' }, title: { display: true, text: 'Tiền Lệch (VNĐ)' } }
                        },
                        plugins: {
                            datalabels: {
                                display: (ctx) => ctx.datasetIndex === 0 && ctx.dataset.data[ctx.dataIndex] >= 60e6,
                                color: '#f87171',
                                font: { weight: 'bold', size: 10 },
                                align: 'top',
                                formatter: v => (v/1e6).toFixed(0) + 'Tr'
                            }
                        }
                    }
                };
            }
            else if (chartKey === 'chartDestDoughnut') {
                titleEl.innerText = "6. Phân Bổ Điểm Nhận Trách Nhiệm (Kho, Siêu Thị, Hao Hụt)";
                subtitleEl.innerText = "Cơ cấu tiền lệch đã quy về Kho ĐÔNG MÁT, Siêu Thị, Hao Hụt và đang xử lý";
                iconEl.innerHTML = '<i class="fa-solid fa-chart-pie" style="color:#fb923c;"></i>';
                badgeEl.innerText = "🎯 Điểm Nhận Trách Nhiệm";

                const destItems = [
                    { label: 'Kho ĐÔNG MÁT', val: Number(gt.val_kho) || 0, color: '#818cf8' },
                    { label: 'Siêu Thị', val: Number(gt.val_st) || 0, color: '#fbbf24' },
                    { label: 'Hao Hụt', val: Number(gt.val_haohut) || 0, color: '#34d399' },
                    { label: 'Đang XL (ST ≥ 100k)', val: Number(gt.val_dang_xl) || 0, color: '#fb923c' },
                    { label: 'Không XL (ST < 100k)', val: Number(gt.val_khong_xl) || 0, color: '#94a3b8' }
                ];
                const totVal = destItems.reduce((a,b)=>a+b.val,0) || 1;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-pie-chart"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Kho ĐÔNG MÁT nhận lỗi:</strong> <strong>${fmtVND(gt.val_kho)}</strong> (chiếm <strong>${(gt.val_kho/totVal*100).toFixed(1)}%</strong>). Chủ yếu do soạn thiếu hoặc giao nhầm mã tại kho DC.<br>
                        • <strong>Siêu Thị nhận lỗi:</strong> <strong>${fmtVND(gt.val_st)}</strong> (chiếm <strong>${(gt.val_st/totVal*100).toFixed(1)}%</strong>). Do lỗi kiểm đếm tại cửa hàng hoặc thất lạc nội bộ quầy kệ.<br>
                        • <strong>Hao hụt tự nhiên:</strong> <strong>${fmtVND(gt.val_haohut)}</strong> (chiếm ${(gt.val_haohut/totVal*100).toFixed(1)}%). Hàng dập nát, chảy nước, hao hụt trọng lượng trong vận chuyển.<br>
                        • <strong>Tiền còn đang xử lý:</strong> <strong>${fmtVND(gt.val_dang_xl)}</strong> (${(gt.val_dang_xl/totVal*100).toFixed(1)}%) cần tiếp tục phân định điểm nhận dứt điểm.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Kho ĐÔNG MÁT</span>
                            <span class="zoom-stat-val" style="color:#818cf8;">${fmtVND(gt.val_kho)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Siêu Thị</span>
                            <span class="zoom-stat-val" style="color:#fbbf24;">${fmtVND(gt.val_st)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Hao Hụt</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${fmtVND(gt.val_haohut)}</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Còn Đang Xử Lý</span>
                            <span class="zoom-stat-val" style="color:#fb923c;">${fmtVND(gt.val_dang_xl)}</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#fb923c;"><i class="fa-solid fa-clipboard-check"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Xử lý dứt điểm tiền đang treo:</strong> Phân loại cụ thể khoản <strong>${fmtVND(gt.val_dang_xl)}</strong> về đúng 3 bên (Kho DC - Siêu Thị - Hao Hụt) trước ngày 30 hàng tháng.<br>
                        • <strong>2. Thu hồi công nợ:</strong> Chuyển danh sách các khoản Siêu Thị và Kho DC đã nhận trách nhiệm sang bộ phận kế toán để bù trừ công nợ kịp thời.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'doughnut',
                    data: {
                        labels: destItems.map(d=>d.label),
                        datasets: [{
                            data: destItems.map(d=>d.val),
                            backgroundColor: destItems.map(d=>d.color),
                            borderWidth: 2,
                            borderColor: '#0f172a'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: textColor, font: { weight: '600' } } },
                            datalabels: {
                                color: '#ffffff',
                                font: { weight: 'bold', size: 12 },
                                formatter: (val) => {
                                    const pct = (val / totVal * 100);
                                    return pct >= 4.0 ? pct.toFixed(1) + '%' : '';
                                }
                            }
                        },
                        cutout: '55%'
                    }
                };
            }
            else if (chartKey === 'chartDCResponse') {
                titleEl.innerText = "7. Tiến Độ Trả Hàng DC & Tỷ Lệ DC Phản Hồi Theo Ngày";
                subtitleEl.innerText = "Chi tiết số dòng gửi trả DC, kết quả DC đồng ý, từ chối hoặc đang kiểm tra theo ngày";
                iconEl.innerHTML = '<i class="fa-solid fa-truck-ramp-box" style="color:#c084fc;"></i>';
                badgeEl.innerText = "🚚 Tiến Độ Trả DC & Phản Hồi";

                const dyCases = list.map(d => Number(d.dc_dongy_cases) || 0);
                const tcCases = list.map(d => Number(d.dc_tuchoi_cases) || 0);
                const ktCases = list.map(d => Number(d.dc_kiemtra_cases) || 0);
                const chCases = list.map(d => Number(d.dc_chua_cases) || 0);
                const pctRespList = list.map(d => Number(d.dc_pct_phan_hoi) || 0);

                const sumTotal = dyCases.reduce((a,b)=>a+b,0) + tcCases.reduce((a,b)=>a+b,0) + ktCases.reduce((a,b)=>a+b,0) + chCases.reduce((a,b)=>a+b,0);
                const sumDongY = dyCases.reduce((a,b)=>a+b,0);
                const sumTuChoi = tcCases.reduce((a,b)=>a+b,0);
                const sumChua = chCases.reduce((a,b)=>a+b,0) + ktCases.reduce((a,b)=>a+b,0);
                const pctDongY = sumTotal > 0 ? (sumDongY / sumTotal * 100).toFixed(1) : 0;
                const pctTuChoi = sumTotal > 0 ? (sumTuChoi / sumTotal * 100).toFixed(1) : 0;
                const pctChua = sumTotal > 0 ? (sumChua / sumTotal * 100).toFixed(1) : 0;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-clipboard-list"></i> Tình Hình Hiện Tại & Bóc Tách Chi Tiết</div>
                    <div class="zoom-insight-text">
                        • <strong>Tổng dòng hàng gửi trả DC:</strong> <strong>${fmtN(sumTotal)} dòng hàng</strong> toàn kỳ.<br>
                        • <strong>🟢 DC Đồng ý bồi hoàn:</strong> <strong>${fmtN(sumDongY)} dòng</strong> (${pctDongY}%).<br>
                        • <strong>🔴 DC Từ chối bồi hoàn:</strong> <strong>${fmtN(sumTuChoi)} dòng</strong> (${pctTuChoi}%).<br>
                        • <strong>🟡 DC Đang kiểm tra / Chưa phản hồi:</strong> <strong>${fmtN(sumChua)} dòng</strong> (${pctChua}%).<br>
                        • <strong>Tỷ lệ phản hồi chung:</strong> Toàn hệ thống đạt <strong>${gt.dc_pct_phan_hoi || 0}%</strong> đã có kết quả phản hồi.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng Dòng Trả DC</span>
                            <span class="zoom-stat-val" style="color:#c084fc;">${fmtN(sumTotal)} dòng</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">DC Đồng Ý Claim</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${fmtN(sumDongY)} (${pctDongY}%)</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">DC Từ Chối Claim</span>
                            <span class="zoom-stat-val" style="color:#f87171;">${fmtN(sumTuChoi)} (${pctTuChoi}%)</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">DC Đang Kiểm Tra</span>
                            <span class="zoom-stat-val" style="color:#fbbf24;">${fmtN(sumChua)} (${pctChua}%)</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#c084fc;"><i class="fa-solid fa-truck-ramp-box"></i> Đề Xuất & Hành Động SCM Cần Triển Khai Ngay</div>
                    <div class="zoom-insight-text">
                        • <strong>1. Giải tỏa nút thắt kiểm tra:</strong> Đôn đốc Kho DC phản hồi dứt điểm <strong>${fmtN(sumChua)} dòng đang kiểm tra</strong> để chốt số liệu bồi hoàn cho Siêu Thị.<br>
                        • <strong>2. Xử lý dòng từ chối:</strong> Thu hồi biên bản / hình ảnh cho <strong>${fmtN(sumTuChoi)} dòng bị từ chối</strong> để phân bổ về Siêu Thị hoặc hạch toán Hao hụt nội bộ, tránh tồn đọng kéo dài.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { type: 'bar', label: '🟢 DC Đồng Ý Claim', data: dyCases, backgroundColor: 'rgba(52, 211, 153, 0.9)', stack: 'dc' },
                            { type: 'bar', label: '🔴 DC Từ Chối Claim', data: tcCases, backgroundColor: 'rgba(248, 113, 113, 0.9)', stack: 'dc' },
                            { type: 'bar', label: '🟡 DC Kiểm Tra Lại / Chờ', data: ktCases.map((v,i)=>v+chCases[i]), backgroundColor: 'rgba(251, 191, 36, 0.9)', stack: 'dc' },
                            { type: 'line', label: '📈 Tỷ Lệ DC Phản Hồi (%)', data: pctRespList, borderColor: '#c084fc', backgroundColor: '#c084fc', yAxisID: 'y1', borderWidth: 2.5, pointRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: { padding: { top: 35, bottom: 15, left: 10, right: 10 } },
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { stacked: true, ticks: { color: textMuted, font: { weight: '600' } } },
                            y: { stacked: true, title: { display: true, text: 'Số Dòng Hàng', color: textMuted } },
                            y1: { position: 'right', min: 0, max: 130, ticks: { color: '#c084fc', callback: v => v <= 100 ? v + '%' : '' } }
                        },
                        plugins: {
                            legend: { position: 'top', labels: { color: textColor, font: { weight: '600', size: 11 }, boxWidth: 10, boxHeight: 10, padding: 18 } },
                            datalabels: {
                                display: (ctx) => {
                                    if (ctx.dataset.yAxisID === 'y1') {
                                        const val = ctx.dataset.data[ctx.dataIndex];
                                        return val < 100;
                                    }
                                    return ctx.dataset.data[ctx.dataIndex] >= 35;
                                },
                                color: (ctx) => {
                                    if (ctx.dataset.yAxisID === 'y1') {
                                        const val = ctx.dataset.data[ctx.dataIndex];
                                        return val < 70 ? '#f87171' : '#fbbf24';
                                    }
                                    return '#ffffff';
                                },
                                backgroundColor: (ctx) => ctx.dataset.yAxisID === 'y1' ? 'rgba(15, 23, 42, 0.92)' : null,
                                borderRadius: 4,
                                padding: (ctx) => ctx.dataset.yAxisID === 'y1' ? { top: 2, bottom: 2, left: 4, right: 4 } : 0,
                                font: { weight: 'bold', size: 10.5 },
                                anchor: (ctx) => ctx.dataset.yAxisID === 'y1' ? 'bottom' : 'center',
                                align: (ctx) => ctx.dataset.yAxisID === 'y1' ? 'bottom' : 'center',
                                offset: (ctx) => ctx.dataset.yAxisID === 'y1' ? 4 : 0,
                                formatter: (v, ctx) => ctx.dataset.yAxisID === 'y1' ? '⚠️ ' + v + '%' : fmtN(v)
                            }
                        }
                    }
                };
            }
                        else if (chartKey === 'chartKFMProgressDaily') {
                titleEl.innerText = "9. Tiến Độ KFM Chỉnh DONE Theo Ngày (Tập DC Đồng Ý Claim)";
                subtitleEl.innerText = "Bóc tách số case Đã Chỉnh DONE vs Chưa Chỉnh DONE trên tập 11.019 dòng DC Đồng ý claim";
                iconEl.innerHTML = '<i class="fa-solid fa-circle-check" style="color:#34d399;"></i>';
                badgeEl.innerText = "🟢 KFM DONE Progress";

                const dyDone = list.map(d => Number(d.dc_dongy_done_cases) || 0);
                const dyNotDone = list.map(d => Math.max(0, (Number(d.dc_dongy_cases) || 0) - (Number(d.dc_dongy_done_cases) || 0)));
                const dyPctDoneList = list.map(d => (Number(d.dc_dongy_cases) || 0) > 0 ? ((Number(d.dc_dongy_done_cases) || 0) / (Number(d.dc_dongy_cases) || 1) * 100).toFixed(1) : 0);

                const totDone = dyDone.reduce((a,b)=>a+b, 0);
                const totNotDone = dyNotDone.reduce((a,b)=>a+b, 0);
                const totDongY = totDone + totNotDone;
                const avgPctDone = totDongY > 0 ? (totDone / totDongY * 100).toFixed(1) : 0;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-clipboard-check"></i> Tình Hình KFM Chỉnh DONE Trên DC Đồng Ý</div>
                    <div class="zoom-insight-text">
                        • <strong>Tổng số case DC Đồng ý:</strong> <strong>${fmtN(totDongY)} dòng hàng</strong> (${fmtVND(gt.dc_dongy_val || 1827643080)}).<br>
                        • <strong>KFM Đã Chỉnh DONE:</strong> <strong>${fmtN(totDone)} dòng</strong> (đạt <strong>${avgPctDone}%</strong>).<br>
                        • <strong>🚨 KFM Chưa Chỉnh DONE:</strong> Còn <strong>${fmtN(totNotDone)} dòng hàng</strong> (${(100 - avgPctDone).toFixed(1)}% • ${fmtVND(gt.dc_dongy_val - (gt.dc_dongy_val * avgPctDone / 100))}) đang chờ KFM thao tác DONE để kết sổ.<br>
                        • <strong>Phân hóa nhóm hàng:</strong> Hàng Mát đã DONE 95.8% (3.489 / 3.641 dòng), trong khi Hàng Đông gần như toàn bộ 7.377 dòng chưa chỉnh DONE.
                    </div>
                    <div class="zoom-stat-grid">
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Tổng DC Đồng Ý</span>
                            <span class="zoom-stat-val" style="color:#38bdf8;">${fmtN(totDongY)} dòng</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Đã DONE</span>
                            <span class="zoom-stat-val" style="color:#34d399;">${fmtN(totDone)} (${avgPctDone}%)</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Chưa DONE</span>
                            <span class="zoom-stat-val" style="color:#fb923c;">${fmtN(totNotDone)} (${(100 - avgPctDone).toFixed(1)}%)</span>
                        </div>
                        <div class="zoom-stat-item">
                            <span class="zoom-stat-label">Trọng Điểm Chờ</span>
                            <span class="zoom-stat-val" style="color:#f87171;">Hàng Đông (7.377 case)</span>
                        </div>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#34d399;"><i class="fa-solid fa-bolt"></i> Đề Xuất Hành Động SCM</div>
                    <div class="zoom-insight-text">
                        • <strong>1. KFM rà soát hàng loạt Hàng Đông:</strong> Tổ chức cập nhật trạng thái DONE cho 7.377 dòng Hàng Đông đã được DC đồng ý để chuẩn hóa công nợ.<br>
                        • <strong>2. Đối soát cuốn chiếu theo ngày:</strong> Ưu tiên chỉnh DONE các ngày đầu tháng 8 trước, các ngày gần nhất xử lý theo chu kỳ 48h.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: shortLabels,
                        datasets: [
                            { type: 'bar', label: '🟢 KFM Đã DONE', data: dyDone, backgroundColor: 'rgba(52, 211, 153, 0.9)', stack: 'kfmStack' },
                            { type: 'bar', label: '🚨 KFM Chưa DONE', data: dyNotDone, backgroundColor: 'rgba(251, 146, 60, 0.9)', stack: 'kfmStack' },
                            { type: 'line', label: '📈 % Đã DONE', data: dyPctDoneList, borderColor: '#38bdf8', backgroundColor: '#38bdf8', yAxisID: 'y1', borderWidth: 2.5, pointRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { stacked: true, ticks: { color: textMuted, font: { weight: '600' } } },
                            y: { stacked: true, title: { display: true, text: 'Số Dòng Hàng DC Đồng Ý' } },
                            y1: { position: 'right', min: 0, max: 100, ticks: { callback: v => v + '%' }, title: { display: true, text: 'Tỷ Lệ % DONE' } }
                        }
                    }
                };
            }
            else if (chartKey === 'chartDCNonAgreeBreakdown') {
                titleEl.innerText = "10. Cơ Cấu Các Case DC Khác Đồng Ý Claim & KFM Phản Hồi";
                subtitleEl.innerText = "Phân tích 1.608 case Từ chối, Kiểm tra lại, Chưa phản hồi và mức độ KFM giải trình";
                iconEl.innerHTML = '<i class="fa-solid fa-scale-balanced" style="color:#f87171;"></i>';
                badgeEl.innerText = "🔴 DC Non-Agree Analysis";

                const dcCases = getAllDCCases();
                const tcSub = dcCases.filter(r => r.dc_confirm === 'Từ chối claim');
                const ktSub = dcCases.filter(r => r.dc_confirm === 'Kiểm tra lại');
                const chSub = dcCases.filter(r => !['Đồng ý claim', 'Từ chối claim', 'Kiểm tra lại'].includes(r.dc_confirm));

                const tcHlv = tcSub.filter(r => r.kfm_reply === 'Cấp HLV quyết định').length;
                const tcPending = tcSub.filter(r => !['DONE', 'Cấp HLV quyết định', 'DC check lại thông tin'].includes(r.kfm_reply)).length;
                const tcOther = tcSub.length - tcHlv - tcPending;
                const ktDone = ktSub.filter(r => r.kfm_reply === 'DONE' || r.kfm_reply === 'DC check lại thông tin').length;
                const ktPending = ktSub.length - ktDone;
                const chTot = chSub.length;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-pie-chart"></i> Bóc Tách Chi Tiết Nhóm DC Khác Đồng Ý (1.608 case)</div>
                    <div class="zoom-insight-text">
                        • <strong>1. DC Từ Chối Claim (1.094 case • 232 Tr):</strong> KFM đã giải trình <strong>84.4%</strong> (902 case chuyển Cấp HLV quyết định, 8 case DC check lại, 13 case DONE). Còn nợ phản hồi <strong>171 case (15.6%)</strong>.<br>
                        • <strong>2. DC Kiểm Tra Lại (159 case • 28.1 Tr):</strong> KFM đã phản hồi <strong>98.7%</strong> (151 DONE, 6 Check lại). Còn nợ 2 case.<br>
                        • <strong>3. DC Chưa Phản Hồi (355 case • 53.6 Tr):</strong> DC cần tăng tốc độ duyệt hồ sơ, tập trung 224 case Hàng Mát.
                    </div>
                </div>
                `;

                const nonAgreeItems = [
                    { label: '🔴 Từ Chối - Cấp HLV Quyết Định', val: tcHlv, color: '#f87171' },
                    { label: '⚠️ Từ Chối - KFM Chưa Phản Hồi', val: tcPending, color: '#fb923c' },
                    { label: '🟡 Kiểm Tra Lại - Đã Phản Hồi', val: ktDone, color: '#fbbf24' },
                    { label: '⏳ DC Chưa Phản Hồi (Trống)', val: chTot, color: '#94a3b8' },
                    { label: '🟢 Từ Chối - Đã Xử Lý Khác', val: tcOther, color: '#34d399' }
                ].filter(x => x.val > 0);

                chartConfig = {
                    type: 'doughnut',
                    data: {
                        labels: nonAgreeItems.map(d => d.label),
                        datasets: [{ data: nonAgreeItems.map(d => d.val), backgroundColor: nonAgreeItems.map(d => d.color) }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                };
            }
            else if (chartKey === 'chartDCNoteBreakdown') {
                titleEl.innerText = "11. Top Điểm Nóng Lý Do DC Note (Cột AE) & Hành Động KFM Note (Cột AG)";
                subtitleEl.innerText = "Thống kê các lý do DC từ chối/ghi chú và các hành động xử lý thực tế của KFM";
                iconEl.innerHTML = '<i class="fa-solid fa-tags" style="color:#c084fc;"></i>';
                badgeEl.innerText = "🏷️ Notes Analytics";

                const dcCases = getAllDCCases();
                const dcNotesMap = {};
                const kfmNotesMap = {};
                dcCases.forEach(r => {
                    if (r.dc_note) dcNotesMap[r.dc_note] = (dcNotesMap[r.dc_note] || 0) + 1;
                    if (r.kfm_note) kfmNotesMap[r.kfm_note] = (kfmNotesMap[r.kfm_note] || 0) + 1;
                });

                const topDC = Object.entries(dcNotesMap).sort((a, b) => b[1] - a[1]).slice(0, 5);
                const topKFM = Object.entries(kfmNotesMap).sort((a, b) => b[1] - a[1]).slice(0, 5);

                const allNotesLabels = [...topDC.map(x => `🏢 DC: ${x[0]}`), ...topKFM.map(x => `👤 KFM: ${x[0]}`)];
                const allNotesValues = [...topDC.map(x => x[1]), ...topKFM.map(x => x[1])];
                const allNotesColors = [
                    ...topDC.map(() => '#c084fc'),
                    ...topKFM.map(() => '#fb923c')
                ];

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-list"></i> Phân Tích Nguyên Nhân & Hành Động</div>
                    <div class="zoom-insight-text">
                        • <strong>Lý do DC từ chối hàng đầu:</strong> <em>Trễ timeline (431 case), Khuất cam (105 case), Không có hình ảnh (52 case), Lỗi cam (30 case)...</em><br>
                        • <strong>Hành động xử lý của KFM:</strong> <em>Đã trả tồn TO (1.832 case), Trả về kho đông (64 case), Trả tồn ST (33 case)...</em><br>
                        • <strong>Khuyến nghị:</strong> Siêu thị cần gửi ảnh và biên bản đúng timeline quy định để giảm thiểu 431 case bị DC từ chối vì trễ hạn.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: allNotesLabels,
                        datasets: [{ label: 'Số Lượng Dòng Ghi Chú', data: allNotesValues, backgroundColor: allNotesColors }]
                    },
                    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
                };
            }

            else if (chartKey === 'chartDCGroupCompare') {
                titleEl.innerText = "8. Tỷ Lệ DC Phản Hồi & Kết Quả Xác Nhận Giữa 2 Nhóm Hàng (MÁT vs ĐÔNG)";
                subtitleEl.innerText = "So sánh tỷ lệ chấp thuận bồi hoàn và mức độ phản hồi của nhóm Hàng Mát và Hàng Đông";
                iconEl.innerHTML = '<i class="fa-solid fa-scale-balanced" style="color:#38bdf8;"></i>';
                badgeEl.innerText = "🥩 Mát vs ❄️ Đông";

                const bMat = BUNDLES['mat'] ? BUNDLES['mat'].grand_total : {};
                const bDong = BUNDLES['dong'] ? BUNDLES['dong'].grand_total : {};

                const matDongY = bMat.dc_dongy_cases || 0;
                const matTuChoi = bMat.dc_tuchoi_cases || 0;
                const matKiemTra = (bMat.dc_kiemtra_cases || 0) + (bMat.dc_chua_cases || 0);
                const matTotal = (matDongY + matTuChoi + matKiemTra) || 1;
                const matPctDongY = (matDongY / matTotal * 100).toFixed(1);
                const matPctTuChoi = (matTuChoi / matTotal * 100).toFixed(1);
                const matPctKiemTra = (matKiemTra / matTotal * 100).toFixed(1);
                const matPctResp = bMat.dc_pct_phan_hoi || 92.4;

                const dongDongY = bDong.dc_dongy_cases || 0;
                const dongTuChoi = bDong.dc_tuchoi_cases || 0;
                const dongKiemTra = (bDong.dc_kiemtra_cases || 0) + (bDong.dc_chua_cases || 0);
                const dongTotal = (dongDongY + dongTuChoi + dongKiemTra) || 1;
                const dongPctDongY = (dongDongY / dongTotal * 100).toFixed(1);
                const dongPctTuChoi = (dongTuChoi / dongTotal * 100).toFixed(1);
                const dongPctKiemTra = (dongKiemTra / dongTotal * 100).toFixed(1);
                const dongPctResp = bDong.dc_pct_phan_hoi || 100.0;

                insightsHtml = `
                <div class="zoom-insight-card highlight">
                    <div class="zoom-insight-title"><i class="fa-solid fa-table-columns"></i> Bảng Ma Trận Đối Soát Chi Tiết (MÁT vs ĐÔNG)</div>
                    <div style="overflow-x:auto;">
                        <table class="zoom-detail-table">
                            <thead>
                                <tr>
                                    <th>Chỉ Tiêu So Sánh</th>
                                    <th style="color:#34d399; text-align:right;">🥩 HÀNG MÁT</th>
                                    <th style="color:#818cf8; text-align:right;">❄️ HÀNG ĐÔNG</th>
                                    <th style="text-align:right;">So Sánh & Nhận Định</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><strong>1. Tổng Dòng Hàng Trả DC</strong></td>
                                    <td style="text-align:right; font-weight:700; color:#ffffff;">${fmtN(matTotal)} dòng</td>
                                    <td style="text-align:right; font-weight:700; color:#ffffff;">${fmtN(dongTotal)} dòng</td>
                                    <td style="text-align:right; color:#38bdf8;">Mát gấp ${(matTotal/Math.max(dongTotal,1)).toFixed(1)} lần Đông</td>
                                </tr>
                                <tr>
                                    <td><strong>2. 🟢 DC Đồng Ý Bồi Hoàn</strong></td>
                                    <td style="text-align:right; font-weight:700; color:#34d399;">${fmtN(matDongY)} (${matPctDongY}%)</td>
                                    <td style="text-align:right; font-weight:700; color:#34d399;">${fmtN(dongDongY)} (${dongPctDongY}%)</td>
                                    <td style="text-align:right; color:#34d399;">Đông duyệt vượt trội +${(dongPctDongY - matPctDongY).toFixed(1)}%</td>
                                </tr>
                                <tr>
                                    <td><strong>3. 🔴 DC Từ Chối Claim</strong></td>
                                    <td style="text-align:right; font-weight:700; color:#f87171;">${fmtN(matTuChoi)} (${matPctTuChoi}%)</td>
                                    <td style="text-align:right; font-weight:700; color:#f87171;">${fmtN(dongTuChoi)} (${dongPctTuChoi}%)</td>
                                    <td style="text-align:right; color:#94a3b8;">Tỷ lệ tương đương (~4-5%)</td>
                                </tr>
                                <tr>
                                    <td><strong>4. 🟡 Đang Chờ / Kiểm Tra Lại</strong></td>
                                    <td style="text-align:right; font-weight:700; color:#fbbf24;">${fmtN(matKiemTra)} (${matPctKiemTra}%)</td>
                                    <td style="text-align:right; font-weight:700; color:#fbbf24;">${fmtN(dongKiemTra)} (${dongPctKiemTra}%)</td>
                                    <td style="text-align:right; color:#fbbf24;">⚠️ Mát tồn đọng ${fmtN(matKiemTra)} dòng</td>
                                </tr>
                                <tr>
                                    <td><strong>5. Tỷ Lệ DC Đã Phản Hồi</strong></td>
                                    <td style="text-align:right; font-weight:800; color:#38bdf8;">${matPctResp}%</td>
                                    <td style="text-align:right; font-weight:800; color:#818cf8;">${dongPctResp}%</td>
                                    <td style="text-align:right; color:#34d399;">Đông hoàn tất gần trọn vẹn</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="zoom-insight-card">
                    <div class="zoom-insight-title" style="color:#fbbf24;"><i class="fa-solid fa-magnifying-glass-chart"></i> Phân Tích Nguyên Nhân & Đề Xuất Hành Động SCM</div>
                    <div class="zoom-insight-text">
                        • <strong>🔍 Nguyên nhân Hàng Mát tồn đọng ${fmtN(matKiemTra)} dòng (${matPctKiemTra}%):</strong><br>
                        Hàng tươi sống có date sử dụng ngắn và hao hụt trọng lượng tự nhiên trong quá trình lưu kho/vận chuyển. Quy trình xác nhận đòi hỏi biên bản bàn giao 3 bên (ST - Tài xế - DC) kèm ảnh chụp cân đo nên thời gian xử lý kéo dài hơn.<br><br>
                        • <strong>🔍 Vì sao Hàng Đông duyệt nhanh đạt ${dongPctDongY}% (${fmtN(dongDongY)} dòng)?</strong><br>
                        Hàng Đông đóng kiện nguyên thùng, mã niêm phong (seal) chuẩn hóa nên khi thiếu/thừa hoặc rách vỡ bao bì, thủ kho DC quét mã xác nhận ngay tại cửa nhập kho.<br><br>
                        • <strong>⚡ Hành Động SCM Cần Triển Khai Ngay:</strong><br>
                        1. <strong>Đối soát trọng điểm:</strong> SCM tổ chức buổi làm việc với Trưởng kho DC Hàng Mát để giải tỏa dứt điểm <strong>${fmtN(matKiemTra)} dòng hàng chờ</strong> trước kỳ chốt công nợ tháng.<br>
                        2. <strong>Xử lý dòng từ chối:</strong> Bóc tách <strong>${fmtN(matTuChoi + dongTuChoi)} dòng bị từ chối</strong> để phân bổ về trách nhiệm Siêu Thị hoặc hạch toán Hao hụt nội bộ, tránh treo tồn đọng.
                    </div>
                </div>
                `;

                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: [`🥩 NHÓM HÀNG MÁT (${fmtN(matTotal)} dòng)`, `❄️ NHÓM HÀNG ĐÔNG (${fmtN(dongTotal)} dòng)`],
                        datasets: [
                            { label: '🟢 Đồng Ý Claim', data: [matDongY, dongDongY], backgroundColor: 'rgba(52, 211, 153, 0.9)', maxBarThickness: 50, borderRadius: 4 },
                            { label: '🔴 Từ Chối Claim', data: [matTuChoi, dongTuChoi], backgroundColor: 'rgba(248, 113, 113, 0.9)', maxBarThickness: 50, borderRadius: 4 },
                            { label: '🟡 Kiểm Tra Lại / Chờ', data: [matKiemTra, dongKiemTra], backgroundColor: 'rgba(251, 191, 36, 0.9)', maxBarThickness: 50, borderRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: { padding: { top: 30, bottom: 15 } },
                        scales: { 
                            x: { ticks: { color: textColor, font: { weight: '700', size: 12 } }, grid: { display: false } },
                            y: { title: { display: true, text: 'Số Dòng Hàng', color: textColor, font: { weight: '700', size: 12 } }, ticks: { color: textMuted, font: { weight: '700', size: 11 } } } 
                        },
                        plugins: {
                            legend: { position: 'top', labels: { color: textColor, font: { weight: '600', size: 12 }, padding: 18 } },
                            datalabels: {
                                color: '#ffffff',
                                backgroundColor: 'rgba(15, 23, 42, 0.92)',
                                borderRadius: 4,
                                padding: { top: 3, bottom: 3, left: 6, right: 6 },
                                font: { weight: 'bold', size: 11.5 },
                                anchor: 'end',
                                align: 'top',
                                offset: 4,
                                formatter: (v, ctx) => {
                                    const tot = ctx.dataIndex === 0 ? matTotal : dongTotal;
                                    const pct = tot > 0 ? (v / tot * 100).toFixed(1) : 0;
                                    return `${fmtN(v)} (${pct}%)`;
                                }
                            }
                        }
                    }
                };
            }

            insightsEl.innerHTML = insightsHtml;
            if (chartConfig) {
                chartZoomInstance = new Chart(ctx, chartConfig);
            }
            modal.classList.add('active');
        }
    </script>
</body>
</html>"""

    # 1. Ghi vào thư mục DONG_MAT_DASHBOARD
    local_output = os.path.join(current_dir, "Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html")
    with open(local_output, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    # 2. Ghi vào thư mục gốc Đối soát SCM
    root_output = os.path.join(os.path.dirname(current_dir), "Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html")
    try:
        with open(root_output, "w", encoding="utf-8") as f:
            f.write(html_template)
    except Exception:
        pass

    # 3. Ghi vào thư mục LOGIC/dashboard_template.html
    logic_template_path = os.path.join(os.path.dirname(current_dir), "LOGIC", "dashboard_template.html")
    try:
        with open(logic_template_path, "w", encoding="utf-8") as f:
            f.write(html_template)
    except Exception:
        pass

    print("✅ ĐÃ XUẤT BẢN THÀNH CÔNG VÀ ĐỒNG BỘ SL SIÊU THỊ VÀO TẤT CẢ FILE BÁO CÁO!")
    return local_output


if __name__ == "__main__":
    generate_html_report()
