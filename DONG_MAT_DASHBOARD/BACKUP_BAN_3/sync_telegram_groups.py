# -*- coding: utf-8 -*-
"""
Hệ thống Tự động Đồng bộ Nhóm Telegram SCM Kingfoodmart & Gom Cụm Siêu Thị Realtime
- Nhóm ABA, Đông Mát và Nhóm KRC được gom thành Cụm Siêu Thị của Mình (Store Clusters)
- Cập nhật thông tin Realtime từ Telegram: Tin nhắn mới nhất, thời gian trao đổi, số tin chưa đọc, chứng từ ảnh
- Sử dụng Telethon với tài khoản chính: 0978009295 (KFM - SCM - Hà Phạm)
"""

import os
import sys
import json
import re
import asyncio
from datetime import datetime
from collections import defaultdict
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

API_ID = 28938971
API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
SESSION_NAME = 'user_session'

# Determine directories dynamically
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Ensure directories exist
os.makedirs(os.path.join(CURRENT_DIR, 'data'), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, 'daily_details'), exist_ok=True)

# Find store map excel
STORE_EXCEL_PATH = os.path.join(CURRENT_DIR, 'data', 'Danh_Sach_Sieu_Thi.xlsx')
if not os.path.exists(STORE_EXCEL_PATH):
    c_excel = r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT\Danh sách Siêu thị.xlsx'
    if os.path.exists(c_excel):
        STORE_EXCEL_PATH = c_excel

OUTPUT_JSON_PATH = os.path.join(CURRENT_DIR, 'data', 'telegram_groups.json')
OUTPUT_JS_PATH = os.path.join(ROOT_DIR, 'daily_details', 'telegram_groups.js')
OUTPUT_EXCEL_PATH = os.path.join(ROOT_DIR, 'Danh_Sach_Group_Telegram_SCM.xlsx')


def load_store_map():
    store_map = {}
    name_to_id = {}
    chat_to_store = {}

    if os.path.exists(STORE_EXCEL_PATH):
        try:
            df = pd.read_excel(STORE_EXCEL_PATH, dtype=str)
            id_col = [c for c in df.columns if 'ID ST' in c or 'MÃ ST' in c][0]
            name_col = [c for c in df.columns if 'Tên Siêu thị' in c or 'Chi nhánh' in c][0]
            chat_col = [c for c in df.columns if 'CHAT' in c.upper()][0] if any('CHAT' in c.upper() for c in df.columns) else None

            for _, row in df.iterrows():
                id_st = str(row.get(id_col, '') or '').strip().upper()
                name_st = str(row.get(name_col, '') or '').strip()
                chat_id = str(row.get(chat_col, '') or '').strip() if chat_col else ''
                
                if id_st and id_st.lower() != 'nan':
                    # Format as standard A### e.g. A101
                    m = re.search(r'\d+', id_st)
                    if m:
                        std_code = f"A{int(m.group(0)):03d}"
                    else:
                        std_code = id_st

                    # Clean store address
                    clean_name = re.sub(r'^KFM_[A-Z0-9]+_[A-Z0-9]+\s*-\s*', '', name_st)

                    store_map[std_code] = {
                        "store_code": std_code,
                        "raw_id": id_st,
                        "store_name": clean_name or name_st,
                        "full_name": name_st,
                        "chat_id_excel": chat_id
                    }

                    if clean_name and len(clean_name) >= 4:
                        name_to_id[clean_name.lower()] = std_code
                    if name_st and len(name_st) >= 5:
                        name_to_id[name_st.lower()] = std_code

                    if chat_id and chat_id != 'nan':
                        chat_to_store[chat_id] = std_code
                        if not chat_id.startswith('-100') and chat_id.startswith('-'):
                            chat_to_store['-100' + chat_id[1:]] = std_code

        except Exception as e:
            print(f"⚠️ Không thể đọc file danh sách siêu thị: {e}")

    return store_map, name_to_id, chat_to_store


