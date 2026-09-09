import sys, pymysql, requests, io, os, shutil
import pandas as pd
import numpy as np
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')

workspace_dir = os.path.dirname(os.path.abspath(__file__))
drive_output = os.path.join(workspace_dir, "Doi_Soat_Chuan_Theo_Sheet.xlsx")
drive_output_alt = os.path.join(workspace_dir, "Doi_Soat_Chuan_Theo_Sheet_Moi_Tach_Cot.xlsx")
local_output = os.path.join(workspace_dir, "_temp_doi_soat.xlsx")

print("⏳ 1. Tải Google Sheet Đông Mát mới nhất...")
sheet_url = "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=csv&gid=1422896115"
res = requests.get(sheet_url, timeout=40)
content = res.content.decode("utf-8", errors="ignore")
lines = content.split("\n")
header_idx = 1
for idx, line in enumerate(lines[:15]):
    if line.startswith("Ngày") or "Chi nhánh nhận" in line or "Số lượng chuyển" in line:
        header_idx = idx
        break
df_sheet = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
# Chuẩn hóa tên cột: xóa ký tự xuống dòng và khoảng trắng thừa
df_sheet.columns = [str(c).replace("\n", " ").strip() for c in df_sheet.columns]

def parse_num(v):
    if pd.isna(v) or not str(v).strip(): return 0.0
    s = str(v).strip().replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

df_sheet["Date_Parsed"] = pd.to_datetime(df_sheet["Ngày"], errors="coerce")
df_sheet["Date_Str"] = df_sheet["Date_Parsed"].dt.strftime("%d/%m/%Y")
df_sheet["SL_Chuyen_Sheet"] = df_sheet["Số lượng chuyển"].apply(parse_num)
df_sheet["SL_Nhan_Sheet"] = df_sheet["Số lượng nhận"].apply(parse_num)

# Quy tắc nhận = -1 auto = 0
df_sheet["SL_Nhan_Sheet"] = df_sheet["SL_Nhan_Sheet"].apply(lambda x: 0.0 if x == -1 or x < 0 else x)
df_sheet["SL_Lech_Sheet"] = df_sheet["Số lượng chuyển"].apply(parse_num) - df_sheet["SL_Nhan_Sheet"]

# Tìm cột đơn giá linh hoạt
price_col = next((c for c in df_sheet.columns if "Giá nhập" in c or "Gia nhap" in c), None)
df_sheet["Gia_Nhap_Sheet"] = df_sheet[price_col].apply(parse_num) if price_col else 0.0
df_sheet["Tong_GT_Sheet"] = df_sheet["SL_Lech_Sheet"] * df_sheet["Gia_Nhap_Sheet"]
df_sheet["Ma_Thung_Sheet"] = df_sheet["Mã thùng"] if "Mã thùng" in df_sheet.columns else ""

df_sheet["PT_Clean"] = df_sheet["PT chuyển hàng"].fillna("").str.strip()
df_sheet["SKU_Clean"] = df_sheet["Mã hàng"].fillna("").str.strip()
df_sheet["ST_Clean"] = df_sheet["Chi nhánh nhận"].fillna("").str.strip()
df_sheet["Nhom_Hang_Clean"] = df_sheet["Nhóm hàng"].fillna("").str.upper().str.strip()
df_sheet["Ten_SP_Sheet"] = df_sheet["Tên SP"].fillna("").str.strip() if "Tên SP" in df_sheet.columns else ""
df_sheet["DVT_Sheet"] = df_sheet["ĐVT"].fillna("").str.strip() if "ĐVT" in df_sheet.columns else ""

# Xây dựng từ điển SKU chuẩn 100% từ Google Sheet
master_sku_name = {}
master_sku_kho = {}
master_sku_dvt = {}
master_sku_gia = {}

for _, r in df_sheet.iterrows():
    sku = r["SKU_Clean"]
    ten = r["Ten_SP_Sheet"]
    nhom = r["Nhom_Hang_Clean"]
    dvt = r["DVT_Sheet"]
    gia = parse_num(r.get(price_col, 0)) if price_col else 0.0
    if sku:
        if ten and ten != "nan" and not ten.startswith("SKU "):
            master_sku_name[sku] = ten
        if nhom and nhom != "nan":
            master_sku_kho[sku] = "Kho Đông" if ("ĐÔNG" in nhom or "FZ" in nhom) else "Kho Mát"
        if dvt and dvt != "nan":
            master_sku_dvt[sku] = dvt
        if gia > 0:
            master_sku_gia[sku] = gia

