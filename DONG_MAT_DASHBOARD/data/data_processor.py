# -*- coding: utf-8 -*-
"""
Module tiền xử lý, làm sạch và chuẩn hóa dữ liệu cho Dashboard ĐÔNG MÁT.
"""

import pandas as pd
import numpy as np
import re


def parse_number(val) -> float:
    """
    Chuyển đổi chuỗi số linh hoạt xử lý lẫn lộn định dạng VN (1.234,50) và EN (1,234.50).
    """
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val) if not np.isnan(val) else 0.0
    
    s = str(val).strip()
    if not s or s.lower() in ["nan", "none", "null", "-", ""]:
        return 0.0
    
    s = s.replace("%", "").strip()
    num_dots = s.count(".")
    num_commas = s.count(",")
    
    if num_dots > 0 and num_commas > 0:
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_comma > last_dot:  # Định dạng VN: 1.234,50
            s = s.replace(".", "").replace(",", ".")
        else:  # Định dạng EN: 1,234.50
            s = s.replace(",", "")
    elif num_commas > 0:
        if num_commas > 1:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif num_dots > 0:
        parts = s.split(".")
        if num_dots > 1:
            s = s.replace(".", "")
        else:
            if len(parts[1]) == 3 and parts[0] not in ["0", "-0", ""]:
                s = s.replace(".", "")
                
    try:
        return float(s)
    except Exception:
        return 0.0


