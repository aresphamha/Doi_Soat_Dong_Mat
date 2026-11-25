import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql_check = """
SELECT 
    i.code as `Mã chuyển hàng`,
    i.status,
    i.note as `Ghi chú chuyển (phiếu)`,
    i.created_by,
    DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) as transfer_date
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
"""
df = fetch_data_to_df(sql_check)
print(f"Total rows on 22nd: {len(df)}")
if not df.empty:
    print(df.to_string())
