import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT b.branch_code, b.branch_name, COUNT(*) as count 
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
JOIN __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard b ON i.from_branch_id = b.branch_id
WHERE b.branch_name LIKE '%RAU CỦ%' AND b.branch_code != 'HCM010002'
AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
AND i.status = 5
AND i.created_by = '5f1152906c86b40006155d97'
GROUP BY b.branch_code, b.branch_name
"""

df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_surplus_branches.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
