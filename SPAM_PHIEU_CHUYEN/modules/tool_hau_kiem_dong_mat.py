# -*- coding: utf-8 -*-
"""
MODULE 5: HẬU KIỂM ĐÔNG MÁT
Truy vấn các phiếu Hậu Kiểm Đông Mát lệch (double_checked_status = 1, status = 5),
ưu tiên D-1 rồi sang D-0, kết xuất ảnh bảng chi tiết và gửi trực tiếp vào các nhóm Telegram Siêu thị tương ứng.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
import pytz
import pandas as pd
import requests
from PIL import Image

try:
    import dataframe_image as dfi
except ImportError:
    dfi = None

from telethon import TelegramClient

from .common import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_BOT_TOKEN,
    ensure_telegram_session,
    find_mapping_file,
    load_sent_stores,
    record_sent_store,
    get_tags_for_group,
    get_db_connection
)

async def run(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("❄️ [MODULE HẬU KIỂM ĐÔNG MÁT] BẮT ĐẦU CHẠY TOOL: HẬU KIỂM ĐÔNG MÁT...")
    print("=======================================================")
    
    excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
    if not os.path.exists(excel_path):
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        
    df_chat = pd.read_excel(excel_path, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID']))

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_now = datetime.now(vn_tz)
    
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

    try:
        conn = get_db_connection()
        if target_date:
            vn_target = datetime.strptime(target_date, '%Y-%m-%d')
            vn_start = vn_tz.localize(vn_target.replace(hour=0, minute=0, second=0, microsecond=0))
            vn_end = vn_tz.localize(vn_target.replace(hour=23, minute=59, second=59, microsecond=999999))
            utc_start = vn_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            utc_end = vn_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            date_str = vn_start.strftime('%d.%m')
            date_iso = vn_start.strftime('%Y-%m-%d')
            print(f"⏰ [CHỈ ĐỊNH NGÀY] Truy vấn ngày: {date_iso} ({utc_start} -> {utc_end} UTC)")
            df_tickets = pd.read_sql(get_query_for_range(utc_start, utc_end), conn)
        else:
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
                date_iso = vn_d1.strftime('%Y-%m-%d')
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
                date_iso = vn_now.strftime('%Y-%m-%d')

        df_branches = pd.read_sql("SELECT branch_id, branch_name FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name IS NOT NULL AND branch_name != '' GROUP BY branch_id, branch_name", conn)
        id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
        conn.close()
    except Exception as e:
        print(f"⚠️ [LỖI KẾT NỐI DATABASE 103.140.248.250]: {e}")
        print("💡 Gợi ý: Database chặn IP Cloud quốc tế. Vui lòng mở Chay_Local_Runner.bat để chạy trên máy tính.")
        return

    print(f"📊 Tổng số phiếu Hậu Kiểm Đông Mát cần xử lý: {len(df_tickets)} (Ngày đối soát: {date_str})")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Hậu kiểm Đông Mát nào cần xử lý.")
        return

    df_tickets['Mã Hậu Kiểm'] = df_tickets['double_check_code']
    df_tickets['Phiếu chuyển'] = df_tickets['code']
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('CLA40102/FZA50102 _ Sóng Thần')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Cần hậu kiểm'
    grouped = df_tickets.groupby('Nơi nhận')

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')

    client = TelegramClient(session_base, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    sent_today = load_sent_stores('hau_kiem_dong_mat', date_iso)

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            search_name = str(store_name).replace(' - MINI', '').replace(' - WIN', '').replace(' - SUPER', '').strip()
            chat_id_raw = chat_map.get(search_name)
        if not chat_id_raw:
            continue
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        if str(chat_id) in sent_today:
            print(f"⏩ [ĐÃ GỬI TRƯỚC ĐÓ] Bỏ qua {store_name} ({chat_id})")
            continue

        tag_text = await get_tags_for_group(client, chat_id)
        caption = f"**ĐÔNG MÁT**\n{date_str}\nSiêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM ĐÔNG MÁT gấp nhé team \n{tag_text}"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_dongmat_hk_{int(chat_id)}.png"
                cols_to_keep = ['Mã Hậu Kiểm', 'Phiếu chuyển', 'Nơi chuyển', 'Nơi nhận', 'Trạng thái']
                df_slice = group[cols_to_keep].reset_index(drop=True)
                dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=200)
                
                with Image.open(img_path) as img:
                    width, height = img.size
                    if width / height > 15:
                        new_height = int(width / 15)
                        new_img = Image.new("RGB", (width, new_height), "white")
                        offset = (new_height - height) // 2
                        new_img.paste(img, (0, offset))
                        new_img.save(img_path)

                with open(img_path, 'rb') as f:
                    resp = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                try:
                    res_json = resp.json()
                except Exception:
                    res_json = {}
                if resp.status_code == 200 and res_json.get('ok'):
                    record_sent_store('hau_kiem_dong_mat', date_iso, str(chat_id))
                    print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                else:
                    err_msg = res_json.get('description', f'HTTP {resp.status_code}')
                    print(f"❌ [LỖI GỬI TELEGRAM] {store_name} ({chat_id}): {err_msg}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Hậu Kiểm Đông Mát!")
