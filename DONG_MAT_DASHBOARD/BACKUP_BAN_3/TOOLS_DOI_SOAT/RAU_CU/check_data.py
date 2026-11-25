import sys, requests, pandas as pd, os
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/spreadsheets/d/1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM/export?format=xlsx'
res = requests.get(url, timeout=30)
with open('tmp_c.xlsx', 'wb') as f:
    f.write(res.content)

xl  = pd.ExcelFile('tmp_c.xlsx')
sheet = [s for s in xl.sheet_names if 'Ch' in s][0]
df  = xl.parse(sheet, header=2, dtype=str)

col_ngay = 'Ngày chuyển hàng'
df[col_ngay] = pd.to_datetime(df[col_ngay], errors='coerce')
latest = df[col_ngay].dropna().max()
df2 = df[df[col_ngay] == latest]

print("Ngay:", latest.strftime('%d.%m.%Y'))
print("Tong rows:", len(df2))

# Loc DC GIAO THIEU
df3 = df2[df2['Lỗi'].astype(str).str.strip().str.upper() == 'DC GIAO THIẾU']
st_dc = sorted([s for s in df3['ID ST'].dropna().str.strip().unique() if s and s != 'nan'])
print("Sau loc DC GIAO THIEU:", len(st_dc), "ST")
print("DS:", st_dc)

try: os.remove('tmp_c.xlsx')
except: pass
