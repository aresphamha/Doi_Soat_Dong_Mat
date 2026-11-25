import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql_branches = """
SELECT _id, name 
FROM __cdc_kfm_6dbff9a1_5409395f_L1_branches
WHERE name LIKE '%Rau%' OR name LIKE '%RAU%' OR name LIKE '%rau%' OR name LIKE '%chênh lệch%'
"""
df = fetch_data_to_df(sql_branches)
print(df.to_string())
