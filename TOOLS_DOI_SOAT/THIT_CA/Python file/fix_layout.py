import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the broken kho_name assignment
content = content.replace('kho_name = "{kho_name}"', 'kho_name = "Kho Thịt Cá"')

# Find the block and remove it
block_regex = re.compile(
    r'(st\.sidebar\.title\("Cài đặt chung"\)\n'
    r'khu_vuc = st\.sidebar\.radio\("Khu vực đối soát:", \["Thịt Cá", "Rau Củ Quả"\]\)\n'
    r'\n'
    r'if khu_vuc == "Thịt Cá":\n.*?'
    r'    icon = "🥬"\n)',
    re.DOTALL
)

match = block_regex.search(content)
if match:
    block = match.group(1)
    # Remove it from its current position
    content = content.replace(block, "")
    
    # Insert it right after st.set_page_config
    insert_after = 'st.set_page_config(page_title="Dashboard Đối Soát Kho", page_icon="📊", layout="wide")'
    new_insertion = insert_after + "\n\n" + block
    content = content.replace(insert_after, new_insertion)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Moved sidebar config to the top successfully.")
else:
    print("Could not find the block to move!")
