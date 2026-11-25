import sys
import os

# Add directory to path to import app_thit_ca's fetch_data_to_df
sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = "SELECT _id as branch_id, code as branch_code, name as branch_name FROM __cdc_kfm_ec9d24ab_33bc7bbc_L2___branches WHERE code IN ('KRC', 'KRCCLCH')"
try:
    df = fetch_data_to_df(sql)
    print(df)
except Exception as e:
    print(f"Lỗi: {e}")
