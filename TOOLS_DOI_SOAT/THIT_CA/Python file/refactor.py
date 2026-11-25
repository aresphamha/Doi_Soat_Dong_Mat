import os

with open('app_thit_ca.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

imports_and_db = []
common_setup = []
rest_of_code = []

state = 0
for line in lines:
    if state == 0:
        if 'st.set_page_config' in line:
            common_setup.append(line)
            state = 1
        else:
            imports_and_db.append(line)
    elif state == 1:
        if 'if khu_vuc == "Thịt Cá":' in line:
            state = 2
            # Skip the radio button setup and this if block because we will manually create it
            # But wait, there is `st.sidebar.title("Cài đặt chung")` before the if.
            # We need to extract that too.
        else:
            common_setup.append(line)
    elif state == 2:
        rest_of_code.append(line)

# Wait, the `rest_of_code` starts with the inside of `if khu_vuc == "Thịt Cá":`.
# It's better to just use string replacement.

with open('app_thit_ca.py', 'r', encoding='utf-8') as f:
    full_text = f.read()

# 1. Extract the shared prefix
prefix_end = full_text.find('if khu_vuc == "Thịt Cá":')
prefix = full_text[:prefix_end]

# 2. Extract the body
body = full_text[prefix_end:]

# 3. Create Thit Ca body
# The body currently has:
# if khu_vuc == "Thịt Cá":
#     ...
# else:
#     ...
# def get_excel_bytes(df):
# ...

# We want to replace the `if/else` block with just the Thit Ca variables.
thit_ca_vars = """
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"
    file_layout = "LayoutImportThitCa.xlsx"
    shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
    surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235' AND i.created_by = '5f1152906c86b40006155d97'"
    kho_name = "Kho Thịt Cá"
    kho_code = "MF01"
    icon = "🥩"
    khu_vuc = "Thịt Cá"
"""

rau_cu_vars = """
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'HCM010002')"
    surplus_condition = "i.from_branch_id = '6982f5f1d360600007807f7b'"
    kho_name = "Kho Rau Củ"
    kho_code = "KRC"
    icon = "🥬"
    khu_vuc = "Rau Củ Quả"
"""

# Strip out the if/else block from body
func_start = body.find('def get_excel_bytes(df):')
body_funcs_and_ui = body[func_start:]

def create_func_block(func_name, vars_block, code_block):
    # Rename load_data to avoid cache conflicts
    cb = code_block.replace('@st.cache_data(ttl=600)\ndef load_data(url):', f'@st.cache_data(ttl=600)\ndef load_data_{func_name}(url):')
    cb = cb.replace('df_all = load_data(data_url)', f'df_all = load_data_{func_name}(data_url)')
    
    # We will wrap the entire block in a function, so we need to indent it
    lines = cb.split('\n')
    indented_lines = ['    ' + line for line in lines]
    
    return f"def render_{func_name}():\n{vars_block}\n" + "\n".join(indented_lines) + "\n"

thit_ca_block = create_func_block("thit_ca", thit_ca_vars, body_funcs_and_ui)
rau_cu_block = create_func_block("rau_cu", rau_cu_vars, body_funcs_and_ui)

router = """
if khu_vuc_selected == "Thịt Cá":
    render_thit_ca()
else:
    render_rau_cu()
"""

final_code = prefix.replace('khu_vuc = st.sidebar.radio', 'khu_vuc_selected = st.sidebar.radio') + "\n" + thit_ca_block + "\n" + rau_cu_block + "\n" + router

with open('app_thit_ca_split.py', 'w', encoding='utf-8') as f:
    f.write(final_code)

print("Created app_thit_ca_split.py")
