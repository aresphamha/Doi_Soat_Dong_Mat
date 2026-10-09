# -*- coding: utf-8 -*-
"""
Module tải dữ liệu từ Google Sheets cho Dashboard Đối Soát ĐÔNG MÁT & THỊT CÁ.
Hỗ trợ hợp nhất 6 nguồn dữ liệu từ Google Sheets:
- 3 nguồn Đông - Mát: Đông Mát 28.07-09.2026, Mát T10, Đông T10
- 3 nguồn Thịt Cá: Thịt Cá T7-T8, Thịt Cá 28.08-09.26, Thịt Cá T10.26
"""

import io
import os
import time
import requests
import pandas as pd

try:
    from config.settings import (
        GOOGLE_SHEET_DONG_MAT_T7_T9_URL,
        GOOGLE_SHEET_MAT_T10_URL,
        GOOGLE_SHEET_DONG_T10_URL,
        GOOGLE_SHEET_THIT_CA_T7_T8_URL,
        GOOGLE_SHEET_THIT_CA_2808_0926_URL,
        GOOGLE_SHEET_THIT_CA_T10_URL,
        GOOGLE_SHEET_URL,
        GOOGLE_SHEET_THIT_CA_URL,
        GOOGLE_SHEET_THIT_CA_NEW_URL,
        REQUEST_TIMEOUT
    )
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import (
        GOOGLE_SHEET_DONG_MAT_T7_T9_URL,
        GOOGLE_SHEET_MAT_T10_URL,
        GOOGLE_SHEET_DONG_T10_URL,
        GOOGLE_SHEET_THIT_CA_T7_T8_URL,
        GOOGLE_SHEET_THIT_CA_2808_0926_URL,
        GOOGLE_SHEET_THIT_CA_T10_URL,
        GOOGLE_SHEET_URL,
        GOOGLE_SHEET_THIT_CA_URL,
        GOOGLE_SHEET_THIT_CA_NEW_URL,
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
                    ("chi nhánh nhận" in line_lower and ("mã hàng" in line_lower or "barcode" in line_lower or "tên" in line_lower)) or
                    ("chi nhanh nhan" in line_lower and ("ma hang" in line_lower or "barcode" in line_lower or "ten" in line_lower))):
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
                elif c_lower in ["barcode", "mã sp", "ma sp"]:
                    # Dự phòng trường hợp cột Barcode thay cho Mã hàng
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
                # Nếu nguồn đã chỉ định rõ nhóm hàng mặc định (MÁT / ĐÔNG / THỊT CÁ)
                if "Nhóm hàng" not in df.columns or df["Nhóm hàng"].isna().all():
                    df["Nhóm hàng"] = default_group
                else:
                    df["Nhóm hàng"] = df["Nhóm hàng"].fillna(default_group)
                    # Nếu sheet thuần 1 nhóm (vd sheet Mát T10 hoặc Đông T10), gán đồng nhất
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
    Tải và hợp nhất toàn bộ dữ liệu từ 6 nguồn Google Sheets:
    1. Sheet Đông Mát Gốc (28.07 - 09.2026) -> Mát & Đông
    2. Sheet Mát Tháng 10 -> Mát
    3. Sheet Đông Tháng 10 -> Đông
    4. Sheet Thịt Cá Tháng 7 + 8 -> Thịt Cá
    5. Sheet Thịt Cá 28.08 - 09.26 -> Thịt Cá
    6. Sheet Thịt Cá Tháng 10.26 -> Thịt Cá
    """
    dfs = []
    
    sources = [
        # --- Nhóm Đông - Mát ---
        ("1/6: Đông Mát 28.07 - 09.2026 (Gốc)", GOOGLE_SHEET_DONG_MAT_T7_T9_URL, None),
        ("2/6: Mát Tháng 10 (KFM - SCF)", GOOGLE_SHEET_MAT_T10_URL, "MÁT"),
        ("3/6: Đông Tháng 10 (KFM - SCF)", GOOGLE_SHEET_DONG_T10_URL, "ĐÔNG"),
        # --- Nhóm Thịt Cá ---
        ("4/6: Thịt Cá Tháng 7 + 8 (KFM - SCF)", GOOGLE_SHEET_THIT_CA_T7_T8_URL, "THỊT CÁ"),
        ("5/6: Thịt Cá 28.08 - 09.26 (KFM - SCF)", GOOGLE_SHEET_THIT_CA_2808_0926_URL, "THỊT CÁ"),
        ("6/6: Thịt Cá Tháng 10.26 (KFM - SCF)", GOOGLE_SHEET_THIT_CA_T10_URL, "THỊT CÁ"),
    ]
    
    for label, url, def_grp in sources:
        try:
            print(f"📥 Đang tải Sheet {label}...")
            df = fetch_raw_sheet_csv(url, default_group=def_grp)
            print(f"   -> Đã tải {len(df):,} dòng ({label.split(':')[1].strip()})")
            dfs.append(df)
        except Exception as e:
            print(f"❌ Lỗi tải Sheet {label}: {e}")

    if not dfs:
        raise RuntimeError("Không thể tải bất kỳ Google Sheet nào trong 6 nguồn!")

    # Gộp tất cả các nguồn
    df_combined = pd.concat(dfs, ignore_index=True, sort=False)

    # Điền mapping CLV2 & CLV3 theo Mã hàng cho các dòng còn trống
    if "CLV2" in df_combined.columns and "Mã hàng" in df_combined.columns:
        clv2_map = df_combined[df_combined["CLV2"].notna() & (df_combined["CLV2"] != "")].groupby("Mã hàng")["CLV2"].first().to_dict()
        df_combined["CLV2"] = df_combined["CLV2"].fillna(df_combined["Mã hàng"].map(clv2_map)).fillna("")
    if "CLV3" in df_combined.columns and "Mã hàng" in df_combined.columns:
        clv3_map = df_combined[df_combined["CLV3"].notna() & (df_combined["CLV3"] != "")].groupby("Mã hàng")["CLV3"].first().to_dict()
        df_combined["CLV3"] = df_combined["CLV3"].fillna(df_combined["Mã hàng"].map(clv3_map)).fillna("")

    print(f"✅ HỢP NHẤT TOÀN BỘ 6 NGUỒN: Tổng cộng {len(df_combined):,} dòng dữ liệu!")
    return df_combined
