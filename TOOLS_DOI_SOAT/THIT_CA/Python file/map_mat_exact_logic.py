
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
df_sho = df_shortage[df_shortage['Chênh_lệch_num'] > 0].copy()

# 3. Load Surplus
print('Đang tải dữ liệu Dư Mát 29.07...')
surplus_path = glob.glob(r'C:\Users\PC\Downloads\*mát 29.07*.xlsx')[0]
df_surplus = pd.read_excel(surplus_path, dtype=str)
df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
df_surplus['Mã hàng'] = df_surplus['Mã hàng'].apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)
df_surplus['Số lượng nhận'] = df_surplus['Số lượng nhận'].apply(clean_qty)
df_sur = df_surplus[df_surplus['Số lượng nhận'] > 0].copy()

# 4. Thực hiện Khớp chéo giống logic Thịt Cá
print('Đang thực hiện Map chéo (Khớp 1-1 giống Thịt Cá)...')
cross_matches = []
skus_shortage = df_sho['Mã hàng'].unique()
skus_surplus = df_sur['Mã hàng'].unique()
common_skus = set(skus_shortage).intersection(skus_surplus)

matched_sho_keys = set()
matched_sur_keys = set()

for sku in common_skus:
    sku_shortages = df_sho[df_sho['Mã hàng'] == sku].copy()
    sku_surpluses = df_sur[df_sur['Mã hàng'] == sku].copy()
    
    for idx_sur, row_sur in sku_surpluses.iterrows():
        sur_qty = row_sur['Số lượng nhận']
        sur_store = row_sur['Chi nhánh nhận']
        sur_crate = row_sur.get('Mã thùng', '-')
        sur_transfer = row_sur.get('Mã chuyển hàng', '-')
        sku_name = row_sur.get('Tên hàng', row_sur.get('Tên SP', ''))
        dvt = row_sur.get('ĐVT', row_sur.get('Đơn vị tính', ''))
        
        sur_store_clean = str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store
        pos_sur = store_to_pos.get(sur_store_clean, None)
        
        matching_shortages = []
        for idx_sho, row_sho in sku_shortages.iterrows():
            sho_qty = row_sho['Chênh_lệch_num']
            # Chú ý: Ở đây khớp 1-1 chính xác số lượng
            if abs(sur_qty - sho_qty) <= 0.01:
                matching_shortages.append(row_sho)
        
        if len(matching_shortages) > 0:
            best_match = None
            best_dist = 9999
            for sho_row in matching_shortages:
                sho_store = sho_row['Chi nhánh nhận']
                sho_store_clean = str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store
                pos_sho = store_to_pos.get(sho_store_clean, None)
                
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
                sho_qty = best_match['Chênh_lệch_num']
                sho_crate = best_match.get('Mã thùng', '-')
                
                sho_store_clean = str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store
                pos_sho = store_to_pos.get(sho_store_clean, None)
                
                if best_dist != 9999:
                    prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                else:
                    prob = "Không xác định (Thiếu Layout)"
                    
                cross_matches.append({
                    'Mã hàng': sku,
                    'Tên hàng': sku_name,
                    'ĐVT': dvt,
                    'ST Nhận Dư (Thừa)': sur_store,
                    'Vị trí Dư': pos_sur if pd.notna(pos_sur) else '-',
                    'Mã Thùng Thừa': sur_crate,
                    'Mã Chuyển Hàng Thừa': sur_transfer,
                    'SL Thừa (kg)': sur_qty,
                    'ST Nhận Thiếu (Thiếu)': sho_store,
                    'Vị trí Thiếu': pos_sho if pd.notna(pos_sho) else '-',
                    'Mã Thùng Thiếu': sho_crate,
                    'SL Thiếu (kg)': sho_qty,
                    'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                    'Khả năng nhầm': prob,
                    'Lỗi': 'DC giao nhầm CH'
                })
                matched_sur_keys.add((sur_store, sku))
                matched_sho_keys.add((sho_store, sku))

df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
    'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa',
    'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu',
    'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
])

out_dir = r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT'
out_file = os.path.join(out_dir, 'Ket_Qua_Map_Mat_Chinh_Xac_2907.xlsx')
df_cross.to_excel(out_file, index=False)
print('SUCCESS! Wrote', len(df_cross), 'rows to', out_file)
