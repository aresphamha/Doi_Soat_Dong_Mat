import pandas as pd
df = pd.read_excel('Danh sách Siêu thị.xlsx', dtype=str)
df = df[df['CHAT ID'].notna() & (df['CHAT ID'] != 'nan')]

counts = df['ID ST'].value_counts()
duplicates = counts[counts > 1].index.tolist()

if duplicates:
    print('CÁC SIÊU THỊ BỊ TRÙNG LẶP CHAT ID (CÓ NHIỀU DÒNG):')
    for d in duplicates:
        rows = df[df['ID ST'] == d]
        for _, row in rows.iterrows():
            print(f"- {row['ID ST']}: {row['CHAT ID']} ({row['Tên Siêu thị']})")
else:
    print('Không có siêu thị nào bị trùng lặp Chat ID.')

short_ids = df[~df['CHAT ID'].str.startswith('-100')]
if not short_ids.empty:
    print('\nCÁC SIÊU THỊ CÓ CHAT ID NGẮN (CÓ THỂ LÀ GROUP THƯỜNG HOẶC GROUP CŨ/ABA/KRC):')
    for _, row in short_ids.iterrows():
        print(f"- {row['ID ST']}: {row['CHAT ID']} ({row['Tên Siêu thị']})")
