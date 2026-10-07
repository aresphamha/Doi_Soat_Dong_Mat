import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'g:\My Drive\DOCS\transport_daily_report\script')
from data_pipeline.config import load_starrocks_config, load_clickhouse_config
import pymysql
import requests
import pandas as pd
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Branch Info from ClickHouse
cfg_ch = load_clickhouse_config()
url = f"{cfg_ch['base_url']}/?database={cfg_ch['database']}"
auth = (cfg_ch['user'], cfg_ch['password'])

r = requests.post(url, data="SELECT id, branch_code, branch_name FROM kf_branch_location".encode('utf-8'), auth=auth, timeout=30)
lines = r.text.strip().split('\n')
branch_dict = {}
for line in lines:
    parts = line.split('\t')
    if len(parts) >= 3:
        branch_dict[parts[0].strip()] = {'code': parts[1].strip(), 'name': parts[2].strip()}

# 2. TO Warehouse Mapping: to_branch (Nơi nhận chuyển hoàn / đối soát)
TO_DEST_MAP = {
    '6982f5f1d360600007807f7b': {'wh_name': 'KRCCLCH - KRC Lệch (Cũ)', 'category': 'Rau Củ', 'code': 'KRCCLCH', 'full_name': 'KHO RAU CỦ XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG (Cũ)'},
    '6aabb403055d2e0007eb9ded': {'wh_name': 'FEA20104 - Bình Thắng Chờ Đối Soát (Mới)', 'category': 'Rau Củ', 'code': 'FEA20104', 'full_name': 'FEA20104 _ Bình Thắng _ Chờ Đối Soát (Mới)'},
    
    '6a34ed8d6607ba000703e235': {'wh_name': 'MF02 - MeatFish Lệch (Cũ)', 'category': 'Thịt Cá (MeatFish)', 'code': 'MF02', 'full_name': 'MeatFish - Miền Đông - SCF - Lệch Chuyển Hàng (Cũ)'},
    '6aabb4e6e493030007272a95': {'wh_name': 'MFA30104 - Sóng Thần Chờ Đối Soát (Mới)', 'category': 'Thịt Cá (MeatFish)', 'code': 'MFA30104', 'full_name': 'MFA30104 _ Sóng Thần _ Chờ Đối Soát (Mới)'},

    '6a34ee406607ba000703e5b8': {'wh_name': 'CL03 - Chill Lệch (Cũ)', 'category': 'Chill (Đông Mát)', 'code': 'CL03', 'full_name': 'Chill - Miền Đông - SCF - Lệch Chuyển Hàng (Cũ)'},
    '6aa6a22bdf3d880007872063': {'wh_name': 'CLA40104 - Sóng Thần Chờ Đối Soát (Mới)', 'category': 'Chill (Đông Mát)', 'code': 'CLA40104', 'full_name': 'CLA40104 _ Sóng Thần _ Chờ Đối Soát (Mới)'},

    '6a34ecb96607ba000703dc79': {'wh_name': 'FZ03 - Frozen Lệch (Cũ)', 'category': 'Frozen (Đông Lạnh)', 'code': 'FZ03', 'full_name': 'Frozen - Miền Đông - SCF - Lệch Chuyển Hàng (Cũ)'},
    '6aa77e599d7b1b00070121f5': {'wh_name': 'FZA50104 - Sóng Thần Chờ Đối Soát (Mới)', 'category': 'Frozen (Đông Lạnh)', 'code': 'FZA50104', 'full_name': 'FZA50104 _ Sóng Thần _ Chờ Đối Soát (Mới)'},

    '65654b82df01db0007400173': {'wh_name': 'SLCL - Seedlog Lệch (Chính)', 'category': 'Seedlog (Dry)', 'code': 'HCM008008', 'full_name': 'KHO SEEDLOG XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG'},
    '62342407b35d1d0007379692': {'wh_name': 'SLKT - Seedlog Khai Trương', 'category': 'Seedlog (Dry)', 'code': 'HCM008002', 'full_name': 'KHO SEEDLOG KHAI TRƯƠNG'},
}

TO_ORDER = [
    'KRCCLCH - KRC Lệch (Cũ)',
    'FEA20104 - Bình Thắng Chờ Đối Soát (Mới)',
    'MF02 - MeatFish Lệch (Cũ)',
    'MFA30104 - Sóng Thần Chờ Đối Soát (Mới)',
    'CL03 - Chill Lệch (Cũ)',
    'CLA40104 - Sóng Thần Chờ Đối Soát (Mới)',
    'FZ03 - Frozen Lệch (Cũ)',
    'FZA50104 - Sóng Thần Chờ Đối Soát (Mới)',
    'SLCL - Seedlog Lệch (Chính)',
    'SLKT - Seedlog Khai Trương',
    'Khác / Cửa hàng'
]

# 3. Transfer Warehouse Mapping: from_branch_id (Nơi chuyển đi)
TR_ORIGIN_MAP = {
    '5fdc170ebd89c10006f15b7c': {'wh_name': 'KRC (Cũ)', 'category': 'Rau Củ', 'code': 'KRC', 'full_name': 'KHO RAU CỦ (Cũ)'},
    '6aabb3f3f426e20007f81559': {'wh_name': 'FEA20102 (Mới)', 'category': 'Rau Củ', 'code': 'FEA20102', 'full_name': 'FEA20102 _ Bình Thắng _ Quá Cảnh'},
    '6a3e383fe20b440007640326': {'wh_name': 'KRC Bánh Tươi (Cũ)', 'category': 'Rau Củ (Bánh tươi)', 'code': 'KRCBT', 'full_name': 'KHO QUÁ CẢNH BÁNH TƯƠI'},
    '6aabb45fd18e9d00073200a4': {'wh_name': 'FEA20197 Bánh Tươi (Mới)', 'category': 'Rau Củ (Bánh tươi)', 'code': 'FEA20197', 'full_name': 'FEA20197 _ Bình Thắng _ Bánh Tươi'},

    '6a34ed56f23028000774139f': {'wh_name': 'MF01 (Cũ)', 'category': 'Thịt Cá (MeatFish)', 'code': 'MF01', 'full_name': 'MeatFish - Miền Đông - Quá Cảnh'},
    '6aabb4d0e493030007272a3f': {'wh_name': 'MFA30102 (Mới)', 'category': 'Thịt Cá (MeatFish)', 'code': 'MFA30102', 'full_name': 'MFA30102 _ Sóng Thần _ Quá Cảnh'},

    '6a34ee2aebb48c000760d803': {'wh_name': 'CL02 (Cũ)', 'category': 'Chill (Đông Mát)', 'code': 'CL02', 'full_name': 'Chill - Miền Đông - Quá Cảnh'},
    '6aa6a1eedf3d880007871f3f': {'wh_name': 'CLA40102 (Mới)', 'category': 'Chill (Đông Mát)', 'code': 'CLA40102', 'full_name': 'CLA40102 _ Sóng Thần _ Quá Cảnh'},

    '6a34ec8d77173000073e64e2': {'wh_name': 'FZ02 (Cũ)', 'category': 'Frozen (Đông Lạnh)', 'code': 'FZ02', 'full_name': 'Frozen - Miền Đông - Quá Cảnh'},
    '6aa77de130fded00073d4521': {'wh_name': 'FZA50102 (Mới)', 'category': 'Frozen (Đông Lạnh)', 'code': 'FZA50102', 'full_name': 'FZA50102 _ Sóng Thần _ Quá Cảnh'},

    '6234219eb35d1d00073793ab': {'wh_name': 'KSL (Chính)', 'category': 'Seedlog (Dry)', 'code': 'KSL', 'full_name': 'KHO SEEDLOG (Chính)'},
    '62342407b35d1d0007379692': {'wh_name': 'SLKT (Khai Trương)', 'category': 'Seedlog (Dry)', 'code': 'SLKT', 'full_name': 'KHO SEEDLOG KHAI TRƯƠNG'},
}

TR_ORDER = [
    'KRC (Cũ)',
    'FEA20102 (Mới)',
    'KRC Bánh Tươi (Cũ)',
    'FEA20197 Bánh Tươi (Mới)',
    'MF01 (Cũ)',
    'MFA30102 (Mới)',
    'CL02 (Cũ)',
    'CLA40102 (Mới)',
    'FZ02 (Cũ)',
    'FZA50102 (Mới)',
    'KSL (Chính)',
    'SLKT (Khai Trương)',
    'Khác / Cửa hàng'
]

