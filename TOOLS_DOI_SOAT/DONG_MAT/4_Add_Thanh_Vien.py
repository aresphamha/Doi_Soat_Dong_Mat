import asyncio
import os
import sys
import pandas as pd
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

api_id = 28938971
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
current_dir = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(current_dir, 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'G:\My Drive\Đối soát SCM', 'user_session')
if not os.path.exists(session_path + '.session'):
    session_path = os.path.join(r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT', 'user_session')

TARGET_MEMBER = os.environ.get('TARGET_MEMBER', '@doi_soat_SCM_bot').strip()
if not TARGET_MEMBER.startswith('@') and not TARGET_MEMBER.isdigit():
    TARGET_MEMBER = '@' + TARGET_MEMBER

TARGET_CHAT_IDS = os.environ.get('TARGET_CHAT_IDS', 'ALL').strip()

def find_excel():
    candidates = [
        os.path.join(current_dir, 'Danh sách Siêu thị.xlsx'),
        os.path.join(r'G:\My Drive\Đối soát SCM\SPAM_PHIEU_CHUYEN\CONFIG_DATA', 'Danh sách Siêu thị.xlsx'),
        r'C:\Users\Thu Ha\Desktop\ĐỐI SOÁT\ĐÔNG MÁT\Danh sách Siêu thị.xlsx'
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

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

async def main():
    print('=' * 75)
    print('👥 TOOL TỰ ĐỘNG THÊM BOT / THÀNH VIÊN VÀO GROUP THEO YÊU CẦU')
    print(f'🤖 USERNAME CẦN ADD: {TARGET_MEMBER}')
    print(f'🎯 DANH SÁCH CHAT ID YÊU CẦU: {TARGET_CHAT_IDS if TARGET_CHAT_IDS != "ALL" else "TẤT CẢ CÁC GROUP CÓ TRONG DANH BẠ"}')
    print('=' * 75)

    excel_file = find_excel()
    if not os.path.exists(excel_file):
        print(f'❌ Không tìm thấy file danh bạ Siêu thị tại: {excel_file}')
        return

    df = pd.read_excel(excel_file, dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
    df['CHAT ID'] = df['CHAT ID'].str.replace('.0', '', regex=False).str.strip()
    df = df.reset_index(drop=True)

    if TARGET_CHAT_IDS and TARGET_CHAT_IDS != 'ALL':
        req_list = [x.strip() for x in TARGET_CHAT_IDS.replace(',', ' ').split() if x.strip()]
        
        def match_row(r):
            cid = str(r['CHAT ID']).strip()
            id_st = str(r.get('ID ST', '')).strip()
            ten_st = str(r.get('Tên Siêu thị', '')).strip()
            for q in req_list:
                if q == cid or q == id_st or q in cid or q in ten_st:
                    return True
            return False
            
        df = df[df.apply(match_row, axis=1)].reset_index(drop=True)

    if df.empty:
        print('⚠️ Không tìm thấy nhóm nào khớp với danh sách Chat ID bạn yêu cầu!')
        return

    print(f'📊 Tìm thấy {len(df)} nhóm cần xử lý theo yêu cầu.\n')

    async with TelegramClient(session_path, api_id, api_hash) as client:
        print('✅ Đăng nhập Telegram chính chủ thành công!')
        
        try:
            user_entity = await client.get_entity(TARGET_MEMBER)
            name = getattr(user_entity, "first_name", TARGET_MEMBER)
            print(f'👤 Tìm thấy đối tượng: {name} (ID: {user_entity.id})\n')
        except Exception as e:
            print(f'❌ Không tìm thấy user/bot "{TARGET_MEMBER}" trên Telegram: {e}')
            return

        success_cnt = 0
        already_cnt = 0
        fail_cnt = 0

        for idx, row in df.iterrows():
            id_st = str(row.get('ID ST', ''))
            ten_st = str(row.get('Tên Siêu thị', id_st))
            raw_cid = str(row['CHAT ID']).strip()
            
            try:
                cid = int(raw_cid)
            except Exception:
                continue

            print(f'[{idx+1}/{len(df)}] ST: {ten_st} (Chat ID: {cid}) ... ', end='', flush=True)

            try:
                group_entity = await client.get_entity(cid)
                
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
                await asyncio.sleep(2)

            except UserAlreadyParticipantError:
                print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                already_cnt += 1
            except Exception as ex:
                err_str = str(ex)
                if 'already in' in err_str.lower():
                    print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                    already_cnt += 1
                elif "can't be added" in err_str.lower() or 'not allowed' in err_str.lower():
                    print('⚠️ Bot chưa được mở quyền vào nhóm trên BotFather!')
                    fail_cnt += 1
                else:
                    print(f'❌ Lỗi: {err_str[:40]}')
                    fail_cnt += 1

        print('\n' + '=' * 75)
        print('🎉 HOÀN TẤT TIẾN TRÌNH THÊM THÀNH VIÊN THEO YÊU CẦU!')
        print(f'- ✅ Thêm mới thành công : {success_cnt} group')
        print(f'- ℹ️ Đã có sẵn từ trước : {already_cnt} group')
        print(f'- ❌ Thất bại / Lỗi      : {fail_cnt} group')
        print('=' * 75)

if __name__ == '__main__':
    asyncio.run(main())
