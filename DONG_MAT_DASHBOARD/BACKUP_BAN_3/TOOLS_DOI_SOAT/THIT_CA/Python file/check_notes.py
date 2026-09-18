import sys
import os
import pandas as pd

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

sql = """
SELECT 
    i.note as i_note,
    l.description as l_desc,
    l.reason as l_reason
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
  AND i.created_by != '5f1152906c86b40006155d97'
  AND i.status = 5
LIMIT 50
"""
df = fetch_data_to_df(sql)
df.to_csv('notes_output.csv', encoding='utf-8-sig', index=False)
