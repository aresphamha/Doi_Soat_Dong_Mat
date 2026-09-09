# -*- coding: utf-8 -*-
"""
Hệ thống tạo Báo Cáo Web Đối Soát ĐÔNG MÁT Độc Lập Siêu Nhẹ & Tốc Độ Cao.
Hợp nhất dữ liệu từ cả 3 nguồn Google Sheets:
1. Báo cáo gốc ĐÔNG MÁT (Mát & Đông)
2. Báo cáo Thịt Cá Tháng 7 + 8 (KFM - SCF)
3. Báo cáo Thịt Cá 28.08 - 09.26 (KFM - SCF) Mới
"""

import os
import sys
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

try:
    from config.settings import PRODUCT_GROUPS, THEME_COLORS
    from data.data_loader import fetch_all_sources_combined
    from data.data_processor import process_dong_mat_dataframe
except ImportError:
    from DONG_MAT_DASHBOARD.config.settings import PRODUCT_GROUPS, THEME_COLORS
    from DONG_MAT_DASHBOARD.data.data_loader import fetch_all_sources_combined
    from DONG_MAT_DASHBOARD.data.data_processor import process_dong_mat_dataframe


def enrich_business_logic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bổ sung các phân loại nghiệp vụ cho từng dòng dữ liệu.
    """
    df = df.copy()

    # 1. Điểm nhận / Đích đến (Destination)
    def determine_destination(r):
        vk = float(r.get("Val_Tong_Kho", 0.0) or 0.0)
        vst = float(r.get("Val_Tong_ST", 0.0) or 0.0)
        vhh = float(r.get("Val_Tong_HaoHut", 0.0) or 0.0)
        if vk > 0:
            return "Kho ĐÔNG MÁT"
        if vst > 0:
            return "Siêu thị"
        if vhh > 0:
            return "Hao hụt"
        return "Chưa xác định"

    # Vectorized / List comp for destination
    vk_arr = df["Val_Tong_Kho"].values
    vst_arr = df["Val_Tong_ST"].values
    vhh_arr = df["Val_Tong_HaoHut"].values
    destinations = []
    for vk, vst, vhh in zip(vk_arr, vst_arr, vhh_arr):
        if vk > 0:
            destinations.append("Kho ĐÔNG MÁT")
        elif vst > 0:
            destinations.append("Siêu thị")
        elif vhh > 0:
            destinations.append("Hao hụt")
        else:
            destinations.append("Chưa xác định")
    df["Destination"] = destinations

    # 2. Ngưỡng 100k theo Siêu thị - Ngày
    st_col = "ID ST" if "ID ST" in df.columns else "Chi nhánh nhận"
    store_day_totals = df.groupby([st_col, "Date_Str"])["Val_Tong_GT"].transform("sum")
    df["Store_Day_Val_Total"] = store_day_totals
    df["Is_Store_Over_100k"] = store_day_totals >= 100000

    # 3. Trạng thái 3 cấp độ (Status_3Level)
    dc_conf_vals = df["DC_Confirm"].astype(str).str.strip().values
    val_tot_vals = df["Val_Tong_GT"].values
    is_over_vals = df["Is_Store_Over_100k"].values
    vk_vals = df["Val_Tong_Kho"].values
    vst_vals = df["Val_Tong_ST"].values

    status_list = []
    for dc_c, vtot, is_over, vk, vst in zip(dc_conf_vals, val_tot_vals, is_over_vals, vk_vals, vst_vals):
        if dc_c and dc_c.lower() not in ["", "nan", "none", "null"]:
            status_list.append("Đã xử lý")
        elif vk == 0 and vst == 0:
            status_list.append("Đã xử lý")
        elif is_over or vtot >= 100000:
            status_list.append("Cần xử lý gấp")
        else:
            status_list.append("Theo dõi")
    df["Status_3Level"] = status_list

    return df


def filter_dataset(df: pd.DataFrame, group_code: str = 'all', month_filter: str = 'all') -> pd.DataFrame:
    """
    Lọc dữ liệu theo Nhóm Hàng & Tháng.
    """
    sub = df.copy()

    # Lọc Nhóm hàng
    if group_code == 'thit_ca':
        sub = sub[sub["Nhóm hàng"] == "THỊT CÁ"]
    elif group_code == 'mat':
        sub = sub[sub["Nhóm hàng"] == "MÁT"]
    elif group_code == 'dong':
        sub = sub[sub["Nhóm hàng"] == "ĐÔNG"]

    # Lọc Tháng
    if month_filter != 'all' and pd.notnull(sub["Date_Parsed"]).any():
        if month_filter.startswith("Tháng "):
            try:
                m_num = int(month_filter.replace("Tháng ", "").strip())
                sub = sub[sub["Date_Parsed"].dt.month == m_num]
            except Exception:
                pass
        elif month_filter.isdigit():
            m_num = int(month_filter)
            sub = sub[sub["Date_Parsed"].dt.month == m_num]

    return sub


def compute_kpi_summary(df: pd.DataFrame) -> dict:
    """
    Tính toán 6 thẻ chỉ số KPI tổng hợp.
    """
    total_records = len(df)
    total_val = float(df["Val_Tong_GT"].sum()) if total_records > 0 else 0.0
    val_dc = float(df["Val_Tong_Kho"].sum()) if total_records > 0 else 0.0
    val_st = float(df["Val_Tong_ST"].sum()) if total_records > 0 else 0.0
    val_hh = float(df["Val_Tong_HaoHut"].sum()) if total_records > 0 else 0.0
    val_cxd = float(df["Val_Tong_CXD"].sum()) if total_records > 0 else 0.0

    qty_chuyen = float(df["Qty_Chuyen"].sum()) if total_records > 0 else 0.0
    qty_nhan = float(df["Qty_Nhan"].sum()) if total_records > 0 else 0.0
    qty_lech = float(df["Qty_Lech"].sum()) if total_records > 0 else 0.0

    pct_lech = (qty_lech / qty_chuyen * 100) if qty_chuyen > 0 else 0.0

    # Tỷ lệ phản hồi DC
    dc_resolved = len(df[df["DC_Confirm"].astype(str).str.strip().ne("") & ~df["DC_Confirm"].astype(str).str.lower().isin(["nan", "none", "null"])])
    pct_dc_resolved = (dc_resolved / total_records * 100) if total_records > 0 else 0.0

    # ST trên 100k
    st_col = "ID ST" if "ID ST" in df.columns else "Chi nhánh nhận"
    over_100k_stores = df[df["Is_Store_Over_100k"]][st_col].nunique() if total_records > 0 else 0

    return {
        "total_records": total_records,
        "total_val": total_val,
        "val_dc": val_dc,
        "val_st": val_st,
        "val_hh": val_hh,
        "val_cxd": val_cxd,
        "qty_chuyen": qty_chuyen,
        "qty_nhan": qty_nhan,
        "qty_lech": qty_lech,
        "pct_lech": pct_lech,
        "pct_dc_resolved": pct_dc_resolved,
        "over_100k_stores": over_100k_stores
    }


def compute_daily_matrix(df: pd.DataFrame) -> list:
    """
    Tính ma trận chênh lệch theo Ngày & Tháng.
    """
    if df.empty:
        return []

    # Gom theo Date_Str
    grouped = df.groupby("Date_Str", as_index=False).agg(
        date_parsed=("Date_Parsed", "first"),
        qty_chuyen=("Qty_Chuyen", "sum"),
        qty_nhan=("Qty_Nhan", "sum"),
        qty_lech=("Qty_Lech", "sum"),
        val_total=("Val_Tong_GT", "sum"),
        val_dc=("Val_Tong_Kho", "sum"),
        val_st=("Val_Tong_ST", "sum"),
        val_hh=("Val_Tong_HaoHut", "sum"),
        val_cxd=("Val_Tong_CXD", "sum"),
        store_count=("ID ST", "nunique"),
        sku_count=("Mã hàng", "nunique"),
        records_count=("Val_Tong_GT", "count")
    )

    # Sắp xếp theo ngày giảm dần
    grouped = grouped.sort_values(by="date_parsed", ascending=False, na_position="last")

    results = []
    for _, r in grouped.iterrows():
        d_parsed = r["date_parsed"]
        month_str = f"Tháng {d_parsed.month}" if pd.notnull(d_parsed) else "Tháng 8"
        results.append({
            "date": str(r["Date_Str"]),
            "month": month_str,
            "qty_chuyen": float(r["qty_chuyen"]),
            "qty_nhan": float(r["qty_nhan"]),
            "qty_lech": float(r["qty_lech"]),
            "pct_lech": round(float(r["qty_lech"] / r["qty_chuyen"] * 100), 2) if r["qty_chuyen"] > 0 else 0.0,
            "val_total": float(r["val_total"]),
            "val_dc": float(r["val_dc"]),
            "val_st": float(r["val_st"]),
            "val_hh": float(r["val_hh"]),
            "val_cxd": float(r["val_cxd"]),
            "store_count": int(r["store_count"]),
            "sku_count": int(r["sku_count"]),
            "records_count": int(r["records_count"])
        })
    return results


def compute_store_priority_list(df: pd.DataFrame) -> list:
    """
    Tính danh sách siêu thị ưu tiên xử lý (Top lệch lớn).
    """
    if df.empty:
        return []

    st_col = "ID ST" if "ID ST" in df.columns else "Chi nhánh nhận"
    name_col = "Chi nhánh nhận"

    # Group by ST & Date
    st_date_grp = df.groupby([st_col, name_col, "Date_Str"], as_index=False).agg(
        val_total=("Val_Tong_GT", "sum"),
        val_dc=("Val_Tong_Kho", "sum"),
        val_st=("Val_Tong_ST", "sum"),
        val_hh=("Val_Tong_HaoHut", "sum"),
        records_count=("Val_Tong_GT", "count"),
        unresolved_count=("DC_Confirm", lambda x: ((x == "") | (x.isna()) | (x.str.lower().isin(["nan", "none", "null"]))).sum()),
        date_parsed=("Date_Parsed", "first")
    )

    st_date_grp["is_over_100k"] = st_date_grp["val_total"] >= 100000

    # Sắp xếp theo Tiền lệch giảm dần
    st_date_grp = st_date_grp.sort_values(by=["is_over_100k", "val_total"], ascending=[False, False])

    results = []
    for _, r in st_date_grp.head(300).iterrows():
        status = "Đã xử lý" if r["unresolved_count"] == 0 else ("Cần xử lý gấp" if r["is_over_100k"] else "Theo dõi")
        d_parsed = r["date_parsed"]
        month_str = f"Tháng {d_parsed.month}" if pd.notnull(d_parsed) else "Tháng 8"
        results.append({
            "st": str(r[st_col]),
            "name": str(r[name_col]),
            "date": str(r["Date_Str"]),
            "month": month_str,
            "val_total": float(r["val_total"]),
            "val_dc": float(r["val_dc"]),
            "val_st": float(r["val_st"]),
            "val_hh": float(r["val_hh"]),
            "records_count": int(r["records_count"]),
            "status": status,
            "is_over_100k": bool(r["is_over_100k"])
        })
    return results


def compute_error_breakdown(df: pd.DataFrame) -> list:
    """
    Phân loại nguyên nhân lỗi.
    """
    if df.empty:
        return []

    err_grp = df.groupby("Lỗi", as_index=False).agg(
        records_count=("Val_Tong_GT", "count"),
        val_total=("Val_Tong_GT", "sum"),
        val_dc=("Val_Tong_Kho", "sum"),
        val_st=("Val_Tong_ST", "sum"),
        val_hh=("Val_Tong_HaoHut", "sum")
    ).sort_values(by="val_total", ascending=False)

    results = []
    for _, r in err_grp.iterrows():
        results.append({
            "error_type": str(r["Lỗi"]),
            "count": int(r["records_count"]),
            "val_total": float(r["val_total"]),
            "val_dc": float(r["val_dc"]),
            "val_st": float(r["val_st"]),
            "val_hh": float(r["val_hh"])
        })
    return results


def compute_dc_progress(df: pd.DataFrame) -> dict:
    """
    Thống kê tiến độ xử lý của DC (Đã phản hồi vs Chưa phản hồi).
    """
    if df.empty:
        return {"total_cases": 0, "resolved_cases": 0, "pending_cases": 0, "pct_resolved": 0.0}

    total = len(df)
    has_conf = df["DC_Confirm"].astype(str).str.strip().ne("") & ~df["DC_Confirm"].astype(str).str.lower().isin(["nan", "none", "null"])
    resolved = int(has_conf.sum())
    pending = total - resolved
    pct = round(resolved / total * 100, 1) if total > 0 else 0.0

    return {
        "total_cases": total,
        "resolved_cases": resolved,
        "pending_cases": pending,
        "pct_resolved": pct
    }


def generate_all_data_bundles(df: pd.DataFrame) -> dict:
    """
    Tính toán sẵn toàn bộ bundles dữ liệu cho cả 4 nhóm ngành hàng và tất cả các tháng.
    """
    groups = ['all', 'thit_ca', 'mat', 'dong']
    
    # Tìm các tháng có trong dữ liệu
    months = ['all']
    if pd.notnull(df["Date_Parsed"]).any():
        avail_m = sorted(df["Date_Parsed"].dropna().dt.month.unique().tolist())
        for m in avail_m:
            months.append(f"Tháng {m}")

    bundles = {}
    for g in groups:
        bundles[g] = {}
        for m in months:
            sub = filter_dataset(df, group_code=g, month_filter=m)
            bundles[g][m] = {
                "kpi": compute_kpi_summary(sub),
                "daily_matrix": compute_daily_matrix(sub),
                "store_priority": compute_store_priority_list(sub),
                "error_breakdown": compute_error_breakdown(sub),
                "dc_progress": compute_dc_progress(sub)
            }
    return bundles, months


def build_and_export_web_report():
    """
    Pipeline hoàn chỉnh: Tải dữ liệu 3 nguồn -> Tính toán -> Xuất file JS ngày -> Xuất HTML báo cáo.
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
    df_enriched = enrich_business_logic(df_clean)
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

    # Map and rename columns cleanly for JSON export
    export_cols = {
        "ID ST": "st",
        "Chi nhánh nhận": "store_name",
        "Nhóm hàng": "group",
        "Mã hàng": "sku",
        "Tên SP": "sku_name",
        "Qty_Chuyen": "qty_transfer",
        "Qty_Nhan": "qty_receive",
        "Qty_Lech": "qty_diff",
        "Gia_Nhap_Num": "price",
        "Val_Tong_GT": "val_total",
        "Destination": "destination",
        "Lỗi": "error",
        "Is_Store_Over_100k": "is_store_over_100k",
        "Store_Day_Val_Total": "store_day_total",
        "Status_3Level": "status_3level",
        "DC_Confirm": "dc_confirm",
        "DC_Note": "dc_note",
        "KFM_Reply": "kfm_reply",
        "KFM_Note": "kfm_note"
    }
    
    df_export = df_enriched[[c for c in export_cols.keys() if c in df_enriched.columns]].rename(columns=export_cols).copy()
    df_export["Date_Str"] = df_enriched["Date_Str"]

    for d_str, day_df in df_export.groupby("Date_Str"):
        if not d_str or not str(d_str).strip(): continue
        safe_date = str(d_str).replace('/', '_').replace('-', '_')
        records = day_df.drop(columns=["Date_Str"]).to_dict(orient="records")
        js_content = f"window.LOADED_DAILY_RECORDS = window.LOADED_DAILY_RECORDS || {{}};\nwindow.LOADED_DAILY_RECORDS['{d_str}'] = {json.dumps(records, ensure_ascii=False)};"
        with open(os.path.join(daily_details_dir, f"d_{safe_date}.js"), "w", encoding="utf-8") as f:
            f.write(js_content)

    # 4. Xuất DC Cases riêng
    df_dc_all = df_enriched[df_enriched["Destination"] == "Kho ĐÔNG MÁT"]
    dc_export_cols = {
        "Date_Str": "date",
        "ID ST": "st",
        "Chi nhánh nhận": "store_name",
        "Nhóm hàng": "group",
        "Mã hàng": "sku",
        "Tên SP": "sku_name",
        "Qty_Lech": "qty_diff",
        "Val_Tong_GT": "val_total",
        "DC_Confirm": "dc_confirm",
        "DC_Note": "dc_note",
        "KFM_Reply": "kfm_reply",
        "KFM_Note": "kfm_note",
        "Status_3Level": "status_3level"
    }
    df_dc_exp = df_dc_all[[c for c in dc_export_cols.keys() if c in df_dc_all.columns]].rename(columns=dc_export_cols).copy()
    df_dc_exp["month"] = df_dc_all["Date_Parsed"].apply(lambda d: f"Tháng {d.month}" if pd.notnull(d) else "Tháng 8")
    dc_records = df_dc_exp.to_dict(orient="records")
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

    # 6. Tính toán toàn bộ Bundles
    print("📊 Đang tổng hợp dữ liệu KPI & Ma Trận cho tất cả các Tab...")
    bundles, avail_months = generate_all_data_bundles(df_enriched)

    # 7. Đọc template HTML và bơm dữ liệu BUNDLES
    template_path = os.path.join(current_dir, "dashboard_template.html")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(current_dir), "LOGIC", "dashboard_template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Bơm BUNDLES
    bundles_json_str = json.dumps(bundles, ensure_ascii=False)
    if "/*__BUNDLES_JSON__*/{}" in html_content:
        html_content = html_content.replace("/*__BUNDLES_JSON__*/{}", bundles_json_str)
    elif "/*__BUNDLES_JSON__*/" in html_content:
        html_content = html_content.replace("/*__BUNDLES_JSON__*/", bundles_json_str)
    
    bundles_js = f"window.REPORT_BUNDLES = {bundles_json_str};"
    html_content = html_content.replace("// __BUNDLES_PLACEHOLDER__", bundles_js)
    if "/* __REPORT_BUNDLES_INJECTION__ */" in html_content:
        html_content = html_content.replace("/* __REPORT_BUNDLES_INJECTION__ */", bundles_js)

    # Cập nhật thời gian xuất bản
    gen_time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_content = html_content.replace("{{GENERATED_TIME}}", gen_time_str)
    html_content = html_content.replace("{{TOTAL_ROWS}}", f"{len(df_enriched):,}")

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
