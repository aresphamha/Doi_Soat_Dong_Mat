import pandas as pd
import io
import requests
import os
import glob

def clean_qty(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    val = str(x).replace(',', '.')
    try: return float(val)
    except: return 0.0

# 1. Load Layout MD
print('Đang tải Layout MD...')
df_layout = pd.read_excel(r'C:\Users\PC\Downloads\Telegram Desktop\Layout MD.xlsx', sheet_name='layout Mát', dtype=str)
df_layout['Siêu thị'] = df_layout['Siêu thị'].astype(str).str.strip().str.upper()
df_layout['Vị trí '] = pd.to_numeric(df_layout['Vị trí '], errors='coerce')
store_to_pos = dict(zip(df_layout['Siêu thị'], df_layout['Vị trí ']))

# 2. Load Shortage (Chênh lệch) từ Google Sheets
print('Đang tải dữ liệu Chênh Lệch từ Google Sheets...')
url = 'https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=csv&gid=1422896115'
response = requests.get(url)
content = response.content.decode('utf-8')
lines = content.split('\n')

header_idx = 1
for idx, line in enumerate(lines[:15]):
    if 'Số lượng chuyển' in line or 'Mã hàng' in line or 'Chi nhánh nhận' in line:
        header_idx = idx
        break
        
df_shortage = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
date_col = 'Ngày' if 'Ngày' in df_shortage.columns else df_shortage.columns[0]
df_shortage = df_shortage[df_shortage[date_col] == '07/29/2026']

col_group = 'Nhóm hàng' if 'Nhóm hàng' in df_shortage.columns else df_shortage.columns[4]
df_shortage[col_group] = df_shortage[col_group].astype(str).str.strip().str.upper()
df_shortage = df_shortage[df_shortage[col_group] == 'MÁT']

df_shortage['Chênh_lệch_num'] = df_shortage['Chênh lệch'].apply(clean_qty)
df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
df_shortage['Mã hàng'] = df_shortage['Mã hàng'].apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)
df_sho_all = df_shortage[df_shortage['Chênh_lệch_num'] > 0].copy()

# Rename to match standard
diff_grouped = df_sho_all[['Chi nhánh nhận', 'Mã hàng', 'Tên SP', 'Chênh_lệch_num', 'ĐVT', 'Mã thùng']].copy()
diff_grouped.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'Chênh lệch', 'ĐVT', 'Mã thùng thiếu']

# 3. Load Surplus
print('Đang tải dữ liệu Dư Mát 29.07...')
surplus_path = glob.glob(r'C:\Users\PC\Downloads\*mát 29.07*.xlsx')[0]
df_surplus = pd.read_excel(surplus_path, dtype=str)
df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
df_surplus['Mã hàng'] = df_surplus['Mã hàng'].apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)
df_surplus = df_surplus[df_surplus['Người tạo'].str.strip().str.upper() != 'USER HỆ THỐNG']
df_surplus['Số lượng nhận'] = df_surplus['Số lượng nhận'].apply(clean_qty)
df_sur_all = df_surplus[df_surplus['Số lượng nhận'] > 0].copy()

du_grouped = df_sur_all[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'Số lượng nhận', 'Đơn vị tính', 'Mã thùng', 'Mã chuyển hàng']].copy()
du_grouped.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa']

# 4. Merge for internal matching
print('Đang thực hiện khớp nội bộ và khớp chéo...')
merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('')
merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0)
merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0)
merged_internal['Mã thùng thiếu'] = merged_internal['Mã thùng thiếu'].fillna('-')
merged_internal['Mã thùng thừa'] = merged_internal['Mã thùng thừa'].fillna('-')
merged_internal['Mã chuyển hàng thừa'] = merged_internal['Mã chuyển hàng thừa'].fillna('-')

merged_internal['Lệch_tuyệt_đối'] = abs(merged_internal['Chênh lệch'] - merged_internal['SL_du'])
merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)

