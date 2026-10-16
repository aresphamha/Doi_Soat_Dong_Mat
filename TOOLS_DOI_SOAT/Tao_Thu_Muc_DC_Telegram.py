"""
CÔNG CỤ TỰ ĐỘNG TẠO / CẬP NHẬT THƯ MỤC 'DC' TRÊN TELEGRAM
Gom tất cả các nhóm DC / Logistics / Kho vào thư mục riêng trên ứng dụng Telegram.
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
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.types import DialogFilter, TextWithEntities, Channel, Chat

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = CURRENT_DIR

API_ID = 31209455
API_HASH = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
SESSION_PATH = os.path.join(ROOT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'user_session')

def is_dc_group(title: str) -> bool:
    t_upper = (title or "").upper()
    if any(k in t_upper for k in ['ABA', 'ĐÔNG MÁT', 'DONG MAT']):
        return False
    if 'KRC' in t_upper:
        return False
    return any(k in t_upper for k in ['DC', 'LOGISTIC', 'KHO', 'CCDC', 'VẬN CHUYỂN', 'XE'])

async def create_or_update_dc_folder():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('❌ LỖI: Chưa có quyền truy cập Telegram user_session.')
        return

    me = await client.get_me()
    print(f"👤 Tài khoản: {me.first_name} {me.last_name or ''} (@{me.username})")

    res = await client(GetDialogFiltersRequest())
    filters = getattr(res, 'filters', res)
    existing_ids = [getattr(f, 'id', 0) for f in filters if getattr(f, 'id', None) is not None]

    dc_filter = None
    for f in filters:
        title_obj = getattr(f, 'title', None)
        title_text = getattr(title_obj, 'text', str(title_obj)) if title_obj else ''
        if title_text.strip().upper() in ['DC', 'KHO DC', 'DC - LOGISTICS']:
            dc_filter = f
            break

    target_id = dc_filter.id if dc_filter else (max(existing_ids, default=1) + 1)

    print("🔍 Đang quét danh sách các nhóm DC...")
    include_peers = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            title = dialog.name
            if is_dc_group(title):
                try:
                    peer = await client.get_input_entity(entity)
                    include_peers.append(peer)
                except Exception as e:
                    print(f"Bỏ qua '{title}': {e}")
                
                # Giới hạn tối đa 200 nhóm/folder của Telegram Premium
                if len(include_peers) >= 200:
                    break

    print(f"📦 Đã tìm thấy {len(include_peers)} nhóm DC.")

    filter_obj = DialogFilter(
        id=target_id,
        title=TextWithEntities(text="DC", entities=[]),
        pinned_peers=[],
        include_peers=include_peers,
        exclude_peers=[],
        contacts=False,
        non_contacts=False,
        groups=False,
        broadcasts=False,
        bots=False,
        exclude_muted=False,
        exclude_read=False,
        exclude_archived=False,
        title_noanimate=False,
        emoticon='🚚'
    )

    await client(UpdateDialogFilterRequest(id=target_id, filter=filter_obj))
    print(f"✅ ĐÃ TẠO / CẬP NHẬT THÀNH CÔNG THƯ MỤC 'DC' VỚI {len(include_peers)} NHÓM!")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(create_or_update_dc_folder())
