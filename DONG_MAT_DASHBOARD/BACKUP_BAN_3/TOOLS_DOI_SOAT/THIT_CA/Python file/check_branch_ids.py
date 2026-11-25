import sys
import os

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

# Check recent transfer_items for Rau Cu
sql = """
SELECT DISTINCT i.from_branch_id, COUNT(*) as count 
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
WHERE DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
AND i.status = 5
GROUP BY i.from_branch_id
ORDER BY count DESC
LIMIT 10
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_branch_ids.txt', 'w', encoding='utf-8') as f:
    f.write("from_branch_id counts on 2026-07-22:\n")
    f.write(str(df))