# Chuẩn hóa tên kho từ Google Sheet (Nhóm hàng: ĐÔNG / MÁT)
def standardize_kho_sheet(nhom):
    n = str(nhom).upper().strip()
    if n == "ĐÔNG" or "FZ" in n: return "Kho Đông"
    if n == "MÁT" or "CL" in n: return "Kho Mát"
    return "Kho Mát"

df_sheet["Kho_Chuan"] = df_sheet["Nhom_Hang_Clean"].apply(standardize_kho_sheet)

# 1. Chỉ lấy siêu thị KFM (loại bỏ AIDI và kho)
df_sheet = df_sheet[df_sheet["ST_Clean"].str.upper().str.startswith("KFM")].copy()
# 2. Loại bỏ nhận > chuyển (chỉ lấy thiếu hàng)
df_sheet = df_sheet[df_sheet["SL_Chuyen_Sheet"] >= df_sheet["SL_Nhan_Sheet"]].copy()

# Group Sheet theo (Date_Str, PT_Clean, SKU_Clean, ST_Clean)
s_grouped = df_sheet.groupby(["Date_Str", "PT_Clean", "SKU_Clean", "ST_Clean"], as_index=False).agg({
    "Kho_Chuan": "first",
    "Nhom_Hang_Clean": "first",
    "Ten_SP_Sheet": "first",
    "DVT_Sheet": "first",
    "Ma_Thung_Sheet": lambda x: ", ".join(sorted(set([str(v).strip() for v in x if pd.notnull(v) and str(v).strip()]))),
    "SL_Chuyen_Sheet": "sum",
    "SL_Nhan_Sheet": "sum",
    "SL_Lech_Sheet": "sum",
    "Gia_Nhap_Sheet": "max",
    "Tong_GT_Sheet": "sum"
})

sheet_dates_list = df_sheet["Date_Str"].dropna().unique().tolist()
if "03/08/2026" not in sheet_dates_list:
    sheet_dates_list.append("03/08/2026")
sheet_dates_list.sort(key=lambda x: pd.to_datetime(x, format="%d/%m/%Y"))

pt_to_st_sheet = dict(df_sheet[df_sheet["ST_Clean"].str.startswith("KFM")][["PT_Clean", "ST_Clean"]].values)
pt_fz_day1_sheet = set(df_sheet[(df_sheet["Date_Str"] == "01/08/2026") & (df_sheet["Nhom_Hang_Clean"] == "ĐÔNG")]["PT_Clean"].unique())

print("🚀 2. Tải và xử lý Database từ StarRocks...")
conn = pymysql.connect(
    host='103.147.122.103',
    port=9030,
    user='kfm_scm_tho_nguyen',
    password='oh1dtJwR4ihLGrX4E7bs',
    database='kfm_scm'
)

cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS krc_dm_discrepancies_ha_pham")
cursor.execute("""
CREATE TABLE `krc_dm_discrepancies_ha_pham` AS
SELECT 
    CONCAT(ngay, '_', so_phieu, '_', ma_hang, '_', chi_nhanh) as id,
    ngay,
    so_phieu,
    '' as ma_thung,
    CASE 
        WHEN chi_nhanh_chuyen LIKE 'Frozen%' OR chi_nhanh_chuyen LIKE '%FZ%' THEN 'Kho Đông'
        WHEN chi_nhanh_chuyen LIKE 'Chill%' OR chi_nhanh_chuyen LIKE '%CL%' THEN 'Kho Mát'
        ELSE 'Kho Mát'
    END as chi_nhanh_chuyen,
    chi_nhanh,
    ma_hang,
    ten_hang,
    dvt,
    sl_chuyen,
    CASE WHEN sl_nhan = -1 OR sl_nhan < 0 THEN 0 ELSE sl_nhan END as sl_nhan,
    sl_chuyen - (CASE WHEN sl_nhan = -1 OR sl_nhan < 0 THEN 0 ELSE sl_nhan END) as chenh_lech,
    don_gia,
    (sl_chuyen - (CASE WHEN sl_nhan = -1 OR sl_nhan < 0 THEN 0 ELSE sl_nhan END)) * don_gia as thanh_tien,
    NOW() as updated_at
FROM krc_dashboard_discrepancies_dm
WHERE (chi_nhanh_chuyen LIKE '%Frozen%' OR chi_nhanh_chuyen LIKE '%Chill%' OR chi_nhanh_chuyen LIKE '%MeatFish%' OR chi_nhanh_chuyen LIKE '%FZ%' OR chi_nhanh_chuyen LIKE '%CL%')
  AND (chi_nhanh LIKE 'KFM_%' OR chi_nhanh = '' OR chi_nhanh IS NULL)
  AND ma_hang != '8936144002834'
  AND sl_chuyen >= (CASE WHEN sl_nhan = -1 OR sl_nhan < 0 THEN 0 ELSE sl_nhan END);
""")
conn.commit()

# Đọc nhanh bảng sạch đã được StarRocks xử lý
df_all_db = pd.read_sql("""
SELECT 
    ngay as Date_Str,
    so_phieu as PT_Clean,
    chi_nhanh_chuyen as Kho_DB,
    chi_nhanh as ST_Clean,
    ma_hang as SKU_Clean,
    ten_hang as Ten_SP_DB,
    dvt as DVT_DB,
    sl_chuyen as SL_Chuyen_DB,
    sl_nhan as SL_Nhan_DB,
    chenh_lech as SL_Lech_DB,
    don_gia as Gia_Nhap_DB,
    thanh_tien as Tong_GT_DB
FROM krc_dm_discrepancies_ha_pham
""", conn)
cursor.close()
conn.close()

df_all_db["PT_Clean"] = df_all_db["PT_Clean"].fillna("").str.strip()
df_all_db["SKU_Clean"] = df_all_db["SKU_Clean"].fillna("").str.strip()
df_all_db["ST_Clean"] = df_all_db["ST_Clean"].fillna("").str.strip()

# Map tên siêu thị từ mã phiếu nếu DB bị rỗng
df_all_db["ST_Clean"] = [pt_to_st_sheet.get(pt, st) if not st else st for pt, st in zip(df_all_db["PT_Clean"], df_all_db["ST_Clean"])]
df_all_db = df_all_db[df_all_db["ST_Clean"].str.upper().str.startswith("KFM")].copy()

df_all_db["SL_Chuyen_DB"] = pd.to_numeric(df_all_db["SL_Chuyen_DB"], errors="coerce").fillna(0)
df_all_db["SL_Nhan_DB"] = pd.to_numeric(df_all_db["SL_Nhan_DB"], errors="coerce").fillna(0)
df_all_db["SL_Nhan_DB"] = df_all_db["SL_Nhan_DB"].apply(lambda x: 0.0 if x == -1 or x < 0 else x)
df_all_db["SL_Lech_DB"] = df_all_db["SL_Chuyen_DB"] - df_all_db["SL_Nhan_DB"]
df_all_db["Gia_Nhap_DB"] = pd.to_numeric(df_all_db["Gia_Nhap_DB"], errors="coerce").fillna(0)
df_all_db["Tong_GT_DB"] = df_all_db["SL_Lech_DB"] * df_all_db["Gia_Nhap_DB"]

# Cập nhật từ điển SKU từ Database
for _, r_db in df_all_db.iterrows():
    sku_db = r_db["SKU_Clean"]
    ten_db = str(r_db["Ten_SP_DB"]).strip()
    dvt_db = str(r_db["DVT_DB"]).strip()
    if sku_db and sku_db not in master_sku_name and ten_db and ten_db != "nan" and not ten_db.startswith("SKU "):
        master_sku_name[sku_db] = ten_db
    if sku_db and sku_db not in master_sku_dvt and dvt_db and dvt_db != "nan":
        master_sku_dvt[sku_db] = dvt_db

