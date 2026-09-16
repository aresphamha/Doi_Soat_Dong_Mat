import pandas as pd
import numpy as np
import io
import os

file_diff = r"d:\Đối soát kho thịt cá\Chênh lệch 22.07.xlsx"
file_du = r"d:\Đối soát kho thịt cá\Dư 22.07.xlsx"
file_layout = r"d:\Đối soát kho thịt cá\LayoutImportThitCa.xlsx"

out_xlsx = r"d:\Đối soát kho thịt cá\Doi_Soat_Cheo_22_07.xlsx"
out_html = r"d:\Đối soát kho thịt cá\Doi_Soat_Cheo_22_07.html"

try:
    df_diff = pd.read_excel(file_diff, sheet_name='Sheet1')
    df_diff['Mã hàng'] = df_diff['Mã hàng'].astype(str).str.strip()
    df_diff['Chênh lệch'] = df_diff['Số lượng chuyển'] - df_diff['Số lượng nhận']
    
    # Shortages
    df_shortage = df_diff[df_diff['Chênh lệch'].round(5) > 0.0].copy()
    
    # Surpluses
    df_surplus = pd.read_excel(file_du, sheet_name='transfer')
    df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
    df_surplus['SL_du'] = df_surplus['Số lượng nhận']
    
    # Chỉ lấy phần dư theo người tạo là User Hệ Thống
    if 'Người tạo' in df_surplus.columns:
        df_surplus = df_surplus[df_surplus['Người tạo'] == 'User Hệ Thống'].copy()
    
    # Clean/extract surplus crate code from Column V (Ghi chú chuyển (phiếu))
    def extract_surplus_crate(row):
        val = row.get('Ghi chú chuyển (phiếu)', None)
        if pd.isna(val):
            return str(row['Mã thùng']).strip()
        val_str = str(val).strip()
        
        prefixes = ["Các mã bổ sung của thùng", "Các mã bổ sung của phiếu"]
        for prefix in prefixes:
            if val_str.startswith(prefix):
                return val_str[len(prefix):].strip()
        return str(row['Mã thùng']).strip()
        
    df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
    
    # Load warehouse layout positions
    layout_df = pd.read_excel(file_layout, sheet_name='Sheet1')
    layout_df['Siêu thị'] = layout_df['Siêu thị'].astype(str).str.strip()
    store_to_pos = {}
    for _, row in layout_df.iterrows():
        store_to_pos[row['Siêu thị']] = int(row['Vị trí'])
        
    # Aggregate shortages
    diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng', 'Tên hàng']).agg({
        'Chênh lệch': 'sum',
        'Đơn vị tính': 'first',
        'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str))
    }).reset_index()
    diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu'}, inplace=True)
    
    # Aggregate surpluses
    du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng', 'Tên hàng']).agg({
        'SL_du': 'sum',
        'Đơn vị tính': 'first',
        'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
        'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
    }).reset_index()
    du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
    
    # Merge for internal store matching
    merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng'], how='outer')
    merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
    merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
    merged_internal['ĐVT'] = merged_internal['Đơn vị tính_x'].fillna(merged_internal['Đơn vị tính_y']).fillna('kg')
    
    # Calculate matched amount internally
    merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
    merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()
    
    # 1. Khớp nội bộ hoàn toàn (DC thao tác sai)
    df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
    df_exact['Lỗi'] = 'DC thao tác sai'
    df_exact = df_exact[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
    df_exact.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Lỗi']
    
    # 2. Khớp nội bộ một phần
    df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
    df_partial['Diff'] = df_partial['Chênh lệch'] - df_partial['SL_du']
    df_partial['Lỗi'] = 'DC thao tác sai'
    df_partial = df_partial[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Diff', 'Lỗi']]
    df_partial.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Chênh lệch thừa - thiếu', 'Lỗi']
    
    # Net remaining quantities for cross-store matching
    merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
    merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']
    
    rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
    rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()
    
    # 3. Khớp chéo liên siêu thị (Sai hướng giao) - Tích hợp khoảng cách Layout
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
            sur_transfer = row_sur['Mã chuyển hàng thừa'] if 'Mã chuyển hàng thừa' in row_sur else ''
            sku_name = row_sur['Tên hàng']
            dvt = row_sur['ĐVT']
            pos_sur = store_to_pos.get(sur_store, None)
            
            # Find all shortages matching this quantity
            matching_shortages = []
            for idx_sho, row_sho in sku_shortages.iterrows():
                sho_qty = row_sho['Remaining_Shortage']
                if abs(sur_qty - sho_qty) <= 0.01:
                    matching_shortages.append(row_sho)
            
            # Reconcile using layout proximity to resolve ambiguity
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
                        if best_match is None: # fallback
                            best_match = sho_row
                
                if best_match is not None:
                    sho_store = best_match['Chi nhánh nhận']
                    sho_qty = best_match['Remaining_Shortage']
                    sho_crate = best_match['Mã thùng thiếu']
                    pos_sho = store_to_pos.get(sho_store, None)
                    
                    # Classify match probability
                    if best_dist <= 5:
                        prob = "Rất cao (Vị trí kề nhau)"
                    elif best_dist <= 15:
                        prob = "Trung bình (Cùng khu)"
                    else:
                        prob = "Thấp (Trùng hợp số lượng)"
                        
                    cross_matches.append({
                        'Mã hàng': sku,
                        'Tên hàng': sku_name,
                        'ĐVT': dvt,
                        'ST Nhận Dư (Thừa)': sur_store,
                        'Vị trí Dư': pos_sur if pos_sur is not None else '-',
                        'Mã Thùng Thừa': sur_crate,
                        'Mã chuyển hàng thừa': sur_transfer,
                        'SL Thừa': sur_qty,
                        'ST Nhận Thiếu (Thiếu)': sho_store,
                        'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                        'Mã Thùng Thiếu': sho_crate,
                        'SL Thiếu': sho_qty,
                        'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                        'Khả năng nhầm': prob,
                        'Lỗi': 'DC giao nhầm CH'
                    })
                    matched_sur_keys.add((sur_store, sku))
                    matched_sho_keys.add((sho_store, sku))
                    
    df_cross = pd.DataFrame(cross_matches)
    if len(df_cross) == 0:
        df_cross = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 'Mã chuyển hàng thừa', 'SL Thừa', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 'Mã Thùng Thiếu', 'SL Thiếu', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'])
    else:
        # Reorder cross sheet columns to look logical
        df_cross = df_cross[['Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 'Mã chuyển hàng thừa', 'SL Thừa', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 'Mã Thùng Thiếu', 'SL Thiếu', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi']]
        
    # Subtract cross matches from remaining lists
    for index, row in rem_shortages.iterrows():
        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
            rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
            
    for index, row in rem_surpluses.iterrows():
        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
            rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
            
    rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
    rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()
    
    # 4. Tổng Dư >= Tổng Thiếu per SKU (on net remaining)
    sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index()
    sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index()
    
    sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Mã hàng', 'Tên hàng'], how='outer')
    sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
    sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
    sku_totals['Diff'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
    
    df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
    
    # Extract store-level breakdowns
    dvt_mapping = merged_internal.groupby('Mã hàng')['ĐVT'].first().to_dict()
    df_total_gte['ĐVT'] = df_total_gte['Mã hàng'].map(dvt_mapping).fillna('kg')
    
    sur_details = []
    sho_details = []
    for idx, row in df_total_gte.iterrows():
        sku = row['Mã hàng']
        dvt_str = row['ĐVT']
        sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
        sur_list = []
        for _, r in sku_sur.iterrows():
            pos = store_to_pos.get(r['Chi nhánh nhận'], '-')
            sur_list.append(f"{r['Chi nhánh nhận']} (Vị trí: {pos}) ({r['Remaining_Surplus']:.3f} {dvt_str})")
        sur_details.append(" | ".join(sur_list))
        
        sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
        sho_list = []
        for _, r in sku_sho.iterrows():
            pos = store_to_pos.get(r['Chi nhánh nhận'], '-')
            sho_list.append(f"{r['Chi nhánh nhận']} (Vị trí: {pos}) ({r['Remaining_Shortage']:.3f} {dvt_str})")
        sho_details.append(" | ".join(sho_list) if len(sho_list) > 0 else "Không có")
        
    df_total_gte['Chi tiết ST nhận Dư'] = sur_details
    df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
    
    # Reorder columns
    df_total_gte = df_total_gte[['Mã hàng', 'Tên hàng', 'ĐVT', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Diff']]
    df_total_gte.columns = ['Mã hàng', 'Tên hàng', 'ĐVT', 'Tổng Dư Hệ Thống', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng']
    
    # 5. Chỉ có thiếu (Chưa đối soát được)
    df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
    df_only_diff.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu']
    
    # 6. Chỉ có thừa (Chưa đối soát được)
    df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Remaining_Surplus']].copy()
    df_only_du.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa']
    
    # Save to Excel
    with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
        df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
        df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
        df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
        df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
        df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
        df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
        
    out_xlsx_web = out_xlsx.replace('\\', '/')
    
    # Helper HTML formatting for details columns
    def format_details_html(details_str, css_class):
        if not details_str or details_str == "Không có":
            return "<span class='text-white-50'>Không có</span>"
        parts = details_str.split(" | ")
        html = ""
        for p in parts:
            html += f"<div style='margin-bottom: 3px;'><span class='{css_class}'>{p.strip()}</span></div>"
        return html

    # Build exact table rows
    exact_rows = "".join([f"<tr><td>{r['Chi nhánh nhận']}</td><td>{r['Mã hàng']}</td><td>{r['Tên hàng']}</td><td><span class='code-thieu'>{r['Mã thùng thiếu']}</span></td><td><span class='code-thua'>{r['Mã thùng thừa']}</span></td><td><span class='code-transfer'>{r['Mã chuyển hàng thừa']}</span></td><td>{r['SL Thiếu (Chênh lệch)']:.3f} {r['ĐVT']}</td><td>{r['SL Thừa (Nhận dư)']:.3f} {r['ĐVT']}</td><td><span class='badge-error-type'>{r['Lỗi']}</span></td><td><span class='badge-success'>Khớp 100% - Đối trừ</span></td></tr>" for _, r in df_exact.iterrows()])
    
    # Build partial table rows
    partial_rows = "".join([f"<tr><td>{r['Chi nhánh nhận']}</td><td>{r['Mã hàng']}</td><td>{r['Tên hàng']}</td><td><span class='code-thieu'>{r['Mã thùng thiếu']}</span></td><td><span class='code-thua'>{r['Mã thùng thừa']}</span></td><td><span class='code-transfer'>{r['Mã chuyển hàng thừa']}</span></td><td>{r['SL Thiếu (Chênh lệch)']:.3f} {r['ĐVT']}</td><td>{r['SL Thừa (Nhận dư)']:.3f} {r['ĐVT']}</td><td>{r['Chênh lệch thừa - thiếu']:.3f} {r['ĐVT']}</td><td><span class='badge-error-type'>{r['Lỗi']}</span></td><td><span class='badge-warning'>Lệch số lượng</span></td></tr>" for _, r in df_partial.iterrows()])
    
    # Build cross table rows with Layout Positions and Distance
    cross_rows = ""
    for _, r in df_cross.iterrows():
        prob = r['Khả năng nhầm']
        if "Rất cao" in prob:
            prob_badge = "<span class='badge-success'>Rất cao (Liền kề)</span>"
        elif "Trung bình" in prob:
            prob_badge = "<span class='badge-warning'>Trung bình (Gần)</span>"
        else:
            prob_badge = "<span class='badge-danger'>Thấp (Xa nhau)</span>"
            
        cross_rows += f"""<tr>
            <td>{r['Mã hàng']}</td>
            <td>{r['Tên hàng']}</td>
            <td>{r['ST Nhận Dư (Thừa)']} <span class='badge-info'>Vị trí: {r['Vị trí Dư']}</span></td>
            <td><span class='code-thua'>{r['Mã Thùng Thừa']}</span></td>
            <td><span class='code-transfer'>{r['Mã chuyển hàng thừa']}</span></td>
            <td>{r['SL Thừa']:.3f} {r['ĐVT']}</td>
            <td>{r['ST Nhận Thiếu (Thiếu)']} <span class='badge-info'>Vị trí: {r['Vị trí Thiếu']}</span></td>
            <td><span class='code-thieu'>{r['Mã Thùng Thiếu']}</span></td>
            <td>{r['SL Thiếu']:.3f} {r['ĐVT']}</td>
            <td><strong>{r['Độ lệch vị trí (Layout)']}</strong></td>
            <td>{prob_badge}</td>
            <td><span class='badge-cross-type'>{r['Lỗi']}</span></td>
        </tr>"""
    
    # Build total_gte table rows
    total_gte_rows = ""
    for _, r in df_total_gte.iterrows():
        sur_html = format_details_html(r['Chi tiết ST nhận Dư'], 'code-thua')
        sho_html = format_details_html(r['Chi tiết ST nhận Thiếu'], 'code-thieu')
        total_gte_rows += f"""<tr>
            <td>{r['Mã hàng']}</td>
            <td>{r['Tên hàng']}</td>
            <td>{r['Tổng Dư Hệ Thống']:.3f} {r['ĐVT']}</td>
            <td>{sur_html}</td>
            <td>{r['Tổng THIẾU Hệ Thống']:.3f} {r['ĐVT']}</td>
            <td>{sho_html}</td>
            <td>{r['Lượng Thừa Ròng']:.3f} {r['ĐVT']}</td>
            <td><span class='badge-info'>Tổng Dư &gt;= Tổng Thiếu</span></td>
        </tr>"""
        
    # Build only_diff rows
    only_diff_rows = "".join([f"<tr><td>{r['Chi nhánh nhận']}</td><td>{r['Mã hàng']}</td><td>{r['Tên hàng']}</td><td><span class='code-thieu'>{r['Mã thùng thiếu']}</span></td><td>{r['SL Thiếu']:.3f} {r['ĐVT']}</td><td><span class='badge-danger'>Thiếu thực tế</span></td></tr>" for _, r in df_only_diff.iterrows()])
    
    # Build only_du rows
    only_du_rows = "".join([f"<tr><td>{r['Chi nhánh nhận']}</td><td>{r['Mã hàng']}</td><td>{r['Tên hàng']}</td><td><span class='code-thua'>{r['Mã thùng thừa']}</span></td><td><span class='code-transfer'>{r['Mã chuyển hàng thừa']}</span></td><td>{r['SL Thừa']:.3f} {r['ĐVT']}</td><td><span class='badge-info'>Thừa thực tế</span></td></tr>" for _, r in df_only_du.iterrows()])
    
    # HTML contents with 6 tabs
    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo cáo đối soát chéo 22.07</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <!-- DataTables CSS -->
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f3f4f6;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }}
        .card {{
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .card-header {{
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            border-top-left-radius: 15px !important;
            border-top-right-radius: 15px !important;
            border-bottom: none;
            padding: 1.5rem;
        }}
        h1 {{
            font-weight: 700;
            margin-bottom: 0;
            color: #ffffff;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .nav-tabs {{
            border-bottom: 1px solid #1f2937;
        }}
        .nav-link {{
            color: #9ca3af;
            border: none;
            padding: 10px 15px;
            font-weight: 600;
            border-radius: 8px 8px 0 0;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }}
        .nav-link:hover {{
            color: #3b82f6;
            background-color: #1f2937;
        }}
        .nav-link.active {{
            color: #ffffff !important;
            background-color: #1e40af !important;
            border-bottom: 3px solid #3b82f6 !important;
        }}
        
        .table {{
            color: #f3f4f6 !important;
        }}
        .table tbody td {{
            color: #f3f4f6 !important;
            background-color: #111827 !important;
            border-bottom: 1px solid #1f2937 !important;
            font-size: 0.95rem;
            vertical-align: middle;
        }}
        .table thead th {{
            color: #e5e7eb !important;
            background-color: #1f2937 !important;
            border-bottom: 2px solid #374151 !important;
            font-weight: 600;
            font-size: 0.95rem;
        }}
        
        .badge-success {{
            background-color: #065f46;
            color: #34d399;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-warning {{
            background-color: #78350f;
            color: #fbbf24;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-danger {{
            background-color: #7f1d1d;
            color: #fca5a5;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-info {{
            background-color: #1e3a8a;
            color: #93c5fd;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        
        .dataTables_wrapper .dataTables_filter input {{
            background-color: #1f2937;
            border: 1px solid #374151;
            color: #ffffff;
            border-radius: 8px;
            padding: 6px 12px;
        }}
        .dataTables_wrapper .dataTables_length select {{
            background-color: #1f2937;
            border: 1px solid #374151;
            color: #ffffff;
            border-radius: 8px;
        }}
        .paginate_button.page-item.active .page-link {{
            background-color: #3b82f6 !important;
            border-color: #3b82f6 !important;
        }}
        .page-link {{
            background-color: #1f2937;
            border-color: #374151;
            color: #9ca3af;
        }}
        .page-link:hover {{
            background-color: #374151;
            color: #ffffff;
        }}
        
        .btn-download {{
            background-color: #10b981;
            color: white;
            font-weight: 600;
            border-radius: 8px;
            border: none;
            padding: 8px 16px;
            transition: all 0.3s ease;
        }}
        .btn-download:hover {{
            background-color: #059669;
            color: white;
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }}
        
        .badge-error-type {{
            background-color: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.82rem;
            white-space: nowrap;
            display: inline-block;
        }}
        
        .badge-cross-type {{
            background-color: rgba(59, 130, 246, 0.15);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.4);
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.82rem;
            white-space: nowrap;
            display: inline-block;
        }}
        
        .code-thieu {{
            background-color: #271c1c;
            color: #fca5a5;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-weight: 600;
            font-size: 0.88rem;
            border: 1px solid rgba(248, 113, 113, 0.2);
            display: inline-block;
        }}
        .code-thua {{
            background-color: #172554;
            color: #93c5fd;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-weight: 600;
            font-size: 0.88rem;
            border: 1px solid rgba(96, 165, 250, 0.2);
            display: inline-block;
        }}
        .code-transfer {{
            background-color: #1e293b;
            color: #e2e8f0;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-weight: 600;
            font-size: 0.88rem;
            border: 1px solid rgba(226, 232, 240, 0.2);
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="container-fluid px-4">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <h1>📊 Báo Cáo Đối Soát Chéo Thừa - Thiếu Ngày 22.07</h1>
                    <p class="text-white-50 mb-0 mt-1">Hàng Thịt Cá - Tự động đối chiếu chênh lệch giữa Giao thiếu và Nhận dư (Tích hợp Layout khoảng cách chia hàng)</p>
                </div>
                <a href="file:///{out_xlsx_web}" class="btn btn-download">
                    📥 Tải File Excel (.xlsx)
                </a>
            </div>
            <div class="card-body p-4">
                
                <!-- Navigation Tabs -->
                <ul class="nav nav-tabs mb-4" id="reportTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="exact-tab" data-bs-toggle="tab" data-bs-target="#exact" type="button" role="tab">
                            ✅ 1. Khớp Nội Bộ 100% ({len(df_exact)})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="partial-tab" data-bs-toggle="tab" data-bs-target="#partial" type="button" role="tab">
                            ⚠️ 2. Khớp Nội Bộ 1 Phần ({len(df_partial)})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="cross-tab" data-bs-toggle="tab" data-bs-target="#cross" type="button" role="tab">
                            🔀 3. Khớp Chéo Liên ST ({len(df_cross)})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="total-gte-tab" data-bs-toggle="tab" data-bs-target="#total-gte" type="button" role="tab">
                            ⚖️ 4. Tổng Dư >= Tổng Thiếu ({len(df_total_gte)})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="only-diff-tab" data-bs-toggle="tab" data-bs-target="#only-diff" type="button" role="tab">
                            ❌ 5. Chỉ Có Thiếu Ròng ({len(df_only_diff)})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="only-du-tab" data-bs-toggle="tab" data-bs-target="#only-du" type="button" role="tab">
                            ➕ 6. Chỉ Có Thừa Ròng ({len(df_only_du)})
                        </button>
                    </li>
                </ul>
                
                <!-- Tab Contents -->
                <div class="tab-content" id="reportTabsContent">
                    
                    <!-- 1. Khớp nội bộ 100% -->
                    <div class="tab-pane fade show active" id="exact" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="exactTable">
                                <thead>
                                    <tr>
                                        <th>Siêu thị nhận</th>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>Mã thùng thiếu</th>
                                        <th>Mã thùng thừa</th>
                                        <th>Mã chuyển hàng thừa</th>
                                        <th>SL Thiếu</th>
                                        <th>SL Thừa</th>
                                        <th>Lỗi cột</th>
                                        <th>Đánh giá</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {exact_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 2. Khớp nội bộ một phần -->
                    <div class="tab-pane fade" id="partial" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="partialTable">
                                <thead>
                                    <tr>
                                        <th>Siêu thị nhận</th>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>Mã thùng thiếu</th>
                                        <th>Mã thùng thừa</th>
                                        <th>Mã chuyển hàng thừa</th>
                                        <th>SL Thiếu</th>
                                        <th>SL Thừa</th>
                                        <th>Độ lệch</th>
                                        <th>Lỗi cột</th>
                                        <th>Đánh giá</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {partial_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 3. Khớp chéo liên ST -->
                    <div class="tab-pane fade" id="cross" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="crossTable">
                                <thead>
                                    <tr>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>ST Nhận DƯ (Thừa)</th>
                                        <th>Mã thùng thừa</th>
                                        <th>Mã chuyển hàng thừa</th>
                                        <th>SL Thừa</th>
                                        <th>ST Nhận THIẾU</th>
                                        <th>Mã thùng thiếu</th>
                                        <th>SL Thiếu</th>
                                        <th>Độ lệch vị trí (Layout)</th>
                                        <th>Khả năng nhầm</th>
                                        <th>Lỗi cột</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {cross_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 4. Tổng Dư >= Tổng Thiếu -->
                    <div class="tab-pane fade" id="total-gte" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="totalGteTable">
                                <thead>
                                    <tr>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>Tổng DƯ Hệ Thống</th>
                                        <th>Chi tiết siêu thị nhận DƯ</th>
                                        <th>Tổng THIẾU Hệ Thống</th>
                                        <th>Chi tiết siêu thị nhận THIẾU</th>
                                        <th>Lượng Thừa Ròng</th>
                                        <th>Đánh giá</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {total_gte_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 5. Chỉ có thiếu -->
                    <div class="tab-pane fade" id="only-diff" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="onlyDiffTable">
                                <thead>
                                    <tr>
                                        <th>Siêu thị nhận</th>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>Mã thùng thiếu</th>
                                        <th>SL Thiếu</th>
                                        <th>Trạng thái</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {only_diff_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 6. Chỉ có thừa -->
                    <div class="tab-pane fade" id="only-du" role="tabpanel">
                        <div class="table-responsive">
                            <table class="table table-hover w-100" id="onlyDuTable">
                                <thead>
                                    <tr>
                                        <th>Siêu thị nhận</th>
                                        <th>Mã hàng</th>
                                        <th>Tên hàng</th>
                                        <th>Mã thùng thừa</th>
                                        <th>Mã chuyển hàng thừa</th>
                                        <th>SL Thừa</th>
                                        <th>Trạng thái</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {only_du_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                </div>
            </div>
        </div>
    </div>
    
    <!-- Bootstrap 5 and DataTables scripts -->
    <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script>
        $(document).ready(function() {{
            var datatableConfig = {{
                "language": {{
                    "lengthMenu": "Hiển thị _MENU_ dòng",
                    "zeroRecords": "Không tìm thấy dữ liệu phù hợp",
                    "info": "Đang hiển thị từ dòng _START_ đến _END_ trong tổng số _TOTAL_ dòng",
                    "infoEmpty": "Không có dữ liệu",
                    "infoFiltered": "(được lọc từ tổng số _MAX_ dòng)",
                    "search": "Tìm kiếm nhanh:",
                    "paginate": {{
                        "first": "Đầu",
                        "last": "Cuối",
                        "next": "Sau",
                        "previous": "Trước"
                    }}
                }},
                "pageLength": 15,
                "order": [[ 0, "asc" ]]
            }};
            
            $('#exactTable').DataTable(datatableConfig);
            $('#partialTable').DataTable(datatableConfig);
            $('#crossTable').DataTable(datatableConfig);
            $('#totalGteTable').DataTable(datatableConfig);
            $('#onlyDiffTable').DataTable(datatableConfig);
            $('#onlyDuTable').DataTable(datatableConfig);
        }});
    </script>
</body>
</html>
"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Files for meat/fish warehouse exported successfully with dynamic UOMs!")
    
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
