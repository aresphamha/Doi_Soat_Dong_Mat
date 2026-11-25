"""
CÔNG CỤ TỰ ĐỘNG ĐẾM & CẬP NHẬT SỐ LƯỢNG NHÓM VÀO TÊN THƯ MỤC TRÊN TELEGRAM
Tự động đếm chính xác số lượng nhóm trong từng Folder và gán vào tên (tối đa 12 ký tự theo chuẩn Telegram):
- DC -> DC (176)
- KRC -> KRC (199)
- KRC2 -> KRC2 (17)
- ITL - ABA -> ABA (200)
- SCM -> SCM (9)
- NCC -> NCC (2)
"""
import asyncio
import os
import re
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import TextWithEntities

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

API_ID = 31209455
API_HASH = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
SESSION_PATH = os.path.join(ROOT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'user_session')

# Tên viết tắt nếu tên gốc + (số) vượt quá 12 ký tự (giới hạn cứng của Telegram)
SHORT_NAMES = {
    'ITL - ABA': 'ABA',
    '🛻🚚🚛DC': 'DC',
    'DC - S': 'DC',
    'DC - ST': 'DC',
}

async def update_folder_names_with_counts():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('❌ LỖI: Chưa có quyền truy cập Telegram user_session.')
        return

    me = await client.get_me()
    print(f"👤 Tài khoản Telegram: {me.first_name} {me.last_name or ''} (@{me.username})")

    res = await client(GetDialogFiltersRequest())
    filters = getattr(res, 'filters', res)

    print("\n🔄 Đang tiến hành cập nhật tên thư mục kèm số lượng nhóm...")

    updated_count = 0
    for f in filters:
        fid = getattr(f, 'id', None)
        if fid is None:
            continue

        title_obj = getattr(f, 'title', None)
        raw_title = getattr(title_obj, 'text', str(title_obj)) if title_obj else ''
        raw_title = raw_title.strip()
        if not raw_title:
            continue

        # Lấy tên gốc, loại bỏ số lượng cũ (ví dụ "DC (197)" -> "DC")
        base_title = re.sub(r'\s*\(\d+\)$', '', raw_title).strip()
        base_title = SHORT_NAMES.get(base_title, base_title)
        
        peers_count = len(getattr(f, 'include_peers', []))
        suffix = f" ({peers_count})"
        
        # Đảm bảo tổng độ dài <= 12 ký tự (giới hạn của Telegram)
        max_base_len = 12 - len(suffix)
        if len(base_title) > max_base_len:
            base_title = base_title[:max_base_len].strip()

        new_title = f"{base_title}{suffix}"

        # Cập nhật title của filter
        f.title = TextWithEntities(text=new_title, entities=[])

        try:
            req = UpdateDialogFilterRequest(id=fid, filter=f)
            await client(req)
            print(f"  ✓ Thư mục: '{raw_title}'  --->  '{new_title}' (Có {peers_count} nhóm)")
            updated_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"  ❌ Lỗi khi cập nhật thư mục ({raw_title}): {e}")

    print(f"\n🎉 HOÀN TẤT: Đã cập nhật thành công {updated_count} thư mục trên Telegram!")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(update_folder_names_with_counts())
