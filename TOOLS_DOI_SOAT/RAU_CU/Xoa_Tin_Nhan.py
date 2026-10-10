import asyncio
import os
import sys
import datetime
import requests
import pandas as pd
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

API_ID = 28938971
API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
BOT_TOKEN = '8810108114:AAHWJjis5O3bFyx98-qjOs1PQKTAKMem_zU'
URL_DELETE = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'

current_dir = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(current_dir, '..', 'DONG_MAT', 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT', 'user_session')

KEYWORD_TO_DELETE = os.environ.get('CLEAN_KEYWORD', 'To use this bot, you must join our channel:')

async def main():
    print('=' * 80)
    print('🧹 TRẠM THU HỒI & XÓA TIN NHẮN TẬN GỐC BẰNG BOT API (CHẮC CHẮN 100%)')
    print(f'🔑 TỪ KHÓA BẮT BUỘC KHỚP: "{KEYWORD_TO_DELETE}"')
    print('🛡️ CƠ CHẾ: Dùng quyền của chính Bot gửi tin để xóa trực tiếp trên server Telegram')
    print('=' * 80)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print('❌ LỖI: Session Telegram chưa được xác thực!')
        await client.disconnect()
        return

    print('✅ Đăng nhập Telegram thành công!')
    
    deleted_count = 0
    
    # 1. Tìm kiếm toàn cục
    print(f'🔍 Đang tìm kiếm tin nhắn có chứa "{KEYWORD_TO_DELETE}"...')
    async for m in client.iter_messages(None, search=KEYWORD_TO_DELETE, limit=500):
        txt = (getattr(m, 'text', '') or '') + ' ' + (getattr(m, 'caption', '') or '')
        if KEYWORD_TO_DELETE.lower() in txt.lower():
            chat = await m.get_chat()
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            
            # Xóa bằng Bot API
            res = requests.post(URL_DELETE, data={'chat_id': m.chat_id, 'message_id': m.id}, timeout=10).json()
            if res.get('ok'):
                deleted_count += 1
                print(f'  ✅ [XÓA THẬT THÀNH CÔNG] Nhóm: "{chat_name}" (ID: {m.chat_id}) | Msg ID: {m.id}')
            else:
                try:
                    await client.delete_messages(m.chat_id, [m.id], revoke=True)
                    deleted_count += 1
                    print(f'  ✅ [XÓA USER THÀNH CÔNG] Nhóm: "{chat_name}" | Msg ID: {m.id}')
                except Exception as e:
                    pass
            await asyncio.sleep(0.04)

    await client.disconnect()
    
    print('\n' + '=' * 80)
    print(f'🎉 HOÀN TẤT THU HỒI SẠCH TIN RÁC BẰNG BOT API!')
    print(f'- TỔNG CỘNG ĐÃ XÓA THẬT THÀNH CÔNG: {deleted_count} tin nhắn.')
    print('=' * 80)

if __name__ == '__main__':
    asyncio.run(main())
