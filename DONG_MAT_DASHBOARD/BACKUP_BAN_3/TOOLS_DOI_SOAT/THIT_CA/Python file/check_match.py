import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

date_str = '2026-07-22'
shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'HCM010002')"
surplus_condition = "i.from_branch_id = '69532cb676e3cd000760a9e1'"

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
WHERE {shortage_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf01 = fetch_data_to_df(sql_mf01)

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
WHERE {surplus_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND i.created_by = '5f1152906c86b40006155d97' -- User Hệ Thống
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf02 = fetch_data_to_df(sql_mf02)

with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_match_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"MF01 (Thieu) rows: {len(df_mf01)}\n")
    if not df_mf01.empty:
        df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
        df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
        f.write(f"Shortage > 0 rows: {len(df_shortage)}\n")
    else:
        df_shortage = pd.DataFrame()

    f.write(f"MF02 (Thua) rows: {len(df_mf02)}\n")
    if not df_mf02.empty:
        df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()
        f.write(f"Surplus > 0 rows: {len(df_surplus)}\n")
    else:
        df_surplus = pd.DataFrame()
        
    if not df_shortage.empty and not df_surplus.empty:
        df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
        df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
        df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')]
        df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')]
        
        diff_grouped = df_shortage.groupby(['to_branch_id', 'Mã hàng']).agg({'Chênh lệch': 'sum'}).reset_index()
        du_grouped = df_surplus.groupby(['to_branch_id', 'Mã hàng']).agg({'SL_du': 'sum'}).reset_index()
        
        f.write(f"Diff grouped rows: {len(diff_grouped)}\n")
        f.write(f"Du grouped rows: {len(du_grouped)}\n")
        
        skus_shortage = diff_grouped['Mã hàng'].unique()
        skus_surplus = du_grouped['Mã hàng'].unique()
        common_skus = set(skus_shortage).intersection(skus_surplus)
        f.write(f"Unique SKUs in shortage: {len(skus_shortage)}\n")
        f.write(f"Unique SKUs in surplus: {len(skus_surplus)}\n")
        f.write(f"Common SKUs: {len(common_skus)}\n")
        
        # Check matching quantity counts
        matches = 0
        for sku in common_skus:
            sho_qty = diff_grouped[diff_grouped['Mã hàng'] == sku]['Chênh lệch'].values
            sur_qty = du_grouped[du_grouped['Mã hàng'] == sku]['SL_du'].values
            
            for qty in sur_qty:
                if any(abs(sq - qty) <= 0.01 for sq in sho_qty):
                    matches += 1
        
        f.write(f"Potential 1-1 cross matches (same quantity): {matches}\n")
