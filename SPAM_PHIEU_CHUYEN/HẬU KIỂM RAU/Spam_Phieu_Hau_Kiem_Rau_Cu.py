
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

import asyncio
from telethon import TelegramClient
import pandas as pd
import requests
import dataframe_image as dfi
import os
import sys
import pymysql
from datetime import datetime
import pytz

api_id = '28938971'
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'
url_send_photo = f'https://api.telegram.org/bot{bot_token}/sendPhoto'

def get_connection():
    return pymysql.connect(
        host='103.140.248.250',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm'
    )

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
    print("==================================================")
    print("TOOL SPAM TELEGRAM - PHIẾU CẦN HẬU KIỂM RAU CỦ")
    print("==================================================")
    
    print("Đang đọc danh sách Chat ID từ thư mục RAU CỦ...")
    try:
        df_chat = pd.read_excel(find_data_file('Danh sách Siêu thị.xlsx', 'RAU CỦ'), dtype=str)
        df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
        chat_map = dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID']))
    except Exception as e:
        print(f"[LỖI] Không thể đọc file Danh sách Siêu thị.xlsx: {e}")
        input("Bấm Enter để thoát...")
        sys.exit()

    print("Đang tải dữ liệu phiếu hậu kiểm từ hệ thống...")
    try:
        conn = get_connection()
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vn_now = datetime.now(vn_tz)
        vn_start_of_day = vn_now.replace(hour=0, minute=0, second=0, microsecond=0)
        vn_end_of_day = vn_now.replace(hour=23, minute=59, second=59, microsecond=999999)

        utc_start = vn_start_of_day.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        utc_end = vn_end_of_day.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

        query = f"""
        SELECT 
            t.double_check_code,
            t.code,
            t.from_branch_id,
            t.to_branch_id,
            t.total_sku,
            t.total_store_quantity,
            t.total_transfer_quantity
        FROM __cdc_kfm_kf_inventories_kf_transfer_items t
        WHERE t.from_branch_id = '5fdc170ebd89c10006f15b7c'
        AND t.double_check_code IS NOT NULL AND t.double_check_code != ''
        AND t.double_checked_status = 1
        AND t.status = 5
        AND t.created_at >= '{utc_start}' 
        AND t.created_at <= '{utc_end}'
        """
        df_tickets = pd.read_sql(query, conn)
        df_tickets['Mã Hậu Kiểm'] = df_tickets['double_check_code']
        df_tickets['Phiếu chuyển'] = df_tickets['code']
        df_tickets['SKU'] = df_tickets['total_sku']
        
        df_branches = pd.read_sql("SELECT branch_id, branch_name FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name IS NOT NULL AND branch_name != '' GROUP BY branch_id, branch_name", conn)
        id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
        
        conn.close()
    except Exception as e:
        print(f"[LỖI] Không thể lấy dữ liệu từ hệ thống: {e}")
        input("Bấm Enter để thoát...")
        sys.exit()

    if len(df_tickets) == 0:
        print("Tuyệt vời! Không có phiếu chuyển RAU CỦ nào đang treo ở trạng thái 'Cần hậu kiểm' trong hôm nay.")
        input("Bấm Enter để thoát...")
        sys.exit()

    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name)
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Cần hậu kiểm'
    
    # Định dạng cột Số lượng
    def format_qty(row):
        store = row['total_store_quantity']
        transfer = row['total_transfer_quantity']
        return f"{store}/{transfer}"
        
    df_tickets['Số lượng'] = df_tickets.apply(format_qty, axis=1)

    grouped = df_tickets.groupby('Nơi nhận')

    print("Đang khởi động module Telegram...")
    session_path = find_data_file('user_session', 'ĐÔNG MÁT').replace('.session', '')
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

    success_count = 0
    fail_count = 0
    failed_list = []
    print(f"Có {len(grouped)} Siêu thị đang có phiếu Cần hậu kiểm.")

    date_str = vn_now.strftime('%d.%m')

    for store_name, group in grouped:
        id_st = store_name.strip()
        
        if id_st not in chat_map:
            print(f"[CẢNH BÁO] Không tìm thấy Chat ID của Siêu thị {store_name}! Bỏ qua.")
            fail_count += 1
            continue
            
        chat_id_str = str(chat_map[id_st]).replace('.0', '').strip()
        chat_id = int(chat_id_str)
        
        tag_text = await get_tags_for_group(client, chat_id)
        
        caption_text = f'''**RAU CỦ**
{date_str}
Siêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM RAU CỦ gấp nhé team 
{tag_text}'''

        cols_to_keep = ['Mã Hậu Kiểm', 'Phiếu chuyển', 'Nơi chuyển', 'Nơi nhận', 'Trạng thái']
        df_slice = group[cols_to_keep].reset_index(drop=True)
        img_path = f"temp_{id_st[:10].replace('/', '_').replace(' ', '_')}.png"
        
        try:
            dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=200)
            from PIL import Image
            with Image.open(img_path) as img:
                width, height = img.size
                if width / height > 15:
                    new_height = int(width / 15)
                    new_img = Image.new("RGB", (width, new_height), "white")
                    offset = (new_height - height) // 2
                    new_img.paste(img, (0, offset))
                    new_img.save(img_path)
        except Exception as e:
            print(f"Lỗi tạo hình ảnh cho ST {store_name}: {e}")
            fail_count += 1
            continue
            
        try:
            with open(img_path, 'rb') as f:
                res = requests.post(url_send_photo, files={'photo': f}, data={
                    'chat_id': chat_id, 'caption': caption_text, 'parse_mode': 'Markdown'
                })
                if res.status_code == 200:
                    print(f"[THÀNH CÔNG] Đã tag & gửi thông báo cho ST {store_name}.")
                    success_count += 1
                else:
                    print(f"[LỖI] Không thể gửi cho ST {store_name}: {res.text}")
                    fail_count += 1
        except Exception as e:
            print(f"[LỖI] Lỗi kết nối ST {store_name}: {e}")
            fail_count += 1
        
        if os.path.exists(img_path): os.remove(img_path)
        await asyncio.sleep(2)

    await client.disconnect()
        
    print("==================================================")
    print(f"HOÀN TẤT! Đã gửi: {success_count} ST. Thất bại/Bỏ qua: {fail_count} ST.")
    print("==================================================")
    input("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