# Step 1: Khớp nội bộ 100%
df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
loi_text = 'DC thao tác sai'
df_exact['Lỗi'] = loi_text
df_exact = df_exact[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'Lỗi']]
df_exact.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Số lượng Thiếu & Dư (Khớp)', 'Lỗi']

# Step 2: Khớp nội bộ một phần
df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
df_partial['Dif'] = df_partial['Chênh lệch'] - df_partial['SL_du']
df_partial['Lỗi'] = loi_text
df_partial = df_partial[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Dif', 'Lỗi']]
df_partial.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Chênh lệch thừa - thiếu', 'Lỗi']

# Remainder calculation
merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']

rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()

# Step 3: Khớp chéo liên siêu thị
cross_matches = []
skus_shortage = rem_shortages['Mã hàng'].unique()
skus_surplus = rem_surpluses['Mã hàng'].unique()
common_skus = set(skus_shortage).intersection(skus_surplus)

matched_sho_keys = set()
matched_sur_keys = set()

for sku in common_skus:
    sku_shortages = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
    sku_surpluses = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
    
    for idx_sur, row_sur in sku_surpluses.iterrows():
        sur_qty = row_sur['Remaining_Surplus']
        sur_store = row_sur['Chi nhánh nhận']
        sur_crate = row_sur['Mã thùng thừa']
        sur_transfer = row_sur['Mã chuyển hàng thừa']
        sku_name = row_sur['Tên hàng']
        dvt = row_sur['ĐVT']
        pos_sur = store_to_pos.get(str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store, None)
        
        matching_shortages = []
        for idx_sho, row_sho in sku_shortages.iterrows():
            sho_qty = row_sho['Remaining_Shortage']
            if abs(sur_qty - sho_qty) <= 0.01:
                matching_shortages.append(row_sho)
        
        if len(matching_shortages) > 0:
            best_match = None
            best_dist = 9999
            for sho_row in matching_shortages:
                sho_store = sho_row['Chi nhánh nhận']
                pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                if pos_sur is not None and pos_sho is not None and not pd.isna(pos_sur) and not pd.isna(pos_sho):
                    dist = abs(pos_sur - pos_sho)
                    if dist < best_dist:
                        best_dist = dist
                        best_match = sho_row
                else:
                    if best_match is None:
                        best_match = sho_row
            
            if best_match is not None:
                sho_store = best_match['Chi nhánh nhận']
                sho_qty = best_match['Remaining_Shortage']
                sho_crate = best_match['Mã thùng thiếu']
                pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                
                if best_dist != 9999:
                    prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                else:
                    prob = "Không xác định (Thiếu Layout)"
                    
                cross_matches.append({
                    'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                    'Vị trí Dư': pos_sur if pd.notna(pos_sur) else '-', 'Mã Thùng Thừa': sur_crate,
                    'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                    'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pd.notna(pos_sho) else '-',
                    'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                    'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                    'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                })
                matched_sur_keys.add((sur_store, sku))
                matched_sho_keys.add((sho_store, sku))

df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
    'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa',
    'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu',
    'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
])

# Step 4: Tổng dư >= Tổng thiếu
df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
df_only_diff = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
df_only_du = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)'])

# Clean remainder for diff and du
if not rem_shortages.empty:
    rem_shortages = rem_shortages[~rem_shortages.apply(lambda r: (r['Chi nhánh nhận'], r['Mã hàng']) in matched_sho_keys, axis=1)]
    df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
    df_only_diff.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']

if not rem_surpluses.empty:
    rem_surpluses = rem_surpluses[~rem_surpluses.apply(lambda r: (r['Chi nhánh nhận'], r['Mã hàng']) in matched_sur_keys, axis=1)]
    df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Remaining_Surplus']].copy()
    df_only_du.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)']

# 5. Xuất Excel chia Sheet giống hệt Dashboard
out_dir = r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT'
out_file = os.path.join(out_dir, 'Doi_Soat_Cheo_Mat_Day_Du_2907_v2.xlsx')
with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
    df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
    df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
    df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
    df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư_ Tổng Thiếu', index=False)
    df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
    df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)

print('SUCCESS! Wrote all 6 sheets to', out_file)
