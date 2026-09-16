import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\Layout Rau.xlsx"
df = pd.read_excel(layout_file, sheet_name='Sheet1')
with open("C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\check_pos_rau.txt", "w", encoding="utf-8") as f:
    f.write(str(df[df['Siêu thị'].str.contains('KFM_HCM_BTA', na=False, case=False)]) + "\n")
    f.write(str(df[df['Siêu thị'].str.contains('KFM_HCM_TDU - 63 Đường Số 3', na=False, case=False)]) + "\n")
