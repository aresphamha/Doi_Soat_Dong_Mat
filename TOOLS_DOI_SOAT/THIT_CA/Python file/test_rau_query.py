import pandas as pd
import pymysql
import re

conn = pymysql.connect(
    host='103.140.248.250',
    port=9030,
    user='kfm_scm_tho_nguyen',
    password='oh1dtJwR4ihLGrX4E7bs',
    database='kfm_scm',
)

# 1. MF01 (Shortage)
sql_mf01 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.double_check_code as `Mã thùng`,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    l.unit__name as `ĐVT`,
    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'HCM010002')
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf01 = pd.read_sql(sql_mf01, conn)
df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'] # mock
df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()

# 2. MF02 (Surplus)
sql_mf02 = f"""
SELECT 
    i.to_branch_id,
    i.code as `Mã chuyển hàng`,
    i.double_check_code as `Mã thùng`,
    i.note as `Ghi chú chuyển (phiếu)`,
    i.created_by,
    l.description,
    l.reason,
    l.barcode as `Mã hàng`,
    l.name as `Tên hàng`,
    l.unit__name as `ĐVT`,
    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`,
    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `SL_chuyen_du`
FROM __cdc_kfm_kf_inventories_kf_transfer_items i
INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
WHERE i.from_branch_id IN ('69532cb676e3cd000760a9e1', '6982f5f1d360600007807f7b')
  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '2026-07-22'
  AND i.status = 5
  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
"""
df_mf02 = pd.read_sql(sql_mf02, conn)
df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id']

def extract_date(text):
    if pd.isna(text): return None
    match = re.search(r'(?<!\d)(\d{1,2})[\./-](\d{1,2})(?!\d)', str(text))
    if match:
        try:
            d, m = int(match.group(1)), int(match.group(2))
            return f"2026-{m:02d}-{d:02d}"
        except:
            pass
    return None

df_mf02['Note_Date'] = df_mf02['Ghi chú chuyển (phiếu)'].apply(extract_date)
df_mf02['Desc_Date'] = df_mf02['description'].apply(extract_date)
df_mf02['Final_Date'] = df_mf02['Note_Date'].fillna(df_mf02['Desc_Date'])

mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
mask_exclude = mask_non_sys & (df_mf02['Final_Date'].notna()) & (df_mf02['Final_Date'] != '2026-07-22')
df_mf02 = df_mf02[~mask_exclude].copy()

mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
df_mf02.loc[mask_non_sys, 'SL_du'] = df_mf02.loc[mask_non_sys, 'SL_chuyen_du']

df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()

# Print PT1557339 and PT1554372
print("Shortage PT1554372:")
print(df_shortage[df_shortage['Mã chuyển hàng'] == 'PT1554372'])

print("Surplus PT1557339:")
print(df_surplus[df_surplus['Mã chuyển hàng'] == 'PT1557339'])
