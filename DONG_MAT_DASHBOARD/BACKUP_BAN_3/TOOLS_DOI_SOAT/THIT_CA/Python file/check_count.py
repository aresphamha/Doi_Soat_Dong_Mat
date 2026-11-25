import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

date_str = '2026-07-22'

sql = f"""
SELECT COUNT(*)
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
JOIN __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard b 
    ON i.to_branch_id = b.branch_id 
    AND b.branch_code != 'HCM010002'
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
  AND i.status = 5
  AND i.created_by = '5f1152906c86b40006155d97' -- User HT
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_count.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
