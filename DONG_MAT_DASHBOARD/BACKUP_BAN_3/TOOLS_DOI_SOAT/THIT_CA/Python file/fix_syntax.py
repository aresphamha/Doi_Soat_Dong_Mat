file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("ff'", "f'")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed syntax")
