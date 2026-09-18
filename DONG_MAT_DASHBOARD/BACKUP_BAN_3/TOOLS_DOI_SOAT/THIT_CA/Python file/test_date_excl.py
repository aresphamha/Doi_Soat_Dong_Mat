import sys
import os
import pandas as pd
import re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT 
    i.to_branch_id, 
    i.code as `Mã chuyển hàng`, 
    i.transfer_date, 
    i.note as `Ghi chú chuyển`, 
    l.barcode as `Mã hàng`, 
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng` 
FROM __cdc_kfm_kf_inventories_kf_transfer_items i 
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id 
WHERE i.from_branch_id = '65430263f3ffc80007137f8f' 
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) IN ('2026-07-22', '2026-07-23', '2026-07-24') 
  AND i.status = 5
"""
df = fetch_data_to_df(sql)

date_str = '2026-07-22'
day_month = date_str[8:10] + '/' + date_str[5:7] # '22/07'
day_month2 = date_str[8:10] + '.' + date_str[5:7] # '22.07'

def has_different_date(note, current_date_str):
    if not isinstance(note, str) or not note:
        return False
    # extract all dd/mm or dd.mm from note
    matches = re.findall(r'(\d{2})[./](\d{2})', note)
    if not matches:
        return False
    current_d = current_date_str[8:10]
    current_m = current_date_str[5:7]
    for d, m in matches:
        if d != current_d or m != current_m:
            return True
    return False

df['exclude'] = df['Ghi chú chuyển'].apply(lambda x: has_different_date(x, date_str))
print("Excluded:")
print(df[df['exclude']][['Mã chuyển hàng', 'transfer_date', 'Ghi chú chuyển']].drop_duplicates())
print("Included:")
print(df[~df['exclude']][['Mã chuyển hàng', 'transfer_date', 'Ghi chú chuyển']].drop_duplicates().head(20))
