
def find_data_file(filename, default_dir=None):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ', filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(cur_dir, filename)

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
