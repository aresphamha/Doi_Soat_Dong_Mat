import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql_broad = """
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.status,
    i.note as `Ghi chú chuyển (phiếu)`,
    i.created_by,
    DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) as transfer_date,
    l.description,
    l.reason,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) >= '2026-07-20'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) <= '2026-07-26'
  AND i.created_by != '5f1152906c86b40006155d97'
"""
df = fetch_data_to_df(sql_broad)

print(f"Total non-system rows: {len(df)}")
if not df.empty:
    df.to_csv('rau_broad_test.csv', index=False, encoding='utf-8-sig')