# 4. Connect to StarRocks & Fetch Data
cfg_sr = load_starrocks_config()
conn = pymysql.connect(
    host=cfg_sr['host'],
    port=cfg_sr['port'],
    user=cfg_sr['user'],
    password=cfg_sr['password'],
    database=cfg_sr['database'],
    charset='utf8mb4'
)

# Fetch TO
q_to = """
SELECT 
    code,
    status,
    from_pt_code,
    handled_pt_code,
    pt_from_branch,
    from_branch,
    to_branch,
    DATE_FORMAT(DATE_ADD(created_at, INTERVAL 7 HOUR), '%Y-%m-%d') as report_date,
    created_at,
    pt_transfer_date
FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets
WHERE created_at >= '2026-08-31 17:00:00' AND created_at < '2026-09-25 17:00:00'
"""
print("Fetching TO data...")
df_to = pd.read_sql(q_to, conn)

# Fetch Transfer
q_tr = """
SELECT 
    code,
    status,
    from_branch_id,
    to_branch_id,
    DATE_FORMAT(DATE_ADD(created_at, INTERVAL 7 HOUR), '%Y-%m-%d') as report_date,
    created_at,
    received_date
FROM __cdc_kfm_kf_inventories_kf_transfer_items
WHERE created_at >= '2026-08-31 17:00:00' AND created_at < '2026-09-25 17:00:00'
"""
print("Fetching Transfer data...")
df_tr = pd.read_sql(q_tr, conn)
conn.close()

# 5. Enrich TO (using to_branch) and Transfer (using from_branch_id)
TO_STATUS_MAP = {1.0: 'Mới', 3.0: 'Đang xử lý', 5.0: 'Hoàn thành', 7.0: 'Hủy'}
df_to['status_name'] = df_to['status'].map(TO_STATUS_MAP).fillna('Khác')
df_to['wh_account'] = df_to['to_branch'].apply(lambda x: TO_DEST_MAP.get(x, {}).get('wh_name', 'Khác / Cửa hàng'))
df_to['wh_category'] = df_to['to_branch'].apply(lambda x: TO_DEST_MAP.get(x, {}).get('category', 'Khác / Cửa hàng'))
df_to['wh_code'] = df_to['to_branch'].apply(lambda x: TO_DEST_MAP.get(x, {}).get('code', branch_dict.get(x, {}).get('code', 'N/A')))
df_to['wh_full_name'] = df_to['to_branch'].apply(lambda x: TO_DEST_MAP.get(x, {}).get('full_name', branch_dict.get(x, {}).get('name', 'N/A')))

TR_STATUS_MAP = {1.0: 'Phiếu tạm', 3.0: 'Đang chuyển', 5.0: 'Đã nhận', 7.0: 'Hủy'}
df_tr['status_name'] = df_tr['status'].map(TR_STATUS_MAP).fillna('Khác')
df_tr['wh_account'] = df_tr['from_branch_id'].apply(lambda x: TR_ORIGIN_MAP.get(x, {}).get('wh_name', 'Khác / Cửa hàng'))
df_tr['wh_category'] = df_tr['from_branch_id'].apply(lambda x: TR_ORIGIN_MAP.get(x, {}).get('category', 'Khác / Cửa hàng'))
df_tr['wh_code'] = df_tr['from_branch_id'].apply(lambda x: TR_ORIGIN_MAP.get(x, {}).get('code', branch_dict.get(x, {}).get('code', 'N/A')))
df_tr['wh_full_name'] = df_tr['from_branch_id'].apply(lambda x: TR_ORIGIN_MAP.get(x, {}).get('full_name', branch_dict.get(x, {}).get('name', 'N/A')))

all_dates = sorted(list(set(df_to['report_date'].unique()).union(set(df_tr['report_date'].unique()))))

# 6. Generate Excel Report
excel_file = os.path.join(OUTPUT_DIR, "bao_cao_thong_ke_transfer_to_thang_9_2026.xlsx")
writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')
workbook = writer.book

header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#1E3A8A', 'font_color': '#FFFFFF', 'border': 1, 'font_size': 11})
sub_header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#3B82F6', 'font_color': '#FFFFFF', 'border': 1, 'font_size': 10})
total_fmt = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter', 'fg_color': '#E0E7FF', 'font_color': '#1E1B4B', 'border': 1, 'num_format': '#,##0', 'font_size': 10})
num_fmt = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0', 'font_size': 10})
text_fmt = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1E3A8A'})
subtitle_fmt = workbook.add_format({'italic': True, 'font_size': 10, 'font_color': '#64748B'})

# --- SHEET 1: TỔNG HỢP THÁNG 9 ---
ws1 = workbook.add_worksheet('Tong_Hop_Thang_9')
ws1.write('A1', 'BÁO CÁO THỐNG KÊ TRANSFER (NƠI CHUYỂN) & TO (KHO NHẬN TO_BRANCH) THÁNG 09/2026', title_fmt)
ws1.write('A2', 'Dữ liệu từ 01/09/2026 đến 25/09/2026 | TO theo to_branch (nhận chuyển hoàn) & Transfer theo from_branch (nơi chuyển đi)', subtitle_fmt)

