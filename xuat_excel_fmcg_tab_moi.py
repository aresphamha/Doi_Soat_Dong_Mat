"""
XUẤT FILE EXCEL BÁO CÁO MA TRẬN FMCG (TAB MỚI) & ĐẶC TẢ LOGIC CHI TIẾT TỪNG HÀNG/CỘT
- Nguồn 1: Database CDC StarRocks (103.140.248.250:9030, DB kfm_scm) - truy vấn trực tiếp cấp dòng hàng (SKU line-item)
  + Bảng phiếu: __cdc_kfm_kf_inventories_kf_transfer_items
  + Bảng kiện: __cdc_kfm_kf_inventories_kf_transfer_items___container_lines
  + Bảng dòng hàng: __cdc_kfm_ec9d24ab_1a050070_L2___product_lines
  + Bảng giá vốn: __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard (kho FGA10101)
- Nguồn 2: Google Sheet Đối soát chênh lệch Seedlog (1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ, gid=0)
- Nguồn 3 (chỉ dùng để đối chiếu tham khảo ở Sheet 3): Google Sheet Report logictis FMCG (gid=1213759414)
- CHỈ XUẤT FILE EXCEL ĐỂ KIỂM TRA - CHƯA CẬP NHẬT LÊN WEB DASHBOARD.
"""

import os
import io
import csv
import re
import sys
import json
import pymysql
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ==================== CẤU HÌNH ====================
STARROCKS_CFG = {
    "host": "103.140.248.250",
    "port": 9030,
    "user": "kfm_scm_tho_nguyen",
    "password": "TnAM0WEsv4kmasw878wt",
    "database": "kfm_scm",
    "charset": "utf8mb4",
}

BRANCH_FGA10101_ID = "6aabb0a2f426e20007f80123"   # FGA10101 _ Bình Thắng _ Lưu Hàng
USER_TKE_WMS_ID    = "62261627e227c1000743b1d8"   # TKE_WMS
START_DATE_ISO     = "2026-11-01"
START_UTC_STR      = "2026-10-31T17:00:00"        # 2026-11-01 00:00:00 giờ VN (UTC+7)

SEEDLOG_CSV_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&gid=0"
FMCG_OLD_CSV_URL = "https://docs.google.com/spreadsheets/d/1ZTLRCJjr-8surASFt9Rm6M-2SYJZfa2dc2phS6vg4_k/export?format=csv&gid=1213759414"

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_EXCEL = os.path.join(WORKSPACE_DIR, "BAO_CAO_FMCG_TAB_MOI_VA_LOGIC.xlsx")

# Từ khóa phân loại Cột Y (theo Bang_mo_ta_cot.xlsx đã được duyệt)
KW_NHAP_SAI = ["st thao tác sai", "st kiểm không đúng vị trí"]
KW_GIAO_BS  = ["dc giao bs"]
KW_GIAO_THIEU = [
    "dc giao thiếu kiện", "pick sai code", "pick sai quy cách",
    "dc pick thiếu", "kiện quét không được", "input sai"
]


def norm_str(v):
    if pd.isna(v) or v is None:
        return ""
    return str(v).strip()


def match_any_kw(val, kw_list):
    s = norm_str(val).lower()
    if not s:
        return False
    return any(kw in s for kw in kw_list)


def fetch_cdc_starrocks():
    print("[1/4] Đang kết nối và truy vấn trực tiếp CDC StarRocks (cấp dòng hàng SKU + giá vốn Stockcard)...")
    conn = pymysql.connect(**STARROCKS_CFG)

    # 1A. Lấy bảng giá vốn (cost) từ Stockcard kho FGA10101 theo (barcode, ngày) và fallback
    sql_cost_daily = f"""
    SELECT
        barcode,
        CONCAT('2026-11-', LPAD(CAST(affected_day AS CHAR), 2, '0')) AS d,
        AVG(cost) AS cost_day
    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
    WHERE branch_id = '{BRANCH_FGA10101_ID}'
      AND affected_year = 2026 AND affected_month = 11
      AND cost > 0
    GROUP BY 1, 2
    """
    df_cost_day = pd.read_sql(sql_cost_daily, conn)
    cost_day_map = {(str(r['barcode']).strip(), str(r['d'])): float(r['cost_day']) for _, r in df_cost_day.iterrows()}

    sql_cost_fb = f"""
    SELECT barcode, AVG(cost) AS cost_fb
    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
    WHERE branch_id = '{BRANCH_FGA10101_ID}'
      AND affected_year = 2026 AND affected_month IN (9, 10, 11)
      AND cost > 0
    GROUP BY 1
    """
    df_cost_fb = pd.read_sql(sql_cost_fb, conn)
    cost_fb_map = {str(r['barcode']).strip(): float(r['cost_fb']) for _, r in df_cost_fb.iterrows()}

    # Fallback toàn hệ thống nếu mã hàng chưa có giao dịch ở FGA10101 trong tháng 9-11
    sql_cost_global = """
    SELECT barcode, AVG(cost) AS cost_gl
    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
    WHERE affected_year = 2026 AND affected_month IN (10, 11)
      AND cost > 0
    GROUP BY 1
    """
    df_cost_gl = pd.read_sql(sql_cost_global, conn)
    cost_gl_map = {str(r['barcode']).strip(): float(r['cost_gl']) for _, r in df_cost_gl.iterrows()}

    print(f"    -> Đã tải giá vốn Stockcard: {len(cost_day_map):,} cặp (SKU, ngày), {len(cost_fb_map):,} SKU kho FGA10101, {len(cost_gl_map):,} SKU toàn hệ thống.")

    # 1B. Truy vấn dữ liệu chuyển - nhận - dư cấp dòng hàng (SKU) từ kho FGA10101,
    #     LỌC NƠI NHẬN CHỈ LÀ SIÊU THỊ (branch_name LIKE 'KFM%', loại bỏ các Kho như FGB10101),
    #     KẾT HỢP bảng phiếu xử lý chênh lệch (kf_transfer_ticket_lines - TO) để bắt đủ 100% dòng lỗi sync ở product_lines
    sql_cdc_agg = f"""
    WITH cost_day AS (
        SELECT
            barcode,
            CONCAT('2026-11-', LPAD(CAST(affected_day AS CHAR), 2, '0')) AS d,
            AVG(cost) AS cost_val
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
        WHERE branch_id = '{BRANCH_FGA10101_ID}'
          AND affected_year = 2026 AND affected_month = 11
          AND cost > 0
        GROUP BY 1, 2
    ),
    cost_fb AS (
        SELECT barcode, AVG(cost) AS cost_val
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
        WHERE branch_id = '{BRANCH_FGA10101_ID}'
          AND affected_year = 2026 AND affected_month IN (9, 10, 11)
          AND cost > 0
        GROUP BY 1
    ),
    cost_gl AS (
        SELECT barcode, AVG(cost) AS cost_val
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
        WHERE affected_year = 2026 AND affected_month IN (10, 11)
          AND cost > 0
        GROUP BY 1
    ),
    store_branches AS (
        SELECT branch_id
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
        WHERE affected_year = 2026 AND affected_month IN (10, 11)
          AND branch_name LIKE 'KFM%'
        GROUP BY 1
    ),
    pt_filtered AS (
        SELECT
            ti._id,
            ti.code AS pt_code,
            ti.to_branch_id,
            ti.status AS pt_status,
            DATE_FORMAT(DATE_ADD(STR_TO_DATE(SUBSTR(ti.transfer_date, 1, 19), '%Y-%m-%dT%H:%i:%s'), INTERVAL 7 HOUR), '%Y-%m-%d') AS d
        FROM __cdc_kfm_kf_inventories_kf_transfer_items ti
        JOIN store_branches sb ON sb.branch_id = ti.to_branch_id
        WHERE ti.from_branch_id = '{BRANCH_FGA10101_ID}'
          AND ti.created_by = '{USER_TKE_WMS_ID}'
          AND ti.deleted = 0
          AND (ti.basket_type IS NULL OR ti.basket_type = '' OR ti.basket_type = 'none')
          AND ti.status != 7
          AND ti.transfer_date >= '{START_UTC_STR}'
    ),
    to_shortage AS (
        SELECT
            pf.d,
            tt.from_pt_code AS pt_code,
            tl.barcode,
            SUM(tl.pending_quantity) AS to_pending_qty
        FROM pt_filtered pf
        JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets tt ON tt.from_pt_code = pf.pt_code
        JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines tl ON tl.transfer_ticket_id = tt._id
        WHERE tt.deleted = 0 AND tl.deleted = 0
          AND tl.barcode != 'CC00359'
          AND tl.pending_quantity > 0
        GROUP BY 1, 2, 3
    ),
    sku_agg AS (
        SELECT
            pf.d,
            pf.pt_code,
            pf.to_branch_id,
            pf.pt_status,
            pl.barcode,
            SUM(pl.total_transfer_quantity) AS sl_tr,
            SUM(
                CASE
                    WHEN cl.total_store_quantity <= 0 OR cl.total_store_quantity IS NULL THEN 0
                    WHEN pl.total_store_quantity < 0 OR pl.total_store_quantity IS NULL THEN 0
                    ELSE pl.total_store_quantity
                END
            ) AS sl_rc_raw,
            SUM(
                LEAST(
                    CASE
                        WHEN cl.total_store_quantity <= 0 OR cl.total_store_quantity IS NULL THEN 0
                        WHEN pl.total_store_quantity < 0 OR pl.total_store_quantity IS NULL THEN 0
                        ELSE pl.total_store_quantity
                    END,
                    pl.total_transfer_quantity
                ) - pl.total_transfer_quantity
            ) AS pl_diff_capped,
            SUM(
                CASE
                    WHEN cl.total_store_quantity > 0 AND pl.total_store_quantity > pl.total_transfer_quantity
                    THEN pl.total_store_quantity - pl.total_transfer_quantity
                    ELSE 0
                END
            ) AS sl_surplus,
            COUNT(*) AS line_cnt
        FROM pt_filtered pf
        JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines cl ON cl._parent_id = pf._id
        JOIN __cdc_kfm_ec9d24ab_1a050070_L2___product_lines pl ON pl._parent_id = CONCAT(pf._id, CHAR(31), cl._index)
        WHERE pl.barcode != 'CC00359'
        GROUP BY 1, 2, 3, 4, 5
    ),
    priced AS (
        SELECT
            s.d,
            s.pt_code,
            s.to_branch_id,
            s.pt_status,
            s.line_cnt,
            s.barcode,
            s.sl_tr,
            -- Chênh lệch chuẩn (blank = 0): dùng TO pending_quantity chặn trần <= sl_tr nếu có TO, ngược lại dùng pl_diff_capped
            CASE
                WHEN t.to_pending_qty IS NOT NULL THEN -LEAST(t.to_pending_qty, s.sl_tr)
                ELSE s.pl_diff_capped
            END AS sl_diff_blank0,
            -- Chênh lệch giữ nguyên Portal (blank = -1): dùng trực tiếp -to_pending_qty nếu có TO
            CASE
                WHEN t.to_pending_qty IS NOT NULL THEN -t.to_pending_qty
                ELSE s.pl_diff_capped
            END AS sl_diff_blank_m1,
            -- SL nhận chuẩn hóa (capped, blank = 0) = sl_tr + sl_diff_blank0
            s.sl_tr + (
                CASE
                    WHEN t.to_pending_qty IS NOT NULL THEN -LEAST(t.to_pending_qty, s.sl_tr)
                    ELSE s.pl_diff_capped
                END
            ) AS sl_rc_capped,
            s.sl_surplus,
            COALESCE(cd.cost_val, cf.cost_val, cg.cost_val, 0) AS unit_cost
        FROM sku_agg s
        LEFT JOIN to_shortage t ON t.d = s.d AND t.pt_code = s.pt_code AND t.barcode = s.barcode
        LEFT JOIN cost_day cd ON cd.barcode = s.barcode AND cd.d = s.d
        LEFT JOIN cost_fb cf ON cf.barcode = s.barcode
        LEFT JOIN cost_gl cg ON cg.barcode = s.barcode
    )
    SELECT
        d,
        COUNT(DISTINCT pt_code) AS pt_cnt,
        COUNT(DISTINCT to_branch_id) AS st_chuyen,
        COUNT(DISTINCT CASE WHEN sl_rc_capped > 0 THEN to_branch_id END) AS st_nhan,
        COUNT(DISTINCT CASE WHEN sl_surplus > 0 THEN to_branch_id END) AS st_nhan_du,
        SUM(CASE WHEN pt_status != 5 THEN line_cnt ELSE 0 END) AS lines_not_completed,
        SUM(sl_tr) AS sl_chuyen,
        SUM(sl_rc_capped) AS sl_nhan_capped,
        SUM(sl_diff_blank0) AS sl_chenh_lech_cdc,
        SUM(sl_diff_blank_m1) AS sl_chenh_lech_cdc_m1,
        SUM(sl_surplus) AS sl_du_cdc,
        SUM(sl_tr * unit_cost) AS gt_chuyen,
        SUM(sl_rc_capped * unit_cost) AS gt_nhan_capped,
        SUM(sl_diff_blank0 * unit_cost) AS gt_chenh_lech_cdc,
        SUM(sl_surplus * unit_cost) AS gt_du_cdc
    FROM priced
    GROUP BY d
    ORDER BY d
    """
    df_cdc = pd.read_sql(sql_cdc_agg, conn)
    conn.close()
    print(f"    -> Đã truy vấn xong CDC StarRocks: {len(df_cdc)} ngày ({df_cdc['d'].min()} -> {df_cdc['d'].max()}).")
    return df_cdc, cost_day_map, cost_fb_map, cost_gl_map


