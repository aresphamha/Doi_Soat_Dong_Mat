import asyncio
import os
import sys
import re
import argparse
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
from telethon.tl.functions.messages import AddChatUserRequest, GetFullChatRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import (
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
    UserAlreadyParticipantError,
    FloodWaitError,
    PeerFloodError,
    UserNotParticipantError,
)

sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

api_id = 31209455
api_hash = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
current_dir = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(current_dir, 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'G:\My Drive\Đối soát SCM\DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'G:\My Drive\Đối soát SCM', 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT', 'user_session')

async def check_is_participant(client, group_entity, user_entity):
    try:
        if isinstance(group_entity, Channel):
            await client(GetParticipantRequest(channel=group_entity, participant=user_entity))
            return True
        elif isinstance(group_entity, Chat):
            full = await client(GetFullChatRequest(group_entity.id))
            return user_entity.id in [u.id for u in full.users]
    except UserNotParticipantError:
        return False
    except Exception:
        return False
    return False

def parse_target_chat_ids(raw_text):
    if not raw_text or raw_text.strip().upper() == 'ALL':
        return []
    found_ids = []
    # Tách theo dấu phẩy, khoảng trắng, xuống dòng
    tokens = re.split(r'[\s,;\n\r\t]+', raw_text.strip())
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        try:
            cid = int(t)
            found_ids.append(cid)
        except ValueError:
            clean = re.sub(r'[^\d\-]', '', t)
            if clean and clean not in ['-', '']:
                try:
                    found_ids.append(int(clean))
                except Exception:
                    pass
    # Loại bỏ trùng lặp nhưng giữ nguyên thứ tự
    seen = set()
    unique_ids = []
    for x in found_ids:
        if x not in seen:
            seen.add(x)
            unique_ids.append(x)
    return unique_ids

async def main():
    parser = argparse.ArgumentParser(description="Tool tự động thêm Bot / Thành viên vào Group Telegram")
    parser.add_argument("--member", default=os.environ.get('TARGET_MEMBER', '@doi_soat_SCM_bot'), help="Username hoặc ID của Bot/User cần thêm")
    parser.add_argument("--chat-ids", "--stores", default=os.environ.get('TARGET_CHAT_IDS', ''), dest="chat_ids", help="Danh sách Chat ID dán vào (phân cách bởi dấu phẩy/khoảng trắng)")
    args = parser.parse_args()

    target_member = args.member.strip() if args.member else '@doi_soat_SCM_bot'
    if not target_member.startswith('@') and not target_member.isdigit() and not target_member.startswith('-'):
        target_member = '@' + target_member

    raw_chat_ids = args.chat_ids.strip() if args.chat_ids else ''
    parsed_ids = parse_target_chat_ids(raw_chat_ids)

    print('=' * 75)
    print('👥 TOOL TỰ ĐỘNG THÊM BOT / THÀNH VIÊN VÀO GROUP TELEGRAM')
    print(f'🤖 ĐỐI TƯỢNG CẦN THÊM : {target_member}')
    print('=' * 75)

    if not parsed_ids:
        print('❌ LỖI BẢO VỆ: Bạn chưa cung cấp danh sách Chat ID cần thêm!')
        print('👉 Hãy dán danh sách Chat ID mong muốn vào ô số 2 trước khi bấm chạy.')
        print('=' * 75)
        return

    print(f'🎯 DANH SÁCH CHAT ID   : ĐÃ NHẬN {len(parsed_ids)} CHAT ID THEO ĐÚNG YÊU CẦU')
    print('=' * 75)

    async with TelegramClient(session_path, api_id, api_hash) as client:
        me = await client.get_me()
        print(f'✅ Đăng nhập Telegram thành công: {me.first_name} (@{me.username or me.phone})')

        try:
            user_entity = await client.get_entity(target_member)
            name = getattr(user_entity, "first_name", target_member)
            print(f'👤 Tìm thấy đối tượng cần thêm: {name} (ID: {user_entity.id})\n')
        except Exception as e:
            print(f'❌ Không tìm thấy user/bot "{target_member}" trên Telegram: {e}')
            return

        print(f'🔍 Đang lấy thông tin và kiểm tra {len(parsed_ids)} Chat ID bạn đã dán...')
        target_groups = []
        for idx, cid in enumerate(parsed_ids):
            try:
                entity = await client.get_entity(cid)
                title = getattr(entity, 'title', str(cid))
                target_groups.append((cid, title, entity))
            except Exception as ex:
                target_groups.append((cid, f"Chat ID: {cid}", None))

        print(f'📊 Tìm thấy đúng {len(target_groups)} nhóm theo danh sách của bạn.\n')

        success_cnt = 0
        already_cnt = 0
        fail_cnt = 0

        for idx, (cid, title, group_entity) in enumerate(target_groups):
            print(f'[{idx+1}/{len(target_groups)}] {title} (ID: {cid}) ... ', end='', flush=True)

            try:
                if group_entity is None:
                    try:
                        group_entity = await client.get_entity(cid)
                    except Exception as e:
                        print(f'❌ Không tìm thấy nhóm trên Telegram: {e}')
                        fail_cnt += 1
                        continue

                is_in = await check_is_participant(client, group_entity, user_entity)
                if is_in:
                    print('ℹ️ ĐÃ CÓ SẴN TRONG NHÓM (Bỏ qua)')
                    already_cnt += 1
                    continue

                if isinstance(group_entity, Channel):
                    await client(InviteToChannelRequest(channel=group_entity, users=[user_entity]))
                elif isinstance(group_entity, Chat):
                    await client(AddChatUserRequest(chat_id=group_entity.id, user_id=user_entity, fwd_limit=100))

                print('✅ THÊM THÀNH CÔNG!')
                success_cnt += 1
                
                print('⏳ Nghỉ an toàn 5s...')
                await asyncio.sleep(5)

            except UserAlreadyParticipantError:
                print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                already_cnt += 1
            except FloodWaitError as fwe:
                print(f'⏳ Telegram yêu cầu chờ {fwe.seconds}s...')
                await asyncio.sleep(fwe.seconds)
            except Exception as ex:
                err_str = str(ex)
                if 'already in' in err_str.lower():
                    print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                    already_cnt += 1
                elif "can't be added" in err_str.lower() or 'not allowed' in err_str.lower():
                    print('⚠️ Bot chưa được mở quyền thêm vào nhóm!')
                    fail_cnt += 1
                else:
                    print(f'❌ Lỗi: {err_str[:45]}')
                    fail_cnt += 1

        print('\n' + '=' * 75)
        print('🎉 HOÀN TẤT TIẾN TRÌNH THÊM BOT VÀO CÁC NHÓM THEO YÊU CẦU!')
        print(f'- ✅ Thêm mới thành công : {success_cnt} group')
        print(f'- ℹ️ Đã có sẵn từ trước : {already_cnt} group')
        print(f'- ❌ Thất bại / Lỗi      : {fail_cnt} group')
        print('=' * 75)

if __name__ == '__main__':
    asyncio.run(main())
