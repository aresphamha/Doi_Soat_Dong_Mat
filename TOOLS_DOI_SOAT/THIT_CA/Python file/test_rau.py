import sys
import os
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

date_str = '2026-07-22'

shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'HCM010002')"
sql_mf01 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.double_check_code as `Mã thùng`,
    l.barcode as `Mã hàng`,
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
df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()

surplus_condition = "i.from_branch_id = '69532cb676e3cd000760a9e1'"
sql_mf02 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.note as `Ghi chú chuyển`,
    l.barcode as `Mã hàng`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE {surplus_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf02 = fetch_data_to_df(sql_mf02)

print('--- SHORTAGE ---')
print(df_shortage.to_string())
print('\n--- SURPLUS ---')
print(df_mf02.to_string())
