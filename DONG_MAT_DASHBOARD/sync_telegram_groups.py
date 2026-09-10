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

CURRENT_DIR = r'C:\Users\Thu Ha\Doi_Soat_Dong_Mat\DONG_MAT_DASHBOARD'
ROOT_DIR = r'C:\Users\Thu Ha\Doi_Soat_Dong_Mat'

STORE_EXCEL_PATH = os.path.join(CURRENT_DIR, 'data', 'Danh_Sach_Sieu_Thi.xlsx')
if not os.path.exists(STORE_EXCEL_PATH):
    STORE_EXCEL_PATH = r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT\Danh sách Siêu thị.xlsx'

OUTPUT_JSON_PATH = os.path.join(CURRENT_DIR, 'data', 'telegram_groups.json')
OUTPUT_JS_PATH = os.path.join(ROOT_DIR, 'daily_details', 'telegram_groups.js')
OUTPUT_JS_LOCAL = os.path.join(CURRENT_DIR, 'daily_details', 'telegram_groups.js')
OUTPUT_EXCEL_PATH = os.path.join(ROOT_DIR, 'Danh_Sach_Group_Telegram_SCM.xlsx')


def load_store_map():
    store_map = {}
    name_to_id = {}
    if os.path.exists(STORE_EXCEL_PATH):
        try:
            df = pd.read_excel(STORE_EXCEL_PATH, dtype=str)
            id_col = [c for c in df.columns if 'ID ST' in c or 'MÃ ST' in c][0]
            name_col = [c for c in df.columns if 'Tên Siêu thị' in c or 'Chi nhánh' in c][0]
            chat_col = [c for c in df.columns if 'CHAT' in c.upper()][0] if any('CHAT' in c.upper() for c in df.columns) else None

            for _, row in df.iterrows():
                id_st = str(row.get(id_col, '') or '').strip()
                name_st = str(row.get(name_col, '') or '').strip()
                chat_id = str(row.get(chat_col, '') or '').strip() if chat_col else ''
                if id_st and id_st.lower() != 'nan':
                    code = id_st.upper()
                    store_map[code] = {
                        'id_st': code,
                        'name': name_st,
                        'default_chat_id': chat_id
                    }
                    if name_st:
                        name_to_id[name_st.lower()] = code
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc file Danh sách Siêu thị: {e}")
    return store_map, name_to_id


def extract_store_info(title, store_map, name_to_id):
    match = re.search(r'\b(A\d{3}|VH\d|LVN|MTE|HTN|Q7|BTH)\b', title, re.IGNORECASE)
    if match:
        code = match.group(1).upper()
        info = store_map.get(code)
        store_name = info['name'] if info else f"Siêu thị {code}"
        return code, store_name

    title_lower = title.lower()
    for name_key, code in name_to_id.items():
        keywords = [k.strip() for k in name_key.split('-') if len(k.strip()) > 4]
        for kw in keywords:
            if kw in title_lower:
                info = store_map.get(code)
                store_name = info['name'] if info else f"Siêu thị {code}"
                return code, store_name

    return "", ""


def classify_group(title, is_channel, store_code):
    t_upper = title.upper()

    kho_tags = []
    if "DC" in t_upper: kho_tags.append("Kho DC")
    if "ABA" in t_upper: kho_tags.append("Kho Lạnh ABA")
    if "KRC" in t_upper: kho_tags.append("Kho KRC")
    if "ĐÔNG MÁT" in t_upper or "DONG MAT" in t_upper: kho_tags.append("Đông Mát")
    if "THỊT CÁ" in t_upper or "THIT CA" in t_upper: kho_tags.append("Thịt Cá")
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