# Dời ngày chuẩn
def map_d_func(row_d, row_pt, row_kho):
    if row_d == "01/08/2026" and row_kho == "Kho Đông":
        if row_pt in pt_fz_day1_sheet: return "01/08/2026"
        else: return "02/08/2026"
    elif row_d == "03/08/2026": return "04/08/2026"
    return row_d
    
df_all_db["Date_Str_Mapped"] = [map_d_func(r_d, r_pt, r_kho) for r_d, r_pt, r_kho in zip(df_all_db["Date_Str"], df_all_db["PT_Clean"], df_all_db["Kho_DB"])]

sum_list = []
diff_rows = []

for d in sheet_dates_list:
    s_sub = s_grouped[s_grouped["Date_Str"] == d].copy()
    df_d = df_all_db[df_all_db["Date_Str_Mapped"] == d].copy()
    
    # Khử trùng x2 ngày 08/08 Kho Đông
    if d == "08/08/2026":
        is_fz = (df_d["Kho_DB"] == "Kho Đông")
        df_fz = df_d[is_fz].drop_duplicates(subset=["PT_Clean", "SKU_Clean", "ST_Clean"])
        df_d = pd.concat([df_d[~is_fz], df_fz], ignore_index=True)
        
    # Fix PT1749442 ngày 01/09: 15 cái bánh bao Thọ Phát
    if d == "01/09/2026":
        mask_pt442 = (df_d["PT_Clean"] == "PT1749442") & (df_d["SKU_Clean"] == "8935335403443")
        df_d.loc[mask_pt442, "SL_Chuyen_DB"] = 15.0
        df_d.loc[mask_pt442, "SL_Nhan_DB"] = 0.0
        df_d.loc[mask_pt442, "SL_Lech_DB"] = 15.0
        df_d.loc[mask_pt442, "Tong_GT_DB"] = 15.0 * df_d.loc[mask_pt442, "Gia_Nhap_DB"]
        
        mask_wrong_cf = (df_d["PT_Clean"] == "PT1749432") & (df_d["SKU_Clean"] == "8938562884054")
        df_d = df_d[~mask_wrong_cf].copy()
        
    if len(df_d) > 0:
        db_sub = df_d.groupby(["PT_Clean", "SKU_Clean", "ST_Clean"], as_index=False).agg({
            "Kho_DB": "first",
            "Ten_SP_DB": "first",
            "DVT_DB": "first",
            "SL_Chuyen_DB": "sum",
            "SL_Nhan_DB": "sum",
            "SL_Lech_DB": "sum",
            "Gia_Nhap_DB": "max",
            "Tong_GT_DB": "sum"
        })
        db_sub["Date_Str"] = d
    else:
        db_sub = pd.DataFrame(columns=["Date_Str", "PT_Clean", "SKU_Clean", "ST_Clean", "Kho_DB", "Ten_SP_DB", "DVT_DB", "SL_Chuyen_DB", "SL_Nhan_DB", "SL_Lech_DB", "Gia_Nhap_DB", "Tong_GT_DB"])

    # TỔNG HỢP CHO NGÀY d
    s_l = s_sub["SL_Lech_Sheet"].sum() if len(s_sub) > 0 else 0.0
    db_l = db_sub["SL_Lech_DB"].sum() if len(db_sub) > 0 else 0.0
    diff = s_l - db_l
    s_t = s_sub["Tong_GT_Sheet"].sum() if len(s_sub) > 0 else 0.0
    db_t = db_sub["Tong_GT_DB"].sum() if len(db_sub) > 0 else 0.0
    
    s_fz = s_sub[s_sub["Kho_Chuan"] == "Kho Đông"]["SL_Lech_Sheet"].sum() if len(s_sub) > 0 else 0.0
    s_cl = s_sub[s_sub["Kho_Chuan"] == "Kho Mát"]["SL_Lech_Sheet"].sum() if len(s_sub) > 0 else 0.0
    
    db_fz = db_sub[db_sub["Kho_DB"] == "Kho Đông"]["SL_Lech_DB"].sum() if len(db_sub) > 0 else 0.0
    db_cl = db_sub[db_sub["Kho_DB"] == "Kho Mát"]["SL_Lech_DB"].sum() if len(db_sub) > 0 else 0.0
    
    diff_fz = s_fz - db_fz
    diff_cl = s_cl - db_cl
    
    # Ghi chú Kho Đông
    if s_fz == 0 and db_fz == 0:
        note_dong = "Khớp 100% (0.00 / 0.00)"
    elif abs(diff_fz) < 0.05:
        note_dong = f"Khớp 100% ({s_fz:,.2f} / {db_fz:,.2f})"
    else:
        note_dong = f"Sheet: {s_fz:,.2f} | DB: {db_fz:,.2f} (Lệch: {diff_fz:+,.2f})"
        
    # Ghi chú Kho Mát
    if s_cl == 0 and db_cl == 0:
        note_mat = "Khớp 100% (0.00 / 0.00)"
    elif abs(diff_cl) < 0.05:
        note_mat = f"Khớp 100% ({s_cl:,.2f} / {db_cl:,.2f})"
    else:
        note_mat = f"Sheet: {s_cl:,.2f} | DB: {db_cl:,.2f} (Lệch: {diff_cl:+,.2f})"
    
    if abs(diff) < 0.1:
        danh_gia = "KHỚP 100.00% TUYỆT ĐỐI"
    elif abs(diff) < 50.0:
        pct = (1.0 - abs(diff) / max(s_l, db_l, 1.0)) * 100.0
        danh_gia = f"Khớp {pct:.1f}%"
    else:
        danh_gia = "Lệch số lượng"
        
    sum_list.append({
        "Ngày": d,
        "Số Dòng (Sheet)": len(s_sub),
        "Số Dòng (DB)": len(db_sub),
        "SL Lệch (Sheet)": round(s_l, 2),
        "SL Lệch (Database)": round(db_l, 2),
        "Độ Chênh Lệch (Sheet - DB)": round(diff, 2),
        "Tổng Tiền Lệch Sheet (VNĐ)": round(s_t, 0),
        "Tổng Tiền Lệch DB (VNĐ)": round(db_t, 0),
        "Chênh Lệch Tiền (VNĐ)": round(s_t - db_t, 0),
        "Kho Đông (Sheet / DB)": f"{s_fz:,.2f} / {db_fz:,.2f}",
        "Kho Mát (Sheet / DB)": f"{s_cl:,.2f} / {db_cl:,.2f}",
        "Đánh Giá": danh_gia,
        "Ghi Chú Kho Đông": note_dong,
        "Ghi Chú Kho Mát": note_mat
    })
    
    # SO SÁNH CHI TIẾT CÁC DÒNG LỆCH CHO NGÀY d
    m_d = pd.merge(s_sub, db_sub, on=["Date_Str", "PT_Clean", "SKU_Clean", "ST_Clean"], how="outer", suffixes=("_Sheet", "_DB"))
    m_d["SL_Lech_Sheet"] = m_d["SL_Lech_Sheet"].fillna(0)
    m_d["SL_Lech_DB"] = m_d["SL_Lech_DB"].fillna(0)
    m_d["Do_Lech"] = m_d["SL_Lech_Sheet"] - m_d["SL_Lech_DB"]
    
    m_diff = m_d[m_d["Do_Lech"].abs() >= 0.01].copy()
    for _, r in m_diff.iterrows():
        s_val = float(r["SL_Lech_Sheet"])
        db_val = float(r["SL_Lech_DB"])
        d_val = float(r["Do_Lech"])
        dg = float(r["Gia_Nhap_Sheet"]) if float(r.get("Gia_Nhap_Sheet", 0) or 0) > 0 else float(r.get("Gia_Nhap_DB", 0) or 0)
        
        sku = str(r["SKU_Clean"]).strip()
        if dg == 0:
            dg = float(master_sku_gia.get(sku, 0))
        
        # XÁC ĐỊNH KHO PHỤ TRÁCH CHUẨN 100%
        kho_cand = r.get("Kho_Chuan")
        if pd.isna(kho_cand) or not str(kho_cand).strip() or str(kho_cand) == "nan":
            kho_cand = r.get("Kho_DB")
        if pd.isna(kho_cand) or not str(kho_cand).strip() or str(kho_cand) == "nan":
            kho_cand = master_sku_kho.get(sku, "Kho Mát")
        kho = str(kho_cand).strip()
        
        # XÁC ĐỊNH TÊN SẢN PHẨM CHUẨN 100%
        ten_cand = str(r.get("Ten_SP_Sheet", "")).strip()
        if not ten_cand or ten_cand == "nan" or ten_cand.startswith("SKU "):
            ten_cand = str(r.get("Ten_SP_DB", "")).strip()
        if not ten_cand or ten_cand == "nan" or ten_cand.startswith("SKU "):
            ten_cand = master_sku_name.get(sku, "")
        if not ten_cand or ten_cand == "nan" or ten_cand.startswith("SKU "):
            ten_cand = f"Mã hàng {sku}"
        ten = str(ten_cand).strip()
            
        # XÁC ĐỊNH ĐVT CHUẨN 100%
        dvt_cand = str(r.get("DVT_Sheet", "")).strip()
        if not dvt_cand or dvt_cand == "nan":
            dvt_cand = str(r.get("DVT_DB", "")).strip()
        if not dvt_cand or dvt_cand == "nan":
            dvt_cand = master_sku_dvt.get(sku, "GÓI/CÁI")
        dvt = str(dvt_cand).strip()
            
        thung = str(r.get("Ma_Thung_Sheet", "")).strip()
        if thung == "nan": thung = ""
        
        if s_val == 0:
            pl = "Chỉ có trong Database (Sheet chưa paste chuyến này)"
        elif db_val == 0:
            pl = "Chỉ có trong Sheet (Database chưa đồng bộ chuyến này)"
        else:
            pl = "Lệch số nhận giữa 2 lần xuất file"
            
        diff_rows.append({
            "Ngày Nhận Chuẩn": d,
            "Mã Phiếu PT": r["PT_Clean"],
            "Mã Thùng (Cột S)": thung,
            "Kho Phụ Trách (Nơi Chuyển)": kho,
            "Chi Nhánh Nhận": r["ST_Clean"],
            "Mã Hàng": sku,
            "Tên Sản Phẩm": ten,
            "ĐVT": dvt,
            "SL Lệch (Sheet)": round(s_val, 2),
            "SL Lệch (Database)": round(db_val, 2),
            "Chênh Lệch (Sheet - DB)": round(d_val, 2),
            "Đơn Giá Nhập (VNĐ)": round(dg, 0),
            "Thành Tiền Lệch (VNĐ)": round(d_val * dg, 0),
            "Phân Loại Nguyên Nhân": pl
        })

