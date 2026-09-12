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

            if d.message:
                m = d.message
                last_date_raw = m.date.isoformat() if m.date else ""
                last_date_str = m.date.strftime("%d/%m/%Y %H:%M") if m.date else ""
                if m.message:
                    last_msg_text = m.message.replace('\n', ' ').strip()
                    if len(last_msg_text) > 200:
                        last_msg_text = last_msg_text[:197] + "..."
                if getattr(m, 'photo', None) or getattr(m, 'document', None):
                    has_photo = True
                    if not last_msg_text:
                        last_msg_text = "[Hình ảnh / Chứng từ]"

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
                "is_channel": d.is_channel,
                "is_group": d.is_group
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
        "has_recent_activity": False
    })

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

        g_summary = {
            "title": g["title"],
            "chat_id_str": g["chat_id_str"],
            "group_type": g["group_type"],
            "unread": g["unread"],
            "last_message": g["last_message"],
            "last_date": g["last_date"],
            "last_date_raw": g["last_date_raw"]
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
        "other_count": sum(1 for g in groups_data if g["group_type"] not in ["ABA - Đông Mát", "KRC", "Đối soát & IC", "Kho DC & Logistics", "Nội bộ SCM"])
    }

    ticker_groups = [g for g in groups_data if g["last_message"] and g["last_date"]]
    ticker_groups.sort(key=lambda x: x.get("last_date_raw", ""), reverse=True)
    ticker_items = []
    for g in ticker_groups[:15]:
        snippet = g["last_message"]
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        ticker_items.append({
            "group_title": g["title"],
            "store_code": g["store_code"],
            "snippet": snippet,
            "time": g["last_date"]
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
            "Chat ID": g["chat_id_str"],
            "Tên Group Telegram": g["title"],
            "Phân Loại Nhóm": g["group_type"],
            "Danh Mục": g["category"],
            "Mã Siêu Thị": g["store_code"],
            "Tên Siêu Thị": g["store_name"],
            "Kho Phụ Trách": g["kho_tag"],
            "Tin Nhắn Gần Nhất": g["last_message"],
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
    print(f"✨ Cụm có nhóm đã gom: {summary['clusters_with_groups']} Siêu thị.")
    print(f"✨ Cụm có đủ cả ABA & KRC: {summary['clusters_with_both']} Siêu thị.")
    print("==============================================================================")


def main():
    result = asyncio.run(fetch_telegram_groups())
    if result:
        groups_data, account_info, store_map = result
        store_clusters = build_store_clusters(groups_data, store_map)
        export_all(groups_data, account_info, store_clusters)


if __name__ == "__main__":
    main()
