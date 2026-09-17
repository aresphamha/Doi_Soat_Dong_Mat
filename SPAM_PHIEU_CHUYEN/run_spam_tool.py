# -*- coding: utf-8 -*-
"""
Hệ Thống Điều Khiển & Thực Thi Tự Động Toàn Bộ Công Cụ SCM (Cloud Runner & Local CLI)
Hỗ trợ kích hoạt trực tiếp từ Web GitHub Pages qua GitHub Actions Workflow Dispatch.
"""

import os
import sys
import argparse
import base64
import asyncio
import subprocess
from datetime import datetime, timedelta
import pytz
import pymysql
import pandas as pd
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DATA_DIR = os.path.join(ROOT_DIR, "CONFIG_DATA")
TOOLS_BASE_DIR = os.path.join(os.path.dirname(ROOT_DIR), "TOOLS_DOI_SOAT")

def ensure_telegram_session():
    """Tự động khôi phục session Telegram từ biến môi trường hoặc session_b64.txt nếu chạy trên GitHub Actions."""
    session_file = os.path.join(CONFIG_DATA_DIR, "user_session.session")
    if not os.path.exists(session_file):
        b64 = os.environ.get("TELEGRAM_SESSION_B64", "").strip()
        if not b64:
            b64_file = os.path.join(CONFIG_DATA_DIR, "session_b64.txt")
            if os.path.exists(b64_file):
                with open(b64_file, "r", encoding="utf-8") as f:
                    b64 = f.read().strip()
        if b64:
            try:
                os.makedirs(CONFIG_DATA_DIR, exist_ok=True)
                with open(session_file, "wb") as f:
                    f.write(base64.b64decode(b64))
                print(f"✅ Đã khôi phục session Telegram từ Base64 vào {session_file}")
            except Exception as e:
                print(f"⚠️ Lỗi giải mã session: {e}")
    return session_file

def find_mapping_file(filename):
    candidates = [
        os.path.join(CONFIG_DATA_DIR, filename),
        os.path.join(TOOLS_BASE_DIR, "DONG_MAT", filename),
        os.path.join(TOOLS_BASE_DIR, "THIT_CA", filename),
        os.path.join(TOOLS_BASE_DIR, "RAU_CU", filename),
        os.path.join(ROOT_DIR, "CHI TIẾT MÁT", filename),
        os.path.join(ROOT_DIR, "CHI TIẾT THỊT CÁ", filename),
        os.path.join(ROOT_DIR, "HẬU KIỂM RAU", filename),
        os.path.join(ROOT_DIR, "HẬU KIỂM THỊ CÁ", filename),
        os.path.join(ROOT_DIR, filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return candidates[0]

import json

def get_sent_history_file():
    return os.path.join(CONFIG_DATA_DIR, "sent_history.json")

def load_sent_stores(tool_name, date_str):
    hist_file = get_sent_history_file()
    if os.path.exists(hist_file):
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get(date_str, {}).get(tool_name, []))
        except Exception:
            return set()
    return set()

def record_sent_store(tool_name, date_str, store_id):
    hist_file = get_sent_history_file()
    data = {}
    if os.path.exists(hist_file):
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    if date_str not in data:
        data[date_str] = {}
    if tool_name not in data[date_str]:
        data[date_str][tool_name] = []
    if store_id not in data[date_str][tool_name]:
        data[date_str][tool_name].append(store_id)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(hist_file)), exist_ok=True)
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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

def get_db_connection():
    return pymysql.connect(
        host='103.140.248.250',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm',
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30
    )

