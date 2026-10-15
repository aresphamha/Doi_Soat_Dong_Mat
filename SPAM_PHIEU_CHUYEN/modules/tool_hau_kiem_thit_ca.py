# -*- coding: utf-8 -*-
"""
MODULE 4: HẬU KIỂM THỊT CÁ
Truy vấn các phiếu Hậu Kiểm Thịt Cá lệch (double_checked_status = 1, status = 5),
kết xuất ảnh bảng chi tiết và gửi trực tiếp vào các nhóm Telegram Siêu thị tương ứng.
"""

import os
import sys
import asyncio
from datetime import datetime
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
    print("🐟 [MODULE HẬU KIỂM THỊT CÁ] BẮT ĐẦU CHẠY TOOL: HẬU KIỂM THỊT CÁ...")
    print("=======================================================")
    
    excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
    if not os.path.exists(excel_path):
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        
    df_chat = pd.read_excel(excel_path, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID']))

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_now = datetime.now(vn_tz)
    
    if target_date:
        vn_target = datetime.strptime(target_date, '%Y-%m-%d')
        vn_start = vn_tz.localize(vn_target.replace(hour=0, minute=0, second=0, microsecond=0))
        vn_end = vn_tz.localize(vn_target.replace(hour=23, minute=59, second=59, microsecond=999999))
    else:
        vn_start = vn_now.replace(hour=0, minute=0, second=0, microsecond=0)
        vn_end = vn_now.replace(hour=23, minute=59, second=59, microsecond=999999)

    utc_start = vn_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    utc_end = vn_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    date_str = vn_start.strftime('%d.%m')
    date_iso = vn_start.strftime('%Y-%m-%d')

    try:
        conn = get_db_connection()
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
        WHERE t.from_branch_id IN ('6aabb4d0e493030007272a3f', '6a34ed56f23028000774139f')
        AND t.double_check_code IS NOT NULL AND t.double_check_code != ''
        AND t.double_checked_status = 1
        AND t.status = 5
        AND t.created_at >= '{utc_start}' 
        AND t.created_at <= '{utc_end}'
        """
        df_tickets = pd.read_sql(query, conn)
        df_branches = pd.read_sql("SELECT branch_id, branch_name FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name IS NOT NULL AND branch_name != '' GROUP BY branch_id, branch_name", conn)
        id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
        conn.close()
    except Exception as e:
        print(f"⚠️ [LỖI KẾT NỐI DATABASE 103.140.248.250]: {e}")
        print("💡 Gợi ý: Database chặn IP Cloud quốc tế. Vui lòng mở Chay_Local_Runner.bat để chạy trên máy tính.")
        return

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Hậu Kiểm Thịt Cá lệch")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Hậu kiểm Thịt Cá lệch.")
        return

    df_tickets['Mã Hậu Kiểm'] = df_tickets['double_check_code']
    df_tickets['Phiếu chuyển'] = df_tickets['code']
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('MFA30102 _ Sóng Thần _ Quá Cảnh')
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

    sent_today = load_sent_stores('hau_kiem_thit_ca', date_iso)

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
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
        caption = f"**THỊT CÁ**\n{date_str}\nSiêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM THỊT CÁ gấp nhé team \n{tag_text}"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_thitca_hk_{int(chat_id)}.png"
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
                    record_sent_store('hau_kiem_thit_ca', date_iso, str(chat_id))
                    print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                else:
                    err_msg = res_json.get('description', f'HTTP {resp.status_code}')
                    print(f"❌ [LỖI GỬI TELEGRAM] {store_name} ({chat_id}): {err_msg}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Hậu Kiểm Thịt Cá!")
