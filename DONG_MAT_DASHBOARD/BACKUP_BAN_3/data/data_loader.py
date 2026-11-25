# -*- coding: utf-8 -*-
"""
Module tải dữ liệu từ Google Sheets cho Dashboard Đối Soát ĐÔNG MÁT.
"""

import io
import os
import time
import requests
import pandas as pd

try:
    from config.settings import (
        GOOGLE_SHEET_URL, GOOGLE_SHEET_THIT_CA_URL, GOOGLE_SHEET_THIT_CA_NEW_URL,
        REQUEST_TIMEOUT
    )
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import (
        GOOGLE_SHEET_URL, GOOGLE_SHEET_THIT_CA_URL, GOOGLE_SHEET_THIT_CA_NEW_URL,
        REQUEST_TIMEOUT
    )


def deduplicate_columns(columns):
    new_cols = []
    seen = {}
    for col in columns:
        c_str = str(col).strip()
        if not c_str or "unnamed" in c_str.lower():
            c_str = "Extra"
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}.{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    return new_cols


def fetch_raw_sheet_csv(url: str, default_group: str = None, max_retries: int = 3) -> pd.DataFrame:
    """
    Tải trực tiếp định dạng CSV từ Google Sheet với cơ chế thử lại (Retry).
    Tự động quét tìm dòng Header chính xác (dòng bắt đầu bằng Ngày / Tgian nhận / Chi nhánh nhận).
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
            
            try:
                content = res.content.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = res.content.decode("utf-8", errors="replace")
                
            lines = content.splitlines()
            header_idx = 0
            for idx, line in enumerate(lines[:15]):
                line_lower = line.lower()
                # Tìm dòng Header thực sự chứa các cột cốt lõi
                if (line.startswith("Ngày") or line.startswith("ngay") or 
                    line.startswith("Tgian nhận") or line.startswith("tgian") or
                    ("chi nhánh nhận" in line_lower and "mã hàng" in line_lower) or
                    ("chi nhanh nhan" in line_lower and "ma hang" in line_lower)):
                    header_idx = idx
                    break
            
            csv_data = "\n".join(lines[header_idx:])
            df = pd.read_csv(io.StringIO(csv_data), dtype=str)
            df.columns = deduplicate_columns(df.columns)

            # Chuẩn hóa tên cột đồng nhất
            rename_map = {}
            for col in df.columns:
                c_clean = str(col).strip()
                c_lower = c_clean.lower()
                if c_lower in ["tên hàng", "ten hang"]:
                    rename_map[col] = "Tên SP"
                elif c_lower in ["tổng kho thịt cá", "tong kho thit ca"]:
                    rename_map[col] = "Tổng kho"
                elif c_lower in ["kho thịt cá", "kho thit ca"]:
                    rename_map[col] = "Kho ĐÔNG MÁT"
                elif "chi nhánh nhận" in c_lower or "chi nhanh nhan" in c_lower:
                    rename_map[col] = "Chi nhánh nhận"
                elif c_lower in ["nhóm hàng", "nhom hang"]:
                    rename_map[col] = "Nhóm hàng"
                elif "ngày" in c_lower or c_lower == "ngay":
                    rename_map[col] = "Ngày"
                elif "mã hàng" in c_lower or "ma hang" in c_lower:
                    rename_map[col] = "Mã hàng"
                elif "số lượng chuyển" in c_lower or "sl chuyen" in c_lower:
                    rename_map[col] = "Số lượng chuyển"
                elif "số lượng nhận" in c_lower or "sl nhan" in c_lower:
                    rename_map[col] = "Số lượng nhận"
                elif "chênh lệch" in c_lower or "chenh lech" in c_lower:
                    rename_map[col] = "Chênh lệch"
                elif "giá nhập" in c_lower or "gia nhap" in c_lower:
                    rename_map[col] = "Giá nhập (-VAT)"
                elif "tổng gt" in c_lower or "tong gt" in c_lower:
                    rename_map[col] = "Tổng GT"
                elif "tổng hao hụt" in c_lower or "tong hao hut" in c_lower:
                    rename_map[col] = "Tổng hao hụt"
                elif "tổng st" in c_lower or "tong st" in c_lower:
                    rename_map[col] = "Tổng ST"
                elif "tổng kho" in c_lower or "tong kho" in c_lower:
                    rename_map[col] = "Tổng kho"
                elif "lỗi" in c_lower or c_lower == "loi":
                    rename_map[col] = "Lỗi"
                elif "dc xác nhận" in c_lower or "dc xac nhan" in c_lower:
                    rename_map[col] = "DC xác nhận"
                elif "kfm phản hồi" in c_lower or "kfm phan hoi" in c_lower:
                    rename_map[col] = "KFM phản hồi"
                elif "clv2" in c_lower:
                    rename_map[col] = "CLV2"
                elif "clv3" in c_lower:
                    rename_map[col] = "CLV3"
                elif "loại hàng" in c_lower or "loai hang" in c_lower:
                    rename_map[col] = "Loại hàng"
                elif "% hao hụt" in c_lower or "% hao hut" in c_lower:
                    rename_map[col] = "% Hao hụt"
                    
            if rename_map:
                df.rename(columns=rename_map, inplace=True)
                df.columns = deduplicate_columns(df.columns)

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
    Tải và hợp nhất toàn bộ dữ liệu từ 3 nguồn Google Sheets:
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
        print(f"❌ Lỗi tải Sheet Đông Mát: {e}")

    # 2. Sheet Thịt Cá T7+T8
    try:
        print("📥 Đang tải Sheet 2/3: Đối Soát Thịt Cá Tháng 7 + 8...")
        df_tc1 = fetch_raw_sheet_csv(GOOGLE_SHEET_THIT_CA_URL, default_group="THỊT CÁ")
        print(f"   -> Đã tải {len(df_tc1):,} dòng (Thịt Cá T7+T8)")
        dfs.append(df_tc1)
    except Exception as e:
        print(f"❌ Lỗi tải Sheet Thịt Cá T7+T8: {e}")

    # 3. Sheet Thịt Cá Mới (28.08 - 09.26)
    try:
        print("📥 Đang tải Sheet 3/3: Đối Soát Thịt Cá 28.08 - 09.26 (Mới)...")
        df_tc2 = fetch_raw_sheet_csv(GOOGLE_SHEET_THIT_CA_NEW_URL, default_group="THỊT CÁ")
        print(f"   -> Đã tải {len(df_tc2):,} dòng (Thịt Cá 28.08 - 09.26)")
        dfs.append(df_tc2)
    except Exception as e:
        print(f"❌ Lỗi tải Sheet Thịt Cá Mới: {e}")

    if not dfs:
        raise RuntimeError("Không thể tải bất kỳ Google Sheet nào trong 3 nguồn!")

    # Gộp tất cả các nguồn
    df_combined = pd.concat(dfs, ignore_index=True, sort=False)

    # Điền mapping CLV2 & CLV3 theo Mã hàng cho các dòng còn trống
    clv2_map = df_combined[df_combined["CLV2"].notna() & (df_combined["CLV2"] != "")].groupby("Mã hàng")["CLV2"].first().to_dict()
    clv3_map = df_combined[df_combined["CLV3"].notna() & (df_combined["CLV3"] != "")].groupby("Mã hàng")["CLV3"].first().to_dict()
    
    if "Mã hàng" in df_combined.columns:
        df_combined["CLV2"] = df_combined["CLV2"].fillna(df_combined["Mã hàng"].map(clv2_map)).fillna("")
        df_combined["CLV3"] = df_combined["CLV3"].fillna(df_combined["Mã hàng"].map(clv3_map)).fillna("")

    print(f"✅ HỢP NHẤT TOÀN BỘ 3 NGUỒN: Tổng cộng {len(df_combined):,} dòng dữ liệu!")
    return df_combined
