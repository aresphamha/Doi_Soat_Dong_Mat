import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = "SELECT DISTINCT branch_id, branch_code, branch_name FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code LIKE '%KRC%'"
df = fetch_data_to_df(sql)
with open("test_krc2.txt", "w", encoding="utf-8") as f:
    f.write(df.to_string())
