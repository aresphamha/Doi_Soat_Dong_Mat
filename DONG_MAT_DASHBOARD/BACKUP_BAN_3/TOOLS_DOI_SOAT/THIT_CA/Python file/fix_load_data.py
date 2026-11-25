import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the signature of load_data
content = content.replace("def load_data():", "def load_data(url):")
content = content.replace('url_meat_fish = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"', "")
content = content.replace("df = read_csv_with_retry(url_meat_fish)", "df = read_csv_with_retry(url)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed load_data successfully!")
