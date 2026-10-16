# -*- coding: utf-8 -*-
"""
Hàm tiện ích và cấu hình dùng chung cho các Tool Spam Phiếu Chuyển SCM.
"""

import os
import sys
import json
import base64
import subprocess
import pymysql

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thư mục gốc SPAM_PHIEU_CHUYEN và đối soát
MODULES_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(MODULES_DIR)
CONFIG_DATA_DIR = os.path.join(ROOT_DIR, "CONFIG_DATA")
TOOLS_BASE_DIR = os.path.join(os.path.dirname(ROOT_DIR), "TOOLS_DOI_SOAT")

TELEGRAM_API_ID = '28938971'
TELEGRAM_API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
TELEGRAM_BOT_TOKEN = '8810108114:AAHWJjis5O3bFyx98-qjOs1PQKTAKMem_zU'

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
        os.path.join(ROOT_DIR, "HẬU KIỂM ĐÔNG MÁT", filename),
        os.path.join(ROOT_DIR, filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return candidates[0]

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
        password='TnAM0WEsv4kmasw878wt',
        database='kfm_scm',
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30
    )

def execute_external_tool(script_path, extra_args=None, cwd=None):
    """Thực thi file script Python cục bộ với môi trường UTF-8 chuẩn xác và in log Real-time từng dòng."""
    if not os.path.exists(script_path):
        print(f"❌ [LỖI] Không tìm thấy file script: {script_path}", flush=True)
        return False
    work_dir = cwd if cwd else os.path.dirname(script_path)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [sys.executable, "-u", script_path]
    if extra_args:
        cmd.extend(extra_args)
    try:
        proc = subprocess.Popen(
            cmd,
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
