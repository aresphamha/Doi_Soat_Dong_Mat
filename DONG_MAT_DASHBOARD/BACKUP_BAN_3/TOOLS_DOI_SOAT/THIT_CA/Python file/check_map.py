import sys

with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_map.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'cùng' in line.lower() or 'map' in line.lower() or 'khớp' in line.lower():
            out.write(f"Line {i+1}: {line.strip()}\n")
