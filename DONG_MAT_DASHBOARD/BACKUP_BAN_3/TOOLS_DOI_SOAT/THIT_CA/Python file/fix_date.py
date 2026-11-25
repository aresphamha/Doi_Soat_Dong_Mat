import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the date logic in clean_data
old_date_logic = """    # Parse dates strictly (Google Sheets sends dates in MM/DD/YYYY format)
    date_col = 'Ngày' if 'Ngày' in df.columns else ('Ngành' if 'Ngành' in df.columns else 'Ngày')
    
    df['Ngày_parsed'] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
    df['Ngày_str'] = df['Ngày_parsed'].dt.strftime('%d/%m/%Y')
    df['Ngày'] = df['Ngày_parsed']
    df = df[df['Ngày_parsed'].notna()]"""

new_date_logic = """    # Parse dates strictly (Google Sheets sends dates in MM/DD/YYYY format)
    if 'Ngày' in df.columns:
        date_col = 'Ngày'
    elif 'Ngày chuyển hàng' in df.columns:
        date_col = 'Ngày chuyển hàng'
    elif 'Ngành' in df.columns:
        date_col = 'Ngành'
    else:
        date_col = 'Ngày'
    
    df['Ngày_parsed'] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
    df['Ngày_str'] = df['Ngày_parsed'].dt.strftime('%d/%m/%Y')
    df['Ngày'] = df['Ngày_parsed']
    df = df[df['Ngày_parsed'].notna()]"""

content = content.replace(old_date_logic, new_date_logic)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed date logic!")
