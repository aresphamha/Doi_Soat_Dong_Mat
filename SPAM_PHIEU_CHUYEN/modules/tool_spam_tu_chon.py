# -*- coding: utf-8 -*-
"""
MODULE: SPAM TIN NHẮN TÙY CHỌN (CUSTOM SPAM STUDIO)
Cho phép người dùng tùy biến nội dung, gắn thẻ quản lý hoặc gửi ảnh đến từng siêu thị hoặc tất cả siêu thị.
Hỗ trợ đầy đủ 3 nhóm kho:
  1. KHO KHÔ (DC) - Ưu tiên đọc mục chat_id_dc từ CONFIG_DATA_STORES.json & Danh_Sach_Chat_ID_Nhom_DC.xlsx
  2. RAU CỦ (KRC) - Ưu tiên đọc mục chat_id_rc từ CONFIG_DATA_STORES.json & Danh_Sach_Sieu_Thi_Rau_Cu.xlsx
  3. ĐÔNG MÁT / THỊT CÁ - Ưu tiên đọc mục chat_id_dm từ CONFIG_DATA_STORES.json & Danh sách Siêu thị.xlsx
Cơ chế gửi 2 tầng: Telegram Bot API + Telethon User Client fallback.
"""

import os
import sys
import json
import re
import html
import asyncio
from datetime import datetime
import pytz
import pandas as pd
import requests

def convert_markdown_to_telegram_html(text: str) -> str:
    """
    Chuyển đổi cú pháp định dạng người dùng gõ (**bold**, *bold*, _italic_, ~~strike~~, `code`)
    sang chuẩn HTML Telegram an toàn tuyệt đối, tránh lỗi "can't parse entities".
    """
    if not text:
        return ""
    
    # 1. Thoát các ký tự HTML đặc biệt để tránh vỡ thẻ (&, <, >)
    res = html.escape(text)
    
    # 2. In đậm: **text** hoặc *text*
    res = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', res, flags=re.DOTALL)
    # Nếu người dùng gõ *text* đơn
    res = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<b>\1</b>', res)
    
    # 3. In nghiêng: __text__ hoặc _text_
    res = re.sub(r'__(.+?)__', r'<i>\1</i>', res, flags=re.DOTALL)
    res = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', res)
    
    # 4. Gạch ngang: ~~text~~
    res = re.sub(r'~~(.+?)~~', r'<s>\1</s>', res, flags=re.DOTALL)
    
    # 5. Inline code: `text`
    res = re.sub(r'`(.+?)`', r'<code>\1</code>', res)
    
    return res

from telethon import TelegramClient

from .common import (
    ROOT_DIR,
    TOOLS_BASE_DIR,
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_BOT_TOKEN,
    ensure_telegram_session,
    find_mapping_file,
    get_tags_for_group
)

