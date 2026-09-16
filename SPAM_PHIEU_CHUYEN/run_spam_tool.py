# -*- coding: utf-8 -*-
"""
Hệ Thống Điều Khiển & Thực Thi Tự Động 4 Công Cụ SCM (Cloud Runner & Local CLI)
Hỗ trợ kích hoạt trực tiếp từ Web GitHub Pages qua GitHub Actions Workflow Dispatch.
"""

import os
import sys
import argparse
import base64
import asyncio
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

def ensure_telegram_session():
    """Tự động khôi phục session Telegram từ biến môi trường nếu chạy trên GitHub Actions."""
    session_file = os.path.join(CONFIG_DATA_DIR, "user_session.session")
    if not os.path.exists(session_file):
        b64 = os.environ.get("TELEGRAM_SESSION_B64", "").strip()
        if b64:
            try:
                os.makedirs(CONFIG_DATA_DIR, exist_ok=True)
                with open(session_file, "wb") as f:
                    f.write(base64.b64decode(b64))
                print(f"✅ Đã giải mã session từ TELEGRAM_SESSION_B64 vào {session_file}")
            except Exception as e:
                print(f"⚠️ Lỗi giải mã session: {e}")
    return session_file

def find_mapping_file(filename):
    candidates = [
        os.path.join(CONFIG_DATA_DIR, filename),
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

def get_db_connection():
    return pymysql.connect(
        host='103.147.122.103',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm'
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
    print(f"⏰ Khoảng thời gian truy vấn (VN): {vn_start.strftime('%Y-%m-%d %H:%M:%S')} -> {vn_end.strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_db_connection()
    query = f"""
    SELECT 
        t.code as `Mã phiếu chuyển`,
        t.from_branch_id,
        t.to_branch_id,
        t.total_sku as `SKU`,
        t.total_transfer_quantity as `Số lượng`,
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Thịt Cá đang ở trạng thái 'Đang chuyển' (Status=3)")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu treo cần xử lý.")
        return

    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị có phiếu treo: {len(grouped)}")

    # Gửi tin nhắn
    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            print(f"⏩ [Bỏ qua] Không tìm thấy Chat ID cho: {store_name}")
            continue
            
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        caption = f"⚠️ [ĐỐI SOÁT THỊT CÁ - {vn_start.strftime('%d/%m/%Y')}]\nCửa hàng: **{store_name}**\nHiện có **{len(group)}** phiếu chuyển thịt cá đang ở trạng thái Đang Chuyển. Nhờ ST kiểm tra và nhận hàng giúp SCM nhé!"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                # Xuất ảnh bảng
                img_path = f"temp_thit_ca_{int(chat_id)}.png"
                df_slice = group[['Mã phiếu chuyển', 'SKU', 'Số lượng']]
                dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=180)
                
                with open(img_path, 'rb') as f:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
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
    print(f"⏰ Khoảng thời gian truy vấn (VN): {vn_start.strftime('%Y-%m-%d %H:%M:%S')} -> {vn_end.strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_db_connection()
    query = f"""
    SELECT 
        t.code as `Mã phiếu chuyển`,
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Mát đang ở trạng thái 'Đang chuyển' (Status=3)")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Mát treo cần xử lý.")
        return

    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị có phiếu Mát treo: {len(grouped)}")

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            continue
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        caption = f"⚠️ [ĐỐI SOÁT HÀNG MÁT - {vn_start.strftime('%d/%m/%Y')}]\nCửa hàng: **{store_name}**\nHiện có **{len(group)}** phiếu chuyển hàng mát chưa xác nhận nhận hàng. Nhờ ST hoàn tất giúp SCM nhé!"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_mat_{int(chat_id)}.png"
                df_slice = group[['Mã phiếu chuyển']]
                dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=180)
                
                with open(img_path, 'rb') as f:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
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

    conn = get_db_connection()
    query = f"""
    SELECT 
        t.double_check_code as `Mã Hậu Kiểm`,
        t.code as `Phiếu chuyển`,
        t.from_branch_id,
        t.to_branch_id,
        t.total_sku as `SKU`,
        t.total_store_quantity as `ST Nhận`,
        t.total_transfer_quantity as `Xuất đi`
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Hậu Kiểm Rau Củ lệch cần đối soát")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Hậu kiểm Rau Củ lệch trong khoảng thời gian này.")
        return

    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị cần gửi thông báo: {len(grouped)}")

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            continue
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        caption = f"⚠️ [HẬU KIỂM RAU CỦ - {vn_start.strftime('%d/%m/%Y')}]\nCửa hàng: **{store_name}**\nHiện có **{len(group)}** phiếu hậu kiểm rau củ phát hiện chênh lệch. Nhờ ST kiểm tra đối chiếu lại nhé!"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_rau_{int(chat_id)}.png"
                df_slice = group[['Mã Hậu Kiểm', 'Phiếu chuyển', 'ST Nhận', 'Xuất đi']]
                dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=180)
                
                with open(img_path, 'rb') as f:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
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

    conn = get_db_connection()
    query = f"""
    SELECT 
        t.double_check_code as `Mã Hậu Kiểm`,
        t.code as `Phiếu chuyển`,
        t.from_branch_id,
        t.to_branch_id,
        t.total_sku as `SKU`,
        t.total_store_quantity as `ST Nhận`,
        t.total_transfer_quantity as `Xuất đi`
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

    print(f"📊 Tìm thấy {len(df_tickets)} phiếu Hậu Kiểm Thịt Cá lệch")
    if len(df_tickets) == 0:
        print("✅ Không có phiếu Hậu kiểm Thịt Cá lệch trong khoảng thời gian này.")
        return

    df_tickets['Nơi nhận'] = df_tickets['to_branch_id'].map(id_to_name)
    grouped = df_tickets.groupby('Nơi nhận')
    print(f"🏪 Tổng số Siêu thị cần gửi thông báo: {len(grouped)}")

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')
    
    from telethon import TelegramClient
    import dataframe_image as dfi
    api_id = '28938971'
    api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
    bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Bỏ qua bước gửi tin nhắn.")
        await client.disconnect()
        return

    for store_name, group in grouped:
        chat_id_raw = chat_map.get(str(store_name).strip())
        if not chat_id_raw:
            continue
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        caption = f"⚠️ [HẬU KIỂM THỊT CÁ - {vn_start.strftime('%d/%m/%Y')}]\nCửa hàng: **{store_name}**\nHiện có **{len(group)}** phiếu hậu kiểm thịt cá phát hiện chênh lệch. Nhờ ST phản hồi SCM sớm nhé!"
        
        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {store_name} ({chat_id}): {len(group)} phiếu")
        else:
            try:
                img_path = f"temp_thitca_hk_{int(chat_id)}.png"
                df_slice = group[['Mã Hậu Kiểm', 'Phiếu chuyển', 'ST Nhận', 'Xuất đi']]
                dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=180)
                
                with open(img_path, 'rb') as f:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=15
                    )
                if os.path.exists(img_path): os.remove(img_path)
                print(f"🚀 [ĐÃ GỬI] Thành công tới {store_name} ({chat_id})")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [LỖI GỬI] {store_name}: {e}")

    await client.disconnect()
    print("✅ Hoàn thành Tool Hậu Kiểm Thịt Cá!")


def main():
    parser = argparse.ArgumentParser(description="Chạy Tool Spam Phiếu Chuyển SCM")
    parser.add_argument("--tool", choices=["thit_ca", "mat", "hau_kiem_rau", "hau_kiem_thit_ca", "sync_report", "all"], default="all", help="Chọn tool cần chạy")
    parser.add_argument("--date", default=None, help="Ngày đối soát (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Chế độ chạy thử không gửi tin nhắn")
    
    args = parser.parse_args()
    
    date_val = args.date.strip() if args.date and args.date.strip() else None
    
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
    elif args.tool == "all":
        loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
        loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
        loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
        loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
    elif args.tool == "sync_report":
        print("📊 Đang khởi tạo tái xuất bản Báo Cáo Web Đối Soát...")
        from DONG_MAT_DASHBOARD.generate_web_report import generate_web_report
        generate_web_report()

    print("\n==============================================================================")
    print("🎉 TẤT CẢ TÁC VỤ ĐÃ HOÀN THÀNH!")
    print("==============================================================================")

if __name__ == "__main__":
    main()
