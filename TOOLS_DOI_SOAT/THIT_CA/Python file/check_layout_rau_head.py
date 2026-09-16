import pandas as pd

layout_file = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\Layout Rau.xlsx"
df = pd.read_excel(layout_file, header=None)
with open("C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\layout_rau_head.txt", "w", encoding="utf-8") as f:
    f.write(str(df.head()))