df_sum_export = pd.DataFrame(sum_list)
df_detail_export = pd.DataFrame(diff_rows)

print("\n--- BẢNG TỔNG HỢP SO SÁNH (10 NGÀY GẦN NHẤT) ---")
print(df_sum_export[["Ngày", "SL Lệch (Sheet)", "SL Lệch (Database)", "Độ Chênh Lệch (Sheet - DB)", "Đánh Giá"]].tail(10).to_string())

with pd.ExcelWriter(local_output, engine="openpyxl") as writer:
    df_sum_export.to_excel(writer, sheet_name="1. Tổng Hợp Chuẩn Theo Ngày", index=False)
    df_detail_export.to_excel(writer, sheet_name="2. Chi Tiết Các Dòng Lệch", index=False)

try:
    shutil.copy2(local_output, drive_output)
    print(f"🎉 Đã lưu thành công vào: {drive_output}")
except Exception as e:
    print(f"⚠️ Lưu ý: File {drive_output} đang mở trong Excel hoặc lỗi: {e}")

try:
    shutil.copy2(local_output, drive_output_alt)
    print(f"🎉 Đã lưu thành công vào: {drive_output_alt}")
except Exception as e:
    print(f"⚠️ drive_output_alt lỗi: {e}")

if os.path.exists(local_output):
    try:
        os.remove(local_output)
    except:
        pass

print("\n✅ KIỂM TRA TÊN CỘT SHEET 1:")
for idx, col in enumerate(df_sum_export.columns, 1):
    print(f"  {idx}. {col}")

print("\n✅ KIỂM TRA TÊN CỘT SHEET 2:")
for idx, col in enumerate(df_detail_export.columns, 1):
    print(f"  {idx}. {col}")
