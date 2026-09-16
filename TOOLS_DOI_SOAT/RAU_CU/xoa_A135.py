import asyncio, sys, os
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient

api_id   = 28938971
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
BOT_ID   = 8810108114
TU_KHOA  = ['RAU CU', 'HAU KIEM', 'RAU CỦ', 'HẬU KIỂM']
CHAT_ID  = -1004437324085  # A135

current_dir  = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(current_dir, '..', 'ĐÔNG MÁT', 'user_session')

async def main():
    async with TelegramClient(session_path, api_id, api_hash) as client:
        print('Đăng nhập OK, đang quét A135 (bao gồm tất cả topics)...')
        entity = await client.get_entity(CHAT_ID)
        to_del = []

        # Quét main + tất cả topic (forum groups dùng reply_to=topic_id)
        # General topic thường là id=1, thử quét 200 tin không lọc topic
        async for msg in client.iter_messages(entity, limit=200):
            sid = None
            try: sid = msg.sender_id or (msg.from_id.user_id if msg.from_id else None)
            except: pass

            # Nếu không có sender_id, vẫn kiểm tra nội dung
            txt = (getattr(msg, 'text', '') or '') + (getattr(msg, 'caption', '') or '')
            is_bot = (sid == BOT_ID)
            has_kw = any(k.upper() in txt.upper() for k in TU_KHOA)

            if is_bot and has_kw:
                print(f'  [MAIN] Tìm thấy: msg_id={msg.id} topic={getattr(msg,"reply_to",None)} date={msg.date}')
                to_del.append(msg.id)

        # Thử thêm topic General (reply_to=1)
        try:
            async for msg in client.iter_messages(entity, limit=100, reply_to=1):
                sid = None
                try: sid = msg.sender_id or (msg.from_id.user_id if msg.from_id else None)
                except: pass
                txt = (getattr(msg, 'text', '') or '') + (getattr(msg, 'caption', '') or '')
                if (sid == BOT_ID) and any(k.upper() in txt.upper() for k in TU_KHOA):
                    if msg.id not in to_del:
                        print(f'  [TOPIC-1] Tìm thấy: msg_id={msg.id} date={msg.date}')
                        to_del.append(msg.id)
        except Exception as e:
            print(f'  Topic 1 error: {e}')

        if to_del:
            await client.delete_messages(entity, to_del)
            print(f'  ✅ Đã xoá {len(to_del)} tin trong A135!')
        else:
            print('  ℹ️  Không tìm thấy tin nào (kiểm tra BOT_ID có đúng không?)')
            # Debug: in thử 5 tin gần nhất của bot bất kể nội dung
            print('  Debug - 5 tin gần nhất trong group:')
            async for msg in client.iter_messages(entity, limit=5):
                sid = None
                try: sid = msg.sender_id or (msg.from_id.user_id if msg.from_id else None)
                except: pass
                txt = ((getattr(msg,'text','') or '') + (getattr(msg,'caption','') or ''))[:50]
                print(f'    id={msg.id} sender={sid} text={txt!r}')

asyncio.run(main())