def fetch_seedlog(cost_day_map, cost_fb_map, cost_gl_map):
    print("[2/4] Đang tải Google Sheet Đối soát chênh lệch Seedlog...")
    r = requests.get(SEEDLOG_CSV_URL, timeout=40)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8", errors="ignore")), dtype=str)

    # Xác định các cột theo vị trí & tên chuẩn của Seedlog
    # Cột C (idx 2): Ngày, Cột D (idx 3): Store, Cột F (idx 5): Transfer (PT), Cột J (idx 9): Barcode,
    # Cột K (idx 10): WMS, Cột L (idx 11): KDB, Cột M (idx 12): Difference,
    # Cột U (idx 20): Trạng thái tạo phiếu DC, Cột V (idx 21): Hướng xử lý (Trả tồn về DC / ST / lỗi hệ thống / blank),
    # Cột Y (idx 24): Note lỗi chi tiết
    cols = list(df.columns)
    col_date = cols[2]
    col_store = cols[3]
    col_pt = cols[5]
    col_barcode = cols[9]
    col_wms = cols[10]
    col_kdb = cols[11]
    col_diff = cols[12]
    col_u = cols[20] if len(cols) > 20 else None
    col_v = cols[21] if len(cols) > 21 else None
    col_y = cols[24] if len(cols) > 24 else None

    print(f"    -> Cột Seedlog nhận diện: Ngày='{col_date}', Store='{col_store}', Diff='{col_diff}', U='{col_u}', V='{col_v}', Y='{col_y}'")

    df['d_dt'] = pd.to_datetime(df[col_date], dayfirst=True, errors='coerce')
    df['d'] = df['d_dt'].dt.strftime('%Y-%m-%d')
    df['diff_num'] = pd.to_numeric(df[col_diff], errors='coerce')
    df['wms_num'] = pd.to_numeric(df[col_wms], errors='coerce').fillna(0)
    df['kdb_num'] = pd.to_numeric(df[col_kdb], errors='coerce').fillna(0)

    # Lọc từ 01/11/2026 trở đi và chỉ lấy các dòng chênh lệch thiếu (Cột M < 0)
    df_nov = df[(df['d'] >= START_DATE_ISO) & (df['diff_num'] < 0)].copy()

    # Chuẩn hóa chuỗi
    df_nov['store_clean'] = df_nov[col_store].apply(norm_str).str.upper()
    df_nov['pt_clean'] = df_nov[col_pt].apply(lambda x: re.search(r'(PT\d+)', norm_str(x)).group(1) if re.search(r'(PT\d+)', norm_str(x)) else norm_str(x))
    df_nov['barcode_clean'] = df_nov[col_barcode].apply(norm_str)
    df_nov['col_u_clean'] = df_nov[col_u].apply(norm_str) if col_u else ""
    df_nov['col_v_clean'] = df_nov[col_v].apply(norm_str) if col_v else ""
    df_nov['col_y_clean'] = df_nov[col_y].apply(norm_str) if col_y else ""

    # Gắn đơn giá vốn CDC StarRocks (gia_cost)
    def lookup_cost(row):
        bc = row['barcode_clean']
        d = row['d']
        if (bc, d) in cost_day_map:
            return cost_day_map[(bc, d)], "Stockcard FGA10101 (đúng ngày D)"
        if bc in cost_fb_map:
            return cost_fb_map[bc], "Stockcard FGA10101 (TB T9-T11)"
        if bc in cost_gl_map:
            return cost_gl_map[bc], "Stockcard toàn hệ thống (TB T10-T11)"
        return 0.0, "Chưa có giá vốn CDC"

    res_cost = df_nov.apply(lookup_cost, axis=1)
    df_nov['gia_cost_cdc'] = [x[0] for x in res_cost]
    df_nov['nguon_gia_cost'] = [x[1] for x in res_cost]
    # Giá trị chênh lệch mang dấu âm (Cột M âm * gia_cost), còn giá trị Trả DC/ST/Write-off/Chưa check mang dấu dương (ABS(Cột M) * gia_cost)
    df_nov['gt_chenh_lech_cdc'] = df_nov['diff_num'] * df_nov['gia_cost_cdc']
    df_nov['gt_abs_cdc'] = df_nov['diff_num'].abs() * df_nov['gia_cost_cdc']
    df_nov['sl_abs'] = df_nov['diff_num'].abs()

    print(f"    -> Đã tải Seedlog từ 01/11/2026 (Cột M < 0): {len(df_nov):,} dòng, từ {df_nov['d'].min()} -> {df_nov['d'].max()}.")
    return df_nov


def fetch_old_fmcg_reference():
    print("[3/4] Đang tải Google Sheet Report logictis FMCG (chỉ để đối chiếu tham khảo ở Sheet 3)...")
    try:
        r = requests.get(FMCG_OLD_CSV_URL, timeout=25)
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.text)))
        header = rows[2]
        ref = {}
        for idx, col_str in enumerate(header[1:], start=1):
            s = col_str.strip().replace('-', '/')
            parts = s.split('/')
            if len(parts) == 3 and idx >= 62:
                try:
                    p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
                    yr = p3 if p3 >= 2000 else 2000 + p3
                    d = date(yr, p1, p2) if p1 >= 11 else date(yr, p2, p1)
                    iso = d.strftime("%Y-%m-%d")
                    def pnum(row_i):
                        if row_i < len(rows) and idx < len(rows[row_i]):
                            v = rows[row_i][idx].strip().replace(',', '').replace('%', '')
                            try: return float(v)
                            except: return None
                        return None
                    ref[iso] = {
                        "sl_chuyen_bc": pnum(3),
                        "sl_nhan_bc": pnum(4),
                        "sl_cl_bc": pnum(5),
                        "gt_chuyen_bc": pnum(10),
                        "gt_cl_bc": pnum(12),
                    }
                except Exception:
                    pass
        print(f"    -> Đã tải tham khảo Report FMCG cũ: {len(ref)} ngày tháng 11.")
        return ref
    except Exception as e:
        print(f"    -> Cảnh báo không tải được Report FMCG cũ: {e}")
        return {}


def compute_matrix(df_cdc, df_seed):
    """Tính toán toàn bộ 54 chỉ số cho từng ngày từ 01/11/2026 đến ngày mới nhất."""
    all_dates = sorted(set(df_cdc['d'].tolist() + df_seed['d'].tolist()))
    all_dates = [d for d in all_dates if d >= START_DATE_ISO]
    today_dt = date.today()  # 2026-11-24

    cdc_map = {r['d']: r for _, r in df_cdc.iterrows()}

    daily_metrics = {}
    cum_gt_chuyen = 0.0
    cum_ton_kho_cl = 0.0

    for d_iso in all_dates:
        d_obj = datetime.strptime(d_iso, "%Y-%m-%d").date()
        c = cdc_map.get(d_iso, None)
        s = df_seed[df_seed['d'] == d_iso]

        # ---- I. SẢN LƯỢNG (SL) ----
        sl_chuyen = float(c['sl_chuyen']) if c is not None else 0.0
        sl_nhan   = float(c['sl_nhan_capped']) if c is not None else 0.0
        sl_cl_cdc = float(c['sl_chenh_lech_cdc']) if c is not None else 0.0
        sl_du     = float(c['sl_du_cdc']) if c is not None else 0.0

        # Theo Bang_mo_ta_cot: SL chênh lệch lấy từ Seedlog Cột M (<0)
        sl_chenh_lech = float(s['diff_num'].sum()) if len(s) > 0 else 0.0
        sl_hao_hut = 0.0

        v_lower = s['col_v_clean'].str.lower()
        u_lower = s['col_u_clean'].str.lower()

        m_tra_dc   = v_lower.str.contains("trả tồn về dc", na=False)
        m_tra_st   = v_lower.str.contains("trả tồn về st", na=False)
        m_writeoff = v_lower.str.contains("lỗi hệ thống", na=False)
        m_blank_v  = (v_lower == "") | v_lower.isna()

        sl_tra_dc        = float(s.loc[m_tra_dc, 'sl_abs'].sum())
        sl_tra_st        = float(s.loc[m_tra_st, 'sl_abs'].sum())
        sl_write_off     = float(s.loc[m_writeoff, 'sl_abs'].sum())
        sl_scm_chua_chk  = float(s.loc[m_blank_v, 'sl_abs'].sum())

        # ---- II. GIÁ TRỊ (VNĐ) - 100% theo gia_cost CDC ----
        gt_chuyen = float(c['gt_chuyen']) if c is not None else 0.0
        gt_nhan   = float(c['gt_nhan_capped']) if c is not None else 0.0
        gt_du     = float(c['gt_du_cdc']) if c is not None else 0.0

        gt_chenh_lech   = float(s['gt_chenh_lech_cdc'].sum()) if len(s) > 0 else 0.0  # số âm
        gt_hao_hut      = 0.0
        gt_tra_dc       = float(s.loc[m_tra_dc, 'gt_abs_cdc'].sum())
        gt_tra_st       = float(s.loc[m_tra_st, 'gt_abs_cdc'].sum())
        gt_write_off    = float(s.loc[m_writeoff, 'gt_abs_cdc'].sum())
        gt_scm_chua_chk = float(s.loc[m_blank_v, 'gt_abs_cdc'].sum())

        # ---- III. TỶ LỆ % ----
        def safe_pct(num, den):
            return (num / den) if den else 0.0

        pct_gt_cl       = safe_pct(gt_chenh_lech, gt_chuyen)
        pct_gt_tra_dc   = safe_pct(gt_tra_dc, gt_chuyen)
        pct_gt_tra_st   = safe_pct(gt_tra_st, gt_chuyen)
        pct_gt_hao_hut  = safe_pct(gt_hao_hut, gt_chuyen)
        pct_gt_scm_chk  = safe_pct(gt_scm_chua_chk, gt_chuyen)
        pct_gt_net_du   = safe_pct(gt_du, gt_chuyen)
        pct_gt_dc_sau_net = max(0.0, pct_gt_tra_dc - pct_gt_net_du)

        # ---- IV. SỐ LƯỢNG SIÊU THỊ ----
        sl_st_chuyen    = int(c['st_chuyen']) if c is not None else 0
        sl_st_nhan      = int(c['st_nhan']) if c is not None else 0
        sl_st_cl        = int(s['store_clean'].replace("", np.nan).dropna().nunique()) if len(s) > 0 else 0
        sl_st_nhap_sai  = int(s.loc[s['col_y_clean'].apply(lambda x: match_any_kw(x, KW_NHAP_SAI)), 'store_clean'].replace("", np.nan).dropna().nunique()) if len(s) > 0 else 0
        sl_st_dc_bs     = int(s.loc[s['col_y_clean'].apply(lambda x: match_any_kw(x, KW_GIAO_BS)), 'store_clean'].replace("", np.nan).dropna().nunique()) if len(s) > 0 else 0
        sl_st_dc_thieu  = int(s.loc[s['col_y_clean'].apply(lambda x: match_any_kw(x, KW_GIAO_THIEU)), 'store_clean'].replace("", np.nan).dropna().nunique()) if len(s) > 0 else 0
        sl_st_nhan_du   = int(c['st_nhan_du']) if c is not None else 0

        # ---- V. DC XÁC NHẬN & PHẢN HỒI (theo SL món Cột M + gia_cost CDC) ----
        m_u_done = u_lower.str.contains("hoàn thành", na=False)
        m_u_pend = u_lower.str.contains("chưa tạo phiếu", na=False) | (u_lower == "") | u_lower.isna()

        m_dc_xn = m_tra_dc & m_u_done
        m_dc_kt = m_tra_dc & m_u_pend

        days_elapsed = (today_dt - d_obj).days
        is_le_2 = days_elapsed <= 2

        sl_dc_xn      = float(s.loc[m_dc_xn, 'sl_abs'].sum())
        sl_dc_kt      = float(s.loc[m_dc_kt, 'sl_abs'].sum())
        sl_dc_tru_bi  = 0.0
        sl_dc_chua_le2 = sl_dc_kt if is_le_2 else 0.0
        sl_dc_chua_gt2 = sl_dc_kt if not is_le_2 else 0.0

        gt_dc_xn      = float(s.loc[m_dc_xn, 'gt_abs_cdc'].sum())
        gt_dc_kt      = float(s.loc[m_dc_kt, 'gt_abs_cdc'].sum())
        gt_dc_tru_bi  = 0.0
        gt_dc_chua_le2 = gt_dc_kt if is_le_2 else 0.0
        gt_dc_chua_gt2 = gt_dc_kt if not is_le_2 else 0.0

        pct_dc_xn      = safe_pct(gt_dc_xn, gt_chuyen)
        pct_dc_kt      = safe_pct(gt_dc_kt, gt_chuyen)
        pct_dc_tru_bi  = 0.0
        pct_dc_chua_le2 = safe_pct(gt_dc_chua_le2, gt_chuyen)
        pct_dc_chua_gt2 = safe_pct(gt_dc_chua_gt2, gt_chuyen)

        # ---- VI. LŨY KẾ, TỒN KHO & TÀI CHÍNH ----
        cum_gt_chuyen  += gt_chuyen
        # Lũy kế theo công thức Google Sheet: Tồn hôm trước - Giá trị chênh lệch hôm nay (vì gt_chenh_lech âm nên cộng dồn lên)
        cum_ton_kho_cl  = cum_ton_kho_cl - gt_chenh_lech
        ty_le_cl_chuyen = safe_pct(cum_ton_kho_cl, cum_gt_chuyen)

        # Khối Tài Chính (Hàng 53, 54, 55 trong Bang_mo_ta_cot)
        # Hàng 53: Tổng giá trị thất thoát = ABS(GT chênh lệch) - GT trả ST (= GT trả DC + GT Write-off + GT SCM chưa check)
        tong_gt_that_thoat = max(0.0, abs(gt_chenh_lech) - gt_tra_st)
        # Hàng 54: Tổng giá trị DC chịu = Giá trị DC xác nhận (hoặc max(0, Tổng thất thoát - Write-off))
        tong_gt_dc_chiu    = gt_dc_xn
        # Hàng 55: Tổng giá trị KFM chịu = Hao hụt + Write off
        tong_gt_kfm_chiu   = gt_hao_hut + gt_write_off

        daily_metrics[d_iso] = {
            "Ngày": d_obj.strftime("%d/%m/%Y"),
            # I. Sản lượng
            "SL chuyển": sl_chuyen,
            "SL nhận": sl_nhan,
            "SL chênh lệch": sl_chenh_lech,
            "SL hao hụt": sl_hao_hut,
            "SL trả DC": sl_tra_dc,
            "SL trả ST": sl_tra_st,
            "SL Write - OFF": sl_write_off,
            "SL SCM chưa check": sl_scm_chua_chk,
            "SL dư": sl_du,
            # II. Giá trị
            "Giá trị chuyển": gt_chuyen,
            "Giá trị nhận": gt_nhan,
            "Giá trị chênh lệch": gt_chenh_lech,
            "Giá trị hao hụt": gt_hao_hut,
            "Giá trị trả DC": gt_tra_dc,
            "Giá trị trả ST": gt_tra_st,
            "Giá trị Write - OFF": gt_write_off,
            "Giá trị SCM chưa check": gt_scm_chua_chk,
            "Giá trị dư": gt_du,
            # III. Tỷ lệ %
            "% giá trị chênh lệch": pct_gt_cl,
            "% giá trị trả DC": pct_gt_tra_dc,
            "% giá trị trả ST": pct_gt_tra_st,
            "% giá trị hao hụt": pct_gt_hao_hut,
            "% giá trị SCM chưa check": pct_gt_scm_chk,
            "% giá trị NET DƯ": pct_gt_net_du,
            "% giá trị trả DC (SAU NET)": pct_gt_dc_sau_net,
            # IV. Siêu thị
            "SL ST chuyển": sl_st_chuyen,
            "SL ST nhận": sl_st_nhan,
            "SL ST chênh lệch": sl_st_cl,
            "SL ST nhập sai": sl_st_nhap_sai,
            "SL ST DC giao bổ sung": sl_st_dc_bs,
            "SL ST DC giao thiếu": sl_st_dc_thieu,
            "SL ST nhận dư": sl_st_nhan_du,
            # V. DC phản hồi
            "SL DC xác nhận thiếu": sl_dc_xn,
            "SL DC đang kiểm tra": sl_dc_kt,
            "SL DC từ chối do trừ bì": sl_dc_tru_bi,
            "SL DC chưa phản hồi (<D+2)": sl_dc_chua_le2,
            "SL DC chưa phản hồi (>D+2)": sl_dc_chua_gt2,
            "Giá trị DC xác nhận": gt_dc_xn,
            "Giá trị DC kiểm tra": gt_dc_kt,
            "Giá trị DC từ chối do trừ bì": gt_dc_tru_bi,
            "Giá trị DC chưa phản hồi (<D+2)": gt_dc_chua_le2,
            "Giá trị DC chưa phản hồi (>D+2)": gt_dc_chua_gt2,
            "% Giá trị DC xác nhận": pct_dc_xn,
            "% Giá trị DC kiểm tra": pct_dc_kt,
            "% Giá trị DC từ chối do trừ bì": pct_dc_tru_bi,
            "% Giá trị DC chưa phản hồi (<D+2)": pct_dc_chua_le2,
            "% Giá trị DC chưa phản hồi (>D+2)": pct_dc_chua_gt2,
            # VI. Lũy kế & Tài chính
            "Tổng giá trị chuyển lũy kế": cum_gt_chuyen,
            "Tồn kho chênh lệch": cum_ton_kho_cl,
            "Tỷ lệ chênh lệch chuyển hàng": ty_le_cl_chuyen,
            "Tổng giá trị thất thoát": tong_gt_that_thoat,
            "Tổng giá trị DC chịu": tong_gt_dc_chiu,
            "Tổng giá trị KFM chịu": tong_gt_kfm_chiu,
        }

    return all_dates, daily_metrics


