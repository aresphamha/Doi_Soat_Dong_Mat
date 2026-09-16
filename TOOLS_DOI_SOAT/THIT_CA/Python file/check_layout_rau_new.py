import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\Layout Rau.xlsx"
df = pd.read_excel(layout_file, sheet_name='Sheet1')

with open("C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\layout_rau_new_check.txt", "w", encoding="utf-8") as f:
    f.write(f"Columns: {df.columns.tolist()}\n")
    f.write("Head:\n")
    f.write(str(df.head()))