# -------------------------------------------------------------
# MODULE 1: CHI TIẾT THỊT CÁ
# -------------------------------------------------------------
async def run_tool_thit_ca(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("🥩 [1/4] BẮT ĐẦU CHẠY TOOL: CHI TIẾT THỊT CÁ...")
    print("=======================================================")
    
    excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
    if not os.path.exists(excel_path):
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        
    df_chat = pd.read_excel(excel_path, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID']))
    print(f"📋 Đã nạp {len(chat_map)} Siêu thị từ file: {os.path.basename(excel_path)}")

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
    print(f"⏰ Khoảng thời gian truy vấn (VN): {vn_start.strftime('%Y-%m-%d %H:%M:%S')} -> {vn_end.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        conn = get_db_connection()
        query = f"""
        SELECT 
            t.code as `code`,
            t.from_branch_id,
            t.to_branch_id,
            t.total_sku,
            t.total_transfer_quantity,
            t.status
        FROM __cdc_kfm_kf_inventories_kf_transfer_items t
        WHERE t.from_branch_id = '6a34ed56f23028000774139f'
        AND t.status = 3
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Thịt Cá đang ở trạng thái 'Đang chuyển' (Status=3)")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu treo cần xử lý.")
        return

    df_tickets['Mã phiếu chuyển'] = df_tickets['code']
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('KHO THỊT CÁ')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Đang chuyển'
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị có phiếu treo: {len(grouped)}")

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    from PIL import Image
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    sent_today = load_sent_stores('thit_ca', date_iso)

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
        caption = f"**THỊT CÁ**\n{date_str}\nSiêu thị kiểm tra HOÀN THÀNH phiếu CHI TIẾT THỊT CÁ gấp nhé team \n{tag_text}"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_thit_ca_{int(chat_id)}.png"
                cols_to_keep = ['Mã phiếu chuyển', 'Nơi chuyển', 'Nơi nhận', 'Trạng thái']
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
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                record_sent_store('thit_ca', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Chi Tiết Thịt Cá!")

# -------------------------------------------------------------
# MODULE 2: CHI TIẾT MÁT
# -------------------------------------------------------------
async def run_tool_mat(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("🥬 [2/4] BẮT ĐẦU CHẠY TOOL: CHI TIẾT HÀNG MÁT...")
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
        vn_yesterday = vn_now - timedelta(days=1)
        vn_start = vn_yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        vn_end = vn_yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

    utc_start = vn_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    utc_end = vn_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    date_str = vn_start.strftime('%d.%m')
    date_iso = vn_start.strftime('%Y-%m-%d')
    print(f"⏰ Khoảng thời gian truy vấn (VN): {vn_start.strftime('%Y-%m-%d %H:%M:%S')} -> {vn_end.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        conn = get_db_connection()
        query = f"""
        SELECT 
            t.code as `code`,
            t.from_branch_id,
            t.to_branch_id,
            t.status,
            t.ts_do_status
        FROM __cdc_kfm_kf_inventories_kf_transfer_items t
        WHERE t.from_branch_id = '6a34ee2aebb48c000760d803'
        AND t.status = 3
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Mát đang ở trạng thái 'Đang chuyển' (Status=3)")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Mát treo cần xử lý.")
        return

    df_tickets['Mã phiếu chuyển'] = df_tickets['code']
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('KHO MÁT')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Đang chuyển'
    df_tickets['Trạng thái PXK TS'] = df_tickets['ts_do_status'].fillna('Chưa tạo')
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị có phiếu Mát treo: {len(grouped)}")

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    from PIL import Image
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    sent_today = load_sent_stores('mat', date_iso)

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            # thử bỏ hậu tố MINI, WIN, SUPER
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
        caption = f"**MÁT**\n{date_str}\nSiêu thị kiểm tra HOÀN THÀNH phiếu CHI TIẾT HÀNG MÁT gấp nhé team \n{tag_text}"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_mat_{int(chat_id)}.png"
                cols_to_keep = ['Mã phiếu chuyển', 'Nơi chuyển', 'Nơi nhận', 'Trạng thái', 'Trạng thái PXK TS']
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
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                record_sent_store('mat', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Chi Tiết Mát!")

# -------------------------------------------------------------
# MODULE 3: HẬU KIỂM RAU CỦ
# -------------------------------------------------------------
async def run_tool_hau_kiem_rau(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("🥦 [3/4] BẮT ĐẦU CHẠY TOOL: HẬU KIỂM RAU CỦ...")
    print("=======================================================")
    
    excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Rau_Cu.xlsx")
    if not os.path.exists(excel_path):
        excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
        
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
        WHERE t.from_branch_id = '5fdc170ebd89c10006f15b7c'
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Hậu Kiểm Rau Củ lệch")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Hậu kiểm Rau Củ lệch.")
        return

    df_tickets['Mã Hậu Kiểm'] = df_tickets['double_check_code']
    df_tickets['Phiếu chuyển'] = df_tickets['code']
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('KHO RAU CỦ')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Cần hậu kiểm'
    grouped = df_tickets.groupby('Nơi nhận')

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    from PIL import Image
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    sent_today = load_sent_stores('hau_kiem_rau', date_iso)

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
        caption = f"**RAU CỦ**\n{date_str}\nSiêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM RAU CỦ gấp nhé team \n{tag_text}"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_rau_{int(chat_id)}.png"
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
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                record_sent_store('hau_kiem_rau', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Hậu Kiểm Rau Củ!")

# -------------------------------------------------------------
# MODULE 4: HẬU KIỂM THỊT CÁ
# -------------------------------------------------------------
async def run_tool_hau_kiem_thit_ca(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("🐟 [4/4] BẮT ĐẦU CHẠY TOOL: HẬU KIỂM THỊT CÁ...")
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
        WHERE t.from_branch_id = '6a34ed56f23028000774139f'
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
    df_tickets['Nơi chuyển'] = df_tickets['from_branch_id'].map(id_to_name).fillna('KHO THỊT CÁ')
    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    df_tickets['Trạng thái'] = 'Cần hậu kiểm'
    grouped = df_tickets.groupby('Nơi nhận')

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    from PIL import Image
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
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
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                record_sent_store('hau_kiem_thit_ca', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Hậu Kiểm Thịt Cá!")

def execute_external_tool(script_path, cwd=None):
    """Thực thi file script Python cục bộ với môi trường UTF-8 chuẩn xác và in log Real-time từng dòng."""
    if not os.path.exists(script_path):
        print(f"❌ [LỖI] Không tìm thấy file script: {script_path}", flush=True)
        return False
    work_dir = cwd if cwd else os.path.dirname(script_path)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        for line in proc.stdout:
            clean_line = line.rstrip()
            if clean_line:
                print(clean_line, flush=True)
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        print(f"❌ [LỖI THỰC THI] {os.path.basename(script_path)}: {e}", flush=True)
        return False

# -------------------------------------------------------------
# MODULE 5: ĐÔNG MÁT SHEET & SPAM TELEGRAM
# -------------------------------------------------------------
async def run_tool_dong_mat_full(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("❄️ BẮT ĐẦU CHẠY TOOL ĐỐI SOÁT ĐÔNG MÁT GỐC...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Doi_Soat_Dong_Mat.py")
    execute_external_tool(script_path)

async def run_tool_dong_mat_spam(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("📨 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO ĐÔNG MÁT...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "2_Spam_Telegram.py")
    execute_external_tool(script_path)

async def run_tool_lay_chat_id():
    print("\n=======================================================")
    print("🆔 BẮT ĐẦU CHẠY TOOL QUÉT & CẬP NHẬT CHAT ID TELEGRAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Lay_Chat_ID.py")
    execute_external_tool(script_path)

async def run_tool_dong_mat_nhom_dong():
    print("\n=======================================================")
    print("🧊 BẮT ĐẦU CHẠY TOOL ĐỐI SOÁT RIÊNG NHÓM ĐÔNG...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Doi_Soat_Nhom_Dong.py")
    execute_external_tool(script_path)

async def run_tool_thit_ca_spam():
    print("\n=======================================================")
    print("🥩 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO THỊT CÁ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "THIT_CA", "Tool_Spam", "2_Spam_Telegram.py")
    execute_external_tool(script_path)

async def run_tool_rau_cu_spam():
    print("\n=======================================================")
    print("🥦 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO RAU CỦ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "2_Spam_Telegram.py")
    execute_external_tool(script_path)

async def run_tool_spam_tu_chon(stores="ALL", message=None, tag_roles=True, dry_run=False, photo_path=None):
    print("\n=======================================================")
    print("🎯 BẮT ĐẦU CHẠY TOOL: SPAM TIN NHẮN TÙY CHỌN...")
    print("=======================================================")
    
    excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
    if not os.path.exists(excel_path):
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        
    df = pd.read_excel(excel_path, dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
    df['CHAT ID'] = df['CHAT ID'].str.replace('.0', '', regex=False).str.strip()
    if 'Tên viết tắt' not in df.columns:
        df['Tên viết tắt'] = df['ID ST']
    df['Tên viết tắt'] = df['Tên viết tắt'].fillna('').str.strip()

    # Xử lý danh sách cửa hàng
    selected_indices = []
    if not stores or str(stores).strip().upper() == "ALL":
        selected_indices = list(range(len(df)))
        print(f"📋 Đã chọn: TẤT CẢ {len(selected_indices)} Siêu thị")
    else:
        id_map = {}
        for idx, row in df.iterrows():
            id_val = str(row['ID ST']).strip().upper()
            vt_val = str(row['Tên viết tắt']).strip().upper()
            ten_val = str(row['Tên Siêu thị']).strip().upper()
            id_map.setdefault(id_val, []).append(idx)
            if vt_val: id_map.setdefault(vt_val, []).append(idx)
            if ten_val: id_map.setdefault(ten_val, []).append(idx)
        
        parts = [p.strip().upper() for p in str(stores).split(',') if p.strip()]
        for p in parts:
            if p in id_map:
                selected_indices.extend(id_map[p])
            else:
                matched = False
                for k, v in id_map.items():
                    if p in k:
                        selected_indices.extend(v)
                        matched = True
                        break
                if not matched:
                    print(f"⚠️ Không tìm thấy Siêu thị có mã/tên: '{p}'")
        selected_indices = sorted(set(selected_indices))
        print(f"📋 Đã nhận diện {len(selected_indices)} Siêu thị được chọn.")

    if not selected_indices:
        print("❌ Không có Siêu thị nào hợp lệ để gửi tin nhắn.")
        return

    default_msg = "📢 **THÔNG BÁO TỪ PHÒNG SCM**\nNgày: {NGAY}\nKính gửi Cửa hàng: **{TEN_ST}**\nNhờ Siêu thị phối hợp kiểm tra và hoàn tất chứng từ tồn đọng giúp team nhé!\n{TAGS}"
    raw_message = message if message and str(message).strip() else default_msg

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    is_auth = await client.is_user_authorized()
    if not is_auth:
        print("ℹ️ Chế độ gửi: Bot Token Telegram API")

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_now = datetime.now(vn_tz)
    ngay_str = vn_now.strftime('%d/%m/%Y')

    total_count = len(selected_indices)
    success_count = 0

    for i, idx in enumerate(selected_indices, 1):
        row = df.iloc[idx]
        ten_st = str(row['Tên Siêu thị']).strip()
        id_st = str(row['ID ST']).strip()
        chat_id_str = str(row['CHAT ID']).strip()
        
        try:
            chat_id = int(chat_id_str)
        except Exception:
            print(f"⚠️ [{i}/{total_count}] Bỏ qua {ten_st}: Chat ID không hợp lệ ({chat_id_str})")
            continue

        tag_text = ""
        if tag_roles:
            if is_auth:
                tag_text = await get_tags_for_group(client, chat_id)
            else:
                tag_text = "@SM @TC @GSM"

        # Thay thế biến động
        msg = raw_message.replace('{TEN_ST}', ten_st).replace('{ID_ST}', id_st).replace('{NGAY}', ngay_str)
        if '{TAGS}' in msg:
            msg = msg.replace('{TAGS}', tag_text)
        elif tag_roles and tag_text:
            msg = f"{msg}\n{tag_text}"

        if dry_run:
            print(f"🔍 [DRY-RUN] [{i}/{total_count}] Sẽ gửi đến {ten_st} ({chat_id}):\n{msg}\n---")
            success_count += 1
        else:
            try:
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                            data={'chat_id': chat_id, 'caption': msg, 'parse_mode': 'Markdown'},
                            files={'photo': f},
                            timeout=15
                        )
                else:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'},
                        timeout=15
                    )
                print(f"🚀 [{i}/{total_count}] [ĐÃ GỬI] Thành công tới: {ten_st} ({chat_id})")
                success_count += 1
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"❌ [{i}/{total_count}] [LỖI GỬI] {ten_st}: {e}")

    await client.disconnect()
    print(f"\n🎉 HOÀN TẤT SPAM TÙY CHỌN! Đã gửi thành công {success_count}/{total_count} Siêu thị.")

async def run_tool_xoa_tin_nhan():
    print("\n=======================================================")
    print("🗑️ BẮT ĐẦU CHẠY TOOL THU HỒI / XÓA TIN NHẮN ĐÃ SPAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "Xoa_Tin_Nhan.py")
    execute_external_tool(script_path)

async def run_tool_tra_cuu_id():
    print("\n=======================================================")
    print("🔍 BẮT ĐẦU CHẠY TOOL TRA CỨU NHANH CHAT ID GROUP...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "3_Tra_Cuu_ID.py")
    execute_external_tool(script_path)

async def run_tool_add_thanh_vien():
    print("\n=======================================================")
    print("👥 BẮT ĐẦU CHẠY TOOL TỰ ĐỘNG THÊM THÀNH VIÊN VÀO GROUP TELEGRAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "4_Add_Thanh_Vien.py")
    execute_external_tool(script_path)

async def run_tool_xuat_doi_soat_chuan():
    print("\n=======================================================")
    print("📑 BẮT ĐẦU XUẤT FILE BÁO CÁO ĐỐI SOÁT CHUẨN EXCEL...")
    print("=======================================================")
    script_path = os.path.join(os.path.dirname(ROOT_DIR), "xuat_doi_soat_chuan.py")
    execute_external_tool(script_path)

async def run_tool_export_thit_ca():
    print("\n=======================================================")
    print("📈 BẮT ĐẦU CHẠY TOOL XUẤT ĐỐI SOÁT THỊT CÁ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "THIT_CA", "export_thit_ca.py")
    execute_external_tool(script_path)


def main():
    parser = argparse.ArgumentParser(description="Chạy Tool Đối Soát & Spam Phiếu Chuyển SCM")
    parser.add_argument("--tool", choices=[
        "all", "thit_ca", "mat", "hau_kiem_rau", "hau_kiem_thit_ca", 
        "dong_mat_sheet", "dong_mat_nhom_dong", "dong_mat_spam", "thit_ca_spam", "rau_cu_spam",
        "spam_tu_chon", "xoa_tin_nhan", "lay_chat_id", "tra_cuu_id", "add_thanh_vien",
        "xuat_doi_soat_chuan", "export_thit_ca", "sync_report"
    ], default="all", help="Chọn tool cần chạy")
    parser.add_argument("--date", default=None, help="Ngày đối soát (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Chế độ chạy thử không gửi tin nhắn")
    parser.add_argument("--stores", default="ALL", help="Danh sách mã ST cần gửi (ngăn cách bởi dấu phẩy hoặc ALL)")
    parser.add_argument("--message", default=None, help="Nội dung tin nhắn tùy chọn cần spam")
    parser.add_argument("--no-tags", action="store_true", help="Không tự động tag Quản lý/Trưởng ca")
    parser.add_argument("--photo", default=None, help="Đường dẫn file ảnh đính kèm (nếu có)")
    
    args = parser.parse_args()
    date_val = args.date.strip() if args.date and args.date.strip() else None
    tag_roles = not args.no_tags
    
    print("==============================================================================")
    print(f"🚀 KHỞI ĐỘNG HỆ THỐNG RUNNER TOOL SCM CLOUD (Tool: {args.tool}, Date: {date_val or 'Mặc định'}, Dry-run: {args.dry_run})")
    print("==============================================================================")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if args.tool == "thit_ca":
        loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
    elif args.tool == "mat":
        loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
    elif args.tool == "hau_kiem_rau":
        loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
    elif args.tool == "hau_kiem_thit_ca":
        loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
    elif args.tool == "dong_mat_sheet":
        loop.run_until_complete(run_tool_dong_mat_full(date_val, args.dry_run))
    elif args.tool == "dong_mat_nhom_dong":
        loop.run_until_complete(run_tool_dong_mat_nhom_dong())
    elif args.tool == "dong_mat_spam":
        loop.run_until_complete(run_tool_dong_mat_spam(date_val, args.dry_run))
    elif args.tool == "thit_ca_spam":
        loop.run_until_complete(run_tool_thit_ca_spam())
    elif args.tool == "rau_cu_spam":
        loop.run_until_complete(run_tool_rau_cu_spam())
    elif args.tool == "spam_tu_chon":
        loop.run_until_complete(run_tool_spam_tu_chon(args.stores, args.message, tag_roles, args.dry_run, args.photo))
    elif args.tool == "xoa_tin_nhan":
        loop.run_until_complete(run_tool_xoa_tin_nhan())
    elif args.tool == "lay_chat_id":
        loop.run_until_complete(run_tool_lay_chat_id())
    elif args.tool == "tra_cuu_id":
        loop.run_until_complete(run_tool_tra_cuu_id())
    elif args.tool == "add_thanh_vien":
        loop.run_until_complete(run_tool_add_thanh_vien())
    elif args.tool == "xuat_doi_soat_chuan":
        loop.run_until_complete(run_tool_xuat_doi_soat_chuan())
    elif args.tool == "export_thit_ca":
        loop.run_until_complete(run_tool_export_thit_ca())
    elif args.tool == "all":
        loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
        loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
        loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
        loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
    elif args.tool == "sync_report":
        print("📊 Đang khởi tạo tái xuất bản Báo Cáo Web Đối Soát...")
        dashboard_dir = os.path.join(os.path.dirname(ROOT_DIR), "DONG_MAT_DASHBOARD")
        sys.path.insert(0, dashboard_dir)
        from generate_web_report import generate_web_report
        generate_web_report()

    print("\n==============================================================================")
    print("🎉 TẤT CẢ TÁC VỤ ĐÃ HOÀN THÀNH!")
    print("==============================================================================")

if __name__ == "__main__":
    main()

