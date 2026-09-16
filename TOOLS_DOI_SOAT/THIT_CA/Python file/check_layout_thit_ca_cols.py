import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\LayoutImportThitCa.xlsx"
df = pd.read_excel(layout_file)
with open("C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\layout_thit_ca_cols.txt", "w", encoding="utf-8") as f:
    f.write(str(df.columns.tolist()))