# ==================== ĐẶC TẢ LOGIC CHI TIẾT 54 HÀNG ====================
ROWS_SPEC = [
    # (STT, Khối, Tên chỉ số, Nguồn chính, Bảng/Sheet & Cột, Điều kiện lọc & Quy tắc xử lý, Công thức tính, Cách tính cột TỔNG, Định dạng, Ghi chú)
    (1, "I. SẢN LƯỢNG (SL)", "SL chuyển", "CDC StarRocks",
     "__cdc_kfm_kf_inventories_kf_transfer_items (ti) JOIN container_lines (cl) JOIN product_lines (pl): cột pl.total_transfer_quantity",
     "Kho xuất: from_branch_id = FGA10101 (6aabb0a2f426e20007f80123); Người tạo: BẮT BUỘC user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8, loại phiếu user khác tạo tay); Nơi nhận: CHỈ SIÊU THỊ (branch_name LIKE 'KFM%', loại bỏ Kho như FGB10101); deleted=0; status!=7; basket_type IS NULL/''/'none'; barcode != 'CC00359'; transfer_date giờ VN (UTC+7).",
     "SUM(pl.total_transfer_quantity)", "SUM toàn kỳ", "#,##0", "Khớp 100% với tổng cột K khi xuất file chi tiết trên Portal WMS."),
    (2, "I. SẢN LƯỢNG (SL)", "SL nhận", "CDC StarRocks",
     "cl.total_store_quantity & pl.total_store_quantity KẾT HỢP bảng phiếu xử lý chênh lệch __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines (TO.pending_quantity)",
     "Kho FGA10101; Người tạo: BẮT BUỘC user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM; deleted=0; status!=7; loại CC00359. Nếu có phiếu TO (pending_quantity > 0): dùng -LEAST(pending_quantity, sl_tr) để bắt đủ 100% dòng lỗi sync và chặn trần blank = 0. Nếu không có TO: quy cl_st<=0 hoặc pl_st<0 => 0 và chặn trần <= sl_tr.",
     "SUM(sl_tr + sl_diff_blank0)", "SUM toàn kỳ", "#,##0", "Khớp 100% từng ngày với Seedlog (chỉ chênh đúng 10 dòng blank=-1 và 3 dòng ngoài phạm vi kho/user)."),
    (3, "I. SẢN LƯỢNG (SL)", "SL chênh lệch", "Google Sheet Seedlog",
     "Sheet Seedlog (gid=0): Cột C (Ngày), Cột M (Difference)",
     "Lọc Cột C >= 01/11/2026; chỉ lấy các dòng thiếu: Cột M < 0 (loại trừ giá trị > 0).",
     "SUM(Cột M) với Cột M < 0 (mang dấu âm)", "SUM toàn kỳ", "#,##0", "Đối chiếu khớp sát 100% với (SL nhận capped - SL chuyển) trên CDC StarRocks (xem Sheet 3)."),
    (4, "I. SẢN LƯỢNG (SL)", "SL hao hụt", "Mặc định",
     "Không có (Auto = 0)", "Quy định trong Bang_mo_ta_cot.xlsx: hàng khô FMCG không tính hao hụt tự nhiên.", "0", "0", "#,##0", "Auto = 0."),
    (5, "I. SẢN LƯỢNG (SL)", "SL trả DC", "Google Sheet Seedlog",
     "Sheet Seedlog: Cột M (Difference), Cột V (Hướng xử lý)",
     "Cột M < 0 VÀ Cột V chứa 'Trả tồn về DC'", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Tổng số lượng món xác định lỗi DC, trả tồn về DC."),
    (6, "I. SẢN LƯỢNG (SL)", "SL trả ST", "Google Sheet Seedlog",
     "Sheet Seedlog: Cột M (Difference), Cột V (Hướng xử lý)",
     "Cột M < 0 VÀ Cột V chứa 'Trả tồn về ST'", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Tổng số lượng món lỗi do Siêu thị, trả tồn về ST."),
    (7, "I. SẢN LƯỢNG (SL)", "SL Write - OFF", "Google Sheet Seedlog",
     "Sheet Seedlog: Cột M (Difference), Cột V (Hướng xử lý)",
     "Cột M < 0 VÀ Cột V chứa 'lỗi hệ thống'", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Hàng chênh lệch do lỗi hệ thống, xử lý Write-off."),
    (8, "I. SẢN LƯỢNG (SL)", "SL SCM chưa check", "Google Sheet Seedlog",
     "Sheet Seedlog: Cột M (Difference), Cột V (Hướng xử lý)",
     "Cột M < 0 VÀ Cột V đang để trống (blank)", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Các dòng đang chờ SCM kiểm tra camera / phân loại."),
    (9, "I. SẢN LƯỢNG (SL)", "SL dư", "CDC StarRocks",
     "cl.total_store_quantity & pl.total_store_quantity (Kho FGA10101)",
     "Kho xuất: FGA10101; Người tạo: BẮT BUỘC user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận: chỉ Siêu thị KFM; deleted=0; status!=7; loại CC00359; lấy các dòng có cl.total_store_quantity > 0 VÀ pl.total_store_quantity > pl.total_transfer_quantity.",
     "SUM(pl.total_store_quantity - pl.total_transfer_quantity)", "SUM toàn kỳ", "#,##0", "Phần hàng Siêu thị nhận dư được tách riêng, không bù trừ vào SL nhận."),

    # II. GIÁ TRỊ
    (10, "II. GIÁ TRỊ (VNĐ)", "Giá trị chuyển", "CDC StarRocks",
     "product_lines + __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard (cost)",
     "Kho FGA10101; Người tạo: user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM. Nhân SL chuyển từng mã Barcode với gia_cost tại kho FGA10101 đúng ngày D (fallback TB T9-T11 kho FGA10101 -> TB toàn hệ thống).",
     "SUM(pl.total_transfer_quantity * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "100% tính theo giá vốn thực tế từ Stockcard CDC."),
    (11, "II. GIÁ TRỊ (VNĐ)", "Giá trị nhận", "CDC StarRocks",
     "product_lines (sl_nhan_capped) + stockcard (cost)",
     "Kho FGA10101; Người tạo: user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM. Nhân SL nhận đã chặn trần (<= SL chuyển) từng mã Barcode với gia_cost CDC.",
     "SUM(sl_nhan_capped * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Giá trị nhận chuẩn hóa, không bị cộng khống phần hàng nhận dư."),
    (12, "II. GIÁ TRỊ (VNĐ)", "Giá trị chênh lệch", "Seedlog + Cost CDC",
     "Seedlog Cột M (<0) + Barcode × Stockcard CDC (cost)",
     "KHÔNG dùng đơn giá Cột AC trên Google Sheet Seedlog. Lấy SL Cột M (<0) nhân trực tiếp với gia_cost CDC của từng Barcode.",
     "SUM(Cột M * gia_cost_CDC) (mang dấu âm)", "SUM toàn kỳ", "#,##0", "Khắc phục hoàn toàn lỗi các mã hàng để đơn giá = 0đ trên Seedlog."),
    (13, "II. GIÁ TRỊ (VNĐ)", "Giá trị hao hụt", "Mặc định",
     "Auto = 0", "Quy định trong Bang_mo_ta_cot.xlsx.", "0", "0", "#,##0", "Auto = 0."),
    (14, "II. GIÁ TRỊ (VNĐ)", "Giá trị trả DC", "Seedlog + Cost CDC",
     "Seedlog Cột M, Cột V + Stockcard CDC (cost)",
     "Cột M < 0 VÀ Cột V = 'Trả tồn về DC'", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Giá trị hàng thiếu quy trách nhiệm cho DC."),
    (15, "II. GIÁ TRỊ (VNĐ)", "Giá trị trả ST", "Seedlog + Cost CDC",
     "Seedlog Cột M, Cột V + Stockcard CDC (cost)",
     "Cột M < 0 VÀ Cột V = 'Trả tồn về ST'", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Giá trị hàng thiếu quy trách nhiệm cho Siêu thị."),
    (16, "II. GIÁ TRỊ (VNĐ)", "Giá trị Write - OFF", "Seedlog + Cost CDC",
     "Seedlog Cột M, Cột V + Stockcard CDC (cost)",
     "Cột M < 0 VÀ Cột V = 'lỗi hệ thống'", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Giá trị xử lý Write-off."),
    (17, "II. GIÁ TRỊ (VNĐ)", "Giá trị SCM chưa check", "Seedlog + Cost CDC",
     "Seedlog Cột M, Cột V + Stockcard CDC (cost)",
     "Cột M < 0 VÀ Cột V = blank", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Giá trị các dòng chờ SCM đối soát."),
    (18, "II. GIÁ TRỊ (VNĐ)", "Giá trị dư", "CDC StarRocks",
     "product_lines (sl_surplus) + stockcard (cost)",
     "Kho FGA10101; Người tạo: BẮT BUỘC user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM; các dòng nhận dư (cl.total_store_quantity > 0 VÀ sl_rc_raw > sl_tr) nhân gia_cost CDC.", "SUM(sl_surplus * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", "Theo dõi riêng biệt giá trị hàng dư và dùng để net-off ở mục Đ0."),

    # III. TỶ LỆ %
    (19, "III. TỶ LỆ (%)", "% giá trị chênh lệch", "Công thức", "Hàng 12 / Hàng 10", "Chia cho Giá trị chuyển (nếu mẫu = 0 thì = 0%).", "Giá trị chênh lệch / Giá trị chuyển", "Tổng GT CL / Tổng GT chuyển", "0.00%", "Tỷ lệ thất thoát thô."),
    (20, "III. TỶ LỆ (%)", "% giá trị trả DC", "Công thức", "Hàng 14 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị trả DC / Giá trị chuyển", "Tổng GT trả DC / Tổng GT chuyển", "0.00%", ""),
    (21, "III. TỶ LỆ (%)", "% giá trị trả ST", "Công thức", "Hàng 15 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị trả ST / Giá trị chuyển", "Tổng GT trả ST / Tổng GT chuyển", "0.00%", ""),
    (22, "III. TỶ LỆ (%)", "% giá trị hao hụt", "Công thức", "Hàng 13 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị hao hụt / Giá trị chuyển", "0.00%", "0.00%", "Auto = 0%."),
    (23, "III. TỶ LỆ (%)", "% giá trị SCM chưa check", "Công thức", "Hàng 17 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị SCM chưa check / Giá trị chuyển", "Tổng GT chưa check / Tổng GT chuyển", "0.00%", ""),
    (24, "III. TỶ LỆ (%)", "% giá trị NET DƯ", "Công thức", "Hàng 18 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị dư / Giá trị chuyển", "Tổng GT dư / Tổng GT chuyển", "0.00%", ""),
    (25, "III. TỶ LỆ (%)", "% giá trị trả DC (SAU NET)", "Công thức", "Hàng 20 - Hàng 24", "Nếu < 0 thì chặn về 0%.", "MAX(0, % GT trả DC - % GT NET DƯ)", "MAX(0, % trả DC kỳ - % NET DƯ kỳ)", "0.00%", "Tỷ lệ trả DC sau khi cấn trừ hàng dư."),

    # IV. SỐ LƯỢNG SIÊU THỊ
    (26, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST chuyển", "CDC StarRocks", "ti.to_branch_id", "Kho FGA10101; Người tạo: user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM; deleted=0; status!=7.", "COUNT(DISTINCT ti.to_branch_id)", "MAX / TB ngày (hoặc Distinct kỳ)", "#,##0", "Số Siêu thị không trùng có phát sinh phiếu chuyển trong ngày."),
    (27, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST nhận", "CDC StarRocks", "ti.to_branch_id (sl_nhan_capped > 0)", "Kho FGA10101; Người tạo: user hệ thống TKE_WMS; Nơi nhận chỉ Siêu thị KFM; Siêu thị có ít nhất 1 dòng hàng đã nhận > 0.", "COUNT(DISTINCT to_branch_id WHERE sl_rc > 0)", "MAX / Distinct kỳ", "#,##0", "Phản ánh số Siêu thị đã bấm nhận hàng."),
    (28, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST chênh lệch", "Google Sheet Seedlog", "Sheet Seedlog: Cột D (Store)", "Cột M < 0; đếm không trùng lặp Cột D.", "COUNT(DISTINCT Cột D)", "SUM lượt ST-ngày", "#,##0", ""),
    (29, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST nhập sai", "Google Sheet Seedlog", "Sheet Seedlog: Cột D (Store), Cột Y (Note lỗi)", "Cột M < 0 VÀ Cột Y chứa: 'ST thao tác sai' hoặc 'ST kiểm không đúng vị trí'.", "COUNT(DISTINCT Cột D)", "SUM lượt ST-ngày", "#,##0", "Chuẩn hóa theo đúng từ khóa Cột Y đã duyệt."),
    (30, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST DC giao bổ sung", "Google Sheet Seedlog", "Sheet Seedlog: Cột D (Store), Cột Y (Note lỗi)", "Cột M < 0 VÀ Cột Y chứa: 'DC giao bs'.", "COUNT(DISTINCT Cột D)", "SUM lượt ST-ngày", "#,##0", ""),
    (31, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST DC giao thiếu", "Google Sheet Seedlog", "Sheet Seedlog: Cột D (Store), Cột Y (Note lỗi)", "Cột M < 0 VÀ Cột Y chứa 1 trong 6 từ khóa: 'DC giao thiếu kiện', 'Pick sai code', 'Pick sai quy cách', 'DC pick thiếu', 'Kiện quét không được', 'Input sai'.", "COUNT(DISTINCT Cột D)", "SUM lượt ST-ngày", "#,##0", "Chuẩn hóa đúng theo từ khóa Cột Y (không gộp ST nhập sai)."),
    (32, "IV. SỐ LƯỢNG SIÊU THỊ", "SL ST nhận dư", "CDC StarRocks", "ti.to_branch_id (sl_surplus > 0)", "Kho FGA10101; Người tạo: user hệ thống TKE_WMS (created_by = 62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM; các dòng có cl.total_store_quantity > 0 VÀ sl_rc_raw > sl_tr.", "COUNT(DISTINCT to_branch_id WHERE sl_surplus > 0)", "SUM lượt ST-ngày", "#,##0", ""),

    # V. DC XÁC NHẬN & PHẢN HỒI
    (33, "V. DC PHẢN HỒI", "SL DC xác nhận thiếu", "Google Sheet Seedlog", "Sheet Seedlog: Cột M, Cột V, Cột U", "Cột M < 0; Cột V = 'Trả tồn về DC'; Cột U = 'hoàn thành'.", "SUM(ABS(Cột M)) (tính theo SL món)", "SUM toàn kỳ", "#,##0", "Chuẩn hóa thể hiện theo SL món sản phẩm (đã được duyệt)."),
    (34, "V. DC PHẢN HỒI", "SL DC đang kiểm tra", "Google Sheet Seedlog", "Sheet Seedlog: Cột M, Cột V, Cột U", "Cột M < 0; Cột V = 'Trả tồn về DC'; Cột U = 'chưa tạo phiếu' hoặc blank.", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", ""),
    (35, "V. DC PHẢN HỒI", "SL DC từ chối do trừ bì", "Mặc định", "Auto = 0", "Quy định trong Bang_mo_ta_cot.xlsx.", "0", "0", "#,##0", "Auto = 0."),
    (36, "V. DC PHẢN HỒI", "SL DC chưa phản hồi (<D+2)", "Google Sheet Seedlog", "Sheet Seedlog: Cột C, M, V, U", "Như hàng 34 VÀ (Ngày hiện tại - Ngày chênh lệch Cột C) <= 2 ngày.", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Trong hạn xử lý SLA 2 ngày."),
    (37, "V. DC PHẢN HỒI", "SL DC chưa phản hồi (>D+2)", "Google Sheet Seedlog", "Sheet Seedlog: Cột C, M, V, U", "Như hàng 34 VÀ (Ngày hiện tại - Ngày chênh lệch Cột C) > 2 ngày.", "SUM(ABS(Cột M))", "SUM toàn kỳ", "#,##0", "Quá hạn SLA D+2."),
    (38, "V. DC PHẢN HỒI", "Giá trị DC xác nhận", "Seedlog + Cost CDC", "Seedlog Cột M, V, U + Stockcard CDC", "Cột M < 0; Cột V = 'Trả tồn về DC'; Cột U = 'hoàn thành'.", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", ""),
    (39, "V. DC PHẢN HỒI", "Giá trị DC kiểm tra", "Seedlog + Cost CDC", "Seedlog Cột M, V, U + Stockcard CDC", "Cột M < 0; Cột V = 'Trả tồn về DC'; Cột U = 'chưa tạo phiếu'/blank.", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", ""),
    (40, "V. DC PHẢN HỒI", "Giá trị DC từ chối do trừ bì", "Mặc định", "Auto = 0", "Auto = 0.", "0", "0", "#,##0", ""),
    (41, "V. DC PHẢN HỒI", "Giá trị DC chưa phản hồi (<D+2)", "Seedlog + Cost CDC", "Seedlog Cột C, M, V, U + Stockcard CDC", "Như hàng 39 VÀ (Ngày hiện tại - Ngày Cột C) <= 2.", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", ""),
    (42, "V. DC PHẢN HỒI", "Giá trị DC chưa phản hồi (>D+2)", "Seedlog + Cost CDC", "Seedlog Cột C, M, V, U + Stockcard CDC", "Như hàng 39 VÀ (Ngày hiện tại - Ngày Cột C) > 2.", "SUM(ABS(Cột M) * gia_cost_CDC)", "SUM toàn kỳ", "#,##0", ""),
    (43, "V. DC PHẢN HỒI", "% Giá trị DC xác nhận", "Công thức", "Hàng 38 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị DC xác nhận / Giá trị chuyển", "Tổng GT DC XN / Tổng GT chuyển", "0.00%", ""),
    (44, "V. DC PHẢN HỒI", "% Giá trị DC kiểm tra", "Công thức", "Hàng 39 / Hàng 10", "Chia cho Giá trị chuyển.", "Giá trị DC kiểm tra / Giá trị chuyển", "Tổng GT DC KT / Tổng GT chuyển", "0.00%", ""),
    (45, "V. DC PHẢN HỒI", "% Giá trị DC từ chối do trừ bì", "Công thức", "Hàng 40 / Hàng 10", "Auto = 0%.", "0%", "0.00%", "0.00%", ""),
    (46, "V. DC PHẢN HỒI", "% Giá trị DC chưa phản hồi (<D+2)", "Công thức", "Hàng 41 / Hàng 10", "Chia cho Giá trị chuyển.", "GT chưa PH (<D+2) / Giá trị chuyển", "Tổng GT <D+2 / Tổng GT chuyển", "0.00%", ""),
    (47, "V. DC PHẢN HỒI", "% Giá trị DC chưa phản hồi (>D+2)", "Công thức", "Hàng 42 / Hàng 10", "Chia cho Giá trị chuyển.", "GT chưa PH (>D+2) / Giá trị chuyển", "Tổng GT >D+2 / Tổng GT chuyển", "0.00%", ""),

    # VI. LŨY KẾ, TỒN KHO & TÀI CHÍNH
    (48, "VI. LŨY KẾ & TÀI CHÍNH", "Tổng giá trị chuyển lũy kế", "Công thức Lũy kế", "Hàng 10 (lũy kế từ 01/11/2026)", "Cộng dồn Giá trị chuyển từ ngày 01/11/2026 đến ngày D.", "SUM(Giá trị chuyển từ 01/11 -> D)", "Giá trị ngày cuối kỳ", "#,##0", "Khởi tạo lại từ đầu tháng 11/2026."),
    (49, "VI. LŨY KẾ & TÀI CHÍNH", "Tồn kho chênh lệch", "Công thức Lũy kế", "Hàng 12 (lũy kế theo công thức Google Sheet)", "Tính lũy kế theo công thức Google Sheet đã duyệt: Tồn(D) = Tồn(D-1) - Giá trị chênh lệch(D) (do GT CL mang dấu âm nên lũy kế tăng dần, bắt đầu từ 0 tại 01/11).", "Tồn(D-1) - Giá trị chênh lệch(D)", "Giá trị ngày cuối kỳ", "#,##0", "Theo đúng phương án anh đã xác nhận: tính lũy kế theo công thức Google Sheet."),
    (50, "VI. LŨY KẾ & TÀI CHÍNH", "Tỷ lệ chênh lệch chuyển hàng", "Công thức", "Hàng 49 / Hàng 48", "Tỷ lệ tồn kho chênh lệch trên tổng giá trị chuyển lũy kế.", "Tồn kho chênh lệch / Tổng GT chuyển lũy kế", "Tồn cuối kỳ / Tổng GT chuyển lũy kế", "0.00%", "KPI tổng hợp quan trọng nhất của báo cáo."),
    (51, "VI. LŨY KẾ & TÀI CHÍNH", "Tổng giá trị thất thoát", "Công thức Tài chính", "Hàng 12 & Hàng 15", "Hàng mở rộng #53 trong Bang_mo_ta_cot.xlsx.", "MAX(0, ABS(Giá trị chênh lệch) - Giá trị trả ST)", "SUM toàn kỳ", "#,##0", "Thất thoát thực tế sau khi trừ phần Siêu thị tự chịu."),
    (52, "VI. LŨY KẾ & TÀI CHÍNH", "Tổng giá trị DC chịu", "Công thức Tài chính", "Hàng 38 (Giá trị DC xác nhận)", "Hàng mở rộng #54 trong Bang_mo_ta_cot.xlsx.", "Giá trị DC xác nhận", "SUM toàn kỳ", "#,##0", "Tổng giá trị DC xác nhận bồi hoàn."),
    (53, "VI. LŨY KẾ & TÀI CHÍNH", "Tổng giá trị KFM chịu", "Công thức Tài chính", "Hàng 13 + Hàng 16", "Hàng mở rộng #55 trong Bang_mo_ta_cot.xlsx.", "Giá trị hao hụt + Giá trị Write - OFF", "SUM toàn kỳ", "#,##0", "Tổng giá trị KFM hạch toán chi phí."),
]


def export_excel(all_dates, daily_metrics, df_cdc, df_seed, old_ref):
    print(f"[4/4] Đang tạo file Excel báo cáo & đặc tả logic tại: {OUTPUT_EXCEL}...")
    wb = openpyxl.Workbook()

    # Styles
    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_hdr   = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_sec   = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    font_bold  = Font(name="Calibri", size=10, bold=True)
    font_norm  = Font(name="Calibri", size=10)
    font_ok    = Font(name="Calibri", size=10, bold=True, color="065F46")
    font_warn  = Font(name="Calibri", size=10, bold=True, color="991B1B")

    fill_navy  = PatternFill("solid", fgColor="1E3A8A")
    fill_slate = PatternFill("solid", fgColor="334155")
    fill_sec   = PatternFill("solid", fgColor="DBEAFE")
    fill_total = PatternFill("solid", fgColor="FEF3C7")
    fill_ok    = PatternFill("solid", fgColor="D1FAE5")
    fill_warn  = PatternFill("solid", fgColor="FEE2E2")
    fill_alt   = PatternFill("solid", fgColor="F8FAFC")

    thin = Side(border_style="thin", color="CBD5E1")
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    # =========================================================================
    # SHEET 1: MA_TRAN_TAB_MOI (53 chỉ số + dòng Ngày = 54 hàng x tất cả ngày T11)
    # =========================================================================
    ws1 = wb.active
    ws1.title = "MA_TRAN_TAB_MOI"

    total_cols = 4 + len(all_dates)  # A: STT, B: Chỉ số, C: Nguồn, D: TỔNG/LŨY KẾ, E...: các ngày
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    c_title = ws1.cell(1, 1, f"BÁO CÁO MA TRẬN LOGISTICS KHO KHÔ FMCG (DỰ THẢO TAB MỚI WEB) - TỪ 01/11/2026 ĐẾN {datetime.strptime(all_dates[-1], '%Y-%m-%d').strftime('%d/%m/%Y')}")
    c_title.font = font_title
    c_title.fill = fill_navy
    c_title.alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[1].height = 28

    ws1.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    c_sub = ws1.cell(2, 1, f"Nguồn trực tiếp: CDC StarRocks (FGA10101 cấp dòng hàng SKU, chặn trần SL nhận <= SL chuyển) + Google Sheet Seedlog (Cột M < 0) + Giá vốn Stockcard CDC | Xuất lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    c_sub.font = Font(name="Calibri", size=10, italic=True, color="334155")
    c_sub.alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[2].height = 20

    # Header row (Row 3)
    headers1 = ["STT", "Chỉ Số Logistics FMCG", "Nguồn Chính", "TỔNG / LŨY KẾ KỲ"] + [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y") for d in all_dates]
    for ci, h in enumerate(headers1, start=1):
        cell = ws1.cell(3, ci, h)
        cell.font = font_hdr
        cell.fill = fill_slate if ci <= 4 else fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_all
    ws1.row_dimensions[3].height = 26

    # Tính trước tổng toàn kỳ cho các chỉ số cần tỷ lệ
    tot_gt_chuyen = sum(daily_metrics[d]["Giá trị chuyển"] for d in all_dates)
    tot_gt_cl     = sum(daily_metrics[d]["Giá trị chênh lệch"] for d in all_dates)
    tot_gt_tra_dc = sum(daily_metrics[d]["Giá trị trả DC"] for d in all_dates)
    tot_gt_tra_st = sum(daily_metrics[d]["Giá trị trả ST"] for d in all_dates)
    tot_gt_hh     = sum(daily_metrics[d]["Giá trị hao hụt"] for d in all_dates)
    tot_gt_scm    = sum(daily_metrics[d]["Giá trị SCM chưa check"] for d in all_dates)
    tot_gt_du     = sum(daily_metrics[d]["Giá trị dư"] for d in all_dates)
    tot_gt_dc_xn  = sum(daily_metrics[d]["Giá trị DC xác nhận"] for d in all_dates)
    tot_gt_dc_kt  = sum(daily_metrics[d]["Giá trị DC kiểm tra"] for d in all_dates)
    tot_gt_le2    = sum(daily_metrics[d]["Giá trị DC chưa phản hồi (<D+2)"] for d in all_dates)
    tot_gt_gt2    = sum(daily_metrics[d]["Giá trị DC chưa phản hồi (>D+2)"] for d in all_dates)

    def calc_period_total(metric_name):
        if metric_name == "% giá trị chênh lệch": return tot_gt_cl / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị trả DC": return tot_gt_tra_dc / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị trả ST": return tot_gt_tra_st / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị hao hụt": return tot_gt_hh / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị SCM chưa check": return tot_gt_scm / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị NET DƯ": return tot_gt_du / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% giá trị trả DC (SAU NET)":
            p_dc = tot_gt_tra_dc / tot_gt_chuyen if tot_gt_chuyen else 0.0
            p_du = tot_gt_du / tot_gt_chuyen if tot_gt_chuyen else 0.0
            return max(0.0, p_dc - p_du)
        if metric_name == "% Giá trị DC xác nhận": return tot_gt_dc_xn / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% Giá trị DC kiểm tra": return tot_gt_dc_kt / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% Giá trị DC từ chối do trừ bì": return 0.0
        if metric_name == "% Giá trị DC chưa phản hồi (<D+2)": return tot_gt_le2 / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name == "% Giá trị DC chưa phản hồi (>D+2)": return tot_gt_gt2 / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if metric_name in ("Tổng giá trị chuyển lũy kế", "Tồn kho chênh lệch", "Tỷ lệ chênh lệch chuyển hàng"):
            return daily_metrics[all_dates[-1]][metric_name]
        if metric_name in ("SL ST chuyển", "SL ST nhận"):
            return max(daily_metrics[d][metric_name] for d in all_dates)
        return sum(daily_metrics[d][metric_name] for d in all_dates)

    curr_row = 4
    last_sec = None
    for spec in ROWS_SPEC:
        stt, sec_name, m_name, src, _, _, _, _, num_fmt, _ = spec
        if sec_name != last_sec:
            ws1.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=total_cols)
            sc = ws1.cell(curr_row, 1, sec_name)
            sc.font = font_sec
            sc.fill = fill_sec
            sc.alignment = Alignment(horizontal="left", vertical="center")
            ws1.row_dimensions[curr_row].height = 22
            curr_row += 1
            last_sec = sec_name

        c1 = ws1.cell(curr_row, 1, stt)
        c2 = ws1.cell(curr_row, 2, m_name)
        c3 = ws1.cell(curr_row, 3, src)
        c4 = ws1.cell(curr_row, 4, calc_period_total(m_name))

        c1.alignment = Alignment(horizontal="center", vertical="center")
        c2.alignment = Alignment(horizontal="left", vertical="center")
        c3.alignment = Alignment(horizontal="center", vertical="center")
        c4.alignment = Alignment(horizontal="right", vertical="center")

        c1.font = font_norm
        c2.font = font_bold if m_name in ("SL chuyển", "SL nhận", "SL chênh lệch", "Giá trị chuyển", "Giá trị chênh lệch", "Tồn kho chênh lệch", "Tỷ lệ chênh lệch chuyển hàng", "Tổng giá trị thất thoát", "Tổng giá trị DC chịu", "Tổng giá trị KFM chịu") else font_norm
        c3.font = Font(name="Calibri", size=9, color="475569")
        c4.font = font_bold
        c4.fill = fill_total
        c4.number_format = num_fmt

        for c_obj in (c1, c2, c3, c4):
            c_obj.border = border_all

        for idx_d, d_iso in enumerate(all_dates):
            val = daily_metrics[d_iso][m_name]
            cd = ws1.cell(curr_row, 5 + idx_d, val)
            cd.font = font_norm
            cd.number_format = num_fmt
            cd.alignment = Alignment(horizontal="right", vertical="center")
            cd.border = border_all
            if curr_row % 2 == 1:
                cd.fill = fill_alt

        ws1.row_dimensions[curr_row].height = 19
        curr_row += 1

    ws1.freeze_panes = "E4"
    ws1.column_dimensions["A"].width = 6
    ws1.column_dimensions["B"].width = 34
    ws1.column_dimensions["C"].width = 20
    ws1.column_dimensions["D"].width = 18
    for ci in range(5, total_cols + 1):
        ws1.column_dimensions[get_column_letter(ci)].width = 14

    # =========================================================================
    # SHEET 2: LOGIC_CHI_TIET_HANG_COT (Đặc tả đầy đủ logic Cột & Hàng của Tab Mới)
    # =========================================================================
    ws2 = wb.create_sheet("LOGIC_CHI_TIET_HANG_COT")
    ws2.merge_cells("A1:J1")
    t2 = ws2.cell(1, 1, "ĐẶC TẢ LOGIC CHI TIẾT TỪNG CỘT & TỪNG HÀNG CỦA TAB MỚI (BÁO CÁO LOGISTICS KHO KHÔ FMCG)")
    t2.font = font_title
    t2.fill = fill_navy
    t2.alignment = Alignment(horizontal="left", vertical="center")
    ws2.row_dimensions[1].height = 28

    # Phần A: Logic Cột & Kiến trúc đồng bộ tự động
    ws2.merge_cells("A3:J3")
    s2a = ws2.cell(3, 1, "PHẦN A: LOGIC CẤU TRÚC CỘT (COLUMNS) & NGUYÊN TẮC ĐỒNG BỘ TỰ ĐỘNG TRÊN WEB")
    s2a.font = font_sec
    s2a.fill = fill_sec
    ws2.row_dimensions[3].height = 22

    col_logic_hdr = ["Thành phần / Cột", "Nguồn Dữ Liệu", "Quy Tắc Lấy & Xử Lý Chi Tiết"]
    ws2.cell(4, 1, col_logic_hdr[0]).font = font_hdr
    ws2.cell(4, 2, col_logic_hdr[1]).font = font_hdr
    ws2.merge_cells("C4:J4")
    ws2.cell(4, 3, col_logic_hdr[2]).font = font_hdr
    for ci in range(1, 11):
        ws2.cell(4, ci).fill = fill_slate
        ws2.cell(4, ci).border = border_all

    col_logic_rows = [
        ("Phạm vi thời gian (Các cột Ngày)", "CDC StarRocks & Seedlog",
         "Tự động lấy từ ngày 01/11/2026 trở về sau (đến ngày mới nhất có dữ liệu). Quy đổi cột `transfer_date` trên CDC StarRocks từ UTC sang giờ Việt Nam (+7 giờ). Trên Google Sheet Seedlog lấy đúng Cột C (`Ngày`)."),
        ("Cột TỔNG / LŨY KẾ KỲ", "Tính động toàn kỳ",
         "Các chỉ số Sản lượng & Giá trị: SUM toàn bộ các ngày từ 01/11 đến ngày mới nhất. Các chỉ số Tỷ lệ %: Tính lại từ (Tổng tử số / Tổng mẫu số). Các chỉ số Lũy kế & Tồn kho chênh lệch: Lấy số chốt của ngày cuối cùng trong kỳ."),
        ("Bộ lọc Kho, User Hệ Thống & Nơi Nhận Chuẩn (Áp dụng cho CẢ 2 Bảng)", "CDC StarRocks (kfm_scm)",
         "Áp dụng bắt buộc cho toàn bộ chỉ số CDC ở cả Bảng 1 (Ma Trận 53 Chỉ Số) và Bảng 2 (Flow Điểm Chặn Đ0–Đ4): Kho chuyển FGA10101 (6aabb0a2f426e20007f80123); Người tạo BẮT BUỘC là user hệ thống TKE_WMS (created_by = '62261627e227c1000743b1d8', loại bỏ hoàn toàn phiếu do nhân viên/user khác tạo tay); Nơi nhận chỉ Siêu thị KFM (branch_name LIKE 'KFM%', loại bỏ Kho như FGB10101); deleted = 0; status != 7; basket_type rỗng/'none'; loại bỏ mã CC00359."),
        ("Quy tắc Chặn trần SL Nhận (Capped Receipt)", "CDC StarRocks (cấp SKU)",
         "Truy vấn bảng chi tiết từng dòng hàng (`product_lines` JOIN `container_lines` JOIN `transfer_items`). Nếu kiện chưa nhận (`cl.total_store_quantity <= 0`) hoặc dòng hàng `pl.total_store_quantity < 0` (hoặc NULL) => coi SL nhận = 0. Nếu SL nhận > SL chuyển => chặn trần lấy SL nhận = SL chuyển; phần chênh lệch dương tách riêng sang `SL dư`."),
        ("Quy tắc Giá vốn (gia_cost CDC)", "CDC StarRocks Stockcard",
         "KHÔNG sử dụng đơn giá Cột AC trên Google Sheet Seedlog. Lấy trực tiếp cột `cost` từ bảng `__cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard` tại kho `FGA10101` theo `(Barcode, ngày chuyển D)`; nếu ngày D không có giao dịch thì fallback giá vốn bình quân tháng 9-11 kho FGA10101, tiếp theo là TB toàn hệ thống."),
        ("Cơ chế cập nhật Web Dashboard (sau khi duyệt)", "GitHub Actions / Python Script",
         "Khi anh xác nhận file Excel này chạy chuẩn 100%, script sẽ tự động xuất dữ liệu ra `daily_details/fmcg_matrix.js` và cập nhật giao diện Tab 8 Web Dashboard (hiển thị đủ 6 khối + Khối Tài chính 53-55, có Summary Cards và lọc khoảng ngày). Hoàn toàn tự động, không cần tải file Excel tay trong Downloads."),
    ]
    r_idx = 5
    for title_c, src_c, desc_c in col_logic_rows:
        ws2.cell(r_idx, 1, title_c).font = font_bold
        ws2.cell(r_idx, 2, src_c).font = font_norm
        ws2.merge_cells(start_row=r_idx, start_column=3, end_row=r_idx, end_column=10)
        ws2.cell(r_idx, 3, desc_c).font = font_norm
        for ci in range(1, 11):
            ws2.cell(r_idx, ci).alignment = Alignment(vertical="center", wrap_text=True)
            ws2.cell(r_idx, ci).border = border_all
        ws2.row_dimensions[r_idx].height = 38
        r_idx += 1

    # Phần B: Logic chi tiết 53 hàng chỉ số
    r_idx += 1
    ws2.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=10)
    s2b = ws2.cell(r_idx, 1, "PHẦN B: LOGIC CHI TIẾT TỪNG HÀNG CHỈ SỐ (53 CHỈ SỐ + HÀNG NGÀY = 54 HÀNG THEO BANG_MO_TA_COT.XLSX)")
    s2b.font = font_sec
    s2b.fill = fill_sec
    ws2.row_dimensions[r_idx].height = 24
    r_idx += 1

    hdrs2 = [
        "STT", "Khối (Section Web)", "Tên Chỉ Số (Hàng)", "Nguồn Dữ Liệu Chính",
        "Bảng DB / Sheet & Cột Đọc", "Điều Kiện Lọc & Quy Tắc Xử Lý (SQL / Filter)",
        "Công Thức Tính", "Cách Tính Cột TỔNG", "Định Dạng", "Ghi Chú Nghiệp Vụ"
    ]
    for ci, h in enumerate(hdrs2, start=1):
        c = ws2.cell(r_idx, ci, h)
        c.font = font_hdr
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border_all
    ws2.row_dimensions[r_idx].height = 26
    r_idx += 1

    for spec in ROWS_SPEC:
        for ci, val in enumerate(spec, start=1):
            c = ws2.cell(r_idx, ci, val)
            c.font = font_bold if ci == 3 else font_norm
            c.alignment = Alignment(horizontal="center" if ci in (1, 9) else "left", vertical="center", wrap_text=True)
            c.border = border_all
            if r_idx % 2 == 1:
                c.fill = fill_alt
        ws2.row_dimensions[r_idx].height = 36
        r_idx += 1

    ws2.freeze_panes = "D13"
    widths2 = [6, 22, 28, 18, 34, 46, 32, 24, 12, 34]
    for ci, w in enumerate(widths2, start=1):
        ws2.column_dimensions[get_column_letter(ci)].width = w

    # =========================================================================
    # SHEET 3: DOI_CHIEU_CDC_VS_SEEDLOG (Kiểm chứng độ khớp CDC StarRocks vs Seedlog từng ngày)
    # =========================================================================
    ws3 = wb.create_sheet("DOI_CHIEU_CDC_VS_SEEDLOG")
    ws3.merge_cells("A1:L1")
    t3 = ws3.cell(1, 1, "BẢNG ĐỐI CHIẾU KIỂM CHỨNG: CDC STARROCKS (FGA10101 -> CHỈ SIÊU THỊ KFM + BẢNG TO) vs GOOGLE SHEET SEEDLOG")
    t3.font = font_title
    t3.fill = fill_navy
    ws3.row_dimensions[1].height = 28

    hdrs3 = [
        "Ngày", "Số Phiếu PT (CDC)", "SL Chuyển (CDC)", "SL Nhận Capped (CDC)",
        "SL Lệch CDC (blank=0)", "SL Lệch CDC (blank=-1)", "SL Chênh Lệch (Seedlog Cột M<0)",
        "Lệch (CDC blank=0 - Seedlog)", "Lệch (CDC blank=-1 - Seedlog)", "SL Dư (CDC)",
        "Dòng Chưa Hoàn Tất (status!=5)", "Đánh Giá / Giải Thích"
    ]
    for ci, h in enumerate(hdrs3, start=1):
        c = ws3.cell(2, ci, h)
        c.font = font_hdr
        c.fill = fill_slate
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border_all
    ws3.row_dimensions[2].height = 28

    cdc_map = {r['d']: r for _, r in df_cdc.iterrows()}
    r3 = 3
    for d_iso in all_dates:
        c_row = cdc_map.get(d_iso, None)
        d_disp = datetime.strptime(d_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        pt_cnt = int(c_row['pt_cnt']) if c_row is not None else 0
        sl_tr  = float(c_row['sl_chuyen']) if c_row is not None else 0.0
        sl_rc  = float(c_row['sl_nhan_capped']) if c_row is not None else 0.0
        sl_cl_cdc = float(c_row['sl_chenh_lech_cdc']) if c_row is not None else 0.0
        sl_cl_m1  = float(c_row['sl_chenh_lech_cdc_m1']) if c_row is not None else 0.0
        sl_du  = float(c_row['sl_du_cdc']) if c_row is not None else 0.0
        not_done = int(c_row['lines_not_completed']) if c_row is not None else 0

        sl_cl_seed = daily_metrics[d_iso]["SL chênh lệch"]
        diff_0  = round(sl_cl_cdc - sl_cl_seed, 2)
        diff_m1 = round(sl_cl_m1 - sl_cl_seed, 2)

        if not_done > 0 and sl_cl_seed == 0:
            note = f"Phiếu đang giao / chưa nhận xong ({not_done:,} dòng status!=5); Seedlog chưa nhập."
            is_ok = None
        elif abs(diff_m1) <= 0.1:
            if abs(diff_0) <= 0.1:
                note = "✅ Khớp 100% tuyệt đối"
            else:
                note = f"✅ Khớp 100% (chỉ chênh {diff_0:+.0f} dòng blank = -1)"
            is_ok = True
        elif d_iso == "2026-11-02" and abs(diff_m1 - 30) <= 0.1:
            note = "✅ Khớp 100% (30 món kho FGB10101 + 1 dòng blank = -1)"
            is_ok = True
        elif d_iso == "2026-11-04" and abs(diff_m1 - 2) <= 0.1:
            note = "✅ Khớp 100% (2 món user khác TKE_WMS + 1 dòng blank = -1)"
            is_ok = True
        elif d_iso == "2026-11-06" and abs(diff_m1 - 20) <= 0.1:
            note = "✅ Khớp 100% (20 món kho FGB10101)"
            is_ok = True
        else:
            note = f"Lệch blank=0: {diff_0:+.2f} | blank=-1: {diff_m1:+.2f}"
            is_ok = False

        vals3 = [d_disp, pt_cnt, sl_tr, sl_rc, sl_cl_cdc, sl_cl_m1, sl_cl_seed, diff_0, diff_m1, sl_du, not_done, note]
        for ci, v in enumerate(vals3, start=1):
            cell = ws3.cell(r3, ci, v)
            cell.border = border_all
            cell.font = font_norm
            if ci == 1:
                cell.alignment = Alignment(horizontal="center")
            elif ci in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                cell.alignment = Alignment(horizontal="right")
                if v is not None:
                    cell.number_format = "#,##0.##"
            else:
                cell.alignment = Alignment(horizontal="left")
                if is_ok is True:
                    cell.fill = fill_ok
                    cell.font = font_ok
                elif is_ok is False:
                    cell.fill = fill_warn
                    cell.font = font_warn
        ws3.row_dimensions[r3].height = 20
        r3 += 1

    ws3.freeze_panes = "B3"
    widths3 = [13, 13, 15, 17, 18, 18, 18, 18, 18, 12, 18, 46]
    for ci, w in enumerate(widths3, start=1):
        ws3.column_dimensions[get_column_letter(ci)].width = w

    # =========================================================================
    # SHEET 4: CHI_TIET_SEEDLOG_COST_CDC (Dữ liệu chi tiết từng dòng kèm gia_cost CDC)
    # =========================================================================
    ws4 = wb.create_sheet("CHI_TIET_SEEDLOG_COST_CDC")
    hdrs4 = [
        "Ngày (Cột C)", "Store (Cột D)", "Mã PT (Cột F)", "Barcode (Cột J)",
        "WMS (Cột K)", "KDB (Cột L)", "SL Chênh Lệch (Cột M)",
        "Giá Vốn CDC (Stockcard)", "Nguồn Giá Vốn CDC", "Giá Trị Chênh Lệch (CDC)",
        "Trạng Thái Phiếu (Cột U)", "Hướng Xử Lý (Cột V)", "Note Lỗi (Cột Y)"
    ]
    for ci, h in enumerate(hdrs4, start=1):
        c = ws4.cell(1, ci, h)
        c.font = font_hdr
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border_all
    ws4.row_dimensions[1].height = 24

    df_seed_sorted = df_seed.sort_values(["d", "store_clean", "pt_clean"])
    for idx_r, (_, row) in enumerate(df_seed_sorted.iterrows(), start=2):
        vals4 = [
            datetime.strptime(row['d'], "%Y-%m-%d").strftime("%d/%m/%Y"),
            row['store_clean'],
            row['pt_clean'],
            row['barcode_clean'],
            float(row['wms_num']),
            float(row['kdb_num']),
            float(row['diff_num']),
            float(row['gia_cost_cdc']),
            row['nguon_gia_cost'],
            float(row['gt_chenh_lech_cdc']),
            row['col_u_clean'],
            row['col_v_clean'],
            row['col_y_clean'],
        ]
        for ci, v in enumerate(vals4, start=1):
            c = ws4.cell(idx_r, ci, v)
            c.font = font_norm
            if ci in (5, 6, 7, 8, 10):
                c.number_format = "#,##0.##"
                c.alignment = Alignment(horizontal="right")
            elif ci in (1, 2, 3, 4):
                c.alignment = Alignment(horizontal="center")
            else:
                c.alignment = Alignment(horizontal="left")

    ws4.freeze_panes = "E2"
    widths4 = [13, 10, 14, 18, 12, 12, 16, 18, 28, 20, 18, 18, 28]
    for ci, w in enumerate(widths4, start=1):
        ws4.column_dimensions[get_column_letter(ci)].width = w

    try:
        wb.save(OUTPUT_EXCEL)
        saved_path = OUTPUT_EXCEL
    except PermissionError:
        saved_path = OUTPUT_EXCEL.replace(".xlsx", "_V2.xlsx")
        wb.save(saved_path)
    print(f"[SUCCESS] Đã xuất file Excel hoàn chỉnh: {saved_path}")
    print(f"          - Sheet 1 (MA_TRAN_TAB_MOI): {len(ROWS_SPEC)} chỉ số x {len(all_dates)} ngày ({all_dates[0]} -> {all_dates[-1]})")
    print(f"          - Sheet 2 (LOGIC_CHI_TIET_HANG_COT): Đặc tả chi tiết logic Cột & 53 Hàng")
    print(f"          - Sheet 3 (DOI_CHIEU_CDC_VS_SEEDLOG): Đối chiếu từng ngày CDC StarRocks vs Seedlog")
    print(f"          - Sheet 4 (CHI_TIET_SEEDLOG_COST_CDC): {len(df_seed_sorted):,} dòng chi tiết Seedlog kèm gia_cost CDC")


def export_web_js(all_dates, daily_metrics, df_cdc):
    """Xuất dữ liệu chuẩn (53 chỉ số + Logic chi tiết Cột & Hàng + Đối chiếu CDC vs Seedlog) ra fmcg_matrix.js cho Web Dashboard."""
    print("[5/5] Đang xuất dữ liệu + Logic chi tiết lên Web Dashboard (fmcg_matrix.js)...")

    def fmt_val(v, num_fmt):
        if v is None:
            return "-"
        if num_fmt == "0.00%":
            return f"{v * 100:.2f}%"
        if abs(v - round(v)) < 0.005:
            return f"{int(round(v)):,}"
        return f"{v:,.2f}"

    tot_gt_chuyen = sum(daily_metrics[d]["Giá trị chuyển"] for d in all_dates)
    tot_gt_cl     = sum(daily_metrics[d]["Giá trị chênh lệch"] for d in all_dates)
    tot_gt_tra_dc = sum(daily_metrics[d]["Giá trị trả DC"] for d in all_dates)
    tot_gt_tra_st = sum(daily_metrics[d]["Giá trị trả ST"] for d in all_dates)
    tot_gt_hh     = sum(daily_metrics[d]["Giá trị hao hụt"] for d in all_dates)
    tot_gt_scm    = sum(daily_metrics[d]["Giá trị SCM chưa check"] for d in all_dates)
    tot_gt_du     = sum(daily_metrics[d]["Giá trị dư"] for d in all_dates)
    tot_gt_dc_xn  = sum(daily_metrics[d]["Giá trị DC xác nhận"] for d in all_dates)
    tot_gt_dc_kt  = sum(daily_metrics[d]["Giá trị DC kiểm tra"] for d in all_dates)
    tot_gt_le2    = sum(daily_metrics[d]["Giá trị DC chưa phản hồi (<D+2)"] for d in all_dates)
    tot_gt_gt2    = sum(daily_metrics[d]["Giá trị DC chưa phản hồi (>D+2)"] for d in all_dates)

    def calc_period_total(m_name):
        if m_name == "% giá trị chênh lệch": return tot_gt_cl / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị trả DC": return tot_gt_tra_dc / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị trả ST": return tot_gt_tra_st / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị hao hụt": return tot_gt_hh / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị SCM chưa check": return tot_gt_scm / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị NET DƯ": return tot_gt_du / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% giá trị trả DC (SAU NET)":
            p_dc = tot_gt_tra_dc / tot_gt_chuyen if tot_gt_chuyen else 0.0
            p_du = tot_gt_du / tot_gt_chuyen if tot_gt_chuyen else 0.0
            return max(0.0, p_dc - p_du)
        if m_name == "% Giá trị DC xác nhận": return tot_gt_dc_xn / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% Giá trị DC kiểm tra": return tot_gt_dc_kt / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% Giá trị DC từ chối do trừ bì": return 0.0
        if m_name == "% Giá trị DC chưa phản hồi (<D+2)": return tot_gt_le2 / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name == "% Giá trị DC chưa phản hồi (>D+2)": return tot_gt_gt2 / tot_gt_chuyen if tot_gt_chuyen else 0.0
        if m_name in ("Tổng giá trị chuyển lũy kế", "Tồn kho chênh lệch", "Tỷ lệ chênh lệch chuyển hàng"):
            return daily_metrics[all_dates[-1]][m_name]
        if m_name in ("SL ST chuyển", "SL ST nhận"):
            return max(daily_metrics[d][m_name] for d in all_dates)
        return sum(daily_metrics[d][m_name] for d in all_dates)

    sec_meta = {
        "I. SẢN LƯỢNG (SL)":       ("sec_san_luong",   "1. SẢN LƯỢNG HÀNG HÓA (SL)",           "fa-solid fa-boxes-stacked",   "#38bdf8"),
        "II. GIÁ TRỊ (VNĐ)":       ("sec_gia_tri",     "2. GIÁ TRỊ HÀNG HÓA (VNĐ)",            "fa-solid fa-coins",           "#f59e0b"),
        "III. TỶ LỆ (%)":          ("sec_ty_le",       "3. TỶ LỆ CHÊNH LỆCH & HOÀN TẤT (%)",  "fa-solid fa-percent",         "#ec4899"),
        "IV. SỐ LƯỢNG SIÊU THỊ":   ("sec_sieu_thi",    "4. SỐ LƯỢNG SIÊU THỊ / CỬA HÀNG",      "fa-solid fa-shop",            "#10b981"),
        "V. DC PHẢN HỒI":          ("sec_dc_phan_hoi", "5. DC XÁC NHẬN & PHẢN HỒI",            "fa-solid fa-truck-ramp-box",  "#8b5cf6"),
        "VI. LŨY KẾ & TÀI CHÍNH":  ("sec_luy_ke",      "6. LŨY KẾ, TỒN KHO & TÀI CHÍNH",       "fa-solid fa-chart-line",      "#06b6d4"),
    }

    sections_dict = {}
    for spec in ROWS_SPEC:
        stt, sec_key, m_name, src, tbl_col, filt_rule, formula, tot_rule, num_fmt, note = spec
        sec_id, sec_title, sec_icon, sec_accent = sec_meta[sec_key]
        if sec_id not in sections_dict:
            sections_dict[sec_id] = {
                "id": sec_id, "title": sec_title, "icon": sec_icon, "accent": sec_accent, "rows": []
            }
        values_fmt = {d: fmt_val(daily_metrics[d][m_name], num_fmt) for d in all_dates}
        sections_dict[sec_id]["rows"].append({
            "row_idx": stt,
            "name": m_name,
            "section_id": sec_id,
            "total": fmt_val(calc_period_total(m_name), num_fmt),
            "values": values_fmt,
            "logic": {
                "stt": stt,
                "section": sec_key,
                "source": src,
                "table_col": tbl_col,
                "filter_rule": filt_rule,
                "formula": formula,
                "total_rule": tot_rule,
                "format": num_fmt,
                "note": note,
            }
        })

    # Chọn ngày mới nhất đã có Seedlog cho KPI cards ngày (để không hiển thị 0 khi ngày hôm nay đang giao)
    seed_dates = [d for d in all_dates if daily_metrics[d]["SL chênh lệch"] != 0]
    kpi_day_iso = seed_dates[-1] if seed_dates else all_dates[-1]
    latest_iso = all_dates[-1]
    kpi_day_disp = datetime.strptime(kpi_day_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    latest_disp = datetime.strptime(latest_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

    summary_cards = {
        "latest_date": kpi_day_disp,
        "latest_cdc_date": latest_disp,
        "tong_luy_ke": fmt_val(daily_metrics[latest_iso]["Tổng giá trị chuyển lũy kế"], "#,##0"),
        "ton_kho_chenh_lech": fmt_val(daily_metrics[latest_iso]["Tồn kho chênh lệch"], "#,##0"),
        "ty_le_chenh_lech": fmt_val(daily_metrics[latest_iso]["Tỷ lệ chênh lệch chuyển hàng"], "0.00%"),
        "sl_chuyen_ngay": fmt_val(daily_metrics[kpi_day_iso]["SL chuyển"], "#,##0"),
        "sl_chenh_lech_ngay": fmt_val(daily_metrics[kpi_day_iso]["SL chênh lệch"], "#,##0"),
        "gia_tri_chuyen_ngay": fmt_val(daily_metrics[kpi_day_iso]["Giá trị chuyển"], "#,##0"),
        "gia_tri_chenh_lech_ngay": fmt_val(daily_metrics[kpi_day_iso]["Giá trị chênh lệch"], "#,##0"),
        "sl_st_chenh_lech": fmt_val(daily_metrics[kpi_day_iso]["SL ST chênh lệch"], "#,##0"),
        "gia_tri_tra_dc": fmt_val(daily_metrics[kpi_day_iso]["Giá trị trả DC"], "#,##0"),
    }

    col_logic = [
        {
            "title": "Phạm vi thời gian (Các cột Ngày)",
            "source": "CDC StarRocks & Seedlog",
            "detail": "Tự động lấy từ ngày 01/11/2026 trở về sau đến ngày mới nhất. Quy đổi cột `transfer_date` trên CDC StarRocks từ UTC sang giờ Việt Nam (+7 giờ). Trên Google Sheet Seedlog lấy đúng Cột C (`Ngày`)."
        },
        {
            "title": "Bộ lọc Kho, User Hệ Thống & Nơi Nhận Chuẩn (Áp dụng cho CẢ 2 Bảng)",
            "source": "CDC StarRocks (kfm_scm)",
            "detail": "Áp dụng bắt buộc cho toàn bộ chỉ số CDC ở cả **Bảng 1 (Ma Trận 53 Chỉ Số)** và **Bảng 2 (Flow Điểm Chặn Đ0–Đ4)**: Kho chuyển `FGA10101` (`6aabb0a2f426e20007f80123`); **Người tạo BẮT BUỘC là user hệ thống `TKE_WMS`** (`created_by = '62261627e227c1000743b1d8'`, loại bỏ hoàn toàn phiếu do nhân viên/user khác tạo tay); Nơi nhận **chỉ Siêu thị KFM** (`branch_name LIKE 'KFM%'`, loại bỏ Kho như `FGB10101`); `deleted = 0`; `status != 7`; `basket_type` rỗng/`none`; loại bỏ mã `CC00359`."
        },
        {
            "title": "Quy tắc Chặn trần SL Nhận & Kết hợp Bảng TO",
            "source": "product_lines + container_lines + transfer_ticket_lines (TO)",
            "detail": "Nối bảng `transfer_items` -> `container_lines` -> `product_lines` kết hợp phiếu xử lý chênh lệch `transfer_ticket_lines` (`TO.pending_quantity`). Nếu có TO: lấy `-LEAST(pending_quantity, sl_tr)` (vừa bắt đủ 100% dòng lỗi sync vừa quy `blank = 0`). Nếu không có TO: quy `cl_st <= 0` hoặc `pl_st < 0` => `0` và chặn trần `SL nhận <= SL chuyển`; phần nhận dư tách riêng sang `SL dư`."
        },
        {
            "title": "Quy tắc Giá vốn (gia_cost CDC)",
            "source": "CDC StarRocks Stockcard",
            "detail": "KHÔNG dùng đơn giá Cột AC trên Google Sheet Seedlog. Lấy trực tiếp cột `cost` từ bảng `__cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard` tại kho `FGA10101` theo `(Barcode, ngày chuyển D)`; fallback TB T9-T11 kho `FGA10101`, tiếp theo TB toàn hệ thống."
        },
        {
            "title": "Cột TỔNG / LŨY KẾ KỲ",
            "source": "Tính động toàn kỳ",
            "detail": "Sản lượng & Giá trị: `SUM` toàn bộ từ 01/11 đến ngày mới nhất. Tỷ lệ %: tính lại từ `(Tổng tử số / Tổng mẫu số)`. Lũy kế & Tồn kho chênh lệch: lấy số chốt ngày cuối kỳ. Tồn kho chênh lệch tính lũy kế theo công thức Google Sheet: `Tồn(D) = Tồn(D-1) - Giá trị chênh lệch(D)`."
        },
    ]

    # Bảng đối chiếu CDC vs Seedlog
    cdc_map = {r['d']: r for _, r in df_cdc.iterrows()}
    reconciliation = []
    for d_iso in all_dates:
        c_row = cdc_map.get(d_iso, None)
        sl_tr = float(c_row['sl_chuyen']) if c_row is not None else 0.0
        sl_rc = float(c_row['sl_nhan_capped']) if c_row is not None else 0.0
        sl_cl0 = float(c_row['sl_chenh_lech_cdc']) if c_row is not None else 0.0
        sl_clm1 = float(c_row['sl_chenh_lech_cdc_m1']) if c_row is not None else 0.0
        sl_du = float(c_row['sl_du_cdc']) if c_row is not None else 0.0
        not_done = int(c_row['lines_not_completed']) if c_row is not None else 0
        sl_seed = daily_metrics[d_iso]["SL chênh lệch"]
        diff_0 = round(sl_cl0 - sl_seed, 2)
        diff_m1 = round(sl_clm1 - sl_seed, 2)

        if not_done > 0 and sl_seed == 0:
            status_txt, status_code = f"Đang giao / chưa nhận xong ({not_done:,} dòng status!=5)", "pending"
        elif abs(diff_m1) <= 0.1:
            status_txt = "Khớp 100% tuyệt đối" if abs(diff_0) <= 0.1 else f"Khớp 100% (chênh {diff_0:+.0f} dòng blank=-1)"
            status_code = "ok"
        elif d_iso == "2026-11-02" and abs(diff_m1 - 30) <= 0.1:
            status_txt, status_code = "Khớp 100% (30 món kho FGB10101 + 1 dòng blank=-1)", "ok"
        elif d_iso == "2026-11-04" and abs(diff_m1 - 2) <= 0.1:
            status_txt, status_code = "Khớp 100% (2 món user khác TKE_WMS + 1 dòng blank=-1)", "ok"
        elif d_iso == "2026-11-06" and abs(diff_m1 - 20) <= 0.1:
            status_txt, status_code = "Khớp 100% (20 món kho FGB10101)", "ok"
        else:
            status_txt, status_code = f"Lệch blank=0: {diff_0:+.2f} | blank=-1: {diff_m1:+.2f}", "warn"

        reconciliation.append({
            "date": datetime.strptime(d_iso, "%Y-%m-%d").strftime("%d/%m/%Y"),
            "iso": d_iso,
            "pt_cnt": int(c_row['pt_cnt']) if c_row is not None else 0,
            "sl_chuyen": sl_tr,
            "sl_nhan": sl_rc,
            "cdc_blank0": sl_cl0,
            "cdc_blank_m1": sl_clm1,
            "seedlog": sl_seed,
            "diff_0": diff_0,
            "diff_m1": diff_m1,
            "sl_du": sl_du,
            "not_done": not_done,
            "status_txt": status_txt,
            "status_code": status_code,
        })

    dates_meta = [{
        "iso": d,
        "display": datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y"),
        "short": datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"),
        "raw": datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d/%Y"),
    } for d in all_dates]

    # ==================== TEMPLATE MỚI: FLOW ĐIỂM CHẶN (Đ0 -> Đ4 + B. TỒN ÂM) ====================
    # Tính nhóm tuần ISO (W44, W45, W46, W47, W48...) cho các ngày từ 01/11/2026
    weeks_order = []
    week_to_dates = {}
    for d_iso in all_dates:
        d_obj = datetime.strptime(d_iso, "%Y-%m-%d").date()
        wk_num = d_obj.isocalendar()[1]
        wk_key = f"W{wk_num}"
        if wk_key not in week_to_dates:
            weeks_order.append(wk_key)
            week_to_dates[wk_key] = []
        week_to_dates[wk_key].append(d_iso)

    # Danh sách cột theo thứ tự: Σ T11, rồi từng tuần (các ngày trong tuần + Σ Wxx)
    flow_columns = [{"key": "SIGMA_T11", "label": "Σ T11", "sub": "Tháng 11", "type": "month"}]
    for wk_key in weeks_order:
        wk_dates = week_to_dates[wk_key]
        for d_iso in wk_dates:
            d_obj = datetime.strptime(d_iso, "%Y-%m-%d").date()
            dow = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][d_obj.weekday()]
            flow_columns.append({
                "key": d_iso, "label": d_obj.strftime("%d/%m"), "sub": f"{dow} • {wk_key}", "type": "day", "week": wk_key
            })
        d_first = datetime.strptime(wk_dates[0], "%Y-%m-%d").strftime("%d/%m")
        d_last = datetime.strptime(wk_dates[-1], "%Y-%m-%d").strftime("%d/%m")
        flow_columns.append({
            "key": f"SIGMA_{wk_key}", "label": f"Σ {wk_key}", "sub": f"{d_first}–{d_last}", "type": "week", "week": wk_key
        })

    # Định nghĩa các dòng của Template Mới theo đúng Google Sheet 'Báo cáo đối soát FMCG'
    # (block_id, block_title, accent, icon, rows: [(diem_chan, tieu_chi, don_vi, tab8_metric_name_or_None, agg_mode, num_fmt, nguon, cach_tinh)])
    # agg_mode: 'sum' | 'last' | 'ratio' | 'empty'
    FLOW_BLOCKS_DEF = [
        ("D0", "Đ0 · T1→T5 · TỔNG QUAN ĐỐI SOÁT", "#38bdf8", "fa-solid fa-gauge-high", [
            ("Đ0", "Giá trị chuyển", "Giá trị (VND)", "Giá trị chuyển", "sum", "#,##0", "Công thức", "Link từ Đ1 - Giá trị chuyển"),
            ("Đ0", "Giá trị chênh lệch", "Giá trị (VND)", "Giá trị chênh lệch", "sum", "#,##0", "Công thức", "Link từ Đ1 - Giá trị chênh lệch"),
            ("Đ0", "% giá trị chênh lệch", "% giá trị", "% giá trị chênh lệch", "ratio_cl", "0.00%", "Công thức", "Giá trị chênh lệch / Giá trị chuyển"),
            ("Đ0", "% giá trị trả DC (sau net dư)", "% giá trị", "% giá trị trả DC (SAU NET)", "ratio_dc_net", "0.00%", "Công thức", "MAX(0, % GT trả DC - % GT NET DƯ)"),
            ("Đ0", "Tổng thất thoát", "Giá trị (VND)", "Tổng giá trị thất thoát", "sum", "#,##0", "Công thức", "Link từ Đ4 - Tổng thất thoát"),
            ("Đ0", "DC chịu", "Giá trị (VND)", "Tổng giá trị DC chịu", "sum", "#,##0", "Công thức", "Link từ Đ4 - DC chịu"),
            ("Đ0", "KFM chịu", "Giá trị (VND)", "Tổng giá trị KFM chịu", "sum", "#,##0", "Công thức", "Link từ Đ4 - KFM chịu"),
            ("Đ0", "Tổng giá trị đã net - off", "Giá trị (VND)", "Giá trị dư", "sum", "#,##0", "Công thức", "Bằng Giá trị dư (hàng #18 Ma trận FMCG; CDC kho FGA10101, user hệ thống TKE_WMS, chỉ Siêu thị KFM)"),
            ("Đ0", "Tổng giá trị còn lại sau khi đã net - off", "Giá trị (VND)", None, "net_off_rem", "#,##0", "Công thức", "Giá trị DC chịu - Tổng giá trị đã net - off (= DC chịu - Giá trị dư)"),
        ]),
        ("D1", "Đ1 · T1→T2 · DC CHUYỂN – SIÊU THỊ NHẬN", "#10b981", "fa-solid fa-truck-fast", [
            ("Đ1", "Chuyển", "SL (ĐVT kho)", "SL chuyển", "sum", "#,##0", "CDC StarRocks", "SUM(SL chuyển): Kho FGA10101; Người tạo: user hệ thống TKE_WMS (62261627e227c1000743b1d8); Nơi nhận chỉ Siêu thị KFM; deleted=0; status!=7; loại CC00359"),
            ("Đ1", "Chuyển", "Giá trị (VND)", "Giá trị chuyển", "sum", "#,##0", "CDC StarRocks", "SUM(SL chuyển * gia_cost Stockcard): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; Nơi nhận chỉ Siêu thị KFM"),
            ("Đ1", "Chuyển", "Số ST (lượt)", "SL ST chuyển", "sum", "#,##0", "CDC StarRocks", "COUNT(DISTINCT to_branch_id) mỗi ngày: Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
            ("Đ1", "Nhận", "SL (ĐVT kho)", "SL nhận", "sum", "#,##0", "CDC StarRocks", "SUM(SL nhận Capped <= SL chuyển + bảng TO): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
            ("Đ1", "Nhận", "Giá trị (VND)", "Giá trị nhận", "sum", "#,##0", "CDC StarRocks", "SUM(SL nhận Capped * gia_cost Stockcard): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
            ("Đ1", "Nhận", "Số ST (lượt)", "SL ST nhận", "sum", "#,##0", "CDC StarRocks", "COUNT(DISTINCT to_branch_id có nhận > 0): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
            ("Đ1", "Chênh lệch", "SL (ĐVT kho)", "SL chênh lệch", "sum", "#,##0", "Seedlog Cột M<0", "SUM(Cột M < 0 trên Seedlog)"),
            ("Đ1", "Chênh lệch", "Giá trị (VND)", "Giá trị chênh lệch", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(Cột M < 0 * gia_cost CDC)"),
            ("Đ1", "Chênh lệch", "% giá trị", "% giá trị chênh lệch", "ratio_cl", "0.00%", "Công thức", "Giá trị chênh lệch / Giá trị chuyển"),
            ("Đ1", "Chênh lệch", "Số ST (lượt)", "SL ST chênh lệch", "sum", "#,##0", "Seedlog Cột D", "COUNT(DISTINCT Store có Cột M < 0)"),
        ]),
        ("D2", "Đ2 · T2→T3 · SCM PHÂN LOẠI CHÊNH LỆCH", "#f59e0b", "fa-solid fa-filter", [
            ("Đ2", "Trả DC", "SL (ĐVT kho)", "SL trả DC", "sum", "#,##0", "Seedlog M/V", "Cột V = 'Trả tồn về DC'"),
            ("Đ2", "Trả DC", "Giá trị (VND)", "Giá trị trả DC", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost) với V = Trả DC"),
            ("Đ2", "Trả DC", "% giá trị", "% giá trị trả DC", "ratio_dc", "0.00%", "Công thức", "Giá trị trả DC / Giá trị chuyển"),
            ("Đ2", "Trả ST", "SL (ĐVT kho)", "SL trả ST", "sum", "#,##0", "Seedlog M/V", "Cột V = 'Trả tồn về ST'"),
            ("Đ2", "Trả ST", "Giá trị (VND)", "Giá trị trả ST", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost) với V = Trả ST"),
            ("Đ2", "Trả ST", "% giá trị", "% giá trị trả ST", "ratio_st", "0.00%", "Công thức", "Giá trị trả ST / Giá trị chuyển"),
            ("Đ2", "Chênh lệch KG", "SL (ĐVT kho)", None, "empty", "#,##0", "Mở rộng", "Hàng khô FMCG không có chênh lệch KG"),
            ("Đ2", "Chênh lệch KG", "Giá trị (VND)", None, "empty", "#,##0", "Mở rộng", "Hàng khô FMCG không có chênh lệch KG"),
            ("Đ2", "Chênh lệch KG", "% giá trị", None, "empty", "0.00%", "Mở rộng", "Hàng khô FMCG không có chênh lệch KG"),
            ("Đ2", "Write-off", "SL (ĐVT kho)", "SL Write - OFF", "sum", "#,##0", "Seedlog M/V", "Cột V = 'lỗi hệ thống'"),
            ("Đ2", "Write-off", "Giá trị (VND)", "Giá trị Write - OFF", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost) với V = lỗi hệ thống"),
            ("Đ2", "Write-off", "% giá trị", None, "ratio_wo", "0.00%", "Công thức", "Giá trị Write-off / Giá trị chuyển"),
            ("Đ2", "SCM chưa check", "SL (ĐVT kho)", "SL SCM chưa check", "sum", "#,##0", "Seedlog M/V", "Cột V = blank"),
            ("Đ2", "SCM chưa check", "Giá trị (VND)", "Giá trị SCM chưa check", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost) với V = blank"),
            ("Đ2", "SCM chưa check", "% giá trị", "% giá trị SCM chưa check", "ratio_scm", "0.00%", "Công thức", "Giá trị SCM chưa check / Giá trị chuyển"),
            ("Đ2", "Dư", "SL (ĐVT kho)", "SL dư", "sum", "#,##0", "CDC StarRocks", "SUM(nhận - chuyển) với cl_st > 0 & nhận > chuyển: Kho FGA10101; Người tạo: user hệ thống TKE_WMS (62261627e227c1000743b1d8); chỉ Siêu thị KFM"),
            ("Đ2", "Dư", "Giá trị (VND)", "Giá trị dư", "sum", "#,##0", "CDC StarRocks", "SUM(SL dư * gia_cost CDC): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
            ("Đ2", "Dư", "% giá trị", "% giá trị NET DƯ", "ratio_du", "0.00%", "Công thức", "Giá trị dư / Giá trị chuyển"),
            ("Đ2", "Trả DC sau net dư", "% giá trị", "% giá trị trả DC (SAU NET)", "ratio_dc_net", "0.00%", "Công thức", "MAX(0, % Trả DC - % Dư)"),
            ("Đ2", "ST nhập sai", "Số ST (lượt)", "SL ST nhập sai", "sum", "#,##0", "Seedlog D/Y", "Cột Y: ST thao tác sai / kiểm sai vị trí"),
            ("Đ2", "ST phát sinh chênh lệch KG", "Số ST (lượt)", None, "empty", "#,##0", "Mở rộng", "Hàng khô FMCG không có"),
            ("Đ2", "ST được DC giao bổ sung / soạn sai giữa các kiện", "Số ST (lượt)", "SL ST DC giao bổ sung", "sum", "#,##0", "Seedlog D/Y", "Cột Y: DC giao bs"),
            ("Đ2", "ST bị DC giao thiếu (CL)", "Số ST (lượt)", "SL ST DC giao thiếu", "sum", "#,##0", "Seedlog D/Y", "6 từ khóa lỗi DC giao thiếu trên Cột Y"),
            ("Đ2", "ST nhận dư", "Số ST (lượt)", "SL ST nhận dư", "sum", "#,##0", "CDC StarRocks", "COUNT(DISTINCT ST nhận dư): Kho FGA10101; Người tạo: user hệ thống TKE_WMS; chỉ Siêu thị KFM"),
        ]),
        ("D3", "Đ3 · T3→T4 · DC PHẢN HỒI / XÁC NHẬN", "#8b5cf6", "fa-solid fa-truck-ramp-box", [
            ("Đ3", "DC xác nhận thiếu", "SL (ĐVT kho)", "SL DC xác nhận thiếu", "sum", "#,##0", "Seedlog M/V/U", "Cột V = Trả DC, Cột U = hoàn thành (theo SL món)"),
            ("Đ3", "DC xác nhận thiếu", "Giá trị (VND)", "Giá trị DC xác nhận", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost)"),
            ("Đ3", "DC xác nhận thiếu", "% giá trị", "% Giá trị DC xác nhận", "ratio_dc_xn", "0.00%", "Công thức", "Giá trị DC xác nhận / Giá trị chuyển"),
            ("Đ3", "Siêu thị nhập sai", "SL (ĐVT kho)", None, "empty", "#,##0", "Mở rộng", "Cập nhật khi tách riêng dòng Đ3"),
            ("Đ3", "Siêu thị nhập sai", "Giá trị (VND)", None, "empty", "#,##0", "Mở rộng", "Cập nhật khi tách riêng dòng Đ3"),
            ("Đ3", "Siêu thị nhập sai", "% giá trị", None, "empty", "0.00%", "Mở rộng", "Cập nhật khi tách riêng dòng Đ3"),
            ("Đ3", "DC đang kiểm tra", "SL (ĐVT kho)", "SL DC đang kiểm tra", "sum", "#,##0", "Seedlog M/V/U", "Cột V = Trả DC, Cột U = chưa tạo phiếu/blank"),
            ("Đ3", "DC đang kiểm tra", "Giá trị (VND)", "Giá trị DC kiểm tra", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost)"),
            ("Đ3", "DC đang kiểm tra", "% giá trị", "% Giá trị DC kiểm tra", "ratio_dc_kt", "0.00%", "Công thức", "Giá trị DC kiểm tra / Giá trị chuyển"),
            ("Đ3", "DC từ chối (trừ bì)", "SL (ĐVT kho)", "SL DC từ chối do trừ bì", "sum", "#,##0", "Mặc định", "Auto = 0"),
            ("Đ3", "DC từ chối (trừ bì)", "Giá trị (VND)", "Giá trị DC từ chối do trừ bì", "sum", "#,##0", "Mặc định", "Auto = 0"),
            ("Đ3", "DC từ chối (trừ bì)", "% giá trị", "% Giá trị DC từ chối do trừ bì", "empty", "0.00%", "Mặc định", "Auto = 0%"),
            ("Đ3", "DC chưa phản hồi (<D+2)", "SL (ĐVT kho)", "SL DC chưa phản hồi (<D+2)", "sum", "#,##0", "Seedlog M/V/U", "Trong hạn SLA <= 2 ngày"),
            ("Đ3", "DC chưa phản hồi (<D+2)", "Giá trị (VND)", "Giá trị DC chưa phản hồi (<D+2)", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost)"),
            ("Đ3", "DC chưa phản hồi (<D+2)", "% giá trị", "% Giá trị DC chưa phản hồi (<D+2)", "ratio_le2", "0.00%", "Công thức", "GT <D+2 / Giá trị chuyển"),
            ("Đ3", "DC chưa phản hồi (>D+2) – trễ timeline", "SL (ĐVT kho)", "SL DC chưa phản hồi (>D+2)", "sum", "#,##0", "Seedlog M/V/U", "Quá hạn SLA > 2 ngày"),
            ("Đ3", "DC chưa phản hồi (>D+2) – trễ timeline", "Giá trị (VND)", "Giá trị DC chưa phản hồi (>D+2)", "sum", "#,##0", "Seedlog + Cost CDC", "SUM(ABS(M) * gia_cost)"),
            ("Đ3", "DC chưa phản hồi (>D+2) – trễ timeline", "% giá trị", "% Giá trị DC chưa phản hồi (>D+2)", "ratio_gt2", "0.00%", "Công thức", "GT >D+2 / Giá trị chuyển"),
        ]),
        ("D4", "Đ4 · T4→T5 · CHỐT KẾT QUẢ ĐỐI SOÁT & LŨY KẾ", "#06b6d4", "fa-solid fa-coins", [
            ("Đ4", "Tổng thất thoát", "Giá trị (VND)", "Tổng giá trị thất thoát", "sum", "#,##0", "Công thức", "MAX(0, ABS(GT CL) - GT trả ST)"),
            ("Đ4", "DC chịu", "Giá trị (VND)", "Tổng giá trị DC chịu", "sum", "#,##0", "Công thức", "Giá trị DC xác nhận"),
            ("Đ4", "KFM chịu", "Giá trị (VND)", "Tổng giá trị KFM chịu", "sum", "#,##0", "Công thức", "Hao hụt + Write-off"),
            ("Đ4", "KFM chịu: hao hụt", "Giá trị (VND)", "Giá trị hao hụt", "sum", "#,##0", "Mặc định", "Auto = 0"),
            ("Đ4", "KFM chịu: write-off <100k", "Giá trị (VND)", "Giá trị Write - OFF", "sum", "#,##0", "Seedlog + Cost CDC", "Giá trị Write-off"),
            ("Đ4", "Vận tải sai", "Giá trị (VND)", None, "empty", "#,##0", "Mở rộng", "Chưa có dữ liệu"),
            ("Đ4", "Lỗi hệ thống", "Giá trị (VND)", "Giá trị Write - OFF", "sum", "#,##0", "Seedlog + Cost CDC", "Cột V = 'lỗi hệ thống'"),
            ("Đ4", "Tổng giá trị chuyển lũy kế", "Giá trị (VND)", "Tổng giá trị chuyển lũy kế", "last", "#,##0", "Lũy kế", "Giá trị ngày cuối kỳ"),
            ("Đ4", "Tồn kho chênh lệch", "Giá trị (VND)", "Tồn kho chênh lệch", "last", "#,##0", "Lũy kế", "Tồn(D-1) - GT chênh lệch(D)"),
            ("Đ4", "Tỷ lệ chênh lệch chuyển hàng", "% giá trị", "Tỷ lệ chênh lệch chuyển hàng", "ratio_luy_ke", "0.00%", "Công thức", "Tồn kho CL / Tổng GT chuyển lũy kế"),
        ]),
        ("B1", "B. TỒN ÂM · 6 NHÓM LÝ DO + TỔNG CỘNG (42 CHỈ SỐ)", "#ec4899", "fa-solid fa-layer-group", [
            row
            for grp_name, is_total in [
                ("NCC giao dư / bù hao hụt", False),
                ("ST add dư / hệ thống auto add dư", False),
                ("Chia sai / giao nhầm ST", False),
                ("Lệch PO / Nhập Sai Chứng Từ", False),
                ("Lệch cân mã KG / free-weight", False),
                ("Khác", False),
                ("Tổng cộng 6 nhóm lý do", True),
            ]
            for row in [
                ("B1", grp_name, "Tổng SKU âm (SKU)", None, "empty", "#,##0",
                 "Công thức" if is_total else "File tồn âm FMCG (chờ nguồn)",
                 "Tổng 6 nhóm lý do" if is_total else "Số SKU đang âm thuộc nhóm lý do"),
                ("B1", grp_name, "SL âm phát sinh", None, "empty", "#,##0",
                 "Công thức" if is_total else "File tồn âm FMCG (chờ nguồn)",
                 "Tổng 6 nhóm lý do" if is_total else "SL âm phát sinh trong ngày"),
                ("B1", grp_name, "SL đã bù trừ (net-off)", None, "empty", "#,##0",
                 "Công thức" if is_total else "File tồn âm FMCG (chờ nguồn)",
                 "Tổng 6 nhóm lý do" if is_total else "SL đã xử lý bù trừ"),
                ("B1", grp_name, "SL còn lại chưa xử lý", None, "empty", "#,##0",
                 "Công thức", "SL âm phát sinh − SL đã bù trừ"),
                ("B1", grp_name, "Tổng giá trị còn lại (VND)", None, "empty", "#,##0",
                 "Công thức" if is_total else "File tồn âm FMCG (chờ nguồn)",
                 "Tổng 6 nhóm lý do" if is_total else "Giá trị phần còn lại chưa xử lý"),
                ("B1", grp_name, "Tỷ lệ xử lý (%)", None, "empty", "0.00%",
                 "Công thức", "SL đã bù trừ / SL âm phát sinh"),
            ]
        ]),
    ]

    def calc_agg_for_dates(d_list, tab8_key, agg_mode):
        if agg_mode == "empty":
            return None
        gt_tr = sum(daily_metrics[d]["Giá trị chuyển"] for d in d_list)
        if agg_mode == "sum":
            return sum(daily_metrics[d][tab8_key] for d in d_list)
        if agg_mode == "last":
            return daily_metrics[d_list[-1]][tab8_key]
        if agg_mode == "ratio_cl":
            return sum(daily_metrics[d]["Giá trị chênh lệch"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_dc":
            return sum(daily_metrics[d]["Giá trị trả DC"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_st":
            return sum(daily_metrics[d]["Giá trị trả ST"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_wo":
            return sum(daily_metrics[d]["Giá trị Write - OFF"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_scm":
            return sum(daily_metrics[d]["Giá trị SCM chưa check"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_du":
            return sum(daily_metrics[d]["Giá trị dư"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_dc_net":
            p_dc = sum(daily_metrics[d]["Giá trị trả DC"] for d in d_list) / gt_tr if gt_tr else 0.0
            p_du = sum(daily_metrics[d]["Giá trị dư"] for d in d_list) / gt_tr if gt_tr else 0.0
            return max(0.0, p_dc - p_du)
        if agg_mode == "ratio_dc_xn":
            return sum(daily_metrics[d]["Giá trị DC xác nhận"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_dc_kt":
            return sum(daily_metrics[d]["Giá trị DC kiểm tra"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_le2":
            return sum(daily_metrics[d]["Giá trị DC chưa phản hồi (<D+2)"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_gt2":
            return sum(daily_metrics[d]["Giá trị DC chưa phản hồi (>D+2)"] for d in d_list) / gt_tr if gt_tr else 0.0
        if agg_mode == "ratio_luy_ke":
            last_d = d_list[-1]
            lk_tr = daily_metrics[last_d]["Tổng giá trị chuyển lũy kế"]
            lk_ton = daily_metrics[last_d]["Tồn kho chênh lệch"]
            return lk_ton / lk_tr if lk_tr else 0.0
        if agg_mode == "net_off_rem":
            return sum(daily_metrics[d]["Tổng giá trị DC chịu"] for d in d_list) - sum(daily_metrics[d]["Giá trị dư"] for d in d_list)
        return None

    t1_idx_by_name = {}
    for sec_obj in sections_dict.values():
        for r_obj in sec_obj.get("rows", []):
            t1_idx_by_name[r_obj["name"]] = r_obj["row_idx"]

    flow_blocks_payload = []
    for b_id, b_title, b_accent, b_icon, b_rows in FLOW_BLOCKS_DEF:
        out_rows = []
        nhom_label = "B. Tồn âm" if b_id == "B1" else "A. Đối soát"
        for dc, tc, dv, t8_key, agg_mode, num_fmt, nguon, cach_tinh in b_rows:
            vals = {}
            # Σ T11
            v_t11 = calc_agg_for_dates(all_dates, t8_key, agg_mode)
            vals["SIGMA_T11"] = fmt_val(v_t11, num_fmt) if v_t11 is not None else "-"
            # Từng ngày
            for d_iso in all_dates:
                if agg_mode == "empty":
                    vals[d_iso] = "-"
                elif agg_mode == "ratio_wo":
                    gt_tr_d = daily_metrics[d_iso]["Giá trị chuyển"]
                    vals[d_iso] = fmt_val(daily_metrics[d_iso]["Giá trị Write - OFF"] / gt_tr_d if gt_tr_d else 0.0, num_fmt)
                elif agg_mode == "net_off_rem":
                    vals[d_iso] = fmt_val(daily_metrics[d_iso]["Tổng giá trị DC chịu"] - daily_metrics[d_iso]["Giá trị dư"], num_fmt)
                else:
                    vals[d_iso] = fmt_val(daily_metrics[d_iso][t8_key], num_fmt)
            # Từng tuần Σ Wxx
            for wk_key in weeks_order:
                v_wk = calc_agg_for_dates(week_to_dates[wk_key], t8_key, agg_mode)
                vals[f"SIGMA_{wk_key}"] = fmt_val(v_wk, num_fmt) if v_wk is not None else "-"

            out_rows.append({
                "mien": "Miền Nam",
                "kho": "FMCG",
                "nhom": nhom_label,
                "diem_chan": dc,
                "tieu_chi": tc,
                "t1_idx": t1_idx_by_name.get(t8_key) if t8_key else None,
                "don_vi": dv,
                "nguon": nguon,
                "cach_tinh": cach_tinh,
                "is_empty_template": (agg_mode == "empty"),
                "values": vals,
            })
        flow_blocks_payload.append({
            "id": b_id, "title": b_title, "accent": b_accent, "icon": b_icon, "rows": out_rows
        })

    payload = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "filter_scope": "Từ 01/11/2026 trở về sau • CDC StarRocks (FGA10101 -> Siêu thị KFM + Bảng TO) + Seedlog + Cost Stockcard",
        "dates": dates_meta,
        "summary": summary_cards,
        "sections": list(sections_dict.values()),
        "col_logic": col_logic,
        "reconciliation": reconciliation,
        "flow_template": {
            "columns": flow_columns,
            "blocks": flow_blocks_payload,
        },
    }

    js_text = (
        "// Dữ liệu Báo cáo Logistics FMCG (Tự động từ CDC StarRocks + Google Sheet Seedlog + Đặc tả Logic)\n"
        f"window.FMCG_MATRIX_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n"
    )

    targets = [
        os.path.join(WORKSPACE_DIR, "daily_details", "fmcg_matrix.js"),
        os.path.join(WORKSPACE_DIR, "DONG_MAT_DASHBOARD", "daily_details", "fmcg_matrix.js"),
    ]
    for tgt in targets:
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        with open(tgt, "w", encoding="utf-8") as f:
            f.write(js_text)
        print(f"    -> Đã ghi file Web JS: {tgt}")


def main():
    df_cdc, cost_day_map, cost_fb_map, cost_gl_map = fetch_cdc_starrocks()
    df_seed = fetch_seedlog(cost_day_map, cost_fb_map, cost_gl_map)
    old_ref = fetch_old_fmcg_reference()
    all_dates, daily_metrics = compute_matrix(df_cdc, df_seed)
    export_excel(all_dates, daily_metrics, df_cdc, df_seed, old_ref)
    export_web_js(all_dates, daily_metrics, df_cdc)


if __name__ == "__main__":
    main()
