import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = f"""
SELECT DISTINCT branch_code, branch_name 
FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard 
WHERE branch_id = '69532cb676e3cd000760a9e1'
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_branch_code.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
