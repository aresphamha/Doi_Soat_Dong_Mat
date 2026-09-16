import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT code, from_branch_id, to_branch_id
FROM __cdc_kfm_kf_inventories_kf_transfer_items
WHERE code = 'PT1557736'
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_pt.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
