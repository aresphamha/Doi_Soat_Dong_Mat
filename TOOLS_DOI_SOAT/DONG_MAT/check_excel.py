import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_excel('Danh sách Siêu thị.xlsx', dtype=str)
print("COLUMNS:", df.columns.tolist())
print(df.head(10).to_string())
