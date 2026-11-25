
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

import os
import pandas as pd
from telethon.sync import TelegramClient
import asyncio
import re

api_id = 31209455
api_hash = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
session_name = 'user_session'

print("==================================================")
print("TOOL TỰ ĐỘNG LẤY CHAT ID GROUP SIÊU THỊ TỪ TELEGRAM")
print("==================================================")
print("Đang tải file Danh sách Siêu thị để map tự động...")

# 1. Load Store list
df_stores = pd.DataFrame(columns=['Tên Siêu thị', 'ID ST'])
try:
    df_stores = pd.read_excel(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT\Danh sách Siêu thị.xlsx', dtype=str)
    # clean up names
    df_stores['Tên Siêu thị'] = df_stores['Tên Siêu thị'].fillna('').str.strip()
    df_stores['ID ST'] = df_stores['ID ST'].fillna('').str.strip()
    print(f"Đã tải {len(df_stores)} dòng siêu thị.")
except Exception as e:
    print("Lỗi không đọc được file Danh sách Siêu thị.xlsx:", e)

def find_id_st(group_name):
    # Try to find ID ST by matching Tên Siêu thị
    g_name_lower = group_name.lower()
    for _, row in df_stores.iterrows():
        ten_st = row['Tên Siêu thị'].lower()
        if ten_st and ten_st in g_name_lower:
            return row['ID ST']
        
        # Try to find the exact ID ST word in the group name (e.g. A101)
        id_st = row['ID ST'].lower()
        if id_st and len(id_st) >= 3:
            # Check as whole word
            if re.search(r'\b' + re.escape(id_st) + r'\b', g_name_lower):
                return row['ID ST']
    return ""

def extract_kho(group_name):
    g_name_upper = group_name.upper()
    kho_list = []
    if "DC" in g_name_upper: kho_list.append("DC")
    if "ABA" in g_name_upper: kho_list.append("ABA")
    if "ĐÔNG MÁT" in g_name_upper or "DONG MAT" in g_name_upper: kho_list.append("ĐÔNG MÁT")
    if "KRC" in g_name_upper: kho_list.append("KRC")
    
    return ", ".join(kho_list) if kho_list else ""

async def main():
    async with TelegramClient(session_name, api_id, api_hash) as client:
        print("Đăng nhập thành công!")
        print("Đang quét toàn bộ danh bạ các group...")
        dialogs = await client.get_dialogs()
        
        data = []
        for d in dialogs:
            if d.is_group or d.is_channel:
                g_name = d.title
                id_st = find_id_st(g_name)
                kho = extract_kho(g_name)
                
                # Only save if we can map it to an ID ST, or you can save all groups.
                # Here we save ALL groups but populate the columns if matched.
                data.append({
                    'TÊN GROUP': g_name,
                    'CHAT ID': d.id,
                    'ID ST TƯƠNG ỨNG': id_st,
                    'THÔNG TIN KHO': kho
                })
        
        # Sort so that mapped ones are at the top
        df = pd.DataFrame(data)
        df.sort_values(by=['ID ST TƯƠNG ỨNG', 'TÊN GROUP'], ascending=[False, True], inplace=True)
        
        out_file = 'Danh_Sach_Chat_ID_Siêu_Thị_Auto_Map.xlsx'
        df.to_excel(out_file, index=False)
        print(f"==================================================")
        print(f"XONG! Đã quét được {len(df)} groups.")
        mapped_count = len(df[df['ID ST TƯƠNG ỨNG'] != ''])
        print(f"Đã Auto-Map thành công {mapped_count} Siêu thị!")
        print(f"Kết quả đã được lưu tại file: {out_file}")
        print(f"==================================================")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    input("Bấm Enter để thoát...")
