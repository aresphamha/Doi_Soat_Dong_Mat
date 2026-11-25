import sys
import os
import pandas as pd
import re

sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import fetch_data_to_df

date_str = '2026-07-22'

sql_mf02 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.double_check_code as `Mã thùng`,
    i.note as `Ghi chú chuyển (phiếu)`,
    i.created_by,
    DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) as transfer_date,
    l.description,
    l.reason,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    l.unit__name as `ĐVT`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id = '69532cb676e3cd000760a9e1'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) >= '2026-07-22'
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) <= '2026-07-24'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df = fetch_data_to_df(sql_mf02)

target_parts = date_str.split('-')
target_m = int(target_parts[1])
target_d = int(target_parts[2])

def belongs_to_target_date(row):
    t_date = str(row['transfer_date'])
    is_system = str(row.get('created_by', '')) == '5f1152906c86b40006155d97'
    
    if is_system:
        return t_date == date_str
        
    notes = [str(row.get('Ghi chú chuyển (phiếu)', '')), str(row.get('description', '')), str(row.get('reason', ''))]
    combined_note = " ".join([n for n in notes if n and str(n).strip().lower() != 'nan' and str(n).strip().lower() != 'none'])
    
    matches = re.findall(r'(?<!\d)(\d{1,2})[./-](\d{1,2})(?!\d)', combined_note)
    if matches:
        # Check if ANY of the dates in the note match the target date
        for d_str, m_str in matches:
            try:
                d = int(d_str)
                m = int(m_str)
                if d == target_d and m == target_m:
                    return True
            except:
                pass
        # It has dates, but none match the target date
        # Does it match the transfer_date? 
        # Actually if it has dates and none match target_date, it belongs to some other date, so False
        return False
    else:
        # No date in note, rely on transfer_date
        return t_date == date_str

df_filtered = df[df.apply(belongs_to_target_date, axis=1)]
df_surplus = df_filtered[df_filtered['SL_du'].round(5) > 0.0]

df_all_surplus = df[df['SL_du'].round(5) > 0.0]
print(f"Total surplus rows fetched: {len(df)}")
print(f"Total surplus rows with SL_du > 0: {len(df_all_surplus)}")
df_all_surplus.to_csv('rau_surplus_test.csv', index=False, encoding='utf-8-sig')
