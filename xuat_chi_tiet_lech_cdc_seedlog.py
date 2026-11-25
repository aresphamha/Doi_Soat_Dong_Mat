"""
XUẤT CHI TIẾT TỪNG DÒNG LỆCH GIỮA CDC STARROCKS VÀ GOOGLE SHEET 'ĐỐI SOÁT CHÊNH LỆCH SEEDLOG'
(Phạm vi: 01/11/2026 -> 22/11/2026 - các ngày đã chốt Seedlog)
"""

import os
import io
import re
import sys
import pymysql
import requests
import pandas as pd
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

STARROCKS_CFG = {
    "host": "103.140.248.250",
    "port": 9030,
    "user": "kfm_scm_tho_nguyen",
    "password": "TnAM0WEsv4kmasw878wt",
    "database": "kfm_scm",
    "charset": "utf8mb4",
}

BRANCH_FGA10101_ID = "6aabb0a2f426e20007f80123"
USER_TKE_WMS_ID    = "62261627e227c1000743b1d8"
SEEDLOG_CSV_URL    = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&gid=0"

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_EXCEL  = os.path.join(WORKSPACE_DIR, "CHI_TIET_LECH_CDC_VS_SEEDLOG.xlsx")


def norm_bc(v):
    """Chuẩn hóa barcode (bỏ khoảng trắng, bỏ số 0 ở đầu để khớp cả trường hợp Excel/Sheet mất số 0 đầu)."""
    s = str(v).strip() if pd.notna(v) else ""
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0") or s


