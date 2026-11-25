"""
ĐỒNG BỘ DỮ LIỆU BÁO CÁO LOGISTICS KHO KHÔ FMCG (SEEDLOG)
Nguồn: Google Sheet gid=1213759414 (Thọ - Hà)
Chỉ lọc và lấy dữ liệu từ tháng 11/2026 trở về sau.
Xuất ra file daily_details/fmcg_matrix.js và DONG_MAT_DASHBOARD/daily_details/fmcg_matrix.js
"""

import os
import io
import csv
import json
import requests
from datetime import datetime, date

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZTLRCJjr-8surASFt9Rm6M-2SYJZfa2dc2phS6vg4_k/export?format=csv&gid=1213759414"

def parse_col_date(col_str, col_idx):
    s = col_str.strip().replace('-', '/')
    parts = s.split('/')
    if len(parts) != 3:
        return None
    try:
        p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    year = p3 if p3 >= 2000 else 2000 + p3
    
    # Col 1..61 are Oct and Sept 2026
    if col_idx <= 61:
        if p1 == 10:
            return date(year, 10, p2)
        else:
            return date(year, 9, p1)
    else:
        # Col 62 onwards: November 2026 onwards
        # In this sheet, dates are MM/DD/YYYY
        if p1 >= 11:
            return date(year, p1, p2)
        elif p2 >= 11:
            return date(year, p2, p1)
        elif year > 2026:
            if p1 <= 12:
                return date(year, p1, p2)
            return date(year, p2, p1)
    return None

