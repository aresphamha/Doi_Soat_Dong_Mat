import sys
import os
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT 
    i.to_branch_id, 
    i.code as `Mã chuyển hàng`, 
    i.transfer_date, 
    i.note as `Ghi chú chuyển`, 
    l.barcode as `Mã hàng`, 
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng` 
FROM __cdc_kfm_kf_inventories_kf_transfer_items i 
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id 
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1' 
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) IN ('2026-07-22', '2026-07-23', '2026-07-24') 
  AND i.status = 5
"""
df = fetch_data_to_df(sql)
print(df[['Mã chuyển hàng', 'transfer_date', 'Ghi chú chuyển']].drop_duplicates())