def main():
    print("[1/3] Tải Google Sheet Seedlog (01/11 -> 22/11/2026, Cột M < 0)...")
    r = requests.get(SEEDLOG_CSV_URL, timeout=40)
    r.raise_for_status()
    df_s = pd.read_csv(io.StringIO(r.content.decode("utf-8", errors="ignore")), dtype=str)
    cols = list(df_s.columns)
    col_date, col_store, col_pt, col_bc, col_wms, col_kdb, col_diff = cols[2], cols[3], cols[5], cols[9], cols[10], cols[11], cols[12]
    col_v = cols[21] if len(cols) > 21 else None
    col_y = cols[24] if len(cols) > 24 else None

    df_s['d'] = pd.to_datetime(df_s[col_date], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_s['diff_num'] = pd.to_numeric(df_s[col_diff], errors='coerce')
    df_s = df_s[(df_s['d'] >= '2026-11-01') & (df_s['d'] <= '2026-11-22') & (df_s['diff_num'] < 0)].copy()

    df_s['pt_clean'] = df_s[col_pt].fillna('').apply(lambda x: re.search(r'(PT\d+)', str(x)).group(1) if re.search(r'(PT\d+)', str(x)) else str(x).strip())
    df_s['bc_raw'] = df_s[col_bc].fillna('').str.strip()
    df_s['bc_norm'] = df_s['bc_raw'].apply(norm_bc)
    df_s['store_clean'] = df_s[col_store].fillna('').str.strip().str.upper()
    df_s['v_clean'] = df_s[col_v].fillna('').str.strip() if col_v else ''
    df_s['y_clean'] = df_s[col_y].fillna('').str.strip() if col_y else ''

    seed_grp = df_s.groupby(['d', 'pt_clean', 'bc_norm'], as_index=False).agg({
        'store_clean': 'first',
        'bc_raw': 'first',
        'diff_num': 'sum',
        'v_clean': lambda x: ' | '.join(sorted(set(v for v in x if v))),
        'y_clean': lambda x: ' | '.join(sorted(set(v for v in x if v))),
    })
    seed_grp.rename(columns={'pt_clean': 'pt_code', 'diff_num': 'sl_lech_seedlog'}, inplace=True)
    print(f"    -> Seedlog: {len(seed_grp):,} dòng (PT, Barcode), tổng SL = {seed_grp['sl_lech_seedlog'].sum():.2f}")

    print("[2/3] Truy vấn CDC StarRocks tất cả dòng thiếu (01/11 -> 22/11/2026) + kiểm tra nguyên nhân...")
    conn = pymysql.connect(**STARROCKS_CFG)

    # 2A. Tất cả dòng thiếu theo đúng bộ lọc chuẩn FGA10101 + TKE_WMS
    sql_cdc = f"""
    SELECT
        DATE_FORMAT(DATE_ADD(STR_TO_DATE(SUBSTR(ti.transfer_date, 1, 19), '%Y-%m-%dT%H:%i:%s'), INTERVAL 7 HOUR), '%Y-%m-%d') AS d,
        ti.code AS pt_code,
        pl.barcode AS bc_cdc,
        MAX(pl.name) AS ten_sp,
        SUM(pl.total_transfer_quantity) AS sl_chuyen_cdc,
        SUM(
            LEAST(
                CASE
                    WHEN cl.total_store_quantity <= 0 OR cl.total_store_quantity IS NULL THEN 0
                    WHEN pl.total_store_quantity < 0 OR pl.total_store_quantity IS NULL THEN 0
                    ELSE pl.total_store_quantity
                END,
                pl.total_transfer_quantity
            )
        ) AS sl_nhan_capped_cdc,
        SUM(
            LEAST(
                CASE
                    WHEN cl.total_store_quantity <= 0 OR cl.total_store_quantity IS NULL THEN 0
                    WHEN pl.total_store_quantity < 0 OR pl.total_store_quantity IS NULL THEN 0
                    ELSE pl.total_store_quantity
                END,
                pl.total_transfer_quantity
            ) - pl.total_transfer_quantity
        ) AS sl_lech_cdc
    FROM __cdc_kfm_kf_inventories_kf_transfer_items ti
    JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines cl ON cl._parent_id = ti._id
    JOIN __cdc_kfm_ec9d24ab_1a050070_L2___product_lines pl ON pl._parent_id = CONCAT(ti._id, CHAR(31), cl._index)
    WHERE ti.from_branch_id = '{BRANCH_FGA10101_ID}'
      AND ti.created_by = '{USER_TKE_WMS_ID}'
      AND ti.deleted = 0
      AND (ti.basket_type IS NULL OR ti.basket_type = '' OR ti.basket_type = 'none')
      AND ti.status != 7
      AND pl.barcode != 'CC00359'
      AND ti.transfer_date >= '2026-10-31T17:00:00'
      AND ti.transfer_date < '2026-11-22T17:00:00'
    GROUP BY 1, 2, 3
    HAVING sl_lech_cdc < 0
    """
    df_cdc = pd.read_sql(sql_cdc, conn)
    df_cdc['bc_norm'] = df_cdc['bc_cdc'].apply(norm_bc)
    print(f"    -> CDC StarRocks (lệch < 0): {len(df_cdc):,} dòng (PT, Barcode), tổng SL = {df_cdc['sl_lech_cdc'].sum():.2f}")

    # Merge full outer trên (d, pt_code, bc_norm)
    merged = pd.merge(df_cdc, seed_grp, on=['d', 'pt_code', 'bc_norm'], how='outer')
    merged['sl_lech_cdc'] = merged['sl_lech_cdc'].fillna(0.0)
    merged['sl_lech_seedlog'] = merged['sl_lech_seedlog'].fillna(0.0)
    merged['chenh_lech_2_ben'] = (merged['sl_lech_cdc'] - merged['sl_lech_seedlog']).round(4)

    # Lọc các dòng bị lệch (|CDC - Seedlog| > 0.001)
    mism = merged[merged['chenh_lech_2_ben'].abs() > 0.001].copy()
    print(f"    -> Tổng số dòng (PT, Barcode) bị lệch giữa CDC và Seedlog: {len(mism)} dòng!")

    # 2B. Tra cứu sâu nguyên nhân trong DB cho các PT bị lệch (bỏ điều kiện from_branch / created_by / ngày)
    mism_pts = [p for p in mism['pt_code'].dropna().unique().tolist() if p]
    pt_meta = {}
    if mism_pts:
        pts_in = ",".join([f"'{p}'" for p in mism_pts])
        sql_meta = f"""
        SELECT
            ti.code AS pt_code,
            ti.from_branch_id,
            ti.created_by,
            ti.status,
            ti.basket_type,
            DATE_FORMAT(DATE_ADD(STR_TO_DATE(SUBSTR(ti.transfer_date, 1, 19), '%Y-%m-%dT%H:%i:%s'), INTERVAL 7 HOUR), '%Y-%m-%d') AS cdc_transfer_day,
            pl.barcode AS bc_cdc_all,
            MAX(pl.name) AS ten_sp_all,
            SUM(pl.total_transfer_quantity) AS tr_all,
            SUM(CASE WHEN cl.total_store_quantity <= 0 OR pl.total_store_quantity < 0 OR pl.total_store_quantity IS NULL THEN 0 ELSE pl.total_store_quantity END) AS st_all
        FROM __cdc_kfm_kf_inventories_kf_transfer_items ti
        JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines cl ON cl._parent_id = ti._id
        JOIN __cdc_kfm_ec9d24ab_1a050070_L2___product_lines pl ON pl._parent_id = CONCAT(ti._id, CHAR(31), cl._index)
        WHERE ti.code IN ({pts_in})
        GROUP BY 1,2,3,4,5,6,7
        """
        df_meta = pd.read_sql(sql_meta, conn)
        df_meta['bc_norm'] = df_meta['bc_cdc_all'].apply(norm_bc)
        for _, rm in df_meta.iterrows():
            pt_meta[(rm['pt_code'], rm['bc_norm'])] = rm

    conn.close()

    # Phân loại nguyên nhân từng dòng lệch
    def classify_reason(row):
        key = (row['pt_code'], row['bc_norm'])
        meta = pt_meta.get(key, None)
        cdc_v = row['sl_lech_cdc']
        seed_v = row['sl_lech_seedlog']

        if cdc_v < 0 and seed_v == 0:
            return "Chỉ có trên CDC (chưa nhập lên Seedlog hoặc nhập sai mã PT/Barcode/Ngày trên Seedlog)"
        if cdc_v == 0 and seed_v < 0:
            if meta is None:
                return "Không tìm thấy PT/Barcode này trong CDC (có thể gõ nhầm mã PT hoặc Barcode trên Seedlog)"
            if meta['from_branch_id'] != BRANCH_FGA10101_ID:
                return f"Kho xuất KHÔNG phải FGA10101 (from_branch_id={meta['from_branch_id']}, VD: kho FGB10101)"
            if meta['created_by'] != USER_TKE_WMS_ID:
                return f"Người tạo KHÔNG phải TKE_WMS (created_by={meta['created_by']})"
            if str(meta['cdc_transfer_day']) != str(row['d']):
                return f"Lệch ngày: CDC chuyển ngày {meta['cdc_transfer_day']}, nhưng Seedlog ghi ngày {row['d']}"
            if float(meta['st_all']) >= float(meta['tr_all']):
                return f"Trên CDC đã nhận đủ (Chuyển={meta['tr_all']}, Nhận={meta['st_all']}) -> ST có thể điều chỉnh lại sau nhận"
            return f"Lý do khác trên CDC (status={meta['status']}, basket={meta['basket_type']})"
        # Cả 2 đều < 0 nhưng số lượng khác nhau
        return f"Cùng có trên 2 bên nhưng lệch số lượng (CDC={cdc_v}, Seedlog={seed_v})"

    mism['nguyen_nhan'] = mism.apply(classify_reason, axis=1)
    # Bổ sung tên SP từ meta nếu thiếu
    def fill_ten_sp(row):
        if pd.notna(row['ten_sp']) and str(row['ten_sp']).strip():
            return row['ten_sp']
        meta = pt_meta.get((row['pt_code'], row['bc_norm']), None)
        return meta['ten_sp_all'] if meta is not None else ""

    mism['ten_sp_final'] = mism.apply(fill_ten_sp, axis=1)
    mism['barcode_hien_thi'] = mism.apply(lambda r: r['bc_cdc'] if pd.notna(r['bc_cdc']) else r['bc_raw'], axis=1)
    mism = mism.sort_values(['d', 'pt_code', 'barcode_hien_thi'])

    # In tóm tắt nhanh theo ngày để kiểm tra
    print("\n=== TÓM TẮT CHI TIẾT LỆCH THEO NGÀY ===")
    by_day = mism.groupby('d').agg(
        so_dong_lech=('pt_code', 'count'),
        tong_lech_cdc_minus_seed=('chenh_lech_2_ben', 'sum')
    ).reset_index()
    print(by_day.to_string(index=False))

    print("\n=== PHÂN LOẠI NGUYÊN NHÂN ===")
    print(mism.groupby('nguyen_nhan')['chenh_lech_2_ben'].agg(['count', 'sum']).to_string())

    # [3/3] Xuất file Excel
    print(f"\n[3/3] Xuất file Excel: {OUTPUT_EXCEL}...")
    wb = openpyxl.Workbook()

    font_title = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    font_hdr   = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold  = Font(name="Calibri", size=10, bold=True)
    font_norm  = Font(name="Calibri", size=10)
    fill_navy  = PatternFill("solid", fgColor="1E3A8A")
    fill_slate = PatternFill("solid", fgColor="334155")
    fill_warn  = PatternFill("solid", fgColor="FEF3C7")
    fill_red   = PatternFill("solid", fgColor="FEE2E2")
    fill_alt   = PatternFill("solid", fgColor="F8FAFC")
    thin       = Side(border_style="thin", color="CBD5E1")
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Sheet 1: CHI_TIET_LECH_TUNG_DONG
    ws = wb.active
    ws.title = "CHI_TIET_LECH_TUNG_DONG"
    ws.merge_cells("A1:L1")
    t1 = ws.cell(1, 1, f"CHI TIẾT TỪNG MÃ HÀNG BỊ LỆCH GIỮA CDC STARROCKS VÀ GOOGLE SHEET SEEDLOG (01/11 - 22/11/2026) | Tổng: {len(mism)} dòng")
    t1.font = font_title
    t1.fill = fill_navy
    ws.row_dimensions[1].height = 26

    hdrs = [
        "Ngày", "Mã Phiếu PT", "Siêu Thị (Seedlog)", "Barcode", "Tên Sản Phẩm",
        "SL Chuyển (CDC)", "SL Nhận Capped (CDC)", "SL Lệch (CDC)",
        "SL Lệch (Seedlog)", "Độ Lệch (CDC - Seedlog)", "Hướng Xử Lý (Cột V)", "Nguyên Nhân Chi Tiết"
    ]
    for ci, h in enumerate(hdrs, start=1):
        c = ws.cell(2, ci, h)
        c.font = font_hdr
        c.fill = fill_slate
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border_all
    ws.row_dimensions[2].height = 26

    for r_i, (_, row) in enumerate(mism.iterrows(), start=3):
        d_disp = datetime.strptime(row['d'], "%Y-%m-%d").strftime("%d/%m/%Y")
        vals = [
            d_disp,
            row['pt_code'],
            row['store_clean'] if pd.notna(row['store_clean']) else "",
            str(row['barcode_hien_thi']),
            str(row['ten_sp_final']),
            float(row['sl_chuyen_cdc']) if pd.notna(row['sl_chuyen_cdc']) else 0.0,
            float(row['sl_nhan_capped_cdc']) if pd.notna(row['sl_nhan_capped_cdc']) else 0.0,
            float(row['sl_lech_cdc']),
            float(row['sl_lech_seedlog']),
            float(row['chenh_lech_2_ben']),
            row['v_clean'] if pd.notna(row['v_clean']) else "",
            row['nguyen_nhan'],
        ]
        for ci, v in enumerate(vals, start=1):
            cell = ws.cell(r_i, ci, v)
            cell.border = border_all
            cell.font = font_bold if ci == 10 else font_norm
            if ci in (1, 2, 3, 4):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif ci in (6, 7, 8, 9, 10):
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "#,##0.##"
                if ci == 10:
                    cell.fill = fill_red if v < 0 else fill_warn
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if r_i % 2 == 1 and ci != 10:
                cell.fill = fill_alt
        ws.row_dimensions[r_i].height = 22

    ws.freeze_panes = "E3"
    widths = [12, 14, 14, 18, 36, 14, 16, 14, 15, 18, 20, 52]
    for ci, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    # Sheet 2: TONG_HOP_NGUYEN_NHAN
    ws2 = wb.create_sheet("TONG_HOP_NGUYEN_NHAN")
    ws2.merge_cells("A1:D1")
    t2 = ws2.cell(1, 1, "TỔNG HỢP PHÂN LOẠI NGUYÊN NHÂN LỆCH GIỮA CDC STARROCKS VÀ SEEDLOG (01/11 - 22/11/2026)")
    t2.font = font_title
    t2.fill = fill_navy
    ws2.row_dimensions[1].height = 26

    for ci, h in enumerate(["Nguyên Nhân", "Số Dòng Lệch", "Tổng Độ Lệch (CDC - Seedlog)", "Ghi Chú"], start=1):
        c = ws2.cell(2, ci, h)
        c.font = font_hdr
        c.fill = fill_slate
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_all

    grp_reason = mism.groupby('nguyen_nhan', as_index=False).agg(
        so_dong=('pt_code', 'count'),
        tong_lech=('chenh_lech_2_ben', 'sum')
    ).sort_values('so_dong', ascending=False)

    for r_i, (_, rr) in enumerate(grp_reason.iterrows(), start=3):
        ws2.cell(r_i, 1, rr['nguyen_nhan']).border = border_all
        c2 = ws2.cell(r_i, 2, int(rr['so_dong']))
        c2.number_format = "#,##0"
        c2.border = border_all
        c3 = ws2.cell(r_i, 3, round(float(rr['tong_lech']), 2))
        c3.number_format = "#,##0.##"
        c3.border = border_all
        ws2.cell(r_i, 4, "").border = border_all

    ws2.column_dimensions["A"].width = 65
    ws2.column_dimensions["B"].width = 16
    ws2.column_dimensions["C"].width = 28
    ws2.column_dimensions["D"].width = 20

    wb.save(OUTPUT_EXCEL)
    print(f"[SUCCESS] Đã xuất xong: {OUTPUT_EXCEL}")


if __name__ == "__main__":
    main()
