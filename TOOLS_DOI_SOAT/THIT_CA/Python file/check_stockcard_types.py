import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT type, COUNT(*) as count 
FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard 
WHERE branch_code = 'HCM010002' 
AND date = '2026-07-22'
GROUP BY type
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_stockcard_types.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
