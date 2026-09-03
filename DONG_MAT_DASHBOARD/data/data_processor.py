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
    
    # Xử lý dấu %
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
            # Nếu phần thập phân có 3 chữ số và phần nguyên khác 0 -> số phân tách hàng nghìn (VD: 16.000 -> 16000)
            if len(parts[1]) == 3 and parts[0] not in ["0", "-0", ""]:
                s = s.replace(".", "")
            else:
                pass
                
    try:
        return float(s)
    except Exception:
        return 0.0


def process_dong_mat_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline làm sạch dữ liệu toàn diện cho 43 cột trong Sheet Chênh lệch ST.
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
    
    # 2. Chuẩn hóa cột ngày tháng
    date_col = next((c for c in df.columns if "Ngày" in c or "date" in c.lower()), None)
    if date_col:
        df["Date_Parsed"] = pd.to_datetime(df[date_col], format="%d/%m/%Y", errors="coerce")
        df["Date_Str"] = df["Date_Parsed"].dt.strftime("%d/%m/%Y").fillna(df[date_col].astype(str))
    else:
        df["Date_Parsed"] = pd.NaT
        df["Date_Str"] = "Không rõ"
        
    # 3. Chuẩn hóa tất cả các cột văn bản (loại bỏ triệt để NaN, None, whitespace)
    for c in df.columns:
        if c != "Date_Parsed":
            df[c] = df[c].fillna("").astype(str).replace(["nan", "None", "NULL", "null", "<NA>"], "").str.strip()
            
    # Chuẩn hóa Nhóm hàng (MÁT, ĐÔNG)
    if "Nhóm hàng" in df.columns:
        df["Nhóm hàng"] = df["Nhóm hàng"].str.upper()
        df["Nhóm hàng"] = df["Nhóm hàng"].apply(lambda x: "MÁT" if "MÁT" in x or "MAT" in x else ("ĐÔNG" if "ĐÔNG" in x or "DONG" in x else x))
        
    # Chuẩn hóa Loại Lỗi
    if "Lỗi" in df.columns:
        df["Lỗi"] = df["Lỗi"].apply(lambda x: "Chưa phân loại" if not x or x.lower() in ["nan", ""] else x)
        
    # Chuẩn hóa Tình trạng Claim DC
    if "DC xác nhận" in df.columns:
        df["Claim_Status"] = df["DC xác nhận"].apply(
            lambda x: "Chưa phản hồi" if not x or x.lower() in ["nan", ""] else x
        )
    else:
        df["Claim_Status"] = "Chưa phản hồi"
        
    # 4. Chuẩn hóa các cột số liệu & tính toán tài chính
    numeric_targets = [
        "Số lượng chuyển", "Số lượng nhận", "Chênh lệch", "Hạo hụt tự nhiên",
        "SL trả tồn về ST", "SL chênh lệch CXD", "% Hao hụt", "Tổng GT",
        "Tổng hao hụt", "Tổng ST", "Tổng kho", "Tổng chưa xác định"
    ]
    
    # Cột Giá nhập
    col_gia = next((c for c in df.columns if "Giá nhập" in c), None)
    if col_gia:
        df["Gia_Nhap_Num"] = df[col_gia].apply(parse_number)
    else:
        df["Gia_Nhap_Num"] = 0.0

    for nc in numeric_targets:
        matched_col = next((c for c in df.columns if nc.lower() in c.lower()), None)
        if matched_col:
            df[f"{nc}_Num"] = df[matched_col].apply(parse_number)
        else:
            df[f"{nc}_Num"] = 0.0
            
    # Tên chuẩn hóa rút gọn cho các cột tính toán
    df["Qty_Chuyen"] = df["Số lượng chuyển_Num"]
    df["Qty_Nhan"] = df["Số lượng nhận_Num"]
    df["Qty_Lech"] = df["Chênh lệch_Num"]
    df["Val_Tong_GT"] = df["Tổng GT_Num"]
    df["Val_Tong_Kho"] = df["Tổng kho_Num"]
    df["Val_Tong_ST"] = df["Tổng ST_Num"]
    df["Val_Tong_HaoHut"] = df["Tổng hao hụt_Num"]
    df["Val_Tong_CXD"] = df["Tổng chưa xác định_Num"]
    
    # 5. Chuẩn hóa 4 Cột Trọng Tâm AD - AG (DC Xác Nhận & KFM Thông Tin)
    # Cột AD: DC xác nhận
    df["DC_Confirm"] = df["DC xác nhận"] if "DC xác nhận" in df.columns else ""
    
    # Cột AE: NOTE của DC phản hồi
    dc_note_col = next((c for c in df.columns if c in ["NOTE.1", "NOTE_1"] or (c.startswith("NOTE") and "1" in c)), None)
    if not dc_note_col and len([c for c in df.columns if "NOTE" in c]) >= 2:
        dc_note_col = [c for c in df.columns if "NOTE" in c][1]
    df["DC_Note"] = df[dc_note_col] if dc_note_col and dc_note_col in df.columns else ""

    # Cột AF: KFM phản hồi
    df["KFM_Reply"] = df["KFM phản hồi"] if "KFM phản hồi" in df.columns else ""

    # Cột AG: NOTE của KFM thông tin
    kfm_note_col = next((c for c in df.columns if c in ["NOTE.2", "NOTE_2"] or (c.startswith("NOTE") and "2" in c)), None)
    if not kfm_note_col and len([c for c in df.columns if "NOTE" in c]) >= 3:
        kfm_note_col = [c for c in df.columns if "NOTE" in c][2]
    df["KFM_Note"] = df[kfm_note_col] if kfm_note_col and kfm_note_col in df.columns else ""

    # 6. Tạo cột tìm kiếm tổng hợp (Search Index)
    def safe_col(col_name):
        if col_name in df.columns:
            return df[col_name].fillna("").astype(str)
        return ""

    df["Search_Index"] = (
        safe_col("ID ST") + " " +
        safe_col("Chi nhánh nhận") + " " +
        safe_col("Mã hàng") + " " +
        safe_col("Tên SP") + " " +
        safe_col("PT chuyển hàng") + " " +
        safe_col("Mã thùng") + " " +
        safe_col("TO") + " " +
        safe_col("Lỗi") + " " +
        safe_col("DC_Confirm") + " " +
        safe_col("DC_Note") + " " +
        safe_col("KFM_Reply") + " " +
        safe_col("KFM_Note")
    ).str.lower()
    
    return df
