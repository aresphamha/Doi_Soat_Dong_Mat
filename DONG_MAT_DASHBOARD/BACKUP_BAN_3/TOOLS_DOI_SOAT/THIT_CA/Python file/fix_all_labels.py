import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace hardcoded labels with dynamic f-strings
content = content.replace("Tổng kho Thịt Cá", "{kho_name}") # Note: f"Tổng {kho_name}"
content = content.replace("T?ng kho Th?t C", "{kho_name}")

content = content.replace("Kho thịt cá", "{kho_name.lower()}")
content = content.replace("kho thịt cá", "{kho_name.lower()}")
content = content.replace("Kho Thịt Cá", "{kho_name}")
content = content.replace("KHO THỊT CÁ", "{kho_name.upper()}")
content = content.replace("KHO THỊT CA", "{kho_name.upper()}")

# specifically fix the f-strings
# We need to make sure we don't break existing f-strings or non-f-strings.
# A simple way for the labels in dictionary mappings:
content = content.replace("'SL đã xác nhận được trả {kho_name.lower()}'", "f'SL đã xác nhận được trả {kho_name.lower()}'")
content = content.replace("'Giá trị đã trả {kho_name} (VND)'", "f'Giá trị đã trả {kho_name} (VND)'")

# In the create_pivot function and others, some strings are dict keys.
# Let's just use string replace.
def wrap_fstring(text):
    # This is complex, better to use regex for specific lines
    pass

# Let's do regex for the specific lines seen in the grep output
# 1. line 166: ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', 'Tổng kho Thịt Cá', 'Tổng chưa xác định']
content = content.replace("'Tổng kho Thịt Cá'", "f'Tổng {kho_name.lower()}'")

# 2. line 182: col_kho_list = [c for c in df.columns if 'KHO THỊT CA' in c.upper() or ...
content = content.replace("'KHO THỊT CA' in c.upper()", "kho_name.upper() in c.upper()")

# 3. line 196: col_total_kho_list = [c for c in df.columns if 'Tổng kho Thịt Cá' in c or 'Tổng kho thịt cá' in c or 'Tổng kho rau' in c.lower()]
content = content.replace("'Tổng kho Thịt Cá' in c or 'Tổng kho thịt cá' in c", "f'Tổng {kho_name.lower()}' in c.lower()")

# 4. line 204: df['LyDo_Kho'].str.contains('kho thịt cá')
content = content.replace("df['LyDo_Kho'].str.contains('kho thịt cá')", "df['LyDo_Kho'].str.contains(kho_name.lower())")

# 5. line 444, 470, 567, 571, 594, 617: f-strings that have "Kho thịt cá", "kho thịt cá"
# Since they are already f-strings, we can just put {kho_name.lower()} inside them.
# The previous replace already did this: "kho thịt cá" -> "{kho_name.lower()}"
# Let's verify that replacing "Kho thịt cá" with "{kho_name.lower()}" works in f-strings.
# Yes, because the f-string will evaluate {kho_name.lower()}.

# 6. line 682, 690, 694, 697, 709, 712, 716, 719, 735, 736, 740, 743, 750, 752, 755, 758
# These use 'SL KHO THỊT CA' or 'GT KHO THỊT CA'
content = content.replace("'SL KHO THỊT CA'", "f'SL {kho_name.upper()}'")
content = content.replace("'GT KHO THỊT CA'", "f'GT {kho_name.upper()}'")

# In lambdas like `lambda r: f"{(r.get('Chưa xác nhận', 0) / r[f'SL {kho_name.upper()}']` - wait, python lambdas can use f-strings as dict keys? Yes: `r[f'SL {kho_name.upper()}']`

# 7. line 885, 892, 908, 915, 942, 1039, 1050, 1088 (Dictionary mapping renames)
content = content.replace("'SL đã xác nhận được trả {kho_name.lower()}'", "f'SL đã xác nhận được trả {kho_name.lower()}'")
content = content.replace("'Giá trị đã trả {kho_name} (VND)'", "f'Giá trị đã trả {kho_name} (VND)'")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated all labels")
