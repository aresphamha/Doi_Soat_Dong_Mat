import sys

with open(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ\2_Spam_Telegram.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "grouped = df_thieu.groupby('ID ST')" in line:
        new_lines.append("    df_thieu = df_thieu[df_thieu['ID ST'].str.contains('NTD|Q50', case=False, na=False)]\n")
        new_lines.append(line)
    else:
        new_lines.append(line)

with open(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ\test_ntd_q50.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
