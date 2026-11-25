import sys

with open('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'mapped_branches' in line:
            print(f"Line {i+1}: {line.strip()}")
