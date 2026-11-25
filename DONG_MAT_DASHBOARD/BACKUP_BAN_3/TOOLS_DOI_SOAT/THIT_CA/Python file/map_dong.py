
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

def clean_qty(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    val = str(x).replace(',', '.')
    try: return float(val)
    except: return 0.0

def run_mapping():
    # 1. Load Shortage (Chênh lệch) từ Google Sheets
    url = 'https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=csv&gid=1422896115'
    print('Đang tải dữ liệu Chênh Lệch từ Google Sheets...')
    response = requests.get(url)
    content = response.content.decode('utf-8')
    lines = content.split('\n')
    
    header_idx = 1
    for idx, line in enumerate(lines[:15]):
        if 'Số lượng chuyển' in line or 'Mã hàng' in line or 'Chi nhánh nhận' in line:
            header_idx = idx
            break
            
    df_shortage = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)

    # 2. Lọc cột E (Nhóm hàng) == ĐÔNG và Chênh lệch > 0 (Thiếu)
    print('Đang lọc dữ liệu nhóm ĐÔNG...')
    if 'Nhóm hàng' in df_shortage.columns:
        df_shortage['Nhóm hàng'] = df_shortage['Nhóm hàng'].astype(str).str.strip().str.upper()
        df_shortage = df_shortage[df_shortage['Nhóm hàng'] == 'ĐÔNG']
    else:
        # Nếu cột thứ 5 không tên
        col_e = df_shortage.columns[4]
        df_shortage[col_e] = df_shortage[col_e].astype(str).str.strip().str.upper()
        df_shortage = df_shortage[df_shortage[col_e] == 'ĐÔNG']

    df_shortage['Chênh_lệch_num'] = df_shortage['Chênh lệch'].apply(clean_qty)
    df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
    df_shortage['Mã hàng'] = df_shortage['Mã hàng'].apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)

    # Shortage là các dòng có Chênh lệch > 0
    df_sho = df_shortage[df_shortage['Chênh_lệch_num'] > 0].copy()

    # 3. Load Surplus (Dư đông 28.07.xlsx)
    print('Đang tải dữ liệu Dư Đông...')
    surplus_path = r'C:\Users\PC\Downloads\Dư đông 28.07.xlsx'
    if not os.path.exists(surplus_path):
        print(f"Lỗi: Không tìm thấy file {surplus_path}")
        return

    df_surplus = pd.read_excel(surplus_path, dtype=str)
    df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
    df_surplus['Mã hàng'] = df_surplus['Mã hàng'].apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else x)
    df_surplus['Số lượng nhận'] = df_surplus['Số lượng nhận'].apply(clean_qty)
    
    # Lấy các dòng dư (Số lượng nhận > 0)
    df_sur = df_surplus[df_surplus['Số lượng nhận'] > 0].copy()

    # 4. Map Hàng Thiếu với Hàng Dư
    print('Đang thực hiện Map dữ liệu...')
    matches = []
    
    # Gom nhóm số lượng dư theo từng Mã Hàng và Chi Nhánh
    surplus_dict = {}
    for _, row in df_sur.iterrows():
        sku = row['Mã hàng']
        if sku not in surplus_dict:
            surplus_dict[sku] = []
        surplus_dict[sku].append({'store': row['Chi nhánh nhận'], 'qty': row['Số lượng nhận']})

    # Duyệt qua từng dòng thiếu để bù bằng số dư
    for _, row in df_sho.iterrows():
        sku = row['Mã hàng']
        store_short = row['Chi nhánh nhận']
        qty_short = row['Chênh_lệch_num']
        ten_sp = row.get('Tên SP', row.get('Tên hàng', ''))
        
        if sku in surplus_dict:
            for sur in surplus_dict[sku]:
                if sur['qty'] > 0 and qty_short > 0:
                    take = min(sur['qty'], qty_short)
                    sur['qty'] -= take
                    qty_short -= take
                    
                    matches.append({
                        'Mã hàng': sku,
                        'Tên SP': ten_sp,
                        'Chi nhánh THIẾU': store_short,
                        'SL THIẾU (được bù)': take,
                        'Chi nhánh DƯ': sur['store'],
                    })
                if qty_short == 0:
                    break
                    
        # Nếu vẫn còn thiếu mà không có dư để bù, ghi nhận lại
        if qty_short > 0:
            matches.append({
                'Mã hàng': sku,
                'Tên SP': ten_sp,
                'Chi nhánh THIẾU': store_short,
                'SL THIẾU (được bù)': 0,
                'Chi nhánh DƯ': 'KHÔNG CÓ DƯ ĐỂ BÙ',
            })

    # 5. Xuất File Kết Quả
    df_matches = pd.DataFrame(matches)
    out_dir = r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT'
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'Ket_Qua_Map_Dong_2807.xlsx')

    if not df_matches.empty:
        df_matches.to_excel(out_file, index=False)
        print(f'\nMAPPING THÀNH CÔNG! Đã map được {len(df_matches)} dòng.')
        print(f'Đã lưu kết quả tại: {out_file}')
    else:
        print('\nKHÔNG CÓ DÒNG NÀO MAP ĐƯỢC VỚI NHAU.')

if __name__ == '__main__':
    run_mapping()
