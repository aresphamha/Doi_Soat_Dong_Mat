
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

﻿import asyncio
from telethon import TelegramClient
import pandas as pd
import requests
import dataframe_image as dfi
import os
import sys

api_id = '28938971'
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'
url_send_photo = f'https://api.telegram.org/bot{bot_token}/sendPhoto'

async def get_tags_for_group(client, chat_id):
    tags = []
    try:
        participants = await client.get_participants(chat_id)
        for p in participants:
            name = ""
            if p.first_name: name += p.first_name
            if p.last_name: name += " " + p.last_name
            name_upper = name.upper()
            if ' TC' in name_upper or '-TC' in name_upper or ' SM' in name_upper or '-SM' in name_upper or ' GSM' in name_upper or '-GSM' in name_upper:
                tags.append(f"[{name}](tg://user?id={p.id})")
    except Exception as e:
        pass
    return " ".join(tags) if tags else "@SM @TC @GSM"

async def main():
    current_dir = r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ'
    master_excel = os.path.join(current_dir, 'Danh sách Siêu thị.xlsx')
    df_chat = pd.read_excel(master_excel, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['ID ST TƯƠNG ỨNG'], df_chat['CHAT ID']))

    url = 'https://docs.google.com/spreadsheets/d/1vPHHrZf5prEgE_09j_RbQQC1gNWhUmV0Q6aah6Z3mjQ/export?format=xlsx'
    res = requests.get(url)
    with open('temp_google_sheet_rau_cu.xlsx', 'wb') as f:
        f.write(res.content)
        
    xl = pd.ExcelFile('temp_google_sheet_rau_cu.xlsx')
    sheet_name = [s for s in xl.sheet_names if 'Chênh lệch' in s or 'ST' in s or 'Ch' in s][0]
    df_thieu = xl.parse(sheet_name, header=2)
    
    col_ngay = 'Ngày' if 'Ngày' in df_thieu.columns else 'Ngày chuyển hàng'
    df_thieu[col_ngay] = pd.to_datetime(df_thieu[col_ngay], errors='coerce')
    latest_date = df_thieu[col_ngay].dropna().max()
    date_str = latest_date.strftime('%d.%m') if pd.notna(latest_date) else 'Hôm nay'
    df_thieu = df_thieu[df_thieu[col_ngay] == latest_date]

    if 'Lỗi' in df_thieu.columns:
        df_thieu = df_thieu[df_thieu['Lỗi'].astype(str).str.strip().str.upper() == 'DC GIAO THIẾU']

    df_thieu['ID ST'] = df_thieu['ID ST'].astype(str).str.strip()
    
    # FILTER FOR OPS, A107, A151 ONLY
    df_thieu = df_thieu[df_thieu['ID ST'].isin(['OPS', 'A107', 'A151'])]
    
    grouped = df_thieu.groupby('ID ST')
    
    session_path = os.path.join(current_dir, '..', 'ĐÔNG MÁT', 'user_session')
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

    success_count = 0
    fail_count = 0

    for id_st, group in grouped:
        if id_st not in chat_map:
            print(f"[LỖI] ID {id_st} không có trong chat_map!")
            fail_count += 1
            continue
            
        chat_id_str = str(chat_map[id_st]).replace('.0', '').strip()
        chat_id = int(chat_id_str)
        
        tag_text = await get_tags_for_group(client, chat_id)
        
        caption_text = f'''**RAU CỦ QUẢ**\n{date_str}\nST kiểm tra lại giúp Hà sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng\n\n- Với mã hàng nhận thiếu item(nếu có chụp hình QUÊN up trong phiếu) : cung cấp hình ảnh SL thực nhận \n\n*NOTE*:\n Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM\n \n{tag_text}'''

        cols_to_keep = ['ID ST', 'Mã hàng', 'Tên Hàng', 'ĐVT', 'Số lượng chuyển']
        cols_exist = [c for c in cols_to_keep if c in group.columns]
        df_slice = group[cols_exist].reset_index(drop=True)
        img_path = f"temp_{id_st}.png"
        
        styled = df_slice.style.set_properties(**{
            'background-color': '#ffffff',
            'color': 'black',
            'border-color': 'gray',
            'border-style': 'solid',
            'border-width': '1px',
            'text-align': 'center',
            'padding': '10px 20px'
        }).set_table_styles([{
            'selector': 'th',
            'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('border', '1px solid gray'), ('padding', '10px 20px')]
        }])
        dfi.export(styled, img_path, table_conversion="matplotlib", dpi=200)
            
        with open(img_path, 'rb') as f:
            res = requests.post(url_send_photo, files={'photo': f}, data={
                'chat_id': chat_id, 'caption': caption_text, 'parse_mode': 'Markdown'
            })
            if res.status_code == 200:
                print(f"[THÀNH CÔNG] Đã tag tên & gửi ảnh RAU CỦ QUẢ cho ST {id_st}.")
                success_count += 1
            else:
                print(f"[LỖI] Không thể gửi RAU CỦ QUẢ cho ST {id_st}: {res.text}")
                fail_count += 1
        
        if os.path.exists(img_path): os.remove(img_path)

    await client.disconnect()
    xl.close()
    if os.path.exists('temp_google_sheet_rau_cu.xlsx'): os.remove('temp_google_sheet_rau_cu.xlsx')
    print(f"DONE. Success: {success_count}, Fail: {fail_count}")

if __name__ == '__main__':
    asyncio.run(main())