async def fetch_telegram_groups():
    print("==============================================================================")
    print("🚀 BẮT ĐẦU ĐỒNG BỘ REALTIME & GOM CỤM NHÓM TELEGRAM SCM (0978009295)...")
    print("==============================================================================")

    store_map, name_to_id = load_store_map()
    print(f"📋 Đã nạp từ điển {len(store_map)} Siêu thị.")

    session_file = os.path.join(CURRENT_DIR, SESSION_NAME)
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
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        account_info["name"] = full_name
        account_info["username"] = f"@{me.username}" if me.username else ""
        account_info["phone"] = getattr(me, 'phone', '0978009295')
        account_info["user_id"] = me.id
        print(f"✅ Đăng nhập: {full_name} ({account_info['username']}) - Phone: {account_info['phone']}")

        print("⏳ Đang quét danh bạ và trích xuất tin nhắn realtime...")
        async for dialog in client.iter_dialogs(limit=1000):
            entity = dialog.entity
            is_group = False
            is_channel = False

            if isinstance(entity, Chat):
                is_group = True
            elif isinstance(entity, Channel):
                if getattr(entity, 'megagroup', False):
                    is_group = True
                elif getattr(entity, 'broadcast', False):
                    is_channel = True
                else:
                    is_group = True

            if is_group or is_channel:
                title = dialog.name or "Không tên"
                chat_id = dialog.id
                chat_id_str = str(chat_id)
                alt_chat_id = ""
                if chat_id_str.startswith('-100'):
                    alt_chat_id = '-' + chat_id_str[4:]
                elif chat_id_str.startswith('-') and len(chat_id_str) <= 11:
                    alt_chat_id = '-100' + chat_id_str[1:]

                store_code, store_name = extract_store_info(title, store_map, name_to_id)
                category, group_type, kho_str = classify_group(title, is_channel, store_code)

                # Realtime Message Details
                msg = dialog.message
                msg_text = ""
                msg_date = ""
                msg_date_raw = 0
                has_media = False
                if msg:
                    msg_text = (msg.message or "").strip()
                    if msg.media:
                        has_media = True
                        if not msg_text:
                            msg_text = "📷 [Hình ảnh / Biên bản chênh lệch]"
                    if msg.date:
                        msg_date_raw = msg.date.timestamp()
                        msg_date = msg.date.strftime("%d/%m %H:%M")

                username = getattr(entity, 'username', '') or ''
                members = getattr(entity, 'participants_count', 0) or 0
                unread = dialog.unread_count or 0

                groups_data.append({
                    "id": chat_id,
                    "chat_id_str": chat_id_str,
                    "alt_chat_id": alt_chat_id,
                    "title": title,
                    "store_code": store_code,
                    "store_name": store_name,
                    "category": category,
                    "group_type": group_type,
                    "kho": kho_str,
                    "members": members,
                    "unread": unread,
                    "last_message": msg_text[:140] if msg_text else "",
                    "last_date": msg_date,
                    "last_date_raw": msg_date_raw,
                    "has_media": has_media,
                    "username": username,
                    "type": "Channel" if is_channel else "Group/Supergroup",
                    "link": f"https://t.me/{username}" if username else ""
                })

        print(f"🎉 Hoàn tất quét! Tổng cộng: {len(groups_data)} nhóm & kênh.")

    except Exception as e:
        print(f"❌ Lỗi Telethon: {e}")
    finally:
        await client.disconnect()

    # Xây dựng gom cụm Siêu thị ("Group Mình")
    clusters_map = {}
    for g in groups_data:
        code = g['store_code']
        if code:
            if code not in clusters_map:
                clusters_map[code] = {
                    "store_code": code,
                    "store_name": g['store_name'] or f"Siêu thị {code}",
                    "aba_groups": [],
                    "krc_groups": [],
                    "other_groups": [],
                    "unread_total": 0,
                    "last_activity_date": "",
                    "last_activity_raw": 0,
                    "latest_message_snippet": ""
                }
            c = clusters_map[code]
            if g['group_type'] == "ABA - Đông Mát":
                c['aba_groups'].append(g)
            elif g['group_type'] == "KRC":
                c['krc_groups'].append(g)
            else:
                c['other_groups'].append(g)

            c['unread_total'] += g['unread']
            if g['last_date_raw'] > c['last_activity_raw']:
                c['last_activity_raw'] = g['last_date_raw']
                c['last_activity_date'] = g['last_date']
                c['latest_message_snippet'] = f"[{g['group_type']}] {g['last_message']}"

    # Sắp xếp cụm siêu thị: Ưu tiên siêu thị vừa có hoạt động gần nhất lên đầu
    clusters_list = list(clusters_map.values())
    clusters_list.sort(key=lambda x: (
        -x['unread_total'],
        -x['last_activity_raw'],
        x['store_code']
    ))

    # Đếm số lượng theo loại nhóm
    aba_count = sum(1 for g in groups_data if g['group_type'] == "ABA - Đông Mát")
    krc_count = sum(1 for g in groups_data if g['group_type'] == "KRC")
    ic_count = sum(1 for g in groups_data if g['group_type'] == "Đối soát & IC")
    dc_count = sum(1 for g in groups_data if g['group_type'] == "Kho DC & Logistics")
    scm_count = sum(1 for g in groups_data if g['group_type'] == "Nội bộ SCM")

    # Realtime ticker items (top 15 recent messages)
    recent_messages = [g for g in groups_data if g['last_message']]
    recent_messages.sort(key=lambda x: x['last_date_raw'], reverse=True)
    ticker_items = []
    for rm in recent_messages[:15]:
        ticker_items.append({
            "store_code": rm['store_code'],
            "group_title": rm['title'],
            "group_type": rm['group_type'],
            "time": rm['last_date'],
            "snippet": rm['last_message'],
            "has_media": rm['has_media']
        })

    summary = {
        "total_groups": len(groups_data),
        "total_clusters": len(clusters_list),
        "aba_count": aba_count,
        "krc_count": krc_count,
        "ic_count": ic_count,
        "dc_count": dc_count,
        "scm_count": scm_count,
        "both_aba_krc_count": sum(1 for c in clusters_list if c['aba_groups'] and c['krc_groups']),
        "account": account_info
    }

    # Xuất file JSON
    payload = {
        "summary": summary,
        "clusters": clusters_list,
        "groups": groups_data,
        "ticker": ticker_items
    }
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Xuất file JS cho Web
    js_content = f"window.TELEGRAM_GROUPS_DATA = {json.dumps(payload, ensure_ascii=False)};"
    for js_path in [OUTPUT_JS_PATH, OUTPUT_JS_LOCAL]:
        os.makedirs(os.path.dirname(js_path), exist_ok=True)
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)

    # Xuất file Excel 2 Sheets
    cluster_rows = []
    for idx, c in enumerate(clusters_list, 1):
        aba_names = " | ".join(g['title'] for g in c['aba_groups'])
        aba_ids = " | ".join(g['chat_id_str'] for g in c['aba_groups'])
        krc_names = " | ".join(g['title'] for g in c['krc_groups'])
        krc_ids = " | ".join(g['chat_id_str'] for g in c['krc_groups'])

        cluster_rows.append({
            "STT": idx,
            "Mã Siêu Thị": c['store_code'],
            "Tên Siêu Thị": c['store_name'],
            "Nhóm ABA - Đông Mát": aba_names or "(Chưa có)",
            "Chat ID ABA": aba_ids or "",
            "Nhóm KRC": krc_names or "(Chưa có)",
            "Chat ID KRC": krc_ids or "",
            "Tin Chưa Đọc": c['unread_total'],
            "Hoạt Động Gần Nhất": c['last_activity_date'],
            "Tin Nhắn Mới Nhất": c['latest_message_snippet']
        })

    group_rows = []
    for idx, g in enumerate(groups_data, 1):
        group_rows.append({
            "STT": idx,
            "Mã ST": g['store_code'],
            "Tên Siêu Thị": g['store_name'],
            "Tên Group Telegram": g['title'],
            "Loại Nhóm": g['group_type'],
            "Phân Loại Nghiệp Vụ": g['category'],
            "Chat ID": g['chat_id_str'],
            "Kho Phụ Trách": g['kho'],
            "Số Thành Viên": g['members'],
            "Tin Chưa Đọc": g['unread'],
            "Thời Gian Tin Mới": g['last_date'],
            "Nội Dung Tin Mới": g['last_message']
        })

    with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine='openpyxl') as writer:
        pd.DataFrame(cluster_rows).to_excel(writer, sheet_name="Gom_Cum_Sieu_Thi", index=False)
        pd.DataFrame(group_rows).to_excel(writer, sheet_name="Toan_Bo_Group_Telegram", index=False)

    print(f"📊 Đã xuất Excel 2 Sheets: {OUTPUT_EXCEL_PATH}")
    print("==============================================================================")
    print(f"✅ HOÀN TẤT ĐỒNG BỘ REALTIME TELEGRAM SCM:")
    print(f"   - Tổng số Siêu thị gom cụm: {summary['total_clusters']}")
    print(f"   - Siêu thị có CẢ Group ABA & KRC: {summary['both_aba_krc_count']}")
    print(f"   - Tổng số Group ABA - Đông Mát: {summary['aba_count']}")
    print(f"   - Tổng số Group KRC: {summary['krc_count']}")
    print(f"   - Tổng số Group Đối Soát & IC: {summary['ic_count']}")
    print(f"   - Tổng số Nhóm quét được: {summary['total_groups']}")
    print("==============================================================================")

    return payload


if __name__ == '__main__':
    asyncio.run(fetch_telegram_groups())
