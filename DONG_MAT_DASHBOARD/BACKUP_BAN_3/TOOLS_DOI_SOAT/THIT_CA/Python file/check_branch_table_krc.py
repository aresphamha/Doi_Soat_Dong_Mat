import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT code, name
FROM __cdc_kfm_62a69022_b94514be_branch___branch
WHERE code LIKE 'KRC%'
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_branch_table_krc.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
