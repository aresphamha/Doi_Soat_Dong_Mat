import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix shortage_condition and surplus_condition not being defined
block_to_replace = """if khu_vuc == "Thịt Cá":
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"
    file_layout = "LayoutImportThitCa.xlsx"
else:
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
"""

new_block = """if khu_vuc == "Thịt Cá":
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"
    file_layout = "LayoutImportThitCa.xlsx"
    shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
    surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235'"
else:
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRC')"
    surplus_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRCCLCH')"
"""
content = content.replace(block_to_replace, new_block)


# Fix the 'Ngày' KeyError
ngay_logic_old = "df['Ngày_str'] = pd.to_datetime(df['Ngày'], format='%d/%m/%Y', errors='coerce').dt.strftime('%d/%m/%Y')"
ngay_logic_new = """if 'Ngày' in df.columns:
        df['Ngày_str'] = pd.to_datetime(df['Ngày'], format='%d/%m/%Y', errors='coerce').dt.strftime('%d/%m/%Y')
    elif 'Ngày chuyển hàng' in df.columns:
        df['Ngày_str'] = pd.to_datetime(df['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce').dt.strftime('%d/%m/%Y')
    else:
        df['Ngày_str'] = ''"""
content = content.replace(ngay_logic_old, ngay_logic_new)

# Wait, the date format in Rau Cu Qua is "06/25/2026", which is %m/%d/%Y.

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed both issues!")
