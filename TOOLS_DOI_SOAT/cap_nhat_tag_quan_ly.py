# -*- coding: utf-8 -*-
"""
TOOL TỰ ĐỘNG QUÉT & ĐỒNG BỘ DANH BẠ TAG QUẢN LÝ / TRƯỞNG CA (SM, GSM, TC)
Tự động quét toàn bộ nhóm Telegram siêu thị (cả Kho Rau Củ và ABA Đông Mát/Thịt Cá),
nhận diện chính xác cú pháp vai trò SM, TC, GSM, TC(TT), SM(TT), _SM_, -SM-, v.v.,
lưu vào group_tags_map.json và đẩy lên Cloud GitHub Repository.
"""

import os
import sys
import json
import re
import asyncio
import base64
import urllib.request
import pandas as pd
from telethon import TelegramClient

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DATA_DIR = os.path.join(ROOT_DIR, "CONFIG_DATA")
SPAM_CONFIG_DIR = os.path.join(ROOT_DIR, "SPAM_PHIEU_CHUYEN", "CONFIG_DATA")

api_id = '28938971'
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'

def find_session_file():
    candidates = [
        os.path.join(SPAM_CONFIG_DIR, "user_session.session"),
        os.path.join(CONFIG_DATA_DIR, "user_session.session"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "DONG_MAT", "user_session.session"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "RAU_CU", "user_session.session")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return candidates[0]

def get_target_json_paths():
    return [
        os.path.join(CONFIG_DATA_DIR, "group_tags_map.json"),
        os.path.join(SPAM_CONFIG_DIR, "group_tags_map.json"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "CONFIG_DATA", "group_tags_map.json"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "RAU_CU", "group_tags_map.json"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "THIT_CA", "Tool_Spam", "group_tags_map.json"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "DONG_MAT", "group_tags_map.json")
    ]

def is_manager_role(name):
    if not name: return False
    name_upper = name.upper()
    pattern = r'(^|[\s\-_(\[\./])(SM|GSM|TC)([\s\-_)\]\./(]|$)'
    return bool(re.search(pattern, name_upper))

def push_tags_to_github():
    config_file = os.path.join(ROOT_DIR, ".github_config.json")
    if not os.path.exists(config_file):
        print("ℹ️ Không tìm thấy .github_config.json, bỏ qua bước push GitHub.")
        return
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        token = cfg.get('token', '')
        if not token:
            return

        owner_repo = "aresphamha/Doi_Soat_Dong_Mat"
        branch = "main"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SCM-Tag-Sync'
        }

        # 1. Get latest commit
        ref_url = f"https://api.github.com/repos/{owner_repo}/git/ref/heads/{branch}"
        req = urllib.request.Request(ref_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            ref_data = json.loads(resp.read().decode())
            latest_commit_sha = ref_data['object']['sha']

        # 2. Upload blobs
        main_json = os.path.join(CONFIG_DATA_DIR, "group_tags_map.json")
        with open(main_json, 'r', encoding='utf-8') as f:
            json_content = f.read()

        blob_url = f"https://api.github.com/repos/{owner_repo}/git/blobs"
        blob_payload = {"content": json_content, "encoding": "utf-8"}
        blob_req = urllib.request.Request(blob_url, data=json.dumps(blob_payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(blob_req) as b_resp:
            b_data = json.loads(b_resp.read().decode())
            blob_sha = b_data['sha']

        rel_paths = [
            "CONFIG_DATA/group_tags_map.json",
            "SPAM_PHIEU_CHUYEN/CONFIG_DATA/group_tags_map.json",
            "TOOLS_DOI_SOAT/CONFIG_DATA/group_tags_map.json",
            "TOOLS_DOI_SOAT/RAU_CU/group_tags_map.json",
            "TOOLS_DOI_SOAT/THIT_CA/Tool_Spam/group_tags_map.json",
            "TOOLS_DOI_SOAT/DONG_MAT/group_tags_map.json"
        ]

        tree_items = [{"path": p, "mode": "100644", "type": "blob", "sha": blob_sha} for p in rel_paths]

        tree_url = f"https://api.github.com/repos/{owner_repo}/git/trees"
        tree_payload = {"base_tree": latest_commit_sha, "tree": tree_items}
        tree_req = urllib.request.Request(tree_url, data=json.dumps(tree_payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(tree_req) as t_resp:
            new_tree_sha = json.loads(t_resp.read().decode())['sha']

        commit_url = f"https://api.github.com/repos/{owner_repo}/git/commits"
        commit_payload = {
            "message": "🔄 Full Sync Telegram Manager Tags Registry (SM/GSM/TC)",
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
        commit_req = urllib.request.Request(commit_url, data=json.dumps(commit_payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(commit_req) as c_resp:
            new_commit_sha = json.loads(c_resp.read().decode())['sha']

        update_ref_url = f"https://api.github.com/repos/{owner_repo}/git/refs/heads/{branch}"
        update_payload = {"sha": new_commit_sha, "force": False}
        update_req = urllib.request.Request(update_ref_url, data=json.dumps(update_payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(update_req) as u_resp:
            print(f"☁️ ĐÃ ĐỒNG BỘ DANH BẠ TAGS MỚI LÊN CLOUD GITHUB THÀNH CÔNG! ({new_commit_sha[:7]})")
    except Exception as e:
        print(f"⚠️ Không thể đồng bộ lên GitHub: {e}")

async def main():
    print("==============================================================================")
    print("🔄 BẮT ĐẦU QUÉT & CẬP NHẬT TỰ ĐỘNG TAG QUẢN LÝ / TRƯỞNG CA (SM, GSM, TC)")
    print("==============================================================================")

    session_path = find_session_file()
    session_base = session_path.replace('.session', '')
    if not os.path.exists(session_path):
        print(f"❌ Chưa có file session Telegram: {session_path}")
        return

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Phiên Telegram chưa được xác thực trên máy tính.")
        await client.disconnect()
        return

    print("✅ Đã kết nối Telegram cá nhân thành công.")

    # 1. Thu thập toàn bộ Chat ID từ các file Excel
    chat_info_map = {}
    excel_files = [
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "DONG_MAT", "Danh sách Siêu thị.xlsx"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "RAU_CU", "Danh sách Siêu thị.xlsx"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "DONG_MAT", "Danh_Sach_Sieu_Thi_Dong_Mat.xlsx"),
        os.path.join(CONFIG_DATA_DIR, "Danh sách Siêu thị.xlsx")
    ]
    for ef in excel_files:
        if os.path.exists(ef):
            try:
                df = pd.read_excel(ef, dtype=str)
                if 'CHAT ID' in df.columns:
                    valid = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
                    for _, row in valid.iterrows():
                        cid_clean = str(row['CHAT ID']).replace('.0', '').strip()
                        st_name = str(row.get('Tên Siêu thị', '')).strip()
                        try:
                            cid_int = int(cid_clean)
                            chat_info_map[cid_int] = st_name
                        except:
                            pass
            except Exception:
                pass

    # 2. Lấy danh sách dialogs từ Telegram
    dialogs = await client.get_dialogs()
    for d in dialogs:
        if d.is_group or d.is_channel:
            if d.id not in chat_info_map:
                chat_info_map[d.id] = d.name or str(d.id)

    print(f"📋 Tổng số Group Chat ID cần quét danh bạ: {len(chat_info_map)} nhóm")

    tag_map = {}
    found_count = 0

    for i, (cid, gname) in enumerate(chat_info_map.items(), 1):
        chat_key = str(cid)
        try:
            participants = await asyncio.wait_for(client.get_participants(cid), timeout=12)
            tags = []
            for p in participants:
                name = ""
                if p.first_name: name += p.first_name
                if p.last_name: name += " " + p.last_name
                name = name.strip()
                if is_manager_role(name):
                    tags.append(f"[{name}](tg://user?id={p.id})")

            if tags:
                tag_map[chat_key] = " ".join(tags)
                found_count += 1
                print(f"✓ [{i}/{len(chat_info_map)}] {gname}: {len(tags)} quản lý")
            else:
                tag_map[chat_key] = "@SM @TC @GSM"
        except Exception as e:
            tag_map[chat_key] = "@SM @TC @GSM"
            print(f"⚠️ [{i}/{len(chat_info_map)}] {gname} ({cid}): {e}")

        await asyncio.sleep(0.15)

    await client.disconnect()

    # 3. Ghi ra tất cả các file JSON
    for p in get_target_json_paths():
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(tag_map, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    print("\n==============================================================================")
    print(f"🎉 HOÀN TẤT! Đã quét và lưu {len(tag_map)} nhóm vào group_tags_map.json ({found_count} nhóm có Quản lý đích danh).")
    print("==============================================================================")

    push_tags_to_github()

if __name__ == "__main__":
    asyncio.run(main())
