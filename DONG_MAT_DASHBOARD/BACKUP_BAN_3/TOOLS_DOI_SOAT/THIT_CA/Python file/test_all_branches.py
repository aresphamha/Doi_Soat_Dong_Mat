import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql_broad = """
SELECT 
    i.from_branch_id,
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.created_by,
    DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) as transfer_date,
    i.note
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
WHERE DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) >= '2026-07-22'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) <= '2026-07-24'
  AND i.created_by != '5f1152906c86b40006155d97'
  AND i.status = 5
"""
df = fetch_data_to_df(sql_broad)

if not df.empty:
    print(df.groupby('from_branch_id').size())
    df.to_csv('all_branches_test.csv', index=False, encoding='utf-8-sig')
else:
    print("No records found.")