def process_dong_mat_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline làm sạch dữ liệu toàn diện cho tất cả các cột.
    """
    df = df_raw.copy()
    
    # 1. Đổi tên cột trùng lặp (ví dụ NOTE, NOTE.1, NOTE.2)
    new_cols = []
    seen = {}
    for col in df.columns:
        c_clean = str(col).strip()
        if c_clean in seen:
            seen[c_clean] += 1
            new_cols.append(f"{c_clean}_{seen[c_clean]}")
        else:
            seen[c_clean] = 0
            new_cols.append(c_clean)
    df.columns = new_cols
    
    # 2. Chuẩn hóa cột ngày tháng linh hoạt
    date_col = next((c for c in df.columns if "ngày" in c.lower() or "ngay" in c.lower() or "date" in c.lower()), None)
    if date_col:
        def _parse_dt(v):
            if pd.isna(v) or not str(v).strip() or str(v).lower() in ["nan", "none", "null"]:
                return pd.NaT
            v_str = str(v).strip()
            for fmt in ["%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    return pd.to_datetime(v_str, format=fmt)
                except Exception:
                    pass
            try:
                return pd.to_datetime(v_str, errors="coerce", dayfirst=False)
            except Exception:
                return pd.NaT

        df["Date_Parsed"] = df[date_col].apply(_parse_dt)
        df["Date_Str"] = df["Date_Parsed"].dt.strftime("%d/%m/%Y").fillna(df[date_col].astype(str))
    else:
        df["Date_Parsed"] = pd.NaT
        df["Date_Str"] = "Không rõ"
        
    # 3. Chuẩn hóa tất cả các cột văn bản
    for c in df.columns:
        if c != "Date_Parsed":
            df[c] = df[c].fillna("").astype(str).replace(["nan", "None", "NULL", "null", "<NA>"], "").str.strip()
            
    # Chuẩn hóa Nhóm hàng (THỊT CÁ, MÁT, ĐÔNG)
    grp_col = next((c for c in df.columns if "nhóm hàng" in c.lower() or "nhom hang" in c.lower() or "group" in c.lower()), None)
    if grp_col:
        def _norm_grp(x):
            if not x or pd.isna(x):
                return "KHÁC"
            s = str(x).strip().upper()
            if "THỊT" in s or "THIT" in s or "CÁ" in s or "CA" in s or "MEAT" in s or "FISH" in s:
                return "THỊT CÁ"
            if "MÁT" in s or "MAT" in s or "CHILL" in s:
                return "MÁT"
            if "ĐÔNG" in s or "DONG" in s or "FROZEN" in s:
                return "ĐÔNG"
            return s
            
        df["Nhóm hàng"] = df[grp_col].apply(_norm_grp)
    else:
        df["Nhóm hàng"] = "KHÁC"
        
    # Chuẩn hóa Loại Lỗi
    err_col = next((c for c in df.columns if "lỗi" in c.lower() or c.lower() == "loi" or "error" in c.lower()), None)
    if err_col:
        df["Lỗi"] = df[err_col].apply(lambda x: "Chưa phân loại" if not x or x.lower() in ["nan", ""] else x)
    else:
        df["Lỗi"] = "Chưa phân loại"
        
    # Chuẩn hóa Tình trạng Claim DC
    dc_conf_col = next((c for c in df.columns if "dc xác nhận" in c.lower() or "dc xac nhan" in c.lower() or "dc_confirm" in c.lower()), None)
    if dc_conf_col:
        df["Claim_Status"] = df[dc_conf_col].apply(
            lambda x: "Chưa phản hồi" if not x or x.lower() in ["nan", ""] else x
        )
        df["DC_Confirm"] = df[dc_conf_col]
    else:
        df["Claim_Status"] = "Chưa phản hồi"
        df["DC_Confirm"] = ""
        
    # 4. Chuẩn hóa các cột số liệu & tính toán tài chính
    numeric_targets = [
        "Số lượng chuyển", "Số lượng nhận", "Chênh lệch", "Hao hụt tự nhiên",
        "SL trả tồn về ST", "SL chênh lệch CXD", "% Hao hụt", "Tổng GT",
        "Tổng hao hụt", "Tổng ST", "Tổng kho", "Tổng chưa xác định"
    ]
    
    col_gia = next((c for c in df.columns if "giá nhập" in c.lower() or "gia nhap" in c.lower() or "price" in c.lower()), None)
    if col_gia:
        df["Gia_Nhap_Num"] = [parse_number(v) for v in df[col_gia]]
    else:
        df["Gia_Nhap_Num"] = 0.0

    for nc in numeric_targets:
        matched_col = next((c for c in df.columns if nc.lower() in c.lower()), None)
        if matched_col:
            df[f"{nc}_Num"] = [parse_number(v) for v in df[matched_col]]
        else:
            df[f"{nc}_Num"] = 0.0
            
    df["Qty_Chuyen"] = df["Số lượng chuyển_Num"]
    df["Qty_Nhan"] = df["Số lượng nhận_Num"]
    df["Qty_Lech"] = df["Chênh lệch_Num"]
    df["Val_Tong_GT"] = df["Tổng GT_Num"]
    df["Val_Tong_Kho"] = df["Tổng kho_Num"]
    df["Val_Tong_ST"] = df["Tổng ST_Num"]
    df["Val_Tong_HaoHut"] = df["Tổng hao hụt_Num"]
    df["Val_Tong_CXD"] = df["Tổng chưa xác định_Num"]
    
    # 5. Cột trọng tâm AD - AG (DC Xác Nhận & KFM Thông Tin)
    dc_note_col = next((c for c in df.columns if c in ["NOTE.1", "NOTE_1"] or (c.startswith("NOTE") and "1" in c)), None)
    if not dc_note_col and len([c for c in df.columns if "NOTE" in c]) >= 2:
        dc_note_col = [c for c in df.columns if "NOTE" in c][1]
    df["DC_Note"] = df[dc_note_col] if dc_note_col and dc_note_col in df.columns else ""

    kfm_rep_col = next((c for c in df.columns if "kfm phản hồi" in c.lower() or "kfm phan hoi" in c.lower()), None)
    df["KFM_Reply"] = df[kfm_rep_col] if kfm_rep_col and kfm_rep_col in df.columns else ""

    kfm_note_col = next((c for c in df.columns if c in ["NOTE.2", "NOTE_2"] or (c.startswith("NOTE") and "2" in c)), None)
    if not kfm_note_col and len([c for c in df.columns if "NOTE" in c]) >= 3:
        kfm_note_col = [c for c in df.columns if "NOTE" in c][2]
    df["KFM_Note"] = df[kfm_note_col] if kfm_note_col and kfm_note_col in df.columns else ""

    return df
