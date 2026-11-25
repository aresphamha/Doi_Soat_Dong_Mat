import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
DESCRIBE __cdc_kfm_kf_inventories_kf_transfer_items
"""
df = fetch_data_to_df(sql)
print("Transfer Items columns:")
print(df)

sql2 = """
DESCRIBE __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items
"""
df2 = fetch_data_to_df(sql2)
print("Line Items columns:")
print(df2)