def extract_store_code_from_title(title: str, chat_id: str, store_map: dict, name_to_id: dict, chat_to_store: dict) -> str:
    if not title:
        return ""

    # 1. Match by Chat ID
    if chat_id and chat_id in chat_to_store:
        return chat_to_store[chat_id]

    t_clean = title.strip()

    # 2. Pattern A + số (A101, A174, A01, A-101, A_101)
    m = re.search(r'\bA[-._\s]?(\d{2,4})\b', t_clean, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        cand = f"A{num:03d}"
        if cand in store_map:
            return cand
        cand_short = f"A{num}"
        if cand_short in store_map:
            return cand_short
        return cand

    # 3. Pattern ST + số (ST01, ST-101)
    m = re.search(r'\bST[-._\s]?(\d{1,4})\b', t_clean, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        cand = f"A{num:03d}"
        if cand in store_map:
            return cand
        cand_st = f"ST{num:02d}"
        if cand_st in store_map:
            return cand_st
        return cand

    # 4. Pattern số đứng đầu hoặc sau gạch (001 - Thảo Điền)
    m2 = re.search(r'\b(0\d{2}|\d{3})\b', t_clean)
    if m2:
        num = int(m2.group(1))
        cand = f"A{num:03d}"
        if cand in store_map:
            return cand

    # 5. Match theo tên siêu thị / địa chỉ
    t_lower = t_clean.lower()
    for name, s_code in name_to_id.items():
        if len(name) >= 5 and name in t_lower:
            return s_code

    return ""


def classify_group(title: str, store_code: str, is_channel: bool):
    t_upper = (title or "").upper()

    kho_tags = []
    if 'ABA' in t_upper:
        kho_tags.append('ABA')
    if 'ĐÔNG MÁT' in t_upper or 'DONG MAT' in t_upper or 'CHILL' in t_upper or 'FROZEN' in t_upper:
        kho_tags.append('Đông Mát')
    if 'KRC' in t_upper:
        kho_tags.append('KRC')
    if 'THỊT CÁ' in t_upper or 'THIT CA' in t_upper or 'MEATFISH' in t_upper:
        kho_tags.append('Thịt Cá')

    kho_str = ", ".join(kho_tags) if kho_tags else ""

    if any(k in t_upper for k in ['ABA', 'ĐÔNG MÁT', 'DONG MAT']):
        group_type = "ABA - Đông Mát"
    elif 'KRC' in t_upper:
        group_type = "KRC"
    elif any(k in t_upper for k in ['ĐỐI SOÁT', 'DOI SOAT', 'IC -', 'KIỂM KÊ', 'CHÊNH LỆCH']):
        group_type = "Đối soát & IC"
    elif any(k in t_upper for k in ['DC', 'LOGISTIC', 'KHO', 'CCDC', 'VẬN CHUYỂN', 'XE']):
        group_type = "Kho DC & Logistics"
    elif any(k in t_upper for k in ['SCM', 'NỘI BỘ', 'REPORT', 'BÁO CÁO']):
        group_type = "Nội bộ SCM"
    elif is_channel:
        group_type = "Kênh Thông Báo"
    else:
        group_type = "Nhóm Khác"

    category = "Nhóm Siêu thị" if store_code else group_type

    return category, group_type, kho_str


def is_broadcast_or_spam_message(text: str) -> bool:
    """
    Loại trừ 100% các tin nhắn thông báo, nhắc việc, quy chế, bot gửi tự động:
    - Lịch định kỳ: 📅, 🗓️, 📢, 🔔
    - Các mẫu mở đầu: 'Hi team', 'Chào team', 'Cảm ơn team', 'Lưu ý quan trọng', 'Remind'...
    - Tin SCM/Coordinator nhắc việc gửi hàng loạt cho Siêu thị (như: ST bổ sung thêm hình ảnh, ST kiểm tra lại giúp,
      ghi nhận ST nhận dư nhưng không add phiếu HK, tránh phát sinh ảnh hưởng vận hành, phát sinh lần sau...)
    - Chỉ đạo / quy chế camera, thùng rổ, cutoff...
    """
    if not text:
        return False
    t = text.strip()
    t_lower = t.lower()

    # 1. Các biểu tượng lịch, loa phát thanh gửi định kỳ
    if re.search(r'[📅🗓️📢🔔]\s*\d{1,2}[./-]\d{1,2}', t):
        return True

    # 2. Tiền tố chào hỏi / nhắc nhở / thông báo gửi hàng loạt
    announcement_prefixes = [
        'hi team', 'chào team', 'cảm ơn team', 'chào cả nhà', 'chào anh chị',
        'anh remind lại', 'remind lại', 'remind',
        'thông báo:', 'thông báo quan trọng', 'lưu ý quan trọng', 'lưu ý:',
        'st lưu ý', 'siêu thị lưu ý', 'quy chế', 'hướng dẫn kiểm hàng',
        'cảnh báo kiểm tra date', 'thời điểm cutoff', 'lưu ý nhận hàng'
    ]
    for p in announcement_prefixes:
        if t_lower.startswith(p) or f'\n{p}' in t_lower:
            return True

    # 3. Mẫu Coordinator SCM nhắc nhở / thông báo / cảnh báo gửi siêu thị:
    scm_request_patterns = [
        r'st\s+(bổ\s+sung\s+thêm\s+hình\s+ảnh|bổ\s+sung\s+hình\s+ảnh|gửi\s+hình\s+ảnh|chụp\s+lại\s+hình\s+ảnh)',
        r'hình\s+ảnh\s+phải\s+thấy\s+rõ\s+số\s+kg',
        r'sau\s+thời\s+gian\s+trên|sau\s+\d+h\s+ngày',
        r'không\s+nhận\s+được\s+phản\s+hồi.*hệ\s+thống\s+trả\s+tồn',
        r'ghi\s+nhận\s+st\s+nhận\s+dư\s+nhưng\s+không\s+add',
        r'ghi\s+nhận\s+st\s+vừa\s+trừ\s+tn\s+vừa\s+add',
        r'ghi\s+nhận\s+st\s+nhập\s+thiếu',
        r'không\s+thông\s+tin\s+scm\s+tạo\s+bổ\s+sung',
        r'tránh\s+phát\s+sinh\s+ảnh\s+hưởng\s+vận\s+hành',
        r'phát\s+sinh\s+lần\s+sau.*tiếp\s+theo|phát\s+sinh\s+lần\s+sau.*liên\s+quan',
        r'st\s+lưu\s+ý\s+(ktra|kiểm\s+tra|nhập\s+đúng)',
        r'st\s+(kiểm\s+tra|ktra|báo|hoàn\s+thành|xác\s+nhận)\s+lại?\s+giúp\s+(hà|ny|thấm|thư|quỳnh|nhung|scm)',
        r'(báo|kiểm\s+tra|ktra|gửi)\s+giúp\s+(hà|ny|thấm|thư|quỳnh|nhung|scm)',
        r'điều\s+chuyển\s+kịp\s+thời\s+nhé\s+cảm\s+ơn\s+team',
        r'cảm\s+ơn\s+team',
        r'nhờ\s+team\s+đối\s+soát',
        r'báo\s+siêu\s+thị\s+rút\s+tồn\s+về\s+kho\s+giúp',
        r'nhập\s+sót\s+sl\s+các\s+mã\s+hàng\s+trên',
        r'case\s+này.*bổ\s+sung\s+cam|case\s+này.*gửi\s+lại\s+danh\s+sách',
        r'(thư|thấm|hà|ny|quỳnh|nhung|scm|p|q|t)\s+gửi\s+(phiếu|pt|po)\s*(bs|bổ\s+sung|rút\s+tồn)?',
        r'phiếu\s+auto\s+nhập\s+tồn\s+st|hệ\s+thống\s+tự\s+nhập\s+tồn',
        r'(nhé|nha|giúp)\s+(st|siêu\s+thị)\b.*(gửi|check|ktra|kiểm\s+tra|hủy|cam|done|lưu\s+ý|báo|nhập|rút\s+tồn)',
        r'cho\s+e\s+xin\s+đoạn\s+cam|gửi\s+về\s+dc\s+claim|claim\s+nhé\s+st'
    ]
    for pat in scm_request_patterns:
        if re.search(pat, t_lower):
            return True

    # 4. Các quy chế vận hành, camera, thùng rổ, cutoff
    broadcast_phrases = [
        'lưu ý quan trọng',
        'hậu kiểm hàng thịt cá',
        'kiểm hàng đúng vị trí camera',
        'thao tác kiểm đếm',
        'thao tác kiểm đếm và cân hàng',
        'trong vùng camera',
        'trả rổ/thùng xanh',
        'bắt buộc phải có trip',
        'không có trip sẽ không thực hiện trả',
        'st bắt buộc phải scan từng kiện',
        'bắt buộc phải scan',
        'báo cáo phát sinh nhận hàng',
        'thời điểm cutoff',
        'cảnh báo kiểm tra date',
        'kiểm tra gấp xem có hết date',
        'file import của',
        'hoàn thành phiếu hậu kiểm',
        'nhận dư add vào phiếu hậu kiểm',
        'nhận dư nhưng không add phiếu hk',
        'không thông tin scm tạo bổ sung',
        'tránh phát sinh ảnh hưởng vận hành',
        'phát sinh lần sau',
        'st quay lại giúp anh đoạn video',
        'st quay lại giúp anh đoạn clip',
        'st chụp lại giúp anh',
        'hàng không đạt chất lượng'
    ]
    for phrase in broadcast_phrases:
        if phrase in t_lower:
            return True

    # 5. Regex bot ngày tháng định kỳ
    if re.search(r'(thịt cá|đông mát|rau củ quả|krc|aba)\s*\d{1,2}[./-]\d{1,2}', t_lower) and ('kiểm tra lại giúp' in t_lower or 'nhập sót' in t_lower or 'đếm sót' in t_lower):
        return True

    if 'remind' in t_lower:
        return True

    return False


def analyze_message_priority(msg_text: str, is_from_store: bool, has_photo: bool, is_broadcast: bool) -> tuple:
    """
    Phân loại cấp độ cảnh báo nghiệp vụ (CHỈ áp dụng cho phản hồi thực tế từ Siêu Thị/Đối Tác):
    - urgent (1. Khẩn Cấp): Dư mã hàng, Dư SL lớn, Vượt sức bán, Cần điều chuyển gấp, Giao sai/lộn mã, Hư hỏng nặng/bể vỡ, Lỗi TO...
    - high (2. Ưu Tiên Cao): Cần tạo bổ sung (PO/PT BS), Yêu cầu rút tồn kho, Cần tạo PO/TO...
    - medium (3. ST Phản Hồi): ST báo thực nhận, nhận thiếu, hàng hủy, date, đối soát...
    - normal (4. Thông Thường): Tin nhắn khác, done/ok, hoặc chưa có phản hồi.
    """
    if not msg_text or is_broadcast or not is_from_store:
        return "normal", "⚪ Thông Thường", ""

    t_lower = msg_text.lower()

    # 1. KHẨN CẤP (Store báo khẩn)
    urgent_patterns = [
        (r'dư\s+mã\s+hàng', 'DƯ MÃ HÀNG'),
        (r'dư\s+số\s+lượng\s+lớn|dư\s+sl\s+lớn|dư\s+nhiều', 'DƯ SL LỚN'),
        (r'vượt\s+sức\s+bán', 'VƯỢT SỨC BÁN'),
        (r'cần\s+điều\s+chuyển|điều\s+chuyển\s+gấp|chuyển\s+gấp', 'ĐIỀU CHUYỂN GẤP'),
        (r'giao\s+sai\s+kiện|giao\s+sai\s+mã|giao\s+lộn\s+hàng|giao\s+nhầm', 'GIAO SAI HÀNG'),
        (r'hư\s+hỏng\s+nặng|chảy\s+nước|hư\s+hỏng\s+hàng\s+loạt|bể\s+vỡ|bị\s+bể|bể\s+\d+', 'HÀNG HƯ HỎNG/BỂ VỠ'),
        (r'lỗi\s+to|to\s+lỗi|không\s+quét\s+được\s+to|to\s+không\s+vào', 'LỖI TO'),
        (r'gấp\s+lắm|xử\s+lý\s+gấp|khẩn\s+cấp|hỗ\s+trợ\s+gấp|cứu\s+gấp', 'CẦN XỬ LÝ GẤP')
    ]
    for pat, label in urgent_patterns:
        if re.search(pat, t_lower):
            return "urgent", "🚨 Khẩn Cấp", label

    # 2. ƯU TIÊN CAO: Yêu cầu Tạo BS / Rút tồn từ ST
    high_patterns = [
        (r'tạo\s+bổ\s+sung|tạo\s+bs|po\s+bổ\s+sung|po\s+bs|phiếu\s+bổ\s+sung|phiếu\s+bs|pt\s+bổ\s+sung|pt\s+bs|nhập\s+bổ\s+sung|nhập\s+bs', 'CẦN TẠO BS'),
        (r'rút\s+tồn|xin\s+mã\s+pt|mã\s+pt', 'CẦN RÚT TỒN'),
        (r'cần\s+tạo\s+po|thiếu\s+to|chưa\s+có\s+to', 'CẦN TẠO PO/TO')
    ]
    for pat, label in high_patterns:
        if re.search(pat, t_lower):
            return "high", "⚡ Ưu Tiên Cao", label

    # 3. TRUNG BÌNH: ST Phản Hồi thực tế
    medium_patterns = [
        (r'thực\s+nhận|nhận\s+thiếu|giao\s+thiếu|thiếu\s+\d+|dư\s+\d+|không\s+nhận', 'ST BÁO NHẬN/THIẾU/DƯ'),
        (r'hàng\s+hủy|hàng\s+trả|trả\s+về|hàng\s+hư|hàng\s+dập|hết\s+date|cận\s+date|sai\s+date', 'ST BÁO HÀNG TRẢ/HỦY/DATE'),
        (r'lệch\s+tồn|chênh\s+lệch|đã\s+nhập|chưa\s+nhập|phiếu\s+hậu\s+kiểm|phiếu\s+hk|đã\s+add|đã\s+báo|xác\s+nhận', 'ST PHẢN HỒI ĐỐI SOÁT')
    ]
    for pat, label in medium_patterns:
        if re.search(pat, t_lower):
            return "medium", "💬 ST Phản Hồi", label

    if is_from_store and (len(t_lower) >= 3 or has_photo):
        return "medium", "💬 ST Phản Hồi", "Ý kiến ST"

    return "normal", "⚪ Thông Thường", ""


async def fetch_telegram_groups():
    print("==============================================================================")
    print("🚀 BẮT ĐẦU ĐỒNG BỘ REALTIME & GOM CỤM NHÓM TELEGRAM SCM (0978009295)...")
    print("==============================================================================")

    store_map, name_to_id, chat_to_store = load_store_map()
    print(f"📋 Đã nạp từ điển {len(store_map)} Siêu thị từ danh mục SCM.")

    # Locate user_session.session
    session_file = os.path.join(CURRENT_DIR, SESSION_NAME)
    if not os.path.exists(session_file + '.session') and not os.path.exists(session_file):
        alt_sess = r'g:\My Drive\Đối soát SCM\DONG_MAT_DASHBOARD\user_session'
        if os.path.exists(alt_sess + '.session'):
            session_file = alt_sess
        else:
            alt_c = r'C:\Users\Thu Ha\Doi_Soat_Dong_Mat\DONG_MAT_DASHBOARD\user_session'
            if os.path.exists(alt_c + '.session'):
                session_file = alt_c

    client = TelegramClient(session_file, API_ID, API_HASH)

    groups_data = []
    account_info = {
        "name": "KFM - SCM - Hà Phạm - SC007251",
        "username": "@HaPham_SCM",
        "phone": "0978009295",
        "status": "Đã kết nối Session",
        "synced_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("⚠️ Session chưa được cấp quyền đăng nhập!")
            return None

        me = await client.get_me()
        my_id = me.id if me else None
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        account_info["name"] = full_name or account_info["name"]
        account_info["phone"] = f"+{me.phone}" if me.phone else account_info["phone"]
        account_info["username"] = f"@{me.username}" if me.username else account_info["username"]
        account_info["synced_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        print(f"✅ Tài khoản Telegram xác thực: {account_info['name']} ({account_info['phone']}) - {account_info['username']}")
        print(f"⏰ Thời gian đồng bộ: {account_info['synced_at']}")
        print("⏳ Đang quét danh sách hội thoại và nhóm Telegram...")

        dialogs = await client.get_dialogs()
        print(f"🔍 Tìm thấy tổng cộng {len(dialogs)} hội thoại trong tài khoản.")

        for d in dialogs:
            if not (d.is_group or d.is_channel):
                continue

            entity = d.entity
            title = d.name or getattr(entity, 'title', '')
            raw_id = entity.id

            if isinstance(entity, Channel):
                chat_id_str = f"-100{raw_id}"
            elif isinstance(entity, Chat):
                chat_id_str = f"-{raw_id}"
            else:
                chat_id_str = f"-100{raw_id}" if not str(raw_id).startswith("-") else str(raw_id)

            store_code = extract_store_code_from_title(title, chat_id_str, store_map, name_to_id, chat_to_store)
            store_name = store_map.get(store_code, {}).get("store_name", "") if store_code else ""

            category, group_type, kho_str = classify_group(title, store_code, d.is_channel)

            last_msg_text = ""
            last_date_str = ""
            last_date_raw = None
            has_photo = False
            is_from_store = True
            recent_msgs_list = []
            store_msgs = []
            prio_rank = {"urgent": 4, "high": 3, "medium": 2, "normal": 1}

            if d.message:
                raw_top_text = d.message.message or ""

                # Lấy 8 tin nhắn gần nhất để hiển thị lịch sử hội thoại và tìm tin ST phản hồi
                try:
                    recent_msgs = await client.get_messages(d.entity, limit=8)
                except Exception:
                    recent_msgs = [d.message] if d.message else []

                # Duyệt qua các tin nhắn gần nhất (từ mới đến cũ)
                for rm in recent_msgs:
                    rm_text = rm.message or ""
                    rm_sender_id = getattr(rm, 'sender_id', None)
                    rm_is_out = bool(getattr(rm, 'out', False) or (my_id and rm_sender_id == my_id))
                    rm_has_photo = bool(getattr(rm, 'photo', None) or getattr(rm, 'document', None))
                    rm_is_spam = is_broadcast_or_spam_message(rm_text)

                    # Gán tên người gửi hiển thị
                    if rm_is_out:
                        s_name = "Bạn (SCM)"
                    elif store_code:
                        s_name = f"Siêu thị {store_code}"
                    else:
                        s_name = "Siêu thị / Đối tác"

                    # Phân tích cấp độ cho từng tin nhắn
                    m_level, m_badge, m_reason = analyze_message_priority(rm_text, not rm_is_out, rm_has_photo, rm_is_spam)

                    msg_item = {
                        "id": rm.id,
                        "text": rm_text.strip(),
                        "time": rm.date.strftime("%d/%m/%Y %H:%M") if rm.date else "",
                        "time_short": rm.date.strftime("%H:%M") if rm.date else "",
                        "date_iso": rm.date.isoformat() if rm.date else "",
                        "is_me": rm_is_out,
                        "sender_name": s_name,
                        "has_photo": rm_has_photo,
                        "media_info": "Hình ảnh / Chứng từ đính kèm" if rm_has_photo and not rm_text else "",
                        "is_spam": rm_is_spam,
                        "priority_level": m_level,
                        "priority_badge": m_badge,
                        "priority_reason": m_reason
                    }
                    recent_msgs_list.append(msg_item)

                    # Nếu là tin nhắn phản hồi thực tế từ Siêu Thị (không phải SCM và không phải thông báo phát thanh)
                    if not rm_is_out and not rm_is_spam and (rm_text or rm_has_photo):
                        store_msgs.append((msg_item, m_level, m_badge, m_reason))

                # Đảo ngược lại theo thứ tự thời gian tăng dần để hiển thị trong khung chat (cũ -> mới)
                recent_msgs_list.reverse()

            # Xác định TIN MỚI NHẤT (ST PHẢN HỒI) và CẤP ĐỘ CẢNH BÁO
            # TUYỆT ĐỐI KHÔNG HIỂN THỊ TIN THÔNG BÁO Ở ĐÂY
            if store_msgs:
                # Tin ST phản hồi gần nhất (phần tử đầu tiên trong store_msgs vì duyệt từ mới đến cũ)
                latest_store_item, _, _, _ = store_msgs[0]
                last_msg_text = latest_store_item.get("text", "").replace('\n', ' ').strip()
                if not last_msg_text and latest_store_item.get("has_photo"):
                    last_msg_text = "[Hình ảnh / Chứng từ]"
                if len(last_msg_text) > 200:
                    last_msg_text = last_msg_text[:197] + "..."

                last_date_str = latest_store_item.get("time", "")
                last_date_raw = latest_store_item.get("date_iso", "")
                is_from_store = True
                has_photo = bool(latest_store_item.get("has_photo"))

                # Cấp độ cảnh báo của nhóm = MỨC CAO NHẤT trong các tin ST phản hồi gần nhất
                best_prio = max(store_msgs, key=lambda x: prio_rank.get(x[1], 1))
                p_level = best_prio[1]
                p_badge = best_prio[2]
                p_reason = best_prio[3]
            else:
                # Không có tin phản hồi từ Siêu thị (chỉ có tin thông báo định kỳ hoặc chưa có tin)
                last_msg_text = ""
                last_date_raw = d.message.date.isoformat() if d.message and d.message.date else ""
                last_date_str = d.message.date.strftime("%d/%m/%Y %H:%M") if d.message and d.message.date else ""
                is_from_store = False
                has_photo = False
                p_level = "normal"
                p_badge = "⚪ Thông Thường"
                p_reason = ""

            unread = d.unread_count or 0

            groups_data.append({
                "chat_id_str": chat_id_str,
                "raw_id": raw_id,
                "title": title,
                "store_code": store_code,
                "store_name": store_name,
                "category": category,
                "group_type": group_type,
                "kho_tag": kho_str,
                "unread": unread,
                "last_message": last_msg_text,
                "last_date": last_date_str,
                "last_date_raw": last_date_raw or "",
                "has_photo": has_photo,
                "is_from_store": is_from_store,
                "is_channel": d.is_channel,
                "is_group": d.is_group,
                "priority_level": p_level,
                "priority_badge": p_badge,
                "priority_reason": p_reason,
                "recent_messages": recent_msgs_list
            })

    except Exception as e:
        print(f"❌ Lỗi khi quét Telegram: {e}")
        return None
    finally:
        await client.disconnect()

    print(f"✅ Đã phân loại {len(groups_data)} nhóm Telegram nghiệp vụ SCM Kingfoodmart.")
    return groups_data, account_info, store_map


def build_store_clusters(groups_data: list, store_map: dict):
    clusters_map = defaultdict(lambda: {
        "store_code": "",
        "store_name": "",
        "aba_groups": [],
        "krc_groups": [],
        "other_groups": [],
        "total_groups": 0,
        "unread_total": 0,
        "latest_message_snippet": "",
        "last_activity_date": "",
        "last_activity_raw": "",
        "has_recent_activity": False,
        "max_priority": "normal"
    })

    priority_rank = {"urgent": 4, "high": 3, "medium": 2, "normal": 1}

    # Pre-populate all stores from store_map
    for code, info in store_map.items():
        clusters_map[code]["store_code"] = code
        clusters_map[code]["store_name"] = info.get("store_name", "")

    # Group matches into clusters
    for g in groups_data:
        s_code = g["store_code"]
        if not s_code:
            continue

        c = clusters_map[s_code]
        c["store_code"] = s_code
        if not c["store_name"] and g["store_name"]:
            c["store_name"] = g["store_name"]

        c["total_groups"] += 1
        c["unread_total"] += g["unread"]

        g_prio = g.get("priority_level", "normal")
        if priority_rank.get(g_prio, 1) > priority_rank.get(c["max_priority"], 1):
            c["max_priority"] = g_prio

        g_summary = {
            "title": g["title"],
            "chat_id_str": g["chat_id_str"],
            "group_type": g["group_type"],
            "unread": g["unread"],
            "last_message": g["last_message"],
            "last_date": g["last_date"],
            "last_date_raw": g["last_date_raw"],
            "priority_level": g.get("priority_level", "normal"),
            "priority_badge": g.get("priority_badge", "⚪ Thông Thường"),
            "priority_reason": g.get("priority_reason", "")
        }

        if "ABA" in g["group_type"] or "Đông Mát" in g["group_type"]:
            c["aba_groups"].append(g_summary)
        elif "KRC" in g["group_type"]:
            c["krc_groups"].append(g_summary)
        else:
            c["other_groups"].append(g_summary)

        if g["last_date_raw"] and (not c["last_activity_raw"] or g["last_date_raw"] > c["last_activity_raw"]):
            c["last_activity_raw"] = g["last_date_raw"]
            c["last_activity_date"] = g["last_date"]
            c["latest_message_snippet"] = f"[{g['group_type']}] {g['last_message']}" if g['last_message'] else ""

    def store_sort_key(item):
        code = item["store_code"]
        m = re.search(r'\d+', code)
        return int(m.group(0)) if m else 9999

    cluster_list = list(clusters_map.values())
    cluster_list.sort(key=store_sort_key)

    return cluster_list


def export_all(groups_data, account_info, store_clusters):
    urgent_cnt = sum(1 for g in groups_data if g.get("priority_level") == "urgent")
    high_cnt = sum(1 for g in groups_data if g.get("priority_level") == "high")
    medium_cnt = sum(1 for g in groups_data if g.get("priority_level") == "medium")
    normal_cnt = sum(1 for g in groups_data if g.get("priority_level") == "normal")

    summary = {
        "account": account_info,
        "total_groups": len(groups_data),
        "total_clusters": len(store_clusters),
        "clusters_with_groups": sum(1 for c in store_clusters if c["total_groups"] > 0),
        "clusters_with_both": sum(1 for c in store_clusters if c["aba_groups"] and c["krc_groups"]),
        "aba_count": sum(1 for g in groups_data if g["group_type"] == "ABA - Đông Mát"),
        "krc_count": sum(1 for g in groups_data if g["group_type"] == "KRC"),
        "ic_count": sum(1 for g in groups_data if g["group_type"] == "Đối soát & IC"),
        "dc_count": sum(1 for g in groups_data if g["group_type"] == "Kho DC & Logistics"),
        "internal_count": sum(1 for g in groups_data if g["group_type"] == "Nội bộ SCM"),
        "chat_id_count": sum(1 for g in groups_data if "chat id" in g["group_type"].lower() or "chat id" in g["title"].lower()),
        "other_count": sum(1 for g in groups_data if g["group_type"] not in ["ABA - Đông Mát", "KRC", "Đối soát & IC", "Kho DC & Logistics", "Nội bộ SCM"]),
        "urgent_count": urgent_cnt,
        "high_count": high_cnt,
        "medium_count": medium_cnt,
        "normal_count": normal_cnt
    }

    # Ticker: ưu tiên tin nhắn Khẩn cấp / Ưu tiên cao / ST phản hồi
    ticker_groups = [g for g in groups_data if g["last_message"] and g.get("priority_level") in ["urgent", "high", "medium"]]
    if len(ticker_groups) < 10:
        extra = [g for g in groups_data if g["last_message"] and g not in ticker_groups]
        ticker_groups.extend(extra)

    ticker_groups.sort(key=lambda x: (
        0 if x.get("priority_level") == "urgent" else 1 if x.get("priority_level") == "high" else 2 if x.get("priority_level") == "medium" else 3,
        -(datetime.fromisoformat(x["last_date_raw"]).timestamp() if x.get("last_date_raw") else 0)
    ))

    ticker_items = []
    for g in ticker_groups[:20]:
        snippet = g["last_message"]
        if len(snippet) > 85:
            snippet = snippet[:82] + "..."
        ticker_items.append({
            "group_title": g["title"],
            "store_code": g["store_code"],
            "snippet": snippet,
            "time": g["last_date"],
            "priority_badge": g.get("priority_badge", ""),
            "priority_level": g.get("priority_level", "normal")
        })

    full_payload = {
        "summary": summary,
        "ticker": ticker_items,
        "clusters": store_clusters,
        "groups": groups_data
    }

    def save_to_all(paths, content, is_json=False):
        for p in paths:
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'w', encoding='utf-8') as f:
                    if is_json:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    else:
                        f.write(content)
            except Exception as e:
                print(f"Warning writing to {p}: {e}")

    g_root = r'g:\My Drive\Đối soát SCM'
    c_root = r'C:\Users\Thu Ha\Doi_Soat_Dong_Mat'

    json_paths = [
        os.path.join(CURRENT_DIR, 'data', 'telegram_groups.json'),
        os.path.join(g_root, 'DONG_MAT_DASHBOARD', 'data', 'telegram_groups.json'),
        os.path.join(c_root, 'DONG_MAT_DASHBOARD', 'data', 'telegram_groups.json'),
    ]
    save_to_all(json_paths, full_payload, is_json=True)

    js_content = f"window.TELEGRAM_GROUPS_DATA = {json.dumps(full_payload, ensure_ascii=False)};"
    js_paths = [
        os.path.join(ROOT_DIR, 'daily_details', 'telegram_groups.js'),
        os.path.join(CURRENT_DIR, 'daily_details', 'telegram_groups.js'),
        os.path.join(g_root, 'daily_details', 'telegram_groups.js'),
        os.path.join(g_root, 'DONG_MAT_DASHBOARD', 'daily_details', 'telegram_groups.js'),
        os.path.join(g_root, 'LOGIC', 'daily_details', 'telegram_groups.js'),
        os.path.join(c_root, 'daily_details', 'telegram_groups.js'),
        os.path.join(c_root, 'DONG_MAT_DASHBOARD', 'daily_details', 'telegram_groups.js'),
        os.path.join(c_root, 'LOGIC', 'daily_details', 'telegram_groups.js'),
    ]
    save_to_all(js_paths, js_content, is_json=False)

    rows_clusters = []
    for idx, c in enumerate(store_clusters, 1):
        aba_titles = " | ".join(g["title"] for g in c["aba_groups"])
        aba_ids = " | ".join(g["chat_id_str"] for g in c["aba_groups"])
        krc_titles = " | ".join(g["title"] for g in c["krc_groups"])
        krc_ids = " | ".join(g["chat_id_str"] for g in c["krc_groups"])

        rows_clusters.append({
            "STT": idx,
            "Mã Siêu Thị": c["store_code"],
            "Tên Siêu Thị": c["store_name"],
            "Mức Độ Ưu Tiên Cao Nhất": c.get("max_priority", "normal"),
            "Nhóm ABA - Đông Mát": aba_titles,
            "Chat ID ABA": aba_ids,
            "Nhóm KRC": krc_titles,
            "Chat ID KRC": krc_ids,
            "Hoạt Động Gần Nhất": c["last_activity_date"],
            "Tin Nhắn Mới Nhất": c["latest_message_snippet"],
            "Số Tin Chưa Đọc": c["unread_total"],
            "Đủ 2 Nhóm (ABA+KRC)": "CÓ" if c["aba_groups"] and c["krc_groups"] else "THIẾU"
        })

    rows_detail = []
    for idx, g in enumerate(groups_data, 1):
        rows_detail.append({
            "STT": idx,
            "Cấp Độ Cảnh Báo": g.get("priority_badge", "⚪ Thông Thường"),
            "Lý Do Cảnh Báo": g.get("priority_reason", ""),
            "Mã Siêu Thị": g["store_code"],
            "Tên Siêu Thị": g["store_name"],
            "Tên Group Telegram": g["title"],
            "Chat ID": g["chat_id_str"],
            "Phân Loại Nhóm": g["group_type"],
            "Danh Mục": g["category"],
            "Kho Phụ Trách": g["kho_tag"],
            "Tin Nhắn Thực Tế ST": g["last_message"],
            "Thời Gian": g["last_date"],
            "Tin Chưa Đọc": g["unread"]
        })

    excel_paths = [
        OUTPUT_EXCEL_PATH,
        os.path.join(g_root, 'Danh_Sach_Group_Telegram_SCM.xlsx'),
        os.path.join(c_root, 'Danh_Sach_Group_Telegram_SCM.xlsx'),
    ]
    for exp in excel_paths:
        try:
            with pd.ExcelWriter(exp, engine='openpyxl') as writer:
                pd.DataFrame(rows_clusters).to_excel(writer, sheet_name='Gom_Cum_Sieu_Thi', index=False)
                pd.DataFrame(rows_detail).to_excel(writer, sheet_name='Toan_Bo_Nhom_Telegram', index=False)
        except Exception as e:
            print(f"Warning writing excel {exp}: {e}")

    print(f"📊 Đã xuất file Excel: {OUTPUT_EXCEL_PATH}")
    print("==============================================================================")
    print(f"🎉 HOÀN TẤT ĐỒNG BỘ TELEGRAM SCM: {len(groups_data)} Nhóm | {len(store_clusters)} Cụm Siêu Thị!")
    print(f"🚨 Cảnh báo: {urgent_cnt} Khẩn cấp | ⚡ {high_cnt} Ưu tiên cao | 💬 {medium_cnt} ST Phản hồi | ⚪ {normal_cnt} Thông thường.")
    print("==============================================================================")


def main():
    result = asyncio.run(fetch_telegram_groups())
    if result:
        groups_data, account_info, store_map = result
        store_clusters = build_store_clusters(groups_data, store_map)
        export_all(groups_data, account_info, store_clusters)


if __name__ == "__main__":
    main()
