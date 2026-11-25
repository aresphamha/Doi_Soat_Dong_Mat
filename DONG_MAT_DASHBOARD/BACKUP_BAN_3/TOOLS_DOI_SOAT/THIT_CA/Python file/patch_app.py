import re
import os

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update load_data signature and url
content = re.sub(
    r"@st\.cache_data\(ttl=3600\)\s*def load_data\(\):\s*url = \"[^\"]+\"\s*df = pd\.read_csv\(url, on_bad_lines='skip'\)",
    "@st.cache_data(ttl=3600)\ndef load_data(url):\n    df = pd.read_csv(url, on_bad_lines='skip')",
    content
)

# 2. Update col_kho logic in load_data
content = re.sub(
    r"col_kho = \[c for c in df\.columns if 'KHO THỊT CÁ' in c or 'kho thịt cá' in c or 'Kho thịt cá' in c or 'KHO TH' in c\]\[0\]\n\s*df\['LyDo_Kho'\] = df\[col_kho\]\.astype\(str\)\.str\.strip\(\)\.str\.lower\(\)",
    "col_kho_list = [c for c in df.columns if 'KHO THỊT CÁ' in c.upper() or 'KHO TH' in c.upper() or 'KHO RAU' in c.upper() or 'KRC' in c.upper()]\n    col_kho = col_kho_list[0] if col_kho_list else None\n    if col_kho:\n        df['LyDo_Kho'] = df[col_kho].astype(str).str.strip().str.lower()\n    else:\n        df['LyDo_Kho'] = ''",
    content
)

# 3. Update Kho_Rau logic in load_data
content = re.sub(
    r"df\['Kho_Rau'\] = np\.where\(df\['LyDo_Kho'\]\.str\.contains\('kho thịt cá'\), df\['Qty_P'\], 0\)",
    "df['Kho_Rau'] = np.where(df['LyDo_Kho'].str.contains('kho thịt cá') | df['LyDo_Kho'].str.contains('kho rau') | df['LyDo_Kho'].str.contains('krc'), df['Qty_P'], 0)",
    content
)

# 4. Update col_total_kho logic in load_data
content = re.sub(
    r"col_total_kho = \[c for c in df\.columns if 'Tổng kho Thịt Cá' in c or 'Tổng kho thịt cá' in c\]\[0\]",
    "col_total_kho_list = [c for c in df.columns if 'Tổng kho Thịt Cá' in c or 'Tổng kho thịt cá' in c or 'Tổng kho rau' in c.lower()]\n    col_total_kho = col_total_kho_list[0] if col_total_kho_list else None",
    content
)

# 4b. Update Tổng kho rau assignment
content = re.sub(
    r"df\['Tổng kho rau'\] = df\[col_total_kho\]\.apply\(clean_val\)",
    "if col_total_kho:\n        df['Tổng kho rau'] = df[col_total_kho].apply(clean_val)\n    else:\n        df['Tổng kho rau'] = 0.0",
    content
)


# 5. Remove original df_all = load_data() try-except
content = re.sub(
    r"try:\s*df_all = load_data\(\)\s*st\.success\(\"Tải dữ liệu từ Google Sheets thành công!\"\)\s*except Exception as e:\s*st\.error\(f\"Lỗi tải dữ liệu: \{e\}\"\)\s*st\.stop\(\)\n",
    "",
    content
)

# 6. Insert sidebar and dynamic variables before tabs
tabs_original = """tabs = st.tabs([
    "Đối Soát Chéo Dư - Thiếu Kho Thịt Cá",
    "Ghi Nhận Lỗi Liên Siêu Thị (Thịt Cá)",
    "Báo cáo tổng hợp dư thiếu (Thịt Cá)",
    "Lịch sử phân tích",
    "Xuất báo cáo tự động"
])"""
tabs_new = """st.sidebar.title("Cài đặt chung")
khu_vuc = st.sidebar.radio("Khu vực đối soát:", ["Thịt Cá", "Rau Củ Quả"])

if khu_vuc == "Thịt Cá":
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1116669931"
    file_layout = "LayoutImportThitCa.xlsx"
    shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
    surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235'"
else:
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRC')"
    surplus_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'KRCCLCH')"

try:
    df_all = load_data(data_url)
    st.sidebar.success(f"Tải dữ liệu từ Google Sheets thành công!")
except Exception as e:
    st.error(f"Lỗi tải dữ liệu Google Sheets: {e}")
    st.stop()

tabs = st.tabs([
    f"Đối Soát Chéo Dư - Thiếu ({khu_vuc})",
    f"Ghi Nhận Lỗi Liên Siêu Thị ({khu_vuc})",
    f"Báo cáo tổng hợp dư thiếu ({khu_vuc})",
    "Lịch sử phân tích",
    "Xuất báo cáo tự động"
])"""
content = content.replace(tabs_original, tabs_new)

# 7. Update layout file logic inside the tab (around line 1144)
content = content.replace(
    'file_layout = "LayoutImportThitCa.xlsx"',
    '# file_layout already set based on khu_vuc'
)


# 8. Update SQL shortage logic
content = content.replace(
    "WHERE i.from_branch_id = '6a34ed56f23028000774139f' -- MF01",
    "WHERE {shortage_condition}"
)
content = content.replace(
    "sql_mf01 = f\"\"\"",
    "sql_mf01 = f\"\"\""
)

# 9. Update SQL surplus logic
content = content.replace(
    "WHERE i.from_branch_id = '6a34ed8d6607ba000703e235' -- MF02",
    "WHERE {surplus_condition}"
)

# 10. Fix df_all naming (since I changed it, I should verify)
# Everything seems good.

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated app_thit_ca.py successfully.")
