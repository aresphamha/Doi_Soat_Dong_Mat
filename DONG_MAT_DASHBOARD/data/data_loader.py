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
    from config.settings import (
        GOOGLE_SHEET_URL, GOOGLE_SHEET_THIT_CA_URL, GOOGLE_SHEET_THIT_CA_NEW_URL,
        REQUEST_TIMEOUT, CACHE_TTL_SECONDS
    )
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import (
        GOOGLE_SHEET_URL, GOOGLE_SHEET_THIT_CA_URL, GOOGLE_SHEET_THIT_CA_NEW_URL,
        REQUEST_TIMEOUT, CACHE_TTL_SECONDS
    )


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
    
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        
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


def fetch_raw_sheet_csv(url: str = GOOGLE_SHEET_URL, default_group: str = None, max_retries: int = 3) -> pd.DataFrame:
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
            header_idx = 1
            for idx, line in enumerate(lines[:15]):
                if line.startswith("Ngày") or "Chi nhánh nhận" in line or "Số lượng chuyển" in line:
                    header_idx = idx
                    break
            
            df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]

            # Chuẩn hóa tên cột đồng nhất
            rename_map = {
                "Tên Hàng": "Tên SP",
                "Tổng kho thịt cá": "Tổng kho",
                "Kho thịt cá": "Kho ĐÔNG MÁT"
            }
            df.rename(columns=rename_map, inplace=True)

            if default_group:
                df["Nhóm hàng"] = default_group
            elif "Nhóm hàng" not in df.columns:
                df["Nhóm hàng"] = "KHÁC"

            return df
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
            
    raise RuntimeError(f"Không thể kết nối đến Google Sheet ({url}) sau {max_retries} lần thử: {last_err}")


def fetch_all_sources_combined() -> pd.DataFrame:
    """
    Tải và hợp nhất toàn bộ dữ liệu từ 3 nguồn:
    1. Sheet Đông Mát Gốc (Mát & Đông)
    2. Sheet Thịt Cá T7+T8 (KFM - SCF)
    3. Sheet Thịt Cá 28.08 - 09.26 (KFM - SCF) Mới
    """
    dfs = []
    
    # 1. Sheet Đông Mát Gốc
    try:
        print("📥 Đang tải Sheet 1/3: Đối Soát Đông Mát Gốc...")
        df_dm = fetch_raw_sheet_csv(GOOGLE_SHEET_URL)
        print(f"   -> Đã tải {len(df_dm):,} dòng (Đông Mát)")
        dfs.append(df_dm)
    except Exception as e:
        print(f"⚠️ Lỗi tải Sheet Đông Mát: {e}")

    # 2. Sheet Thịt Cá T7+T8
    try:
        print("📥 Đang tải Sheet 2/3: Đối Soát Thịt Cá Tháng 7 + 8...")
        df_tc1 = fetch_raw_sheet_csv(GOOGLE_SHEET_THIT_CA_URL, default_group="THỊT CÁ")
        print(f"   -> Đã tải {len(df_tc1):,} dòng (Thịt Cá T7+T8)")
        dfs.append(df_tc1)
    except Exception as e:
        print(f"⚠️ Lỗi tải Sheet Thịt Cá T7+T8: {e}")

    # 3. Sheet Thịt Cá Mới (28.08 - 09.26)
    try:
        print("📥 Đang tải Sheet 3/3: Đối Soát Thịt Cá 28.08 - 09.26 (Mới)...")
        df_tc2 = fetch_raw_sheet_csv(GOOGLE_SHEET_THIT_CA_NEW_URL, default_group="THỊT CÁ")
        print(f"   -> Đã tải {len(df_tc2):,} dòng (Thịt Cá Mới)")
        dfs.append(df_tc2)
    except Exception as e:
        print(f"⚠️ Lỗi tải Sheet Thịt Cá Mới: {e}")

    if not dfs:
        raise RuntimeError("Không thể tải được dữ liệu từ bất kỳ nguồn Google Sheet nào!")

    df_combined = pd.concat(dfs, ignore_index=True)
    print(f"✅ Tổng hợp dữ liệu thành công: {len(df_combined):,} dòng trên toàn hệ thống!")
    return df_combined


def load_raw_data(source: str = "auto") -> pd.DataFrame:
    return fetch_all_sources_combined()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_cached_raw_data() -> pd.DataFrame:
    return load_raw_data()

