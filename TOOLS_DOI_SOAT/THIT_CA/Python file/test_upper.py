
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
layout_df = pd.read_excel(layout_file, header=None)
layout_df.columns = ['Vị trí', 'Mã', 'Siêu thị']

store_to_pos = {str(row['Siêu thị']).strip().upper(): int(row['Vị trí']) for _, row in layout_df.iterrows()}

test_store1 = 'KFM_HCM_BTA - 99 Đường Số 7'
test_store2 = 'KFM_HCM_TDU - 63 Đường Số 3'

print(f"Test 1: {test_store1.strip().upper() in store_to_pos}")
print(f"Test 2: {test_store2.strip().upper() in store_to_pos}")