def load_channel_stores(c_type):
    """
    Đọc và hợp nhất danh sách Siêu thị & Chat ID từ File Excel kho tương ứng 
    kết hợp với CONFIG_DATA_STORES.json (lấy các Chat ID lưu tại mục Kho Khô/Rau/Đông Mát).
    """
    workspace_root = os.path.dirname(ROOT_DIR)
    json_path = os.path.join(workspace_root, "CONFIG_DATA_STORES.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(ROOT_DIR, "CONFIG_DATA_STORES.json")
    
    stores_map = {} # store_id.upper() -> dict
    
    if c_type in ["kho_kho", "dc", "kho"]:
        channel_name = "📦 KHO KHÔ (DC)"
        excel_path = find_mapping_file("Danh_Sach_Chat_ID_Nhom_DC.xlsx")
        if not os.path.exists(excel_path):
            excel_path = os.path.join(workspace_root, "Danh_Sach_Chat_ID_Nhom_DC.xlsx")
        json_key = "chat_id_dc"
    elif c_type in ["rau_cu", "rc"]:
        channel_name = "🥦 RAU CỦ (KRC)"
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Rau_Cu.xlsx")
        if not os.path.exists(excel_path):
            excel_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "Danh sách Siêu thị.xlsx")
        json_key = "chat_id_rc"
    else:
        channel_name = "🥩 ĐÔNG MÁT / THỊT CÁ"
        excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
        if not os.path.exists(excel_path):
            excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        json_key = "chat_id_dm"

    print(f"📁 Kênh gửi: {channel_name}")
    
    # 1. Đọc từ File Excel (nếu có)
    if os.path.exists(excel_path):
        try:
            print(f"   + Đọc File Excel: {excel_path}")
            df_excel = pd.read_excel(excel_path, dtype=str)
            id_col = 'MÃ SIÊU THỊ' if 'MÃ SIÊU THỊ' in df_excel.columns else ('ID ST' if 'ID ST' in df_excel.columns else ('ID ST TƯƠNG ỨNG' if 'ID ST TƯƠNG ỨNG' in df_excel.columns else df_excel.columns[0]))
            chat_col = 'CHAT ID (SỐ CHUẨN)' if 'CHAT ID (SỐ CHUẨN)' in df_excel.columns else ('CHAT ID' if 'CHAT ID' in df_excel.columns else df_excel.columns[1])
            name_col = 'TÊN NHÓM TELEGRAM' if 'TÊN NHÓM TELEGRAM' in df_excel.columns else ('Tên Siêu thị' if 'Tên Siêu thị' in df_excel.columns else id_col)
            
            for _, r in df_excel.iterrows():
                sid = str(r.get(id_col, '')).strip().upper() if pd.notna(r.get(id_col)) else ''
                cid = str(r.get(chat_col, '')).replace('.0', '').strip() if pd.notna(r.get(chat_col)) else ''
                sname = str(r.get(name_col, '')).strip() if pd.notna(r.get(name_col)) else sid
                short = str(r.get('Tên viết tắt', sid)).strip() if 'Tên viết tắt' in df_excel.columns and pd.notna(r.get('Tên viết tắt')) else sid
                if sid and sid != '---' and cid and cid != 'nan':
                    stores_map[sid] = {
                        'ID ST': sid,
                        'Tên Siêu thị': sname,
                        'Tên viết tắt': short or sid,
                        'CHAT ID': cid
                    }
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc file Excel {excel_path}: {e}")

    # 2. Đọc và hợp nhất từ CONFIG_DATA_STORES.json (Ưu tiên Chat ID mới nhất lưu tại mục Kho Khô / Rau Củ / Đông Mát)
    if os.path.exists(json_path):
        try:
            print(f"   + Đọc cấu hình JSON: {json_path} (Trường: '{json_key}')")
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            json_added = 0
            json_updated = 0
            for item in json_data:
                sid = str(item.get('id', '')).strip().upper()
                sname = str(item.get('name', '')).strip() or sid
                short = str(item.get('short', sid)).strip() or sid
                cid = str(item.get(json_key, '')).strip()
                if sid and cid and cid != 'nan':
                    if sid in stores_map:
                        if stores_map[sid]['CHAT ID'] != cid:
                            stores_map[sid]['CHAT ID'] = cid
                            json_updated += 1
                    else:
                        stores_map[sid] = {
                            'ID ST': sid,
                            'Tên Siêu thị': sname,
                            'Tên viết tắt': short,
                            'CHAT ID': cid
                        }
                        json_added += 1
            if json_added > 0 or json_updated > 0:
                print(f"   + Đồng bộ từ JSON: Thêm mới {json_added} ST, cập nhật {json_updated} Chat ID.")
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc file JSON {json_path}: {e}")

    rows = list(stores_map.values())
    if not rows:
        return pd.DataFrame(columns=['ID ST', 'Tên Siêu thị', 'Tên viết tắt', 'CHAT ID'])
    
    df_res = pd.DataFrame(rows)
    return df_res