def fetch_and_build_fmcg_matrix():
    print(f"[*] Đang tải dữ liệu Google Sheet FMCG: {SHEET_URL}")
    r = requests.get(SHEET_URL, timeout=20)
    r.raise_for_status()
    
    reader = csv.reader(io.StringIO(r.text))
    rows = list(reader)
    if len(rows) < 4:
        raise ValueError("Sheet không đủ số dòng dữ liệu")
    
    header = rows[2]
    
    # Tìm các cột từ tháng 11/2026 trở đi (>= 2026-11-01)
    date_cols = []
    for idx, col in enumerate(header[1:], start=1):
        col_str = col.strip()
        if not col_str:
            continue
        d = parse_col_date(col_str, idx)
        if d and (d.year > 2026 or (d.year == 2026 and d.month >= 11)):
            date_cols.append({
                "col_idx": idx,
                "raw_date": col_str,
                "date_obj": d,
                "iso_date": d.strftime("%Y-%m-%d"),
                "display_date": d.strftime("%d/%m/%Y"),
                "short_date": d.strftime("%d/%m")
            })
            
    # Sắp xếp theo ngày tăng dần (từ 01/11/2026 đến ngày mới nhất)
    date_cols.sort(key=lambda x: x["date_obj"])
    print(f"[+] Tìm thấy {len(date_cols)} cột ngày từ tháng 11/2026 trở đi: {date_cols[0]['display_date']} -> {date_cols[-1]['display_date']}")
    
    # Định nghĩa cấu trúc các khối Section chuẩn nghiệp vụ
    sections_def = [
        {
            "id": "sec_san_luong",
            "title": "1. SẢN LƯỢNG HÀNG HÓA (SL)",
            "icon": "fa-solid fa-boxes-stacked",
            "accent": "#38bdf8",
            "row_range": (3, 10), # 0-indexed: row 3 (Row 4 in Excel: SL chuyển) to row 9 (Row 10: SL dư)
        },
        {
            "id": "sec_gia_tri",
            "title": "2. GIÁ TRỊ HÀNG HÓA (VNĐ)",
            "icon": "fa-solid fa-coins",
            "accent": "#f59e0b",
            "row_range": (10, 17), # row 10 (Row 11: Giá trị chuyển) to row 16 (Row 17: Giá trị dư)
        },
        {
            "id": "sec_ty_le",
            "title": "3. TỶ LỆ CHÊNH LỆCH & HOÀN TẤT (%)",
            "icon": "fa-solid fa-percent",
            "accent": "#ec4899",
            "row_range": (17, 23), # row 17 (Row 18) to row 22 (Row 23)
        },
        {
            "id": "sec_sieu_thi",
            "title": "4. SỐ LƯỢNG SIÊU THỊ / CỬA HÀNG",
            "icon": "fa-solid fa-shop",
            "accent": "#10b981",
            "row_range": (23, 30), # row 23 (Row 24) to row 29 (Row 30)
        },
        {
            "id": "sec_dc_phan_hoi",
            "title": "5. DC XÁC NHẬN & PHẢN HỒI",
            "icon": "fa-solid fa-truck-ramp-box",
            "accent": "#8b5cf6",
            "row_range": (30, 42), # row 30 (Row 31) to row 41 (Row 42)
        },
        {
            "id": "sec_luy_ke",
            "title": "6. LŨY KẾ TOÀN KỲ & TỒN KHO",
            "icon": "fa-solid fa-chart-line",
            "accent": "#06b6d4",
            "row_range": (42, 45), # row 42 (Row 43) to row 44 (Row 45)
        }
    ]
    
    sections = []
    all_metrics = []
    
    for sec in sections_def:
        sec_rows = []
        r_start, r_end = sec["row_range"]
        for r_i in range(r_start, min(r_end, len(rows))):
            r = rows[r_i]
            metric_name = r[0].strip()
            if not metric_name:
                continue
            
            # Đọc giá trị theo từng ngày
            values_by_date = {}
            for dc in date_cols:
                col_i = dc["col_idx"]
                val = r[col_i].strip() if col_i < len(r) else ""
                values_by_date[dc["iso_date"]] = val
                
            row_item = {
                "row_idx": r_i + 1,
                "name": metric_name,
                "section_id": sec["id"],
                "values": values_by_date
            }
            sec_rows.append(row_item)
            all_metrics.append(row_item)
            
        sections.append({
            "id": sec["id"],
            "title": sec["title"],
            "icon": sec["icon"],
            "accent": sec["accent"],
            "rows": sec_rows
        })
        
    # Tạo Summary Cards từ ngày mới nhất (latest date)
    latest_dc = date_cols[-1]
    latest_iso = latest_dc["iso_date"]
    
    def get_val(metric_name):
        for m in all_metrics:
            if m["name"].lower() == metric_name.lower():
                return m["values"].get(latest_iso, "")
        return ""

    summary_cards = {
        "latest_date": latest_dc["display_date"],
        "tong_luy_ke": get_val("Tổng giá trị chuyển lũy kế"),
        "ton_kho_chenh_lech": get_val("Tồn kho chênh lệch"),
        "ty_le_chenh_lech": get_val("Tỷ lệ chênh lệch chuyển hàng"),
        "sl_chuyen_ngay": get_val("SL chuyển"),
        "sl_chenh_lech_ngay": get_val("SL chênh lệch"),
        "gia_tri_chuyen_ngay": get_val("Giá trị chuyển"),
        "gia_tri_chenh_lech_ngay": get_val("Giá trị chênh lệch"),
        "sl_st_chenh_lech": get_val("SL ST chênh lệch"),
        "gia_tri_tra_dc": get_val("Giá trị trả DC")
    }
    
    dates_meta = [{
        "iso": dc["iso_date"],
        "display": dc["display_date"],
        "short": dc["short_date"],
        "raw": dc["raw_date"]
    } for dc in date_cols]
    
    data_payload = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "filter_scope": "Từ 01/11/2026 trở về sau",
        "dates": dates_meta,
        "summary": summary_cards,
        "sections": sections
    }
    
    js_content = f"// Dữ liệu Báo cáo Logistics FMCG (Seedlog) - Tự động cập nhật từ Google Sheet\nwindow.FMCG_MATRIX_DATA = {json.dumps(data_payload, ensure_ascii=False, indent=2)};\n"
    
    # Lưu vào 2 vị trí
    targets = [
        os.path.join("daily_details", "fmcg_matrix.js"),
        os.path.join("DONG_MAT_DASHBOARD", "daily_details", "fmcg_matrix.js")
    ]
    for target in targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"[OK] Đã ghi file: {target}")
        
    print("[SUCCESS] Hoàn thành trích xuất dữ liệu FMCG tháng 11/2026 thành công!")
    return data_payload

if __name__ == "__main__":
    fetch_and_build_fmcg_matrix()
