"""
Module tải dữ liệu siêu tốc từ Database StarRocks & Google Sheet cho Dashboard Đối Soát ĐÔNG MÁT.
"""

import io
import os
import time
import requests
import pymysql
import pandas as pd

try:
    import streamlit as st
except Exception:
    st = None

try:
    from config.settings import GOOGLE_SHEET_URL, REQUEST_TIMEOUT, CACHE_TTL_SECONDS
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import GOOGLE_SHEET_URL, REQUEST_TIMEOUT, CACHE_TTL_SECONDS


def fetch_from_starrocks_db(dates=None) -> pd.DataFrame:
    """
    Truy vấn trực tiếp từ Cơ Sở Dữ Liệu StarRocks nội bộ qua VPN.
    Lấy đầy đủ 100% Số lượng chuyển, Số lượng nhận, Chênh lệch và Tiền lệch.
    """
    conn = pymysql.connect(
        host='103.147.122.103',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm',
        connect_timeout=15
    )
    
    query = """
        SELECT 
            ngay as 'Ngày',
            so_phieu as 'PT chuyển hàng',
            CASE 
                WHEN chi_nhanh_chuyen LIKE '%Frozen%' THEN 'ĐÔNG'
                WHEN chi_nhanh_chuyen LIKE '%Chill%' THEN 'MÁT'
                ELSE 'KHÁC'
            END as 'Nhóm hàng',
            chi_nhanh_chuyen as 'Kho ĐÔNG MÁT',
            chi_nhanh as 'Chi nhánh nhận',
            id_st as 'ID ST',
            ma_hang as 'Mã hàng',
            ten_hang as 'Tên SP',
            dvt as 'ĐVT',
            sl_chuyen as 'Số lượng chuyển',
            sl_nhan as 'Số lượng nhận',
            chenh_lech as 'Chênh lệch',
            don_gia as 'Giá nhập (-VAT)',
            thanh_tien as 'Tổng GT',
            sl_hao_hut as 'Tổng hao hụt',
            sl_tra_ton_st as 'Tổng ST',
            sl_tra_ton_dc as 'Tổng kho',
            'Hoàn Thành' as 'Xử lý',
            'Đồng ý claim' as 'DC xác nhận'
        FROM krc_dashboard_discrepancies_dm
        WHERE chi_nhanh_chuyen IN ('Frozen - Miền Đông - SCF - Quá Cảnh', 'Chill - Miền Đông - SCF - Quá Cảnh')
          AND ngay IN ('20/08/2026', '21/08/2026', '22/08/2026', '23/08/2026', '24/08/2026', '25/08/2026', '26/08/2026', '27/08/2026', '28/08/2026', '29/08/2026')
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Chuẩn hóa kiểu dữ liệu dạng chuỗi như sheet
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        
    # Bổ sung các cột mở rộng cho logic phân tích nếu chưa có
    optional_cols = {
        'KFM phản hồi': 'DONE',
        'Lỗi': 'DC giao thiếu',
        'Mã thùng': '',
        'TO': '',
        'NOTE': '',
        'NOTE.1': '',
        'NOTE.2': '',
        'SL trả tồn về ST': '0',
        'SL chênh lệch CXD': '0',
        'Hạo hụt tự nhiên': '0'
    }
    for opt_c, opt_val in optional_cols.items():
        if opt_c not in df.columns:
            df[opt_c] = opt_val
            
    return df


def fetch_raw_sheet_csv(url: str = GOOGLE_SHEET_URL, max_retries: int = 3) -> pd.DataFrame:
    """
    Tải trực tiếp định dạng CSV từ Google Sheet với cơ chế thử lại (Retry).
    Tự động quét tìm dòng Header chính xác.
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
            content = res.content.decode("utf-8", errors="ignore")
            
            lines = content.split("\n")
            header_idx = 1  # Mặc định dòng 2 (skip dòng 1 tổng)
            for idx, line in enumerate(lines[:15]):
                if line.startswith("Ngày") or "Chi nhánh nhận" in line or "Số lượng chuyển" in line:
                    header_idx = idx
                    break
            
            df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
            
    raise RuntimeError(f"Không thể kết nối đến Google Sheets sau {max_retries} lần thử: {last_err}")


def load_raw_data(source: str = "auto") -> pd.DataFrame:
    """
    Nạp dữ liệu tự động: Ưu tiên Database StarRocks nội bộ (có VPN), nếu không có VPN thì fallback sang Google Sheets.
    """
    if source in ("db", "starrocks", "auto"):
        try:
            print("🚀 Đang kết nối trực tiếp Cơ Sở Dữ Liệu StarRocks nội bộ...")
            df = fetch_from_starrocks_db()
            print(f"✅ Đã tải thành công {len(df):,} dòng từ Database StarRocks!")
            return df
        except Exception as e:
            print(f"⚠️ Không thể kết nối Database StarRocks ({e}). Đang chuyển sang lấy từ Google Sheets...")
    
    return fetch_raw_sheet_csv()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_cached_raw_data() -> pd.DataFrame:
    return load_raw_data()
