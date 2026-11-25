# -*- coding: utf-8 -*-
"""
Script đăng nhập và làm mới Session Telegram an toàn (0978009295)
"""
import os
import sys
import asyncio
import base64
from telethon import TelegramClient

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# API Credentials chuẩn xác của tài khoản SCM
API_ID = 31209455
API_HASH = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
PHONE_NUMBER = '+84978009295'

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(CURRENT_DIR, 'DONG_MAT_DASHBOARD', 'user_session.session')


def release_locked_session():
    """Tự động phát hiện và ngắt các tiến trình chạy ngầm đang chiếm dụng file session Telegram."""
    import time
    import urllib.request
    import subprocess

    print("🔍 Kiểm tra và giải phóng file session đang bị chiếm dụng...")
    
    # 1. Hủy tác vụ Telegram đang chạy trên local runner (nếu có)
    try:
        req = urllib.request.Request("http://127.0.0.1:8088/cancel", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            pass
    except Exception:
        pass

    # 2. Đóng tiến trình chạy sync_telegram_groups hoặc script spam đang chạy ngầm
    try:
        kill_cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*sync_telegram_groups*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"'
        subprocess.run(kill_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        pass

    # 3. Dọn dẹp file session và các file lock/journal của SQLite
    session_base = os.path.join(CURRENT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
    candidate_files = [
        session_base + '.session',
        session_base + '.session-journal',
        session_base + '.session-wal',
        session_base + '.session-shm',
    ]

    for attempt in range(5):
        still_locked = False
        for fpath in candidate_files:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as e:
                    still_locked = True
        if not still_locked:
            print("🗑️ Đã giải phóng và xóa file session cũ thành công.")
            return True
        time.sleep(0.8)

    print("⚠️ Chú ý: File session đang bị khóa bởi ứng dụng khác (ví dụ: Google Drive Sync hoặc tiến trình Python khác).")
    return False


async def main():
    print("==============================================================================")
    print(f"🔐 BẮT ĐẦU ĐĂNG NHẬP TELEGRAM CHO SỐ ĐIỆN THOẠI: {PHONE_NUMBER}")
    print("==============================================================================")
    
    # Giải phóng và xóa session cũ
    release_locked_session()

    client = TelegramClient(os.path.join(CURRENT_DIR, 'DONG_MAT_DASHBOARD', 'user_session'), API_ID, API_HASH)
    
    # Sử dụng client.start để tự động xử lý OTP và mật khẩu 2FA nếu có
    await client.start(phone=PHONE_NUMBER)

    me = await client.get_me()
    print(f"\n✅ ĐĂNG NHẬP THÀNH CÔNG: {me.first_name} {me.last_name or ''} ({me.phone}) - @{me.username or ''}")
    await client.disconnect()

    # Đồng bộ session vào các thư mục công cụ
    target_dirs = [
        CURRENT_DIR,
        os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA'),
        os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'CHI TIẾT MÁT'),
        os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'CHI TIẾT THỊT CÁ'),
        os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'HẬU KIỂM RAU'),
        os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'HẬU KIỂM THỊ CÁ'),
        os.path.join(CURRENT_DIR, 'TOOLS_DOI_SOAT', 'DONG_MAT'),
        os.path.join(CURRENT_DIR, 'TOOLS_DOI_SOAT', 'RAU_CU'),
        os.path.join(CURRENT_DIR, 'TOOLS_DOI_SOAT', 'THIT_CA', 'Tool_Spam'),
    ]

    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'rb') as sf:
            session_bytes = sf.read()
        
        for d in target_dirs:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, 'user_session.session'), 'wb') as df:
                df.write(session_bytes)
        
        # Lưu bản backup b64
        b64_str = base64.b64encode(session_bytes).decode('utf-8')
        with open(os.path.join(CURRENT_DIR, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'session_b64.txt'), 'w', encoding='utf-8') as bf:
            bf.write(b64_str)
        
        print("📁 Đã sao chép và phân bổ file session mới vào toàn bộ các công cụ đối soát!")
    
    print("==============================================================================")
    print("🎉 HOÀN TẤT ĐĂNG NHẬP! BÂY GIỜ BẠN CÓ THỂ BẤM CẬP NHẬT REALTIME BÌNH THƯỜNG.")
    print("==============================================================================")

if __name__ == '__main__':
    asyncio.run(main())
