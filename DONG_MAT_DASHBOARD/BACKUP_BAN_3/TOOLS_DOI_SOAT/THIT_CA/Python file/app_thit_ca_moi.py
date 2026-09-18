
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

import streamlit as st
import pandas as pd
import numpy as np
import pymysql
import io
import datetime

# Custom styling
st.set_page_config(page_title="Hệ thống Đối soát Chéo Thịt Cá", page_icon="🥩", layout="wide")

st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ff4b4b;
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #ff4b4b;
    }
    .metric-label {
        font-size: 13px;
        color: #a3a8b4;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🥩 Đối Soát Chéo Dư - Thiếu Kho Thịt Cá")
st.markdown("Hệ thống tự động kết nối StarRocks qua VPN để đối soát chéo lượng hàng thừa/thiếu hàng ngày.")

# DB connection helper
def get_connection():
    return pymysql.connect(
        host='103.147.122.103',
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

# Date selection
selected_date = st.date_input("Chọn ngày đối soát:", datetime.date(2026, 7, 22))
date_str = selected_date.strftime('%Y-%m-%d')

if True: # Tự động chạy khi thay đổi ngày

    with st.spinner("Đang tải dữ liệu và tính toán đối soát chéo..."):
        try:
            # 1. Fetch branch mapping
            sql_branches = """
            SELECT branch_id, branch_code, branch_name
            FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
            WHERE branch_name IS NOT NULL AND branch_name != ''
            GROUP BY branch_id, branch_code, branch_name
            """

            df_branches = fetch_data_to_df(sql_branches)
            id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))

            # 2. Fetch shortages (MF01)
            sql_mf01 = f"""
            SELECT 
                i.to_branch_id,
                i.code as `Mã chuyển hàng`,
                i.double_check_code as `Mã thùng`,
                l.barcode as `Mã hàng`,
                l.name as `Tên hàng`,
                l.unit__name as `ĐVT`,
                CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
            FROM __cdc_kfm_kf_inventories_kf_transfer_items i
            INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
            WHERE i.from_branch_id = '6a34ed56f23028000774139f' -- MF01
              AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
              AND i.status = 5
              AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
            """
            df_mf01 = fetch_data_to_df(sql_mf01)
            
            if df_mf01.empty:
                st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho MF01 ngày {selected_date.strftime('%d/%m/%Y')}.")
                st.stop()
                
            df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
            df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
            df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
            
            # 3. Fetch surpluses (MF02)
            sql_mf02 = f"""
            SELECT 
                i.to_branch_id,
                i.code as `Mã chuyển hàng`,
                i.double_check_code as `Mã thùng`,
                i.note as `Ghi chú chuyển (phiếu)`,
                l.barcode as `Mã hàng`,
                l.name as `Tên hàng`,
                l.unit__name as `ĐVT`,
                CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`
            FROM __cdc_kfm_kf_inventories_kf_transfer_items i
            INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
            WHERE i.from_branch_id = '6a34ed8d6607ba000703e235' -- MF02
              AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
              AND i.status = 5
              AND i.created_by = '5f1152906c86b40006155d97' -- User Hệ Thống
              AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
            """
            df_mf02 = fetch_data_to_df(sql_mf02)
            df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
            df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()

            # 4. Clean surplus crate code
            def extract_surplus_crate(row):
                val = row.get('Ghi chú chuyển (phiếu)', None)
                if pd.isna(val) or not val:
                    return str(row['Mã thùng']).strip()
                val_str = str(val).strip()
                prefixes = ["Các mã bổ sung của thùng", "Các mã bổ sung của phiếu"]
                for prefix in prefixes:
                    if val_str.startswith(prefix):
                        return val_str[len(prefix):].strip()
                return str(row['Mã thùng']).strip()
                
            if not df_surplus.empty:
                df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
            else:
                df_surplus['Mã thùng'] = ""

            # 5. Load layout
            file_layout = r"d:\Đối soát kho thịt cá\LayoutImportThitCa.xlsx"
            layout_df = pd.read_excel(file_layout, sheet_name='Sheet1')
            layout_df['Siêu thị'] = layout_df['Siêu thị'].astype(str).str.strip()
            store_to_pos = {row['Siêu thị']: int(row['Vị trí']) for _, row in layout_df.iterrows()}

            # Clean barcodes and exclude 'CC' prefixes
            df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
            df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
            df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
            df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()


            # 6. Group shortage & surplus
            diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                'Chênh lệch': 'sum',
                'ĐVT': 'first',
                'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str))
            }).reset_index()
            diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu'}, inplace=True)
            
            if not df_surplus.empty:
                du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                    'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                    'SL_du': 'sum',
                    'ĐVT': 'first',
                    'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                    'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                }).reset_index()
                du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
            else:
                du_grouped = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa'])

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
                            
            df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
                'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 
                'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 
                'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
            ])
            
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
            if not rem_shortages.empty or not rem_surpluses.empty:
                sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
                sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
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
            else:
                df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])

            # Step 5: Chỉ có thiếu ròng
            if not rem_shortages.empty:
                df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
                df_only_diff.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
            else:
                df_only_diff = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
            
            # Step 6: Chỉ có thừa ròng
            if not rem_surpluses.empty:
                df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Remaining_Surplus']].copy()
                df_only_du.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)']
            else:
                df_only_du = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)'])

            # Display KPIs
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">TỔNG KHỚP NỘI BỘ 100%</div>
                        <div class="metric-value">{len(df_exact)} dòng</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">TỔNG KHỚP NỘI BỘ MỘT PHẦN</div>
                        <div class="metric-value">{len(df_partial)} dòng</div>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                    <div class="metric-card" style="border-left-color: #00c0f2;">
                        <div class="metric-label">TỔNG KHỚP CHÉO LIÊN ST 1-1</div>
                        <div class="metric-value" style="color: #00c0f2;">{len(df_cross)} dòng</div>
                    </div>
                """, unsafe_allow_html=True)
            with c4:
                st.markdown(f"""
                    <div class="metric-card" style="border-left-color: #2ebd59;">
                        <div class="metric-label">CHỈ CÓ THIẾU RÒNG / THỪA RÒNG</div>
                        <div class="metric-value" style="color: #2ebd59;">{len(df_only_diff)} / {len(df_only_du)} dòng</div>
                    </div>
                """, unsafe_allow_html=True)

            # Export Excel to Memory for Download Button
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
                df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
                df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
                df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
                df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
                df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
            
            st.download_button(
                label="📥 Tải Xuống Báo Cáo Đối Soát Chéo Excel",
                data=output_excel.getvalue(),
                file_name=f"Doi_Soat_Cheo_Thit_Ca_{date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Tab presentation
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "1. Khớp nội bộ 100%", 
                "2. Khớp nội bộ một phần", 
                "3. Khớp chéo liên ST 1-1", 
                "4. Tổng Dư >= Tổng Thiếu", 
                "5. Chỉ ghi nhận Thiếu ròng", 
                "6. Chỉ ghi nhận Thừa ròng"
            ])
            
            with tab1:
                st.subheader("1. Danh sách Khớp nội bộ 100% (DC thao tác sai)")
                st.dataframe(df_exact, use_container_width=True)
            with tab2:
                st.subheader("2. Danh sách Khớp nội bộ một phần")
                st.dataframe(df_partial, use_container_width=True)
            with tab3:
                st.subheader("3. Danh sách Khớp chéo liên ST 1-1 (DC giao nhầm CH)")
                st.dataframe(df_cross, use_container_width=True)
            with tab4:
                st.subheader("4. Danh sách Tổng Dư >= Tổng Thiếu")
                st.dataframe(df_total_gte, use_container_width=True)
            with tab5:
                st.subheader("5. Danh sách Chỉ ghi nhận Thiếu ròng (Siêu thị nhận thiếu)")
                st.dataframe(df_only_diff, use_container_width=True)
            with tab6:
                st.subheader("6. Danh sách Chỉ ghi nhận Thừa ròng (Siêu thị nhận thừa)")
                st.dataframe(df_only_du, use_container_width=True)

        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi chạy đối soát: {e}")
            st.exception(e)
