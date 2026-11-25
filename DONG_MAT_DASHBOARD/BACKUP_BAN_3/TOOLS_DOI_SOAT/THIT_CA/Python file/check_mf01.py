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
    l.barcode as `Mã hàng`,
    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE {shortage_condition}
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND l.barcode IN ('10312', '10836', '11571', '11129')
"""
df_mf01 = fetch_data_to_df(sql_mf01)
df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']

print(df_mf01.to_string())
