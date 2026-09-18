# -*- coding: utf-8 -*-
"""
TOOL TỰ ĐỘNG QUÉT & ĐỒNG BỘ DANH BẠ TAG QUẢN LÝ / TRƯỞNG CA (SM, GSM, TC)
Tự động quét 220+ nhóm Telegram siêu thị, trích xuất ID Telegram mới nhất,
lưu vào group_tags_map.json và đẩy lên Cloud GitHub Repository.
"""

import os
import sys
import json
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

def find_store_excel():
    candidates = [
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "RAU_CU", "Danh sách Siêu thị.xlsx"),
        os.path.join(ROOT_DIR, "TOOLS_DOI_SOAT", "DONG_MAT", "Danh sách Siêu thị.xlsx"),
        os.path.join(CONFIG_DATA_DIR, "Danh sách Siêu thị.xlsx")
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

        # 2. Upload blobs for all group_tags_map.json paths
        json_content = ""
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
            "message": "🔄 Auto-Sync Updated Telegram Manager Tags Registry (SM/GSM/TC)",
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

    excel_path = find_store_excel()
    if not os.path.exists(excel_path):
        print(f"❌ Không tìm thấy file Excel siêu thị: {excel_path}")
        return

    df = pd.read_excel(excel_path, dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
    print(f"📋 Đã tìm thấy {len(df)} Siêu thị có Chat ID trong {os.path.basename(excel_path)}")

    session_path = find_session_file()
    session_base = session_path.replace('.session', '')
    if not os.path.exists(session_path):
        print(f"❌ Chưa có file session Telegram: {session_path}")
        return

    # Load existing tag map
    existing_tags = {}
    main_json = os.path.join(CONFIG_DATA_DIR, "group_tags_map.json")
    if os.path.exists(main_json):
        try:
            with open(main_json, 'r', encoding='utf-8') as f:
                existing_tags = json.load(f)
        except Exception:
            pass

    client = TelegramClient(session_base, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Phiên Telegram chưa được xác thực trên máy tính.")
        await client.disconnect()
        return

    print("✅ Đã kết nối Telegram cá nhân. Đang quét từng nhóm...")

    updated_count = 0
    new_tags_map = dict(existing_tags)

    for i, row in df.iterrows():
        ten_st = str(row['Tên Siêu thị']).strip()
        chat_id_raw = str(row['CHAT ID']).replace('.0', '').strip()
        try:
            chat_id = int(chat_id_raw)
        except Exception:
            continue

        chat_key = str(chat_id)
        old_tag = existing_tags.get(chat_key, '')

        try:
            participants = await asyncio.wait_for(client.get_participants(chat_id), timeout=8)
            tags = []
            for p in participants:
                name = ""
                if p.first_name: name += p.first_name
                if p.last_name: name += " " + p.last_name
                name_upper = name.upper()
                if any(r in name_upper for r in [' TC', '-TC', ' SM', '-SM', ' GSM', '-GSM']):
                    tags.append(f"[{name}](tg://user?id={p.id})")

            current_tag = " ".join(tags) if tags else "@SM @TC @GSM"
            new_tags_map[chat_key] = current_tag

            if current_tag != old_tag:
                updated_count += 1
                print(f"✨ [{i+1}/{len(df)}] {ten_st} CÓ THAY ĐỔI TAG:")
                print(f"   Cu:  {old_tag or '(Chua co)'}")
                print(f"   Moi: {current_tag}")
            else:
                print(f"✓ [{i+1}/{len(df)}] {ten_st}: OK ({len(tags)} quan ly)")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"⚠️ [{i+1}/{len(df)}] {ten_st} ({chat_id}): Không thể quét thành viên ({e})")

    await client.disconnect()

    # Save to all target paths
    for p in get_target_json_paths():
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(new_tags_map, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    print("\n==============================================================================")
    print(f"🎉 HOÀN TẤT! Đã lưu {len(new_tags_map)} nhóm vào group_tags_map.json (Có {updated_count} nhóm thay đổi).")
    print("==============================================================================")

    # Push to GitHub
    push_tags_to_github()

if __name__ == "__main__":
    asyncio.run(main())
