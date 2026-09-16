import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

path = r'Danh sách Siêu thị.xlsx'
df = pd.read_excel(path, dtype=str)

# Thêm cột Tên viết tắt nếu chưa có
if 'Tên viết tắt' not in df.columns:
    # Tự sinh tên viết tắt mặc định từ ID ST
    df.insert(2, 'Tên viết tắt', df['ID ST'].fillna(''))
    df.to_excel(path, index=False)
    print(f"✅ Đã thêm cột 'Tên viết tắt' vào file Excel.")
    print(f"   → Mở file và điền tên viết tắt cho từng siêu thị!")
else:
    print("ℹ️  Cột 'Tên viết tắt' đã tồn tại.")

print(df[['Tên Siêu thị','ID ST','Tên viết tắt','CHAT ID']].head(10).to_string())
