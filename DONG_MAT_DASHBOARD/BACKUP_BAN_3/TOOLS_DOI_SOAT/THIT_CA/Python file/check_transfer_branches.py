import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT code, dst_branch_code, dst_branch_id, SUM(quantity) as total_qty
FROM __cdc_kfm_62a69022_b94514be_branch___transfer_branches
WHERE dst_branch_code = 'KRCCLCH'
AND receipt_date = '2026-07-22'
GROUP BY code, dst_branch_code, dst_branch_id
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_transfer_branches.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
