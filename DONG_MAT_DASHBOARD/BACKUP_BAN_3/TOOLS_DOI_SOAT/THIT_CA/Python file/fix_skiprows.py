import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the Meat Fish URL gid back to 1422896115 which was the original
content = content.replace("gid=1116669931", "gid=1422896115")

# Fix the skiprows logic in read_csv_with_retry
new_logic = """                # Dynamic header finding
                lines = content.split('\\n')
                header_idx = 1
                for idx, line in enumerate(lines[:10]):
                    if 'Số lượng chuyển' in line or 'Mã hàng' in line:
                        header_idx = idx
                        break
                return pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)"""

old_logic = "return pd.read_csv(io.StringIO(content), skiprows=1, dtype=str)"

content = content.replace(old_logic, new_logic)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed skiprows and URL successfully!")
