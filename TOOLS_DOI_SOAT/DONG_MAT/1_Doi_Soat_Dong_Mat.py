
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

import pymysql
import pandas as pd
import numpy as np
import os
import io

def get_connection():
    return pymysql.connect(
        host='103.140.248.250',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm',
    )

def fetch_data_to_df(sql_query):
    conn = get_connection()
    try:
        df = pd.read_sql(sql_query, conn)
        return df
    finally:
        conn.close()

def run_mapping(target_date='2026-07-22'):

    import io
    import requests
    # 1. Fetch branch mapping (id to name) -> NOT NEEDED for Dông Mát since we read from local file
    
    # 2. Fetch Shortages from Google Sheet
    url = 'https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=csv&gid=1422896115'
    response = requests.get(url, verify=False)
    content = response.content.decode('utf-8')
    lines_csv = content.split('\n')
    header_idx = 1
    for idx, l in enumerate(lines_csv[:15]):
        if 'Số lượng chuyển' in l or 'Mã hàng' in l or 'Chi nhánh nhận' in l:
            header_idx = idx
            break
            
    df_shortage = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)

    # Filter group MÁT
    col_group = 'Nhóm hàng' if 'Nhóm hàng' in df_shortage.columns else df_shortage.columns[4]
    df_shortage[col_group] = df_shortage[col_group].astype(str).str.strip().str.upper()
    df_shortage = df_shortage[df_shortage[col_group] == 'MÁT']
    
    if 'Tên SP' in df_shortage.columns and 'Tên hàng' not in df_shortage.columns:
        df_shortage['Tên hàng'] = df_shortage['Tên SP']
    if 'ĐVT' not in df_shortage.columns:
        df_shortage['ĐVT'] = 'kg'
    if 'Mã thùng' not in df_shortage.columns:
        df_shortage['Mã thùng'] = ''
    
    df_shortage['Chênh lệch'] = pd.to_numeric(df_shortage['Chênh lệch'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # Filter by latest date
    if 'Ngày' in df_shortage.columns:
        df_shortage['Ngày_parsed'] = pd.to_datetime(df_shortage['Ngày'], format='%m/%d/%Y', errors='coerce')
        latest_date = df_shortage['Ngày_parsed'].dropna().max()
        df_shortage = df_shortage[df_shortage['Ngày_parsed'] == latest_date]
        
    df_shortage = df_shortage[df_shortage['Chênh lệch'] > 0].copy()
    
    # 3. Load Surplus
    df_surplus = pd.read_excel(r'C:\Users\PC\Downloads\dư ĐÔNG MÁT 02.08.xlsx', dtype=str)
    df_surplus['Số lượng chuyển'] = pd.to_numeric(df_surplus['Số lượng chuyển'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df_surplus['Số lượng nhận'] = pd.to_numeric(df_surplus['Số lượng nhận'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df_surplus['SL_du'] = df_surplus['Số lượng nhận']
    df_surplus.rename(columns={'Đơn vị tính': 'ĐVT'}, inplace=True)
    
    # Map Chi nhánh nhận to ID ST
    store_map = dict(zip(df_shortage['Chi nhánh nhận'], df_shortage['ID ST']))
    df_surplus['Chi nhánh nhận'] = df_surplus['Chi nhánh nhận'].map(store_map).fillna(df_surplus['Chi nhánh nhận'])
    df_shortage['Chi nhánh nhận'] = df_shortage['ID ST']
    
    # Filter missing / surplus
    df_surplus = df_surplus[df_surplus['SL_du'] > 0].copy()
    file_layout = r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT\Layout MD.xlsx'
    layout_df = pd.read_excel(file_layout, sheet_name='layout Mát')
    layout_df.columns = layout_df.columns.str.strip()
    layout_df['Siêu thị'] = layout_df['ID ST'].astype(str).str.strip()
    store_to_pos = {row['Siêu thị']: int(row['VỊ trí']) for _, row in layout_df.iterrows()}

    # Clean barcodes and exclude 'CC' prefixes
    df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
    df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
    df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
    df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()


    # 6. Group shortage & surplus
    # 6. Group shortage & surplus
    diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
        'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
        'Chênh lệch': 'sum',
        'ĐVT': 'first',
        'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str))
    }).reset_index()
    diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu'}, inplace=True)
    
    du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
        'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
        'SL_du': 'sum',
        'ĐVT': 'first',
        'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
        'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
    }).reset_index()
    du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)

    # Merge for internal matching
    merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
    merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
    merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
    merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
    merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('kg')
    merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
    merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()


    # Step 1: Khớp nội bộ 100%
    df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
    df_exact['Lỗi'] = 'DC thao tác sai'
    df_exact = df_exact[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
    df_exact.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Lỗi']

    # Step 2: Khớp nội bộ một phần
    df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
    df_partial['Diff'] = df_partial['Chênh lệch'] - df_partial['SL_du']
    df_partial['Lỗi'] = 'DC thao tác sai'
    df_partial = df_partial[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Diff', 'Lỗi']]
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
            pos_sur = store_to_pos.get(sur_store, None)
            
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
                    pos_sho = store_to_pos.get(sho_store, None)
                    if pos_sur is not None and pos_sho is not None:
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
                    pos_sho = store_to_pos.get(sho_store, None)
                    
                    prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                    cross_matches.append({
                        'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                        'Vị trí Dư': pos_sur if pos_sur is not None else '-', 'Mã Thùng Thừa': sur_crate,
                        'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                        'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                        'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                        'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                        'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                    })
                    matched_sur_keys.add((sur_store, sku))
                    matched_sho_keys.add((sho_store, sku))
                    
    df_cross = pd.DataFrame(cross_matches)
    
    # Exclude matched from remainder
    for index, row in rem_shortages.iterrows():
        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
            rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
    for index, row in rem_surpluses.iterrows():
        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
            rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
            
    rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
    rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()

    # Step 4: Tổng Dư >= Tổng Thiếu
    sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index()
    sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index()
    sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Mã hàng', 'Tên hàng'], how='outer')
    sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
    sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
    sku_totals['Diff'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
    
    df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
    
    sur_details, sho_details = [], []
    for idx, row in df_total_gte.iterrows():
        sku = row['Mã hàng']
        sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
        sur_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(r['Chi nhánh nhận'], '-')}) ({r['Remaining_Surplus']:.3f} kg)" for _, r in sku_sur.iterrows()]))
        sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
        sho_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(r['Chi nhánh nhận'], '-')}) ({r['Remaining_Shortage']:.3f} kg)" for _, r in sku_sho.iterrows()]) if len(sku_sho) > 0 else "Không có")
        
    if not df_total_gte.empty:
        df_total_gte['Chi tiết ST nhận Dư'] = sur_details
        df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
        df_total_gte = df_total_gte[['Mã hàng', 'Tên hàng', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Diff']]
        df_total_gte.columns = ['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)']
    else:
        df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])

    # Step 5: Chỉ có thiếu ròng
    df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
    df_only_diff.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
    
    # Step 6: Chỉ có thừa ròng
    df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Remaining_Surplus']].copy()
    df_only_du.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)']

    # 7. Write to Excel
    out_xlsx = rf"C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT\Doi_Soat_Cheo_Dong_Mat_02_08_v2.xlsx"
    with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
        df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
        df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
        df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
        df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
        df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
        df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)

    print("Reconciliation completed successfully! Excel file has been saved.")

    
    # Log summary counts
    print(f"  - Internal Exact matches: {len(df_exact)} rows")
    print(f"  - Internal Partial matches: {len(df_partial)} rows")
    print(f"  - Cross-store 1-1 matches: {len(df_cross)} rows")
    print(f"  - Total Surplus >= Total Shortage: {len(df_total_gte)} rows")
    print(f"  - Net Shortage only: {len(df_only_diff)} rows")
    print(f"  - Net Surplus only: {len(df_only_du)} rows")


if __name__ == "__main__":
    run_mapping()
