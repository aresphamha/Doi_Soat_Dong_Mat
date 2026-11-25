
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

import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\Layout Rau.xlsx"
df = pd.read_excel(layout_file, header=None)
df.columns = ['Vị trí', 'Mã', 'Siêu thị']

with open("C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\layout_rau_content.txt", "w", encoding="utf-8") as f:
    f.write("Layout samples:\n")
    f.write("\n".join(df['Siêu thị'].head(10).astype(str).tolist()) + "\n")
    f.write(f"KFM_HCM_BTA in layout? {df['Siêu thị'].str.contains('KFM_HCM_BTA - 99 Đường Số 7', case=False, na=False).any()}\n")
    f.write(f"KFM_HCM_TDU in layout? {df['Siêu thị'].str.contains('KFM_HCM_TDU - 63 Đường Số 3', case=False, na=False).any()}\n")
