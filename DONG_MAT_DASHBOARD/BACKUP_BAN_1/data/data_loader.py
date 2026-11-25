"""
Module tải dữ liệu siêu tốc từ Google Sheet cho Dashboard Đối Soát ĐÔNG MÁT.
"""

import io
import time
import requests
import pandas as pd
import streamlit as st

try:
    from config.settings import GOOGLE_SHEET_URL, REQUEST_TIMEOUT, CACHE_TTL_SECONDS
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import GOOGLE_SHEET_URL, REQUEST_TIMEOUT, CACHE_TTL_SECONDS


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


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_cached_raw_data() -> pd.DataFrame:
    """
    Hàm bọc cache của Streamlit giúp nạp dữ liệu siêu nhanh trong 1 giây sau lần đầu tải.
    """
    return fetch_raw_sheet_csv()
