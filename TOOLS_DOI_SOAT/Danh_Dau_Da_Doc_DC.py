"""
Đánh dấu đã đọc tất cả tin nhắn trong các nhóm thuộc nhóm Kho DC / Logistics.
"""
import asyncio
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient

API_ID = 31209455
API_HASH = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'user_session')

def is_dc_group(title: str) -> bool:
    t_upper = (title or "").upper()
    if any(k in t_upper for k in ['ABA', 'ĐÔNG MÁT', 'DONG MAT']):
        return False
    if 'KRC' in t_upper:
        return False
    return any(k in t_upper for k in ['DC', 'LOGISTIC', 'KHO', 'CCDC', 'VẬN CHUYỂN', 'XE'])

async def mark_dc_folder_read():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('❌ Chưa có quyền đăng nhập Telegram user_session.')
        return

    me = await client.get_me()
    print(f"👤 Tài khoản: {me.first_name} (@{me.username})")
    print(f"🔄 Đang quét các nhóm DC có tin chưa đọc để đánh dấu...")

    marked_count = 0
    total_unread_messages = 0

    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0 and is_dc_group(dialog.name):
            try:
                unread = dialog.unread_count
                await client.send_read_acknowledge(dialog.entity)
                marked_count += 1
                total_unread_messages += unread
                print(f"  ✓ {dialog.name} ({unread} tin)")
                await asyncio.sleep(0.05)
            except Exception as e:
                pass

    print(f"\n🎉 HOÀN TẤT: Đã đánh dấu ĐÃ ĐỌC cho {marked_count} nhóm DC (tổng cộng {total_unread_messages} tin nhắn)!")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(mark_dc_folder_read())
