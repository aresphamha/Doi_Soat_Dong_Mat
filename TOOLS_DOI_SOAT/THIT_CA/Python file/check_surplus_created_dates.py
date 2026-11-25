import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = f"""
SELECT 
    DATE(DATE_ADD(i._created_at, INTERVAL 7 HOUR)) as created_date,
    COUNT(i._id) as transfer_count,
    COUNT(l.barcode) as item_count
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
LEFT JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
GROUP BY DATE(DATE_ADD(i._created_at, INTERVAL 7 HOUR))
ORDER BY created_date DESC
LIMIT 10
"""
df = fetch_data_to_df(sql)
with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_surplus_created_dates.txt', 'w', encoding='utf-8') as f:
    f.write(str(df))
