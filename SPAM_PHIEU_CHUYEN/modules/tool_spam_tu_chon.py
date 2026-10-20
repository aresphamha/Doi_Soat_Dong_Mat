# -*- coding: utf-8 -*-
"""
MODULE: SPAM TIN NHẮN TÙY CHỌN (CUSTOM SPAM STUDIO)
Cho phép người dùng tùy biến nội dung, gắn thẻ quản lý hoặc gửi ảnh đến từng siêu thị hoặc tất cả siêu thị.
"""

import os
import sys
import asyncio
from datetime import datetime
import pytz
import pandas as pd
import requests

from telethon import TelegramClient

from .common import (
    TOOLS_BASE_DIR,
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_BOT_TOKEN,
    ensure_telegram_session,
    find_mapping_file,
    get_tags_for_group
)

async def run(stores="ALL", message=None, tag_roles=True, dry_run=False, photo_path=None, chat_id_type="dong_mat"):
    c_type = str(chat_id_type).lower().strip() if chat_id_type else "dong_mat"
    if c_type in ["rau_cu", "rc"]:
        channel_name = "🥦 RAU CỦ (KRC)"
        excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Rau_Cu.xlsx")
        if not os.path.exists(excel_path):
            excel_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "Danh sách Siêu thị.xlsx")
        print(f"📁 Đang đọc File Chat ID KHO RAU CỦ: {excel_path}")
    elif c_type in ["kho_kho", "dc"]:
        channel_name = "📦 KHO KHÔ (DC)"
        excel_path = find_mapping_file("Danh_Sach_Chat_ID_Nhom_DC.xlsx")
        if not os.path.exists(excel_path):
            excel_path = os.path.join(os.path.dirname(TOOLS_BASE_DIR), "Danh_Sach_Chat_ID_Nhom_DC.xlsx")
        print(f"📁 Đang đọc File Chat ID KHO KHÔ (DC): {excel_path}")
    else:
        channel_name = "🥩 ĐÔNG MÁT / THỊT CÁ"
        excel_path = find_mapping_file("Danh sách Siêu thị.xlsx")
        if not os.path.exists(excel_path):
            excel_path = find_mapping_file("Danh_Sach_Sieu_Thi_Dong_Mat.xlsx")
        print(f"📁 Đang đọc File Chat ID KHO ĐÔNG MÁT / THỊT CÁ: {excel_path}")
        
    df = pd.read_excel(excel_path, dtype=str)
    
    # Chuẩn hóa tên cột linh hoạt cho cả 3 kho
    id_col = 'MÃ SIÊU THỊ' if 'MÃ SIÊU THỊ' in df.columns else ('ID ST' if 'ID ST' in df.columns else ('ID ST TƯƠNG ỨNG' if 'ID ST TƯƠNG ỨNG' in df.columns else df.columns[0]))
    chat_col = 'CHAT ID (SỐ CHUẨN)' if 'CHAT ID (SỐ CHUẨN)' in df.columns else ('CHAT ID' if 'CHAT ID' in df.columns else df.columns[1])
    name_col = 'TÊN NHÓM TELEGRAM' if 'TÊN NHÓM TELEGRAM' in df.columns else ('Tên Siêu thị' if 'Tên Siêu thị' in df.columns else id_col)

    df['ID ST'] = df[id_col].astype(str).str.strip()
    df['Tên Siêu thị'] = df[name_col].astype(str).str.strip()
    df['CHAT ID'] = df[chat_col].astype(str).str.replace('.0', '', regex=False).str.strip()
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'] != '') & (df['CHAT ID'] != 'nan')]

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
            try:
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                            data={'chat_id': chat_id, 'caption': msg, 'parse_mode': 'Markdown'},
                            files={'photo': f},
                            timeout=15
                        )
                else:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
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
