# -*- coding: utf-8 -*-
import os
import sys

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
        password='TnAM0WEsv4kmasw878wt',
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
            
            if any(role in name_upper for role in [' TC', '-TC', ' SM', '-SM', ' GSM', '-GSM']):
                tags.append(f"[{name}](tg://user?id={p.id})")
    except Exception:
        pass
    return " ".join(tags) if tags else "@SM @TC @GSM"

async def main():
    print("==================================================")
    print("TOOL SPAM TELEGRAM - PHIẾU CẦN HẬU KIỂM ĐÔNG MÁT")
    print("==================================================")
    
    print("Đang đọc danh sách Chat ID từ thư mục ĐÔNG MÁT...")
    try:
        excel_path = find_data_file('Danh sách Siêu thị.xlsx', 'ĐÔNG MÁT')
        if not os.path.exists(excel_path):
            excel_path = find_data_file('Danh_Sach_Sieu_Thi_Dong_Mat.xlsx', 'ĐÔNG MÁT')
        df_chat = pd.read_excel(excel_path, dtype=str)
        df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
        chat_map = dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID']))
    except Exception as e:
        print(f"[LỖI] Không thể đọc file Danh sách Siêu thị.xlsx: {e}")
        input("Bấm Enter để thoát...")
        sys.exit()

    print("Đang tải dữ liệu phiếu hậu kiểm Đông Mát từ hệ thống...")
    try:
        conn = get_connection()
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        vn_now = datetime.now(vn_tz)
        from datetime import timedelta

        def get_query_for_range(utc_start, utc_end):
            return f"""
            SELECT 
                t.double_check_code,
                t.code,
                t.from_branch_id,
                t.to_branch_id,
                t.total_sku,
                t.total_store_quantity,
                t.total_transfer_quantity
            FROM __cdc_kfm_kf_inventories_kf_transfer_items t
            WHERE t.from_branch_id IN (
                '6aa6a1eedf3d880007871f3f',  -- CLA40102 _ Sóng Thần _ Quá Cảnh
                '6aa77de130fded00073d4521',  -- FZA50102 _ Sóng Thần _ Quá Cảnh
                '6a34ee2aebb48c000760d803',  -- CL02 (Cũ)
                '6a34ec8d77173000073e64e2'   -- FZ02 (Cũ)
            )
            AND t.double_check_code IS NOT NULL AND t.double_check_code != ''
            AND t.double_checked_status = 1
            AND t.status = 5
            AND t.created_at >= '{utc_start}' 
            AND t.created_at <= '{utc_end}'
            """

        # 1. Ưu tiên kiểm tra ngày D - 1 (Hôm qua)
        vn_d1 = vn_now - timedelta(days=1)
        vn_d1_start = vn_d1.replace(hour=0, minute=0, second=0, microsecond=0)
        vn_d1_end = vn_d1.replace(hour=23, minute=59, second=59, microsecond=999999)
        utc_d1_start = vn_d1_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        utc_d1_end = vn_d1_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"⏰ [ƯU TIÊN D-1] Đang kiểm tra phiếu treo ngày hôm qua ({vn_d1.strftime('%d/%m/%Y')})...")
        df_d1 = pd.read_sql(get_query_for_range(utc_d1_start, utc_d1_end), conn)
        
        if len(df_d1) > 0:
            df_tickets = df_d1
            date_str = vn_d1.strftime('%d.%m')
            print(f"📌 Tìm thấy {len(df_tickets)} phiếu Hậu Kiểm Đông Mát còn treo từ ngày D-1 ({date_str}) -> Tiến hành SPAM D-1.")
        else:
            # 2. D-1 không còn phiếu treo -> Chuyển sang ngày D (Hôm nay)
            vn_d0_start = vn_now.replace(hour=0, minute=0, second=0, microsecond=0)
            vn_d0_end = vn_now.replace(hour=23, minute=59, second=59, microsecond=999999)
            utc_d0_start = vn_d0_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            utc_d0_end = vn_d0_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"✅ Ngày D-1 đã hết phiếu treo! Chuyển sang kiểm tra phiếu ngày D Hôm nay ({vn_now.strftime('%d/%m/%Y')})...")
            df_tickets = pd.read_sql(get_query_for_range(utc_d0_start, utc_d0_end), conn)
            date_str = vn_now.strftime('%d.%m')

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
        print("Tuyệt vời! Không có phiếu chuyển ĐÔNG MÁT nào đang treo ở trạng thái 'Cần hậu kiểm' trong cả D-1 và hôm nay.")
        input("Bấm Enter để thoát...")
        sys.exit()

    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('CLA40102/FZA50102 _ Sóng Thần')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Cần hậu kiểm'
    
    grouped = df_tickets.groupby('Nơi nhận')

    print("Đang khởi động module Telegram...")
    session_path = find_data_file('user_session', 'ĐÔNG MÁT').replace('.session', '')
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

    success_count = 0
    fail_count = 0
    print(f"Có {len(grouped)} Siêu thị đang có phiếu hậu kiểm.")

    date_str = vn_now.strftime('%d.%m')

    for store_name, group in grouped:
        id_st = str(store_name).strip()
        chat_id_str = chat_map.get(id_st)
        if not chat_id_str:
            search_name = id_st.replace(' - MINI', '').replace(' - WIN', '').replace(' - SUPER', '').strip()
            chat_id_str = chat_map.get(search_name)
            
        if not chat_id_str:
            print(f"[CẢNH BÁO] Không tìm thấy Chat ID của Siêu thị {store_name}! Bỏ qua.")
            fail_count += 1
            continue
            
        chat_id = int(str(chat_id_str).replace('.0', '').strip())
        tag_text = await get_tags_for_group(client, chat_id)
        
        caption_text = f'''**ĐÔNG MÁT**
{date_str}
Siêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM ĐÔNG MÁT gấp nhé team 
{tag_text}'''

        cols_to_keep = ['Mã Hậu Kiểm', 'Phiếu chuyển', 'Nơi chuyển', 'Nơi nhận', 'Trạng thái']
        df_slice = group[cols_to_keep].reset_index(drop=True)
        
        temp_img = f"temp_dongmat_hk_{int(chat_id)}.png"
        try:
            dfi.export(df_slice, temp_img, table_conversion="matplotlib", dpi=200)
            
            from PIL import Image
            with Image.open(temp_img) as img:
                width, height = img.size
                if width / height > 15:
                    new_height = int(width / 15)
                    new_img = Image.new("RGB", (width, new_height), "white")
                    offset = (new_height - height) // 2
                    new_img.paste(img, (0, offset))
                    new_img.save(temp_img)

            with open(temp_img, 'rb') as photo_file:
                payload = {
                    'chat_id': chat_id,
                    'caption': caption_text,
                    'parse_mode': 'Markdown'
                }
                files = {'photo': photo_file}
                r = requests.post(url_send_photo, data=payload, files=files, timeout=15)
                
            if r.status_code == 200:
                print(f"[THÀNH CÔNG] Đã gửi ảnh hậu kiểm đến: {store_name}")
                success_count += 1
            else:
                print(f"[THẤT BẠI] Lỗi gửi ảnh đến: {store_name} | Mã lỗi: {r.text}")
                fail_count += 1
                
        except Exception as e:
            print(f"[LỖI] Xử lý gửi ảnh cho {store_name}: {e}")
            fail_count += 1
        finally:
            if os.path.exists(temp_img):
                try: os.remove(temp_img)
                except: pass
                
        await asyncio.sleep(1)

    print("\n--------------------------------------------------")
    print(f"Hoàn thành gửi tin: Thành công {success_count} | Thất bại {fail_count}")
    print("--------------------------------------------------")
    
    await client.disconnect()
    input("Bấm Enter để thoát...")

if __name__ == "__main__":
    asyncio.run(main())
