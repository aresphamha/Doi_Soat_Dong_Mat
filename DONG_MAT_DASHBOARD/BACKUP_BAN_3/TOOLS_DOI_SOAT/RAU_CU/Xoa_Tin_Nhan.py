import asyncio
import os
import sys
import re
import argparse
import requests
from telethon import TelegramClient

sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

API_ID = 28938971
API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
BOT_TOKEN = '8810108114:AAHWJjis5O3bFyx98-qjOs1PQKTAKMem_zU'
URL_DELETE = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'

current_dir = os.path.dirname(os.path.abspath(__file__))
candidate_sessions = [
    os.path.join(current_dir, '..', 'DONG_MAT', 'user_session'),
    os.path.join(current_dir, '..', '..', 'user_session'),
    os.path.join(os.getcwd(), 'user_session'),
    r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT\user_session'
]
session_path = candidate_sessions[0]
for s in candidate_sessions:
    if os.path.exists(s + '.session'):
        session_path = s
        break

def parse_args():
    parser = argparse.ArgumentParser(description="Thu hồi & xóa tin nhắn rác/spam trên Telegram")
    parser.add_argument('--keyword', '--message', dest='keyword', default=None, help='Từ khóa/câu chữ bắt buộc khớp')
    parser.add_argument('--limit', type=int, default=1500, help='Giới hạn số tin quét tối đa')
    parser.add_argument('--dry-run', action='store_true', help='Chế độ chạy thử, không xóa thật')
    return parser.parse_args()

def is_spam_match(text, keyword):
    if not text or not keyword:
        return False
    t = text.lower()
    k = keyword.lower().strip()
    
    # 1. Khớp nguyên văn
    if k in t:
        return True
        
    # 2. Khớp sau khi bỏ dấu hai chấm ':' ở cuối
    k_no_colon = k.rstrip(':').strip()
    if k_no_colon and k_no_colon in t:
        return True
        
    # 3. Khớp sau khi loại bỏ emoji và ký tự đặc biệt
    k_clean = re.sub(r'[^\w\s:/\.]', '', k).strip()
    if k_clean and k_clean in t:
        return True

    # 4. Kiểm tra link bot spam thường gặp
    if 'anonymouspumptrades' in k and 'anonymouspumptrades' in t:
        return True
    if 'to use this bot' in k and 'to use this bot' in t and 'channel' in t:
        return True

    return False

async def main():
    args = parse_args()
    raw_kw = args.keyword or os.environ.get('CLEAN_KEYWORD') or 'To use this bot, you must join our channel'
    keyword = raw_kw.strip()
    limit = args.limit or 1500
    is_dry_run = args.dry_run

    print('=' * 80)
    print('🧹 TRẠM THU HỒI & XÓA TIN NHẮN TẬN GỐC (SCM CLEAN SPAM BOT)')
    print(f'🔑 TỪ KHÓA BẮT BUỘC KHỚP: "{keyword}"')
    print(f'⚙️ CHẾ ĐỘ: {"🔍 [DRY-RUN - CHẠY THỬ / CHỈ QUÉT]" if is_dry_run else "⚡ [XÓA THẬT 100%]" }')
    print(f'📊 GIỚI HẠN QUÉT: Tối đa {limit} tin nhắn')
    print('🛡️ CƠ CHẾ KÉP: Xóa ưu tiên bằng Bot API -> Fallback xóa bằng User Session')
    print('=' * 80)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print('❌ LỖI: Session Telegram chưa được xác thực!')
        await client.disconnect()
        return

    print('✅ Đăng nhập Telegram thành công!')

    search_q = re.sub(r'[^\w\s\.]', ' ', keyword).strip()
    search_q = ' '.join(search_q.split()[:8])
    if not search_q or len(search_q) < 3:
        search_q = 'To use this bot'

    print(f'🔍 Đang tìm kiếm tin nhắn trên máy chủ Telegram (Query: "{search_q}")...')
    
    deleted_count = 0
    found_count = 0
    groups_affected = set()

    try:
        async for m in client.iter_messages(None, search=search_q, limit=limit):
            txt = (getattr(m, 'text', '') or '') + ' ' + (getattr(m, 'caption', '') or '')
            if is_spam_match(txt, keyword):
                found_count += 1
                try:
                    chat = await m.get_chat()
                    chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
                except Exception:
                    chat_name = f'Chat {m.chat_id}'
                
                groups_affected.add(m.chat_id)
                short_txt = (txt.strip().replace('\n', ' ')[:65] + '...') if len(txt.strip()) > 65 else txt.strip()

                if is_dry_run:
                    print(f'  🔎 [CHẠY THỬ ĐÃ TÌM THẤY] Nhóm: "{chat_name}" (ID: {m.chat_id}) | Msg ID: {m.id} | Nội dung: "{short_txt}"')
                else:
                    deleted = False
                    try:
                        res = requests.post(URL_DELETE, data={'chat_id': m.chat_id, 'message_id': m.id}, timeout=10).json()
                        if res.get('ok'):
                            deleted = True
                            deleted_count += 1
                            print(f'  ✅ [XÓA BOT THÀNH CÔNG] Nhóm: "{chat_name}" (ID: {m.chat_id}) | Msg ID: {m.id}')
                    except Exception as e_bot:
                        pass

                    if not deleted:
                        try:
                            await client.delete_messages(m.chat_id, [m.id], revoke=True)
                            deleted_count += 1
                            print(f'  ✅ [XÓA USER THÀNH CÔNG] Nhóm: "{chat_name}" (ID: {m.chat_id}) | Msg ID: {m.id}')
                        except Exception as e_usr:
                            print(f'  ⚠️ [KHÔNG THỂ XÓA] Nhóm: "{chat_name}" | Msg ID: {m.id} | Lỗi: {e_usr}')

                    await asyncio.sleep(0.04)

    except Exception as e_scan:
        print(f'⚠️ Lỗi trong quá trình quét tin nhắn: {e_scan}')

    await client.disconnect()

    print('\n' + '=' * 80)
    print('🎉 HOÀN TẤT QUÁ TRÌNH THU HỒI TIN NHẮN!')
    print(f'- TỔNG SỐ TIN RÁC TÌM THẤY: {found_count} tin nhắn.')
    if is_dry_run:
        print(f'- CHẾ ĐỘ CHẠY THỬ: Đã giả lập kiểm tra {found_count} tin trên {len(groups_affected)} nhóm.')
        print('👉 Tắt chế độ Dry-Run trên giao diện và bấm chạy lại để XÓA THẬT.')
    else:
        print(f'- TỔNG CỘNG ĐÃ XÓA THÀNH CÔNG: {deleted_count} tin nhắn trên {len(groups_affected)} nhóm.')
    print('=' * 80)

if __name__ == '__main__':
    asyncio.run(main())
