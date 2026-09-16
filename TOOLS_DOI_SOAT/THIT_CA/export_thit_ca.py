
def find_data_file(filename, default_dir=None):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ', filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(cur_dir, filename)

import pandas as pd
import pymysql
import os
import io
import warnings
warnings.filterwarnings('ignore')

def fetch_data_to_df(sql_query):
    conn = pymysql.connect(
        host='103.147.122.103', port=9030,
        user='kfm_scm_tho_nguyen', password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm'
    )
    df = pd.read_sql(sql_query, conn)
    conn.close()
    return df

date_str = '2026-08-13'
shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235'"

# Branches
sql_branches = """
SELECT branch_id, branch_name
FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
WHERE branch_name IS NOT NULL AND branch_name != ''
GROUP BY branch_id, branch_name
"""
df_branches = fetch_data_to_df(sql_branches)
id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))

# Shortage
sql_mf01 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    IFNULL(c.code, i.double_check_code) as `Mã thùng`,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    l.unit__name as `ĐVT`,
    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
LEFT JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines c 
    ON c._parent_id = l._root_id 
    AND c._index = CAST(SPLIT_PART(l._parent_id, char(31), 2) AS INT)
WHERE {shortage_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf01 = fetch_data_to_df(sql_mf01)
df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()

# Surplus
sql_mf02 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.double_check_code as `Mã thùng`,
    i.note as `Ghi chú chuyển (phiếu)`,
    i.created_by,
    l.description,
    l.reason,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    l.unit__name as `ĐVT`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`,
    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `SL_chuyen_du`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE {surplus_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf02 = fetch_data_to_df(sql_mf02)
df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
df_surplus = df_mf02[df_mf02['SL_du'] > 0].copy()

# Layout
file_layout = r"C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ\LayoutImportThitCa.xlsx"
layout_df = pd.read_excel(file_layout, sheet_name=0)
if 'Chi nhánh nhận' in layout_df.columns and 'STT' in layout_df.columns:
    layout_df.rename(columns={'STT': 'Vị trí', 'Chi nhánh nhận': 'Siêu thị'}, inplace=True)
elif 'Siêu thị' not in layout_df.columns:
    layout_df = pd.read_excel(file_layout, sheet_name=0, header=None)
    if len(layout_df.columns) >= 3:
        layout_df.rename(columns={0: 'Vị trí', 1: 'Mã', 2: 'Siêu thị'}, inplace=True)

store_to_pos = {}
if 'Siêu thị' in layout_df.columns and 'Vị trí' in layout_df.columns:
    for _, row in layout_df.iterrows():
        try:
            store_to_pos[str(row['Siêu thị']).strip().upper()] = int(row['Vị trí'])
        except:
            pass

df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()

diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
    'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
    'Chênh lệch': 'sum',
    'ĐVT': 'first',
    'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
    'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
}).reset_index()
diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu', 'Mã chuyển hàng': 'Mã chuyển hàng thiếu'}, inplace=True)

du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
    'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
    'SL_du': 'sum',
    'ĐVT': 'first',
    'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
    'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
}).reset_index()
du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)

merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('')
merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
merged_internal['Lệch_tuyệt_đối'] = abs(merged_internal['Chênh lệch'] - merged_internal['SL_du'])

loi_text = "Thao tác sai"
df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
df_exact['Lỗi'] = loi_text
df_exact = df_exact[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
df_exact.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Lỗi']

df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
df_partial['Dif'] = df_partial['Chênh lệch'] - df_partial['SL_du']
df_partial['Lỗi'] = loi_text
df_partial = df_partial[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Dif', 'Lỗi']]
df_partial.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Chênh lệch thừa - thiếu', 'Lỗi']

merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']

rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()

cross_matches = []
skus_sho = rem_shortages['Mã hàng'].unique()
skus_sur = rem_surpluses['Mã hàng'].unique()
common_skus = set(skus_sho).intersection(skus_sur)

matched_sho_keys = set()
matched_sur_keys = set()
for sku in common_skus:
    sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
    sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
    
    for idx_sur, row_sur in sku_sur.iterrows():
        sur_qty = row_sur['Remaining_Surplus']
        if abs(sur_qty) < 0.01: continue
        sur_store = row_sur['Chi nhánh nhận']
        pos_sur = store_to_pos.get(str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store, None)
        
        matches = []
        for idx_sho, row_sho in sku_sho.iterrows():
            sho_qty = row_sho['Remaining_Shortage']
            if abs(sur_qty - sho_qty) <= 0.01:
                matches.append(row_sho)
                
        if len(matches) > 0:
            best_match = None
            best_dist = 9999
            for sho_row in matches:
                sho_store = sho_row['Chi nhánh nhận']
                pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                if pos_sur is not None and pos_sho is not None:
                    dist = abs(pos_sur - pos_sho)
                    if dist < best_dist:
                        best_dist = dist
                        best_match = sho_row
                else:
                    if best_match is None: best_match = sho_row
            
            if best_match is not None:
                cross_matches.append({
                    'Chi nhánh nhận (Thiếu)': best_match['Chi nhánh nhận'],
                    'Chi nhánh nhận (Thừa)': sur_store,
                    'Mã chuyển hàng thiếu': best_match['Mã chuyển hàng thiếu'],
                    'Mã chuyển hàng thừa': row_sur['Mã chuyển hàng thừa'],
                    'Mã hàng': sku,
                    'Tên hàng': row_sur['Tên hàng'],
                    'ĐVT': row_sur['ĐVT'],
                    'Mã thùng thiếu': best_match['Mã thùng thiếu'],
                    'Mã thùng thừa': row_sur['Mã thùng thừa'],
                    'SL Thiếu': best_match['Remaining_Shortage'],
                    'SL Thừa': sur_qty,
                    'Lỗi (Xác suất)': "Rất cao" if best_dist <= 5 else ("Trung bình" if best_dist <= 15 else "Thấp")
                })
                matched_sho_keys.add(best_match.name)
                matched_sur_keys.add(idx_sur)
                sku_sho.loc[best_match.name, 'Remaining_Shortage'] = 0
                
rem_shortages = rem_shortages[~rem_shortages.index.isin(matched_sho_keys)]
rem_surpluses = rem_surpluses[~rem_surpluses.index.isin(matched_sur_keys)]
df_cross = pd.DataFrame(cross_matches)

sku_sho_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
sku_sur_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
sku_totals = pd.merge(sku_sur_totals, sku_sho_totals, on=['Mã hàng', 'Tên hàng'], how='outer').fillna(0)
df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()

df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy() if not rem_shortages.empty else pd.DataFrame()
df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Remaining_Surplus']].copy() if not rem_surpluses.empty else pd.DataFrame()

output_path = r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ\Bao_Cao_Doi_Soat_Thit_Ca_20260813.xlsx'
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_shortage.to_excel(writer, sheet_name='0. Dữ liệu Thiếu Raw', index=False)
    df_surplus.to_excel(writer, sheet_name='0. Dữ liệu Thừa Raw', index=False)
    df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
    df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
    df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
    df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
    df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
    df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)

print('SUCCESS')
