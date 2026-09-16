import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\Layout Rau.xlsx"
layout_df = pd.read_excel(layout_file, header=None)
layout_df.columns = ['Vị trí', 'Mã', 'Siêu thị']

store_to_pos = {str(row['Siêu thị']).strip().upper(): int(row['Vị trí']) for _, row in layout_df.iterrows()}

test_store1 = 'KFM_HCM_BTA - 99 Đường Số 7'
test_store2 = 'KFM_HCM_TDU - 63 Đường Số 3'

print(f"Test 1: {test_store1.strip().upper() in store_to_pos}")
print(f"Test 2: {test_store2.strip().upper() in store_to_pos}")
