import asyncio
import os
import sys
import json
import re
import argparse
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
from telethon.tl.functions.messages import AddChatUserRequest, GetFullChatRequest
from telethon.tl.types import Channel, Chat, User
from telethon.errors import (
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
    UserAlreadyParticipantError,
    FloodWaitError,
    PeerFloodError,
    UserNotParticipantError,
    ChannelPrivateError,
    ChatAdminRequiredError,
)

sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

api_id = 31209455
api_hash = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))

session_candidates = [
    os.path.join(current_dir, 'user_session.session'),
    os.path.join(root_dir, 'DONG_MAT_DASHBOARD', 'user_session.session'),
    os.path.join(root_dir, 'user_session.session'),
    os.path.join(root_dir, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'user_session.session'),
    os.path.join(r'G:\My Drive\Đối soát SCM\DONG_MAT_DASHBOARD', 'user_session.session'),
    os.path.join(r'G:\My Drive\Đối soát SCM', 'user_session.session'),
]

session_path = os.path.join(current_dir, 'user_session')
for cand in session_candidates:
    if os.path.exists(cand):
        session_path = cand[:-8] if cand.endswith('.session') else cand
        break

def load_store_chat_map():
    """Load mapping từ Mã ST sang Chat ID để hỗ trợ gõ mã ST (A101, LVY...)"""
    mapping = {}
    json_paths = [
        os.path.join(root_dir, 'CONFIG_DATA_STORES.json'),
        os.path.join(root_dir, 'DONG_MAT_DASHBOARD', 'data', 'telegram_groups.json')
    ]
    for jp in json_paths:
        if os.path.exists(jp):
            try:
                with open(jp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        sid = str(item.get('id', '') or '').strip().upper()
                        dm = str(item.get('chat_id_dm', '') or '').strip()
                        rc = str(item.get('chat_id_rc', '') or '').strip()
                        cids = []
                        if dm and dm not in ['nan', '0', '']:
                            cids.append(int(dm) if dm.lstrip('-').isdigit() else dm)
                        if rc and rc not in ['nan', '0', '']:
                            cids.append(int(rc) if rc.lstrip('-').isdigit() else rc)
                        if sid:
                            mapping[sid] = cids
                elif isinstance(data, dict) and 'clusters' in data:
                    for cl in data.get('clusters', []):
                        sid = str(cl.get('store_code', '') or '').strip().upper()
                        cids = []
                        for g in cl.get('groups', []):
                            gid = g.get('chat_id')
                            if gid:
                                try:
                                    cids.append(int(gid))
                                except Exception:
                                    cids.append(gid)
                        if sid and cids:
                            mapping[sid] = list(set(cids))
            except Exception:
                pass
    return mapping

async def check_is_participant(client, group_entity, user_entity):
    try:
        if isinstance(group_entity, Channel):
            await client(GetParticipantRequest(channel=group_entity, participant=user_entity))
            return True
        elif isinstance(group_entity, Chat):
            full = await client(GetFullChatRequest(group_entity.id))
            return user_entity.id in [u.id for u in full.users]
    except (UserNotParticipantError, ChannelPrivateError):
        return False
    except Exception:
        return False
    return False

def parse_target_chat_ids(raw_text, store_map):
    if not raw_text or not raw_text.strip():
        return []
    if raw_text.strip().upper() in ['ALL', 'TAT_CA', 'TOAN_BO', '*']:
        return "ALL"
    
    found_ids = []
    tokens = re.split(r'[\s,;\n\r\t]+', raw_text.strip())
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        # Kiểm tra xem có phải mã siêu thị trong mapping không (A101, LVY...)
        upper_t = t.upper()
        if upper_t in store_map:
            for mapped_cid in store_map[upper_t]:
                found_ids.append(mapped_cid)
            continue
        
        # Thử parse số nguyên Chat ID
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
    parser = argparse.ArgumentParser(description="Tool thêm Bot / Thành viên vào Group Telegram theo Danh Sách Chat ID")
    parser.add_argument("--member", default=os.environ.get('TARGET_MEMBER', '@doi_soat_SCM_bot'), help="Username hoặc ID của Bot/User cần thêm")
    parser.add_argument("--chat-ids", "--stores", default=os.environ.get('TARGET_CHAT_IDS', ''), dest="chat_ids", help="Danh sách Chat ID hoặc Mã Siêu Thị cần thêm")

    # Tiền xử lý argv: nếu argument tiếp theo của --chat-ids hoặc --stores bắt đầu bằng dấu trừ '-' (Chat ID âm của Telegram)
    # argparse mặc định sẽ coi đó là flag không hợp lệ và văng lỗi 'expected one argument'.
    # Gộp thành --chat-ids=... để argparse nhận diện chính xác 100%.
    raw_argv = sys.argv[1:]
    clean_argv = []
    i = 0
    while i < len(raw_argv):
        a = raw_argv[i]
        if a in ["--chat-ids", "--stores"] and i + 1 < len(raw_argv):
            clean_argv.append(f"{a}={raw_argv[i+1]}")
            i += 2
            continue
        elif a == "--member" and i + 1 < len(raw_argv):
            clean_argv.append(f"{a}={raw_argv[i+1]}")
            i += 2
            continue
        clean_argv.append(a)
        i += 1

    args = parser.parse_args(clean_argv)

    target_member = args.member.strip() if args.member else '@doi_soat_SCM_bot'
    if not target_member.startswith('@') and not target_member.isdigit() and not target_member.startswith('-'):
        target_member = '@' + target_member

    raw_chat_ids = args.chat_ids.strip() if args.chat_ids else ''
    if not raw_chat_ids:
        print('=' * 75)
        print('❌ LỖI: BẠN CHƯA CUNG CẤP DANH SÁCH CHAT ID CẦN THÊM!')
        print('👉 Vui lòng dán danh sách Chat ID hoặc Mã Siêu Thị vào ô số 2 trước khi bấm chạy.')
        print('=' * 75)
        return

    store_map = load_store_chat_map()
    parsed_ids = parse_target_chat_ids(raw_chat_ids, store_map)

    print('=' * 75)
    print('👥 TOOL THÊM BOT / THÀNH VIÊN VÀO GROUP TELEGRAM THEO DANH SÁCH CHAT ID')
    print(f'🤖 ĐỐI TƯỢNG CẦN THÊM : {target_member}')
    if parsed_ids == "ALL":
        print('🎯 CHẾ ĐỘ THỰC THI    : 🌐 TOÀN BỘ CÁC GROUP MÀ ACC CHÍNH ĐANG CÓ MẶT')
    else:
        print(f'🎯 DANH SÁCH CUNG CẤP : {len(parsed_ids)} CHAT ID / NHÓM THEO YÊU CẦU')
    print('=' * 75)

    async with TelegramClient(session_path, api_id, api_hash) as client:
        me = await client.get_me()
        print(f'✅ Đăng nhập Telegram thành công: {me.first_name} {me.last_name or ""} (@{me.username or me.phone})')

        try:
            user_entity = await client.get_entity(target_member)
            name = getattr(user_entity, "first_name", target_member)
            print(f'👤 Tìm thấy đối tượng cần thêm: {name} (ID: {user_entity.id})\n')
        except Exception as e:
            print(f'❌ Không tìm thấy user/bot "{target_member}" trên Telegram: {e}')
            return

        target_groups = []

        if parsed_ids == "ALL":
            print('🔍 Đang quét danh bạ tất cả các Group mà Acc Chính đang có mặt...')
            dialogs = await client.get_dialogs()
            for d in dialogs:
                if d.is_group or (d.is_channel and not getattr(d.entity, 'broadcast', False)):
                    target_groups.append((d.id, d.title, d.entity))
            print(f'📊 Tìm thấy tổng cộng {len(target_groups)} group Telegram mà Acc Chính đang tham gia!\n')
        else:
            print(f'🔍 Đang kiểm tra {len(parsed_ids)} Chat ID bạn đã cung cấp (kiểm tra Acc chính có trong group không)...')
            for cid in parsed_ids:
                try:
                    entity = await client.get_entity(cid)
                    title = getattr(entity, 'title', str(cid))
                    target_groups.append((cid, title, entity))
                except Exception:
                    target_groups.append((cid, f"Chat ID: {cid}", None))
            print(f'📊 Đã nạp đúng {len(target_groups)} nhóm theo danh sách cung cấp của bạn.\n')

        if not target_groups:
            print('⚠️ Không tìm thấy nhóm nào để thực hiện!')
            return

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
                        print(f'❌ Acc chính chưa có trong nhóm này (Không thể thêm bot): {e}')
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
                
                print('⏳ Nghỉ an toàn 45s (chống Telegram Rate Limit)...')
                await asyncio.sleep(45)

            except UserAlreadyParticipantError:
                print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                already_cnt += 1
            except FloodWaitError as fwe:
                print(f'⏳ Telegram yêu cầu chờ {fwe.seconds}s...')
                await asyncio.sleep(fwe.seconds)
            except ChatAdminRequiredError:
                print('⚠️ Nhóm giới hạn quyền thêm thành viên (Cần Admin)')
                fail_cnt += 1
            except Exception as ex:
                err_str = str(ex)
                if 'already in' in err_str.lower():
                    print('ℹ️ ĐÃ CÓ TRONG NHÓM')
                    already_cnt += 1
                elif "can't be added" in err_str.lower() or 'not allowed' in err_str.lower() or 'privacy' in err_str.lower():
                    print('⚠️ Quyền riêng tư hoặc chưa mở quyền thêm vào nhóm!')
                    fail_cnt += 1
                else:
                    print(f'❌ Lỗi: {err_str[:50]}')
                    fail_cnt += 1

        print('\n' + '=' * 75)
        print('🎉 HOÀN TẤT TIẾN TRÌNH THÊM BOT VÀO CÁC GROUP CỦA ACC CHÍNH!')
        print(f'- 🎯 Tổng số nhóm đã duyệt: {len(target_groups)} group')
        print(f'- ✅ Thêm mới thành công  : {success_cnt} group')
        print(f'- ℹ️ Đã có sẵn từ trước  : {already_cnt} group')
        print(f'- ⚠️ Bỏ qua / Lỗi / Admin : {fail_cnt} group')
        print('=' * 75)

if __name__ == '__main__':
    asyncio.run(main())
