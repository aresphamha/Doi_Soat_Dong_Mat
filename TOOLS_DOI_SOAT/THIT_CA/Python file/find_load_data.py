file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def load_data" in line:
        start = max(0, i-2)
        end = min(len(lines), i+10)
        print("".join(lines[start:end]))
        break
