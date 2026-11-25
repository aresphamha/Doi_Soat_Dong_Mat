import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add kho_name, kho_code, icon
old_block = """if khu_vuc == "Thịt Cá":
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

new_block = """if khu_vuc == "Thịt Cá":
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"
    file_layout = "LayoutImportThitCa.xlsx"
    shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
    surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235'"
    kho_name = "Kho Thịt Cá"
    kho_code = "MF01"
    icon = "🥩"
else:
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRC')"
    surplus_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRCCLCH')"
    kho_name = "Kho Rau Củ"
    kho_code = "KRC"
    icon = "🥬"
"""
content = content.replace(old_block, new_block)


# 2. Replace st.set_page_config
content = content.replace(
    'st.set_page_config(page_title="Dashboard Đối Soát Kho Thịt Cá", page_icon="🥩", layout="wide")',
    'st.set_page_config(page_title="Dashboard Đối Soát Kho", page_icon="📊", layout="wide")'
)

# 3. Replace st.title
content = content.replace(
    'st.title("🥩 Báo Cáo Đối Soát Kho Thịt Cá")',
    'st.title(f"{icon} Báo Cáo Đối Soát {kho_name}")'
)

# 4. Replace st.subheader in Daily Tab
content = content.replace(
    'st.subheader("🥩 Đối Soát Chéo Dư - Thiếu Kho Thịt Cá")',
    'st.subheader(f"{icon} Đối Soát Chéo Dư - Thiếu {kho_name}")'
)

# 5. Replace MF01 warnings
content = content.replace(
    'st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho MF01 ngày {selected_date.strftime(\'%d/%m/%Y\')}.")',
    'st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho {kho_code} ngày {selected_date.strftime(\'%d/%m/%Y\')}.")'
)
content = content.replace(
    'st.warning(f"Không tìm thấy dữ liệu nhận dư nào về kho MF02 ngày {selected_date.strftime(\'%d/%m/%Y\')}.")',
    'st.warning(f"Không tìm thấy dữ liệu nhận dư nào về kho nhận dư ngày {selected_date.strftime(\'%d/%m/%Y\')}.")'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced texts!")
