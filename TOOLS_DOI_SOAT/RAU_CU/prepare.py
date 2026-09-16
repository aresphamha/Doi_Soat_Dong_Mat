import sys

with open(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ\2_Spam_Telegram.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("    grouped = df_thieu.groupby('ID ST')", "    df_thieu = df_thieu[df_thieu['ID ST'].str.contains('NTD|Q50', case=False, na=False)]\n    grouped = df_thieu.groupby('ID ST')")

with open(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ\test_rau_cu.py', 'w', encoding='utf-8') as f:
    f.write(content)
