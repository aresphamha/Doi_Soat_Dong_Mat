import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_name LIKE '%branch%'
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_tables.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