# Table 1: TO Summary (to_branch)
ws1.write('A4', '1. TỔNG HỢP YÊU CẦU CHUYỂN (TO) THEO KHO NHẬN CHUYỂN HOÀN (TO_BRANCH)', workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#0F172A'}))
to_cols = ['Kho Nhận Chuyển Hoàn (to_branch)', 'Ngành Hàng', 'Mới (Status 1)', 'Đang xử lý (Status 3)', 'Hoàn thành (Status 5)', 'Hủy (Status 7)', 'Tổng Cộng TO', 'Tồn đọng (Mới + ĐXL)']
for col_idx, col_name in enumerate(to_cols):
    ws1.write(4, col_idx, col_name, header_fmt)

r_idx = 5
to_acc_piv = df_to.pivot_table(index='wh_account', columns='status_name', values='code', aggfunc='count', fill_value=0)
for s in ['Mới', 'Đang xử lý', 'Hoàn thành', 'Hủy']:
    if s not in to_acc_piv.columns:
        to_acc_piv[s] = 0

for acc in TO_ORDER:
    if acc in to_acc_piv.index:
        m = to_acc_piv.loc[acc, 'Mới']
        dxl = to_acc_piv.loc[acc, 'Đang xử lý']
        ht = to_acc_piv.loc[acc, 'Hoàn thành']
        h = to_acc_piv.loc[acc, 'Hủy']
        tot = m + dxl + ht + h
        pending = m + dxl
        cat = TO_DEST_MAP.get(next((k for k, v in TO_DEST_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        ws1.write(r_idx, 0, acc, text_fmt)
        ws1.write(r_idx, 1, cat, text_fmt)
        ws1.write(r_idx, 2, m, num_fmt)
        ws1.write(r_idx, 3, dxl, num_fmt)
        ws1.write(r_idx, 4, ht, num_fmt)
        ws1.write(r_idx, 5, h, num_fmt)
        ws1.write(r_idx, 6, tot, num_fmt)
        ws1.write(r_idx, 7, pending, num_fmt)
        r_idx += 1

ws1.write(r_idx, 0, 'TỔNG CỘNG TO', total_fmt)
ws1.write(r_idx, 1, 'Toàn bộ kho', total_fmt)
ws1.write(r_idx, 2, to_acc_piv['Mới'].sum(), total_fmt)
ws1.write(r_idx, 3, to_acc_piv['Đang xử lý'].sum(), total_fmt)
ws1.write(r_idx, 4, to_acc_piv['Hoàn thành'].sum(), total_fmt)
ws1.write(r_idx, 5, to_acc_piv['Hủy'].sum(), total_fmt)
ws1.write(r_idx, 6, to_acc_piv.values.sum(), total_fmt)
ws1.write(r_idx, 7, to_acc_piv['Mới'].sum() + to_acc_piv['Đang xử lý'].sum(), total_fmt)

# Table 2: Transfer Summary (from_branch)
r_idx += 3
ws1.write(r_idx, 0, '2. TỔNG HỢP PHIẾU CHUYỂN (TRANSFER) THEO NƠI CHUYỂN ĐI (FROM_BRANCH)', workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#0F172A'}))
r_idx += 1
tr_cols = ['Nơi Chuyển Đi (from_branch)', 'Ngành Hàng', 'Phiếu tạm (Status 1)', 'Đang chuyển (Status 3)', 'Đã nhận (Status 5)', 'Hủy (Status 7)', 'Tổng Cộng Transfer', 'Tồn đọng (Tạm + Đang chuyển)']
for col_idx, col_name in enumerate(tr_cols):
    ws1.write(r_idx, col_idx, col_name, header_fmt)

r_idx += 1
tr_acc_piv = df_tr.pivot_table(index='wh_account', columns='status_name', values='code', aggfunc='count', fill_value=0)
for s in ['Phiếu tạm', 'Đang chuyển', 'Đã nhận', 'Hủy']:
    if s not in tr_acc_piv.columns:
        tr_acc_piv[s] = 0

for acc in TR_ORDER:
    if acc in tr_acc_piv.index:
        pt = tr_acc_piv.loc[acc, 'Phiếu tạm']
        dc = tr_acc_piv.loc[acc, 'Đang chuyển']
        dn = tr_acc_piv.loc[acc, 'Đã nhận']
        h = tr_acc_piv.loc[acc, 'Hủy']
        tot = pt + dc + dn + h
        pending = pt + dc
        cat = TR_ORIGIN_MAP.get(next((k for k, v in TR_ORIGIN_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        ws1.write(r_idx, 0, acc, text_fmt)
        ws1.write(r_idx, 1, cat, text_fmt)
        ws1.write(r_idx, 2, pt, num_fmt)
        ws1.write(r_idx, 3, dc, num_fmt)
        ws1.write(r_idx, 4, dn, num_fmt)
        ws1.write(r_idx, 5, h, num_fmt)
        ws1.write(r_idx, 6, tot, num_fmt)
        ws1.write(r_idx, 7, pending, num_fmt)
        r_idx += 1

ws1.write(r_idx, 0, 'TỔNG CỘNG TRANSFER', total_fmt)
ws1.write(r_idx, 1, 'Toàn bộ kho & CH', total_fmt)
ws1.write(r_idx, 2, tr_acc_piv['Phiếu tạm'].sum(), total_fmt)
ws1.write(r_idx, 3, tr_acc_piv['Đang chuyển'].sum(), total_fmt)
ws1.write(r_idx, 4, tr_acc_piv['Đã nhận'].sum(), total_fmt)
ws1.write(r_idx, 5, tr_acc_piv['Hủy'].sum(), total_fmt)
ws1.write(r_idx, 6, tr_acc_piv.values.sum(), total_fmt)
ws1.write(r_idx, 7, tr_acc_piv['Phiếu tạm'].sum() + tr_acc_piv['Đang chuyển'].sum(), total_fmt)

ws1.set_column('A:A', 38)
ws1.set_column('B:B', 22)
ws1.set_column('C:H', 20)

# --- SHEET 2: TO MỚI & ĐANG XỬ LÝ (THEO TO_BRANCH & THEO NGÀY) ---
ws2 = workbook.add_worksheet('TO_Moi_DangXuLy')
ws2.write('A1', 'THỐNG KÊ TO MỚI & ĐANG XỬ LÝ (THEO KHO NHẬN TO_BRANCH & THEO NGÀY)', title_fmt)
ws2.write('A2', 'Thống kê lượng TO cần xử lý (Status 1: Mới + Status 3: Đang xử lý) phát sinh từ 01/09/2026 đến 25/09/2026', subtitle_fmt)

df_to_pending = df_to[df_to['status'].isin([1.0, 3.0])]
to_pending_acc_piv = df_to_pending.pivot_table(index='wh_account', columns='report_date', values='code', aggfunc='count', fill_value=0)

ws2.write(3, 0, 'Kho Nhận Chuyển Hoàn (to_branch)', header_fmt)
ws2.write(3, 1, 'Tổng Lũy Kế T9', header_fmt)
for d_idx, d_str in enumerate(all_dates):
    ws2.write(3, d_idx + 2, d_str[5:], sub_header_fmt)

r_idx = 4
for acc in TO_ORDER:
    if acc in to_pending_acc_piv.index or acc in to_acc_piv.index:
        ws2.write(r_idx, 0, acc, text_fmt)
        row_vals = [to_pending_acc_piv.loc[acc, d] if (acc in to_pending_acc_piv.index and d in to_pending_acc_piv.columns) else 0 for d in all_dates]
        tot = sum(row_vals)
        ws2.write(r_idx, 1, tot, total_fmt)
        for d_idx, val in enumerate(row_vals):
            ws2.write(r_idx, d_idx + 2, val, num_fmt)
        r_idx += 1

ws2.write(r_idx, 0, 'TỔNG CỘNG', total_fmt)
tot_all = len(df_to_pending)
ws2.write(r_idx, 1, tot_all, total_fmt)
for d_idx, d_str in enumerate(all_dates):
    col_sum = df_to_pending[df_to_pending['report_date'] == d_str].shape[0]
    ws2.write(r_idx, d_idx + 2, col_sum, total_fmt)

r_idx += 3
ws2.write(r_idx, 0, 'CHI TIẾT: PHÂN TÁCH TO "MỚI" VS "ĐANG XỬ LÝ" THEO NGÀY', workbook.add_format({'bold': True, 'font_size': 11}))
r_idx += 1
ws2.write(r_idx, 0, 'Trạng thái', header_fmt)
ws2.write(r_idx, 1, 'Tổng Tháng 9', header_fmt)
for d_idx, d_str in enumerate(all_dates):
    ws2.write(r_idx, d_idx + 2, d_str[5:], sub_header_fmt)

r_idx += 1
for st_name, st_val in [('Mới (Status 1)', 1.0), ('Đang xử lý (Status 3)', 3.0)]:
    sub_df = df_to[df_to['status'] == st_val]
    ws2.write(r_idx, 0, st_name, text_fmt)
    ws2.write(r_idx, 1, len(sub_df), total_fmt)
    for d_idx, d_str in enumerate(all_dates):
        ws2.write(r_idx, d_idx + 2, sub_df[sub_df['report_date'] == d_str].shape[0], num_fmt)
    r_idx += 1

ws2.set_column('A:A', 38)
ws2.set_column('B:B', 18)
ws2.set_column('C:AB', 8)

# --- SHEET 3: TRANSFER TẠM & ĐANG CHUYỂN (THEO FROM_BRANCH & THEO NGÀY) ---
ws3 = workbook.add_worksheet('Transfer_Tam_DangChuyen')
ws3.write('A1', 'THỐNG KÊ TRANSFER PHIẾU TẠM & ĐANG CHUYỂN (THEO NƠI CHUYỂN FROM_BRANCH & THEO NGÀY)', title_fmt)
ws3.write('A2', 'Thống kê lượng Transfer cần xử lý (Status 1: Phiếu tạm + Status 3: Đang chuyển) phát sinh từ 01/09/2026 đến 25/09/2026', subtitle_fmt)

df_tr_pending = df_tr[df_tr['status'].isin([1.0, 3.0])]
tr_pending_acc_piv = df_tr_pending.pivot_table(index='wh_account', columns='report_date', values='code', aggfunc='count', fill_value=0)

ws3.write(3, 0, 'Nơi Chuyển Đi (from_branch)', header_fmt)
ws3.write(3, 1, 'Tổng Lũy Kế T9', header_fmt)
for d_idx, d_str in enumerate(all_dates):
    ws3.write(3, d_idx + 2, d_str[5:], sub_header_fmt)

r_idx = 4
for acc in TR_ORDER:
    if acc in tr_pending_acc_piv.index or acc in tr_acc_piv.index:
        ws3.write(r_idx, 0, acc, text_fmt)
        row_vals = [tr_pending_acc_piv.loc[acc, d] if (acc in tr_pending_acc_piv.index and d in tr_pending_acc_piv.columns) else 0 for d in all_dates]
        tot = sum(row_vals)
        ws3.write(r_idx, 1, tot, total_fmt)
        for d_idx, val in enumerate(row_vals):
            ws3.write(r_idx, d_idx + 2, val, num_fmt)
        r_idx += 1

ws3.write(r_idx, 0, 'TỔNG CỘNG', total_fmt)
tot_all_tr = len(df_tr_pending)
ws3.write(r_idx, 1, tot_all_tr, total_fmt)
for d_idx, d_str in enumerate(all_dates):
    col_sum = df_tr_pending[df_tr_pending['report_date'] == d_str].shape[0]
    ws3.write(r_idx, d_idx + 2, col_sum, total_fmt)

r_idx += 3
ws3.write(r_idx, 0, 'CHI TIẾT: PHÂN TÁCH TRANSFER "PHIẾU TẠM" VS "ĐANG CHUYỂN" THEO NGÀY', workbook.add_format({'bold': True, 'font_size': 11}))
r_idx += 1
ws3.write(r_idx, 0, 'Trạng thái', header_fmt)
ws3.write(r_idx, 1, 'Tổng Tháng 9', header_fmt)
for d_idx, d_str in enumerate(all_dates):
    ws3.write(r_idx, d_idx + 2, d_str[5:], sub_header_fmt)

r_idx += 1
for st_name, st_val in [('Phiếu tạm (Status 1)', 1.0), ('Đang chuyển (Status 3)', 3.0)]:
    sub_df = df_tr[df_tr['status'] == st_val]
    ws3.write(r_idx, 0, st_name, text_fmt)
    ws3.write(r_idx, 1, len(sub_df), total_fmt)
    for d_idx, d_str in enumerate(all_dates):
        ws3.write(r_idx, d_idx + 2, sub_df[sub_df['report_date'] == d_str].shape[0], num_fmt)
    r_idx += 1

ws3.set_column('A:A', 38)
ws3.set_column('B:B', 18)
ws3.set_column('C:AB', 8)

# --- SHEET 4: CHI TIẾT NGÀY - TO ---
ws4 = workbook.add_worksheet('Chi_Tiet_Ngay_TO')
ws4.write('A1', 'CHI TIẾT SỐ LƯỢNG YÊU CẦU CHUYỂN (TO) TỪNG NGÀY THEO TO_BRANCH & TRẠNG THÁI', title_fmt)
to_daily_cols = ['Ngày', 'Kho Nhận Chuyển Hoàn (to_branch)', 'Mã Kho', 'Mới', 'Đang xử lý', 'Hoàn thành', 'Hủy', 'Tổng Ngày', 'Tồn đọng (Mới+ĐXL)']
for c_idx, c_name in enumerate(to_daily_cols):
    ws4.write(2, c_idx, c_name, header_fmt)

to_day_acc = df_to.pivot_table(index=['report_date', 'wh_account', 'wh_code'], columns='status_name', values='code', aggfunc='count', fill_value=0).reset_index()
for s in ['Mới', 'Đang xử lý', 'Hoàn thành', 'Hủy']:
    if s not in to_day_acc.columns:
        to_day_acc[s] = 0

r_idx = 3
for _, row in to_day_acc.iterrows():
    m = row['Mới']
    dxl = row['Đang xử lý']
    ht = row['Hoàn thành']
    h = row['Hủy']
    tot = m + dxl + ht + h
    pending = m + dxl
    ws4.write(r_idx, 0, row['report_date'], text_fmt)
    ws4.write(r_idx, 1, row['wh_account'], text_fmt)
    ws4.write(r_idx, 2, row['wh_code'], text_fmt)
    ws4.write(r_idx, 3, m, num_fmt)
    ws4.write(r_idx, 4, dxl, num_fmt)
    ws4.write(r_idx, 5, ht, num_fmt)
    ws4.write(r_idx, 6, h, num_fmt)
    ws4.write(r_idx, 7, tot, total_fmt)
    ws4.write(r_idx, 8, pending, total_fmt)
    r_idx += 1

ws4.set_column('A:A', 14)
ws4.set_column('B:B', 38)
ws4.set_column('C:C', 12)
ws4.set_column('D:I', 14)

# --- SHEET 5: CHI TIẾT NGÀY - TRANSFER ---
ws5 = workbook.add_worksheet('Chi_Tiet_Ngay_Transfer')
ws5.write('A1', 'CHI TIẾT SỐ LƯỢNG PHIẾU TRANSFER TỪNG NGÀY THEO NƠI CHUYỂN FROM_BRANCH & TRẠNG THÁI', title_fmt)
tr_daily_cols = ['Ngày', 'Nơi Chuyển Đi (from_branch)', 'Mã Kho', 'Phiếu tạm', 'Đang chuyển', 'Đã nhận', 'Hủy', 'Tổng Ngày', 'Tồn đọng (Tạm+Đang chuyển)']
for c_idx, c_name in enumerate(tr_daily_cols):
    ws5.write(2, c_idx, c_name, header_fmt)

tr_day_acc = df_tr.pivot_table(index=['report_date', 'wh_account', 'wh_code'], columns='status_name', values='code', aggfunc='count', fill_value=0).reset_index()
for s in ['Phiếu tạm', 'Đang chuyển', 'Đã nhận', 'Hủy']:
    if s not in tr_day_acc.columns:
        tr_day_acc[s] = 0

r_idx = 3
for _, row in tr_day_acc.iterrows():
    pt = row['Phiếu tạm']
    dc = row['Đang chuyển']
    dn = row['Đã nhận']
    h = row['Hủy']
    tot = pt + dc + dn + h
    pending = pt + dc
    ws5.write(r_idx, 0, row['report_date'], text_fmt)
    ws5.write(r_idx, 1, row['wh_account'], text_fmt)
    ws5.write(r_idx, 2, row['wh_code'], text_fmt)
    ws5.write(r_idx, 3, pt, num_fmt)
    ws5.write(r_idx, 4, dc, num_fmt)
    ws5.write(r_idx, 5, dn, num_fmt)
    ws5.write(r_idx, 6, h, num_fmt)
    ws5.write(r_idx, 7, tot, total_fmt)
    ws5.write(r_idx, 8, pending, total_fmt)
    r_idx += 1

ws5.set_column('A:A', 14)
ws5.set_column('B:B', 38)
ws5.set_column('C:C', 12)
ws5.set_column('D:I', 14)

# --- SHEET 6: ĐỐI SOÁT KHO CŨ VS KHO MỚI ---
ws6 = workbook.add_worksheet('Doi_Soat_Kho_Cu_Moi')
ws6.write('A1', 'ĐỐI SOÁT CHI TIẾT SỐ LIỆU TỪNG TÀI KHOẢN KHO CŨ VÀ KHO MỚI', title_fmt)
ws6.write('A2', 'TO theo to_branch (nhận chuyển hoàn) và Transfer theo from_branch (nơi xuất đi)', subtitle_fmt)

ds_cols = ['Ngành Hàng', 'Tài Khoản Kho', 'Mã Kho', 'Tên Đầy Đủ', 'Loại Nghiệp Vụ', 'Mới / Phiếu Tạm', 'Đang Xử Lý / Đang Chuyển', 'Hoàn Thành / Đã Nhận', 'Hủy', 'Tổng Phiếu']
for c_idx, c_name in enumerate(ds_cols):
    ws6.write(3, c_idx, c_name, header_fmt)

r_idx = 4
to_acc_full = df_to.groupby(['wh_category', 'wh_account', 'wh_code', 'wh_full_name', 'status_name']).size().unstack(fill_value=0).reset_index()
for s in ['Mới', 'Đang xử lý', 'Hoàn thành', 'Hủy']:
    if s not in to_acc_full.columns:
        to_acc_full[s] = 0

for _, row in to_acc_full.iterrows():
    m = row['Mới']
    dxl = row['Đang xử lý']
    ht = row['Hoàn thành']
    h = row['Hủy']
    tot = m + dxl + ht + h
    ws6.write(r_idx, 0, row['wh_category'], text_fmt)
    ws6.write(r_idx, 1, row['wh_account'], text_fmt)
    ws6.write(r_idx, 2, row['wh_code'], text_fmt)
    ws6.write(r_idx, 3, row['wh_full_name'], text_fmt)
    ws6.write(r_idx, 4, 'TO (Kho nhận to_branch)', text_fmt)
    ws6.write(r_idx, 5, m, num_fmt)
    ws6.write(r_idx, 6, dxl, num_fmt)
    ws6.write(r_idx, 7, ht, num_fmt)
    ws6.write(r_idx, 8, h, num_fmt)
    ws6.write(r_idx, 9, tot, total_fmt)
    r_idx += 1

tr_acc_full = df_tr.groupby(['wh_category', 'wh_account', 'wh_code', 'wh_full_name', 'status_name']).size().unstack(fill_value=0).reset_index()
for s in ['Phiếu tạm', 'Đang chuyển', 'Đã nhận', 'Hủy']:
    if s not in tr_acc_full.columns:
        tr_acc_full[s] = 0

for _, row in tr_acc_full.iterrows():
    pt = row['Phiếu tạm']
    dc = row['Đang chuyển']
    dn = row['Đã nhận']
    h = row['Hủy']
    tot = pt + dc + dn + h
    ws6.write(r_idx, 0, row['wh_category'], text_fmt)
    ws6.write(r_idx, 1, row['wh_account'], text_fmt)
    ws6.write(r_idx, 2, row['wh_code'], text_fmt)
    ws6.write(r_idx, 3, row['wh_full_name'], text_fmt)
    ws6.write(r_idx, 4, 'Transfer (Nơi chuyển from_branch)', text_fmt)
    ws6.write(r_idx, 5, pt, num_fmt)
    ws6.write(r_idx, 6, dc, num_fmt)
    ws6.write(r_idx, 7, dn, num_fmt)
    ws6.write(r_idx, 8, h, num_fmt)
    ws6.write(r_idx, 9, tot, total_fmt)
    r_idx += 1

ws6.set_column('A:B', 28)
ws6.set_column('C:C', 12)
ws6.set_column('D:D', 45)
ws6.set_column('E:E', 28)
ws6.set_column('F:J', 14)

writer.close()
print(f"Excel report written to {excel_file}")

# 7. Generate Standalone HTML Report
html_file = os.path.join(OUTPUT_DIR, "bao_cao_thong_ke_transfer_to_thang_9_2026.html")

to_by_date = df_to.pivot_table(index='report_date', columns='status_name', values='code', aggfunc='count', fill_value=0)
for s in ['Mới', 'Đang xử lý', 'Hoàn thành', 'Hủy']:
    if s not in to_by_date.columns:
        to_by_date[s] = 0

tr_by_date = df_tr.pivot_table(index='report_date', columns='status_name', values='code', aggfunc='count', fill_value=0)
for s in ['Phiếu tạm', 'Đang chuyển', 'Đã nhận', 'Hủy']:
    if s not in tr_by_date.columns:
        tr_by_date[s] = 0

chart_data = {
    'dates': all_dates,
    'to_moi': [int(to_by_date.loc[d, 'Mới']) if d in to_by_date.index else 0 for d in all_dates],
    'to_dxl': [int(to_by_date.loc[d, 'Đang xử lý']) if d in to_by_date.index else 0 for d in all_dates],
    'to_ht': [int(to_by_date.loc[d, 'Hoàn thành']) if d in to_by_date.index else 0 for d in all_dates],
    'to_huy': [int(to_by_date.loc[d, 'Hủy']) if d in to_by_date.index else 0 for d in all_dates],
    'tr_tam': [int(tr_by_date.loc[d, 'Phiếu tạm']) if d in tr_by_date.index else 0 for d in all_dates],
    'tr_dc': [int(tr_by_date.loc[d, 'Đang chuyển']) if d in tr_by_date.index else 0 for d in all_dates],
    'tr_dn': [int(tr_by_date.loc[d, 'Đã nhận']) if d in tr_by_date.index else 0 for d in all_dates],
    'tr_huy': [int(tr_by_date.loc[d, 'Hủy']) if d in tr_by_date.index else 0 for d in all_dates],
}

kpi = {
    'to_total': int(len(df_to)),
    'to_moi': int(df_to[df_to['status'] == 1.0].shape[0]),
    'to_dxl': int(df_to[df_to['status'] == 3.0].shape[0]),
    'to_ht': int(df_to[df_to['status'] == 5.0].shape[0]),
    'to_huy': int(df_to[df_to['status'] == 7.0].shape[0]),
    'to_pending': int(df_to[df_to['status'].isin([1.0, 3.0])].shape[0]),

    'tr_total': int(len(df_tr)),
    'tr_tam': int(df_tr[df_tr['status'] == 1.0].shape[0]),
    'tr_dc': int(df_tr[df_tr['status'] == 3.0].shape[0]),
    'tr_dn': int(df_tr[df_tr['status'] == 5.0].shape[0]),
    'tr_huy': int(df_tr[df_tr['status'] == 7.0].shape[0]),
    'tr_pending': int(df_tr[df_tr['status'].isin([1.0, 3.0])].shape[0]),
}

to_summary_rows = []
for acc in TO_ORDER:
    if acc in to_acc_piv.index:
        m = int(to_acc_piv.loc[acc, 'Mới'])
        dxl = int(to_acc_piv.loc[acc, 'Đang xử lý'])
        ht = int(to_acc_piv.loc[acc, 'Hoàn thành'])
        h = int(to_acc_piv.loc[acc, 'Hủy'])
        cat = TO_DEST_MAP.get(next((k for k, v in TO_DEST_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        to_summary_rows.append({
            'account': acc, 'category': cat, 'moi': m, 'dxl': dxl, 'ht': ht, 'huy': h,
            'total': m + dxl + ht + h, 'pending': m + dxl
        })

tr_summary_rows = []
for acc in TR_ORDER:
    if acc in tr_acc_piv.index:
        pt = int(tr_acc_piv.loc[acc, 'Phiếu tạm'])
        dc = int(tr_acc_piv.loc[acc, 'Đang chuyển'])
        dn = int(tr_acc_piv.loc[acc, 'Đã nhận'])
        h = int(tr_acc_piv.loc[acc, 'Hủy'])
        cat = TR_ORIGIN_MAP.get(next((k for k, v in TR_ORIGIN_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        tr_summary_rows.append({
            'account': acc, 'category': cat, 'tam': pt, 'dc': dc, 'dn': dn, 'huy': h,
            'total': pt + dc + dn + h, 'pending': pt + dc
        })

to_pending_matrix = []
for acc in TO_ORDER:
    if acc in to_pending_acc_piv.index or acc in to_acc_piv.index:
        row_vals = [int(to_pending_acc_piv.loc[acc, d]) if (acc in to_pending_acc_piv.index and d in to_pending_acc_piv.columns) else 0 for d in all_dates]
        cat = TO_DEST_MAP.get(next((k for k, v in TO_DEST_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        to_pending_matrix.append({
            'account': acc,
            'category': cat,
            'total': sum(row_vals),
            'dates': row_vals
        })

tr_pending_matrix = []
for acc in TR_ORDER:
    if acc in tr_pending_acc_piv.index or acc in tr_acc_piv.index:
        row_vals = [int(tr_pending_acc_piv.loc[acc, d]) if (acc in tr_pending_acc_piv.index and d in tr_pending_acc_piv.columns) else 0 for d in all_dates]
        cat = TR_ORIGIN_MAP.get(next((k for k, v in TR_ORIGIN_MAP.items() if v['wh_name'] == acc), ''), {}).get('category', 'Khác')
        tr_pending_matrix.append({
            'account': acc,
            'category': cat,
            'total': sum(row_vals),
            'dates': row_vals
        })

to_daily_list = []
for _, row in to_day_acc.iterrows():
    m = int(row['Mới'])
    dxl = int(row['Đang xử lý'])
    ht = int(row['Hoàn thành'])
    h = int(row['Hủy'])
    to_daily_list.append({
        'date': row['report_date'],
        'account': row['wh_account'],
        'code': row['wh_code'],
        'moi': m, 'dxl': dxl, 'ht': ht, 'huy': h,
        'total': m + dxl + ht + h, 'pending': m + dxl
    })

tr_daily_list = []
for _, row in tr_day_acc.iterrows():
    pt = int(row['Phiếu tạm'])
    dc = int(row['Đang chuyển'])
    dn = int(row['Đã nhận'])
    h = int(row['Hủy'])
    tr_daily_list.append({
        'date': row['report_date'],
        'account': row['wh_account'],
        'code': row['wh_code'],
        'tam': pt, 'dc': dc, 'dn': dn, 'huy': h,
        'total': pt + dc + dn + h, 'pending': pt + dc
    })

acc_comparison_list = []
for _, row in to_acc_full.iterrows():
    m = int(row['Mới'])
    dxl = int(row['Đang xử lý'])
    ht = int(row['Hoàn thành'])
    h = int(row['Hủy'])
    acc_comparison_list.append({
        'category': row['wh_category'],
        'account': row['wh_account'],
        'code': row['wh_code'],
        'full_name': row['wh_full_name'],
        'type': 'TO (Kho nhận to_branch)',
        'col1': m, 'col2': dxl, 'col3': ht, 'col4': h,
        'total': m + dxl + ht + h
    })
for _, row in tr_acc_full.iterrows():
    pt = int(row['Phiếu tạm'])
    dc = int(row['Đang chuyển'])
    dn = int(row['Đã nhận'])
    h = int(row['Hủy'])
    acc_comparison_list.append({
        'category': row['wh_category'],
        'account': row['wh_account'],
        'code': row['wh_code'],
        'full_name': row['wh_full_name'],
        'type': 'Transfer (Nơi chuyển from_branch)',
        'col1': pt, 'col2': dc, 'col3': dn, 'col4': h,
        'total': pt + dc + dn + h
    })

html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thống Kê Transfer (Nơi chuyển) & TO (Kho nhận to_branch) Tháng 09/2026</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0B1120; color: #F1F5F9; }}
    .glass-panel {{ background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
    .custom-scrollbar::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
    .tab-btn.active {{ background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%); color: #FFFFFF; box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.39); }}
    .tag-old {{ background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .tag-new {{ background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }}
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- HEADER -->
    <header class="glass-panel p-6 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xl">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-semibold rounded-full uppercase tracking-wider">
            SCM Realtime Analytics
          </span>
          <span class="text-xs text-slate-400">01/09/2026 ➜ 25/09/2026</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold mt-2 text-white">
          Thống Kê Phiếu Chuyển Transfer & Yêu Cầu (TO) Tháng 09/2026
        </h1>
        <p class="text-sm text-slate-400 mt-1">
          <span class="text-blue-400 font-semibold">TO:</span> Theo Kho Nhận Chuyển Hoàn (<span class="text-amber-300 font-medium">to_branch</span>) | 
          <span class="text-emerald-400 font-semibold">Transfer:</span> Theo Nơi Chuyển Đi (<span class="text-emerald-300 font-medium">from_branch</span>)
        </p>
      </div>
      <div class="flex items-center gap-3">
        <a href="bao_cao_thong_ke_transfer_to_thang_9_2026.xlsx" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-xl flex items-center gap-2 transition shadow-lg shadow-emerald-900/30">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          Tải File Excel (.xlsx)
        </a>
      </div>
    </header>

    <!-- KPI CARDS -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      <div class="glass-panel p-4 rounded-xl border-l-4 border-blue-500">
        <span class="text-xs text-slate-400 font-medium">Tổng Yêu Cầu (TO)</span>
        <div class="text-2xl font-bold text-white mt-1">{kpi['to_total']:,}</div>
        <span class="text-[11px] text-blue-400">01/09 - 25/09</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-amber-500">
        <span class="text-xs text-slate-400 font-medium">TO Mới (Status 1)</span>
        <div class="text-2xl font-bold text-amber-400 mt-1">{kpi['to_moi']:,}</div>
        <span class="text-[11px] text-slate-400">Chờ tiếp nhận</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-purple-500">
        <span class="text-xs text-slate-400 font-medium">TO Đang Xử Lý</span>
        <div class="text-2xl font-bold text-purple-400 mt-1">{kpi['to_dxl']:,}</div>
        <span class="text-[11px] text-slate-400">Status 3</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-emerald-500">
        <span class="text-xs text-slate-400 font-medium">TO Hoàn Thành</span>
        <div class="text-2xl font-bold text-emerald-400 mt-1">{kpi['to_ht']:,}</div>
        <span class="text-[11px] text-slate-400">Status 5</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-rose-500">
        <span class="text-xs text-slate-400 font-medium">TO Hủy</span>
        <div class="text-2xl font-bold text-rose-400 mt-1">{kpi['to_huy']:,}</div>
        <span class="text-[11px] text-slate-400">Status 7</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-cyan-500">
        <span class="text-xs text-slate-400 font-medium">Tồn Đọng TO</span>
        <div class="text-2xl font-bold text-cyan-400 mt-1">{kpi['to_pending']:,}</div>
        <span class="text-[11px] text-cyan-300">Mới + Đang xử lý</span>
      </div>
    </div>

    <!-- TRANSFER KPI CARDS -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      <div class="glass-panel p-4 rounded-xl border-l-4 border-indigo-500">
        <span class="text-xs text-slate-400 font-medium">Tổng Phiếu Transfer</span>
        <div class="text-2xl font-bold text-white mt-1">{kpi['tr_total']:,}</div>
        <span class="text-[11px] text-indigo-400">Toàn hệ thống</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-yellow-500">
        <span class="text-xs text-slate-400 font-medium">Transfer Phiếu Tạm</span>
        <div class="text-2xl font-bold text-yellow-400 mt-1">{kpi['tr_tam']:,}</div>
        <span class="text-[11px] text-slate-400">Status 1</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-sky-500">
        <span class="text-xs text-slate-400 font-medium">Transfer Đang Chuyển</span>
        <div class="text-2xl font-bold text-sky-400 mt-1">{kpi['tr_dc']:,}</div>
        <span class="text-[11px] text-slate-400">Status 3</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-emerald-500">
        <span class="text-xs text-slate-400 font-medium">Transfer Đã Nhận</span>
        <div class="text-2xl font-bold text-emerald-400 mt-1">{kpi['tr_dn']:,}</div>
        <span class="text-[11px] text-slate-400">Status 5</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-rose-500">
        <span class="text-xs text-slate-400 font-medium">Transfer Hủy</span>
        <div class="text-2xl font-bold text-rose-400 mt-1">{kpi['tr_huy']:,}</div>
        <span class="text-[11px] text-slate-400">Status 7</span>
      </div>
      <div class="glass-panel p-4 rounded-xl border-l-4 border-orange-500">
        <span class="text-xs text-slate-400 font-medium">Tồn Đọng Transfer</span>
        <div class="text-2xl font-bold text-orange-400 mt-1">{kpi['tr_pending']:,}</div>
        <span class="text-[11px] text-orange-300">Tạm + Đang chuyển</span>
      </div>
    </div>

    <!-- CHARTS SECTION -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="glass-panel p-5 rounded-2xl">
        <h3 class="text-base font-bold text-white mb-4 flex items-center justify-between">
          <span>Xu Hướng Phát Sinh Yêu Cầu (TO) Theo Ngày</span>
          <span class="text-xs text-slate-400">01/09 - 25/09</span>
        </h3>
        <div class="h-64">
          <canvas id="toChart"></canvas>
        </div>
      </div>
      <div class="glass-panel p-5 rounded-2xl">
        <h3 class="text-base font-bold text-white mb-4 flex items-center justify-between">
          <span>Xu Hướng Phiếu Chuyển (Transfer) Theo Ngày</span>
          <span class="text-xs text-slate-400">01/09 - 25/09</span>
        </h3>
        <div class="h-64">
          <canvas id="trChart"></canvas>
        </div>
      </div>
    </div>

    <!-- NAVIGATION TABS -->
    <div class="flex flex-wrap gap-2 border-b border-slate-800 pb-2">
      <button onclick="switchTab('tab1')" id="btn-tab1" class="tab-btn active px-4 py-2 rounded-xl text-sm font-semibold transition">
        1. Tổng Hợp Tháng 9
      </button>
      <button onclick="switchTab('tab2')" id="btn-tab2" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition">
        2. TO Mới & Đang Xử Lý ({kpi['to_pending']:,})
      </button>
      <button onclick="switchTab('tab3')" id="btn-tab3" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition">
        3. Transfer Tạm & Đang Chuyển ({kpi['tr_pending']:,})
      </button>
      <button onclick="switchTab('tab4')" id="btn-tab4" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition">
        4. Chi Tiết Ngày - TO
      </button>
      <button onclick="switchTab('tab5')" id="btn-tab5" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition">
        5. Chi Tiết Ngày - Transfer
      </button>
      <button onclick="switchTab('tab6')" id="btn-tab6" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition">
        6. Đối Soát Kho Cũ vs Mới
      </button>
    </div>

    <!-- TAB 1: TỔNG HỢP THÁNG 9 -->
    <div id="tab1" class="space-y-6">
      <div class="glass-panel p-6 rounded-2xl">
        <h2 class="text-lg font-bold text-white mb-4">1. Thống Kê Tổng Hợp TO Theo Kho Nhận Chuyển Hoàn (to_branch)</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="border-b border-slate-700 text-slate-400 bg-slate-800/40">
                <th class="p-3">Kho Nhận Chuyển Hoàn (to_branch)</th>
                <th class="p-3">Ngành Hàng</th>
                <th class="p-3 text-right text-amber-400">Mới (Status 1)</th>
                <th class="p-3 text-right text-purple-400">Đang Xử Lý (Status 3)</th>
                <th class="p-3 text-right text-emerald-400">Hoàn Thành (Status 5)</th>
                <th class="p-3 text-right text-rose-400">Hủy (Status 7)</th>
                <th class="p-3 text-right font-bold text-white">Tổng Cộng TO</th>
                <th class="p-3 text-right text-cyan-400 font-bold bg-cyan-950/30">Tồn Đọng (Mới + ĐXL)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30 transition">
                <td class="p-3 font-medium text-slate-200 flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold {'tag-old' if 'Cũ' in r['account'] else ('tag-new' if 'Mới' in r['account'] else 'bg-slate-700 text-slate-300')}">{r['account']}</span>
                </td>
                <td class="p-3 text-slate-400 text-xs">{r['category']}</td>
                <td class="p-3 text-right font-semibold text-amber-400">{r['moi']:,}</td>
                <td class="p-3 text-right font-semibold text-purple-400">{r['dxl']:,}</td>
                <td class="p-3 text-right font-semibold text-emerald-400">{r['ht']:,}</td>
                <td class="p-3 text-right font-semibold text-rose-400">{r['huy']:,}</td>
                <td class="p-3 text-right font-bold text-white">{r['total']:,}</td>
                <td class="p-3 text-right font-bold text-cyan-400 bg-cyan-950/20">{r['pending']:,}</td>
              </tr>
              ''' for r in to_summary_rows])}
              <tr class="bg-blue-900/30 font-bold text-white">
                <td class="p-3" colspan="2">TỔNG CỘNG TO HỆ THỐNG</td>
                <td class="p-3 text-right text-amber-400">{kpi['to_moi']:,}</td>
                <td class="p-3 text-right text-purple-400">{kpi['to_dxl']:,}</td>
                <td class="p-3 text-right text-emerald-400">{kpi['to_ht']:,}</td>
                <td class="p-3 text-right text-rose-400">{kpi['to_huy']:,}</td>
                <td class="p-3 text-right text-white">{kpi['to_total']:,}</td>
                <td class="p-3 text-right text-cyan-400 bg-cyan-900/40">{kpi['to_pending']:,}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="glass-panel p-6 rounded-2xl">
        <h2 class="text-lg font-bold text-white mb-4">2. Thống Kê Tổng Hợp Transfer Theo Nơi Chuyển Đi (from_branch)</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="border-b border-slate-700 text-slate-400 bg-slate-800/40">
                <th class="p-3">Nơi Chuyển Đi (from_branch)</th>
                <th class="p-3">Ngành Hàng</th>
                <th class="p-3 text-right text-yellow-400">Phiếu Tạm (Status 1)</th>
                <th class="p-3 text-right text-sky-400">Đang Chuyển (Status 3)</th>
                <th class="p-3 text-right text-emerald-400">Đã Nhận (Status 5)</th>
                <th class="p-3 text-right text-rose-400">Hủy (Status 7)</th>
                <th class="p-3 text-right font-bold text-white">Tổng Cộng Transfer</th>
                <th class="p-3 text-right text-orange-400 font-bold bg-orange-950/30">Tồn Đọng (Tạm + ĐC)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30 transition">
                <td class="p-3 font-medium text-slate-200 flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold {'tag-old' if 'Cũ' in r['account'] else ('tag-new' if 'Mới' in r['account'] else 'bg-slate-700 text-slate-300')}">{r['account']}</span>
                </td>
                <td class="p-3 text-slate-400 text-xs">{r['category']}</td>
                <td class="p-3 text-right font-semibold text-yellow-400">{r['tam']:,}</td>
                <td class="p-3 text-right font-semibold text-sky-400">{r['dc']:,}</td>
                <td class="p-3 text-right font-semibold text-emerald-400">{r['dn']:,}</td>
                <td class="p-3 text-right font-semibold text-rose-400">{r['huy']:,}</td>
                <td class="p-3 text-right font-bold text-white">{r['total']:,}</td>
                <td class="p-3 text-right font-bold text-orange-400 bg-orange-950/20">{r['pending']:,}</td>
              </tr>
              ''' for r in tr_summary_rows])}
              <tr class="bg-indigo-900/30 font-bold text-white">
                <td class="p-3" colspan="2">TỔNG CỘNG TRANSFER HỆ THỐNG</td>
                <td class="p-3 text-right text-yellow-400">{kpi['tr_tam']:,}</td>
                <td class="p-3 text-right text-sky-400">{kpi['tr_dc']:,}</td>
                <td class="p-3 text-right text-emerald-400">{kpi['tr_dn']:,}</td>
                <td class="p-3 text-right text-rose-400">{kpi['tr_huy']:,}</td>
                <td class="p-3 text-right text-white">{kpi['tr_total']:,}</td>
                <td class="p-3 text-right text-orange-400 bg-orange-900/40">{kpi['tr_pending']:,}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: TO MỚI & ĐANG XỬ LÝ -->
    <div id="tab2" class="space-y-6 hidden">
      <div class="glass-panel p-6 rounded-2xl">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-4">
          <div>
            <h2 class="text-lg font-bold text-white">Bảng Thống Kê TO Mới & Đang Xử Lý Theo Kho Nhận (to_branch)</h2>
            <p class="text-xs text-slate-400">Chi tiết lượng TO chưa hoàn thành (Mới + Đang xử lý) phát sinh theo từng ngày từ 01/09 đến 25/09</p>
          </div>
          <span class="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-bold">
            Tổng Tồn: {kpi['to_pending']:,} TO
          </span>
        </div>
        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left text-xs whitespace-nowrap">
            <thead>
              <tr class="border-b border-slate-700 bg-slate-800/60 text-slate-300">
                <th class="p-3 sticky left-0 bg-slate-900 z-10">Kho Nhận Chuyển Hoàn (to_branch)</th>
                <th class="p-3 text-right font-bold text-cyan-400 bg-cyan-950/40 sticky left-44 z-10">Tổng Tháng 9</th>
                {''.join([f'<th class="p-2 text-right text-slate-400">{d[5:]}</th>' for d in all_dates])}
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30 transition">
                <td class="p-3 font-medium text-slate-200 sticky left-0 bg-slate-900/90 z-10">{r['account']}</td>
                <td class="p-3 text-right font-bold text-cyan-400 bg-cyan-950/20 sticky left-44 z-10">{r['total']:,}</td>
                {''.join([f"<td class='p-2 text-right {'text-amber-400 font-semibold' if val > 0 else 'text-slate-600'}'>{val}</td>" for val in r['dates']])}
              </tr>
              ''' for r in to_pending_matrix])}
              <tr class="bg-blue-900/40 font-bold text-white">
                <td class="p-3 sticky left-0 bg-blue-950 z-10">TỔNG CỘNG</td>
                <td class="p-3 text-right text-cyan-300 bg-cyan-900/60 sticky left-44 z-10">{kpi['to_pending']:,}</td>
                {''.join([f"<td class='p-2 text-right text-cyan-300'>{sum([to_pending_matrix[idx]['dates'][d_idx] for idx in range(len(to_pending_matrix))])}</td>" for d_idx in range(len(all_dates))])}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: TRANSFER TẠM & ĐANG CHUYỂN -->
    <div id="tab3" class="space-y-6 hidden">
      <div class="glass-panel p-6 rounded-2xl">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-4">
          <div>
            <h2 class="text-lg font-bold text-white">Bảng Thống Kê Transfer Phiếu Tạm & Đang Chuyển Theo Nơi Chuyển (from_branch)</h2>
            <p class="text-xs text-slate-400">Chi tiết lượng Transfer chưa hoàn tất (Phiếu tạm + Đang chuyển) theo từng ngày từ 01/09 đến 25/09</p>
          </div>
          <span class="px-3 py-1 bg-orange-500/20 text-orange-300 border border-orange-500/30 rounded-lg text-xs font-bold">
            Tổng Tồn: {kpi['tr_pending']:,} Phiếu
          </span>
        </div>
        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left text-xs whitespace-nowrap">
            <thead>
              <tr class="border-b border-slate-700 bg-slate-800/60 text-slate-300">
                <th class="p-3 sticky left-0 bg-slate-900 z-10">Nơi Chuyển Đi (from_branch)</th>
                <th class="p-3 text-right font-bold text-orange-400 bg-orange-950/40 sticky left-44 z-10">Tổng Tháng 9</th>
                {''.join([f'<th class="p-2 text-right text-slate-400">{d[5:]}</th>' for d in all_dates])}
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30 transition">
                <td class="p-3 font-medium text-slate-200 sticky left-0 bg-slate-900/90 z-10">{r['account']}</td>
                <td class="p-3 text-right font-bold text-orange-400 bg-orange-950/20 sticky left-44 z-10">{r['total']:,}</td>
                {''.join([f"<td class='p-2 text-right {'text-yellow-400 font-semibold' if val > 0 else 'text-slate-600'}'>{val}</td>" for val in r['dates']])}
              </tr>
              ''' for r in tr_pending_matrix])}
              <tr class="bg-indigo-900/40 font-bold text-white">
                <td class="p-3 sticky left-0 bg-indigo-950 z-10">TỔNG CỘNG</td>
                <td class="p-3 text-right text-orange-300 bg-orange-900/60 sticky left-44 z-10">{kpi['tr_pending']:,}</td>
                {''.join([f"<td class='p-2 text-right text-orange-300'>{sum([tr_pending_matrix[idx]['dates'][d_idx] for idx in range(len(tr_pending_matrix))])}</td>" for d_idx in range(len(all_dates))])}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 4: CHI TIẾT NGÀY - TO -->
    <div id="tab4" class="space-y-6 hidden">
      <div class="glass-panel p-6 rounded-2xl">
        <h2 class="text-lg font-bold text-white mb-4">Chi Tiết Số Lượng TO Từng Ngày Theo Kho Nhận (to_branch)</h2>
        <div class="overflow-x-auto max-h-[600px] custom-scrollbar">
          <table class="w-full text-left text-xs">
            <thead class="sticky top-0 bg-slate-900 z-10">
              <tr class="border-b border-slate-700 text-slate-400">
                <th class="p-2.5">Ngày</th>
                <th class="p-2.5">Kho Nhận Chuyển Hoàn (to_branch)</th>
                <th class="p-2.5">Mã Kho</th>
                <th class="p-2.5 text-right text-amber-400">Mới</th>
                <th class="p-2.5 text-right text-purple-400">Đang Xử Lý</th>
                <th class="p-2.5 text-right text-emerald-400">Hoàn Thành</th>
                <th class="p-2.5 text-right text-rose-400">Hủy</th>
                <th class="p-2.5 text-right font-bold text-white">Tổng Ngày</th>
                <th class="p-2.5 text-right font-bold text-cyan-400">Tồn Đọng</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30">
                <td class="p-2 text-slate-300">{r['date']}</td>
                <td class="p-2 font-medium text-slate-200">{r['account']}</td>
                <td class="p-2 font-mono text-slate-400">{r['code']}</td>
                <td class="p-2 text-right text-amber-400 font-semibold">{r['moi']}</td>
                <td class="p-2 text-right text-purple-400 font-semibold">{r['dxl']}</td>
                <td class="p-2 text-right text-emerald-400">{r['ht']}</td>
                <td class="p-2 text-right text-rose-400">{r['huy']}</td>
                <td class="p-2 text-right font-bold text-white">{r['total']}</td>
                <td class="p-2 text-right font-bold text-cyan-400">{r['pending']}</td>
              </tr>
              ''' for r in to_daily_list])}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: CHI TIẾT NGÀY - TRANSFER -->
    <div id="tab5" class="space-y-6 hidden">
      <div class="glass-panel p-6 rounded-2xl">
        <h2 class="text-lg font-bold text-white mb-4">Chi Tiết Số Lượng Transfer Từng Ngày Theo Nơi Chuyển (from_branch)</h2>
        <div class="overflow-x-auto max-h-[600px] custom-scrollbar">
          <table class="w-full text-left text-xs">
            <thead class="sticky top-0 bg-slate-900 z-10">
              <tr class="border-b border-slate-700 text-slate-400">
                <th class="p-2.5">Ngày</th>
                <th class="p-2.5">Nơi Chuyển Đi (from_branch)</th>
                <th class="p-2.5">Mã Kho</th>
                <th class="p-2.5 text-right text-yellow-400">Phiếu Tạm</th>
                <th class="p-2.5 text-right text-sky-400">Đang Chuyển</th>
                <th class="p-2.5 text-right text-emerald-400">Đã Nhận</th>
                <th class="p-2.5 text-right text-rose-400">Hủy</th>
                <th class="p-2.5 text-right font-bold text-white">Tổng Ngày</th>
                <th class="p-2.5 text-right font-bold text-orange-400">Tồn Đọng</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30">
                <td class="p-2 text-slate-300">{r['date']}</td>
                <td class="p-2 font-medium text-slate-200">{r['account']}</td>
                <td class="p-2 font-mono text-slate-400">{r['code']}</td>
                <td class="p-2 text-right text-yellow-400 font-semibold">{r['tam']}</td>
                <td class="p-2 text-right text-sky-400 font-semibold">{r['dc']}</td>
                <td class="p-2 text-right text-emerald-400">{r['dn']}</td>
                <td class="p-2 text-right text-rose-400">{r['huy']}</td>
                <td class="p-2 text-right font-bold text-white">{r['total']}</td>
                <td class="p-2 text-right font-bold text-orange-400">{r['pending']}</td>
              </tr>
              ''' for r in tr_daily_list])}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 6: ĐỐI SOÁT KHO CŨ VS MỚI -->
    <div id="tab6" class="space-y-6 hidden">
      <div class="glass-panel p-6 rounded-2xl">
        <h2 class="text-lg font-bold text-white mb-2">Đối Soát Chi Tiết Từng Tài Khoản Kho Cũ & Kho Mới</h2>
        <p class="text-xs text-slate-400 mb-4">TO theo to_branch (nhận chuyển hoàn) & Transfer theo from_branch (nơi xuất đi)</p>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="border-b border-slate-700 bg-slate-800/60 text-slate-300">
                <th class="p-2.5">Ngành Hàng</th>
                <th class="p-2.5">Tài Khoản Kho</th>
                <th class="p-2.5">Mã Kho</th>
                <th class="p-2.5">Tên Đầy Đủ</th>
                <th class="p-2.5">Loại Nghiệp Vụ</th>
                <th class="p-2.5 text-right">Mới / Tạm</th>
                <th class="p-2.5 text-right">Đang Xử Lý / Đang Chuyển</th>
                <th class="p-2.5 text-right">Hoàn Thành / Đã Nhận</th>
                <th class="p-2.5 text-right">Hủy</th>
                <th class="p-2.5 text-right font-bold text-white">Tổng Phiếu</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              {''.join([f'''
              <tr class="hover:bg-slate-800/30">
                <td class="p-2 font-semibold text-slate-200">{r['category']}</td>
                <td class="p-2 text-blue-400 font-medium">{r['account']}</td>
                <td class="p-2 font-mono text-slate-300">{r['code']}</td>
                <td class="p-2 text-slate-400">{r['full_name']}</td>
                <td class="p-2 font-medium {'text-purple-400' if 'TO' in r['type'] else 'text-emerald-400'}">{r['type']}</td>
                <td class="p-2 text-right text-amber-400 font-semibold">{r['col1']:,}</td>
                <td class="p-2 text-right text-sky-400 font-semibold">{r['col2']:,}</td>
                <td class="p-2 text-right text-emerald-400">{r['col3']:,}</td>
                <td class="p-2 text-right text-rose-400">{r['col4']:,}</td>
                <td class="p-2 text-right font-bold text-white">{r['total']:,}</td>
              </tr>
              ''' for r in acc_comparison_list])}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- FOOTER -->
    <footer class="text-center text-xs text-slate-500 py-4">
      Hệ thống Logistics SCM Kingfoodmart • Dữ liệu kết xuất từ StarRocks & ClickHouse Realtime • Tháng 09/2026
    </footer>

  </div>

  <script>
    function switchTab(tabId) {{
      document.querySelectorAll('[id^="tab"]').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(el => {{
        el.classList.remove('active', 'text-white');
        el.classList.add('text-slate-300');
      }});
      
      document.getElementById(tabId).classList.remove('hidden');
      const btn = document.getElementById('btn-' + tabId);
      btn.classList.add('active', 'text-white');
      btn.classList.remove('text-slate-300');
    }}

    const chartData = {json.dumps(chart_data)};

    const ctxTO = document.getElementById('toChart').getContext('2d');
    new Chart(ctxTO, {{
      type: 'line',
      data: {{
        labels: chartData.dates.map(d => d.substring(5)),
        datasets: [
          {{ label: 'Mới', data: chartData.to_moi, borderColor: '#F59E0B', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.3 }},
          {{ label: 'Đang xử lý', data: chartData.to_dxl, borderColor: '#A855F7', backgroundColor: 'transparent', tension: 0.3 }},
          {{ label: 'Hoàn thành', data: chartData.to_ht, borderColor: '#10B981', backgroundColor: 'transparent', tension: 0.3 }},
          {{ label: 'Hủy', data: chartData.to_huy, borderColor: '#EF4444', backgroundColor: 'transparent', tension: 0.3 }}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#94A3B8', font: {{ size: 10 }} }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#64748B', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{ ticks: {{ color: '#64748B', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
        }}
      }}
    }});

    const ctxTR = document.getElementById('trChart').getContext('2d');
    new Chart(ctxTR, {{
      type: 'line',
      data: {{
        labels: chartData.dates.map(d => d.substring(5)),
        datasets: [
          {{ label: 'Phiếu tạm', data: chartData.tr_tam, borderColor: '#EAB308', backgroundColor: 'rgba(234, 179, 8, 0.1)', fill: true, tension: 0.3 }},
          {{ label: 'Đang chuyển', data: chartData.tr_dc, borderColor: '#38BDF8', backgroundColor: 'transparent', tension: 0.3 }},
          {{ label: 'Đã nhận', data: chartData.tr_dn, borderColor: '#10B981', backgroundColor: 'transparent', tension: 0.3 }}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#94A3B8', font: {{ size: 10 }} }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#64748B', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{ ticks: {{ color: '#64748B', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML dashboard updated to {html_file}")
