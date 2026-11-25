import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = "SELECT _id, code, name FROM __cdc_kfm_ec9d24ab_33bc7bbc_L3___branch WHERE code LIKE 'KRC%'"
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_branch_table.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
