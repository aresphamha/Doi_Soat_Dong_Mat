import pandas as pd
import io
import requests

content = requests.get('https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115').content.decode('utf-8')
lines = content.split('\n')
header_idx = 0
for i, line in enumerate(lines):
    if 'Ngày xuất' in line or 'ID ST' in line or 'ST' in line:
        header_idx = i
        break
df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
with open('columns_out.txt', 'w', encoding='utf-8') as f:
    f.write(f"V (21): {df.columns[21]}\n")
    f.write(f"Y (24): {df.columns[24]}\n")
