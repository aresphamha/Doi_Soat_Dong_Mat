import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql1 = """
SELECT COUNT(*) as count FROM __cdc_kfm_kf_inventories_kf_transfer_items i
WHERE i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRCCLCH')
AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
AND i.status = 5
AND i.created_by = '5f1152906c86b40006155d97'
"""

sql2 = """
SELECT COUNT(*) as count FROM __cdc_kfm_kf_inventories_kf_transfer_items i
WHERE i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name LIKE '%RAU CỦ%' AND branch_code != 'HCM010002')
AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
AND i.status = 5
AND i.created_by = '5f1152906c86b40006155d97'
"""

df1 = fetch_data_to_df(sql1)
df2 = fetch_data_to_df(sql2)

with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_surplus.txt', 'w', encoding='utf-8') as f:
    f.write(f"Count with KRCCLCH: {df1['count'].iloc[0] if not df1.empty else 0}\n")
    f.write(f"Count with LIKE RAU CỦ: {df2['count'].iloc[0] if not df2.empty else 0}\n")
