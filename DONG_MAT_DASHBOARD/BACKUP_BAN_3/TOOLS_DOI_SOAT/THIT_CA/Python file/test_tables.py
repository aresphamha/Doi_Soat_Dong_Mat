import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = "SHOW TABLES LIKE '%branch%'"
df = fetch_data_to_df(sql)
print(df)