async def run(stores="ALL", message=None, tag_roles=True, dry_run=False, photo_path=None, chat_id_type="dong_mat"):
    c_type = str(chat_id_type).lower().strip() if chat_id_type else "dong_mat"
    df = load_channel_stores(c_type)

    if df.empty:
        print("❌ Không có dữ liệu Siêu thị hoặc Chat ID nào được tìm thấy cho kênh này!")
        return

    # Xử lý danh sách cửa hàng
    selected_indices = []
    if not stores or str(stores).strip().upper() == "ALL":
        selected_indices = list(range(len(df)))
        print(f"📋 Đã chọn: TẤT CẢ {len(selected_indices)} Siêu thị có Chat ID")
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

    if not message or not str(message).strip():
        print("❌ LỖI BẢO VỆ: Bạn chưa nhập nội dung tin nhắn cụ thể (--message). Đã hủy gửi để tránh spam nhầm thông báo mẫu!")
        return
    raw_message = str(message).strip()

    session_file = ensure_telegram_session()
    session_base = session_file.replace('.session', '')

    client = TelegramClient(session_base, TELEGRAM_API_ID, TELEGRAM_API_HASH)
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
            sent_ok = False
            # Chuẩn hóa văn bản sang định dạng HTML Telegram an toàn tuyệt đối
            html_msg = convert_markdown_to_telegram_html(msg)

            # 1. Thử gửi qua Telegram Bot API trước (với parse_mode='HTML')
            try:
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        resp = requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                            data={'chat_id': chat_id, 'caption': html_msg, 'parse_mode': 'HTML'},
                            files={'photo': f},
                            timeout=20
                        )
                else:
                    resp = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        data={'chat_id': chat_id, 'text': html_msg, 'parse_mode': 'HTML'},
                        timeout=20
                    )
                res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})

                # Xử lý Supergroup migration
                if resp.status_code == 400 and res_json.get('parameters', {}).get('migrate_to_chat_id'):
                    new_cid = res_json['parameters']['migrate_to_chat_id']
                    print(f"🔄 [CHUYỂN SUPERGROUP] ST {ten_st} đổi sang Chat ID: {new_cid}. Đang gửi lại ngay...", flush=True)
                    chat_id = new_cid
                    if photo_path and os.path.exists(photo_path):
                        with open(photo_path, 'rb') as f:
                            resp = requests.post(
                                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                                data={'chat_id': chat_id, 'caption': html_msg, 'parse_mode': 'HTML'},
                                files={'photo': f},
                                timeout=20
                            )
                    else:
                        resp = requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            data={'chat_id': chat_id, 'text': html_msg, 'parse_mode': 'HTML'},
                            timeout=20
                        )
                    res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})

                # Xử lý fallback nếu gặp lỗi parse entities
                if resp.status_code == 400 and "can't parse entities" in res_json.get('description', '').lower():
                    clean_plain = re.sub(r'<[^>]+>', '', html_msg)
                    if photo_path and os.path.exists(photo_path):
                        with open(photo_path, 'rb') as f:
                            resp = requests.post(
                                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                                data={'chat_id': chat_id, 'caption': clean_plain},
                                files={'photo': f},
                                timeout=20
                            )
                    else:
                        resp = requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            data={'chat_id': chat_id, 'text': clean_plain},
                            timeout=20
                        )
                    res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})

                if resp.status_code == 200 and res_json.get('ok'):
                    sent_ok = True
                else:
                    err_desc = res_json.get('description', f'HTTP {resp.status_code}')
                    if is_auth:
                        print(f"⚠️ [BOT BÁO LỖI] {ten_st} ({chat_id}): {err_desc} -> Chuyển sang Telethon User Client...")
            except Exception as ex_bot:
                if is_auth:
                    print(f"⚠️ [LỖI KẾT NỐI BOT] {ten_st}: {ex_bot} -> Chuyển sang Telethon User Client...")

            # 2. Dự phòng: Gửi qua Telethon User Client nếu Bot API thất bại
            if not sent_ok and is_auth:
                try:
                    if photo_path and os.path.exists(photo_path):
                        await client.send_file(int(chat_id), photo_path, caption=html_msg, parse_mode='html')
                    else:
                        await client.send_message(int(chat_id), html_msg, parse_mode='html')
                    sent_ok = True
                except Exception as ex_user:
                    print(f"❌ [LỖI USER CLIENT] {ten_st} ({chat_id}): {ex_user}")

            if sent_ok:
                print(f"🚀 [{i}/{total_count}] [ĐÃ GỬI] Thành công tới: {ten_st} ({chat_id})")
                success_count += 1
                await asyncio.sleep(1.2)
            else:
                print(f"❌ [{i}/{total_count}] [GỬI THẤT BẠI] {ten_st} ({chat_id})")

    await client.disconnect()
    print(f"\n🎉 HOÀN TẤT SPAM TÙY CHỌN! Đã gửi thành công {success_count}/{total_count} Siêu thị.")
