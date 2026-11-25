
def find_data_file(filename, fallback_desktop_folder):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát', fallback_desktop_folder, filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return candidates[0]

﻿import sys

with open(r'C:\Users\PC\Desktop\AI\Đối soát\SPAM PHIẾU CHUYỂN\HẬU KIỂM RAU\Spam_Phieu_Hau_Kiem_Rau_Cu.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("    grouped = df_tickets.groupby('Nơi nhận')", "    df_tickets = df_tickets[df_tickets['Nơi nhận'].str.contains('NTD|Q50', case=False, na=False)]\n    grouped = df_tickets.groupby('Nơi nhận')")

with open(r'C:\Users\PC\Desktop\AI\Đối soát\SPAM PHIẾU CHUYỂN\HẬU KIỂM RAU\test_rau_cu.py', 'w', encoding='utf-8') as f:
    f.write(content)
