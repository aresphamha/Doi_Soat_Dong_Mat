
def find_data_file(filename, default_dir=None):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ', filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(cur_dir, filename)

import asyncio
import random
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

# ============================================================
# CẤU HÌNH
# ============================================================
api_id   = 28938971
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
session  = 'user_session'

DELAY_MIN = 60
DELAY_MAX = 80
# ============================================================

async def kiem_tra_da_co_trong_group(client, group_entity, user_entity):
    """
    Kiểm tra user đã là thành viên của group chưa.
    Trả về True nếu đã có, False nếu chưa có.
    """
    try:
        if isinstance(group_entity, Channel):
            await client(GetParticipantRequest(
                channel=group_entity,
                participant=user_entity
            ))
            return True  # Có kết quả → đã là thành viên
        elif isinstance(group_entity, Chat):
            full = await client(GetFullChatRequest(group_entity.id))
            user_ids = [u.id for u in full.users]
            return user_entity.id in user_ids
    except UserNotParticipantError:
        return False
    except Exception:
        return False  # Lỗi khác → coi như chưa có để thử add

async def main():
    print("=" * 60)
    print("   TOOL ADD THÀNH VIÊN VÀO TẤT CẢ GROUP SIÊU THỊ")
    print("=" * 60)

    # ── Nhập username ─────────────────────────────────────────
    print()
    username_input = input("  Nhập username cần add (VD: @nguyenvana): ").strip()
    if not username_input:
        print("[LỖI] Bạn chưa nhập username!")
        input("Bấm Enter để thoát...")
        return
    if not username_input.startswith('@'):
        username_input = '@' + username_input
    print(f"  → Sẽ add: {username_input}\n")

    # ── Đọc danh sách siêu thị ────────────────────────────────
    df = pd.read_excel(find_data_file('Danh sách Siêu thị.xlsx'), dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
    df['CHAT ID'] = df['CHAT ID'].str.replace('.0', '', regex=False).str.strip()
    df = df.reset_index(drop=True)

    success_list = []
    skip_list    = []
    fail_list    = []

    async with TelegramClient(session, api_id, api_hash) as client:
        print("✅ Đăng nhập Telegram thành công!\n")

        # Lấy entity của user cần add
        try:
            user_entity = await client.get_entity(username_input)
            print(f"  Tìm thấy user: {user_entity.first_name} (ID: {user_entity.id})\n")
        except Exception as e:
            print(f"[LỖI] Không tìm được user '{username_input}': {e}")
            input("Bấm Enter để thoát...")
            return

        # ══════════════════════════════════════════════════════
        # GIAI ĐOẠN 1: QUÉT NHANH — KIỂM TRA TƯ CÁCH THÀNH VIÊN
        # ══════════════════════════════════════════════════════
        print("=" * 60)
        print("  GIAI ĐOẠN 1: QUÉT KIỂM TRA TƯ CÁCH THÀNH VIÊN...")
        print("=" * 60)

        can_add_rows  = []   # Danh sách group chưa có user → cần add
        da_co_rows    = []   # Danh sách group đã có user → bỏ qua
        loi_lay_group = []   # Không lấy được entity

        for idx, row in df.iterrows():
            ten_st  = str(row.get('Tên Siêu thị', ''))
            id_st   = str(row.get('ID ST', ''))
            chat_id = int(row['CHAT ID'])

            print(f"  [{idx+1}/{len(df)}] {ten_st} ({id_st}) ... ", end='', flush=True)

            try:
                group_entity = await client.get_entity(chat_id)
                da_co = await kiem_tra_da_co_trong_group(client, group_entity, user_entity)

                if da_co:
                    print("✅ Đã có")
                    da_co_rows.append(row)
                    skip_list.append(f"{ten_st} ({id_st})")
                else:
                    print("➕ Chưa có → Cần add")
                    can_add_rows.append((row, group_entity))

            except Exception as e:
                print(f"❌ Lỗi: {e}")
                loi_lay_group.append(f"{ten_st} ({id_st}) - {e}")

            await asyncio.sleep(0.5)  # Delay nhẹ khi quét để tránh rate limit

        print()
        print(f"  ─── KẾT QUẢ QUÉT ───────────────────────────────")
        print(f"  ✅ Đã là thành viên : {len(da_co_rows)} group (bỏ qua)")
        print(f"  ➕ Chưa có, cần add : {len(can_add_rows)} group")
        print(f"  ❌ Không lấy được  : {len(loi_lay_group)} group")
        print()

        if not can_add_rows:
            print("  🎉 Không còn group nào cần add! Đã hoàn tất.")
            input("Bấm Enter để thoát...")
            return

        input(f"  Bấm Enter để bắt đầu ADD {len(can_add_rows)} group còn lại...")

        # ══════════════════════════════════════════════════════
        # GIAI ĐOẠN 2: ADD VÀO CÁC GROUP CHƯA CÓ
        # ══════════════════════════════════════════════════════
        print()
        print("=" * 60)
        print(f"  GIAI ĐOẠN 2: ADD '{username_input}' VÀO {len(can_add_rows)} GROUP")
        print("=" * 60 + "\n")

        for i, (row, group_entity) in enumerate(can_add_rows, start=1):
            ten_st  = str(row.get('Tên Siêu thị', ''))
            id_st   = str(row.get('ID ST', ''))

            print(f"[{i}/{len(can_add_rows)}] {ten_st} ({id_st})")

            try:
                # ── Supergroup / Channel ──────────────────────
                if isinstance(group_entity, Channel):
                    try:
                        await client(InviteToChannelRequest(
                            channel=group_entity,
                            users=[user_entity]
                        ))
                        print(f"  ✅ ADD THÀNH CÔNG (supergroup)")
                        success_list.append(f"{ten_st} ({id_st})")
                    except UserAlreadyParticipantError:
                        print(f"  ⏭️  Đã là thành viên - bỏ qua")
                        skip_list.append(f"{ten_st} ({id_st})")
                    except UserPrivacyRestrictedError:
                        print(f"  ❌ User bật chế độ riêng tư")
                        fail_list.append(f"{ten_st} ({id_st}) - Privacy restricted")
                    except UserNotMutualContactError:
                        print(f"  ❌ Chưa có liên hệ chung")
                        fail_list.append(f"{ten_st} ({id_st}) - Not mutual contact")
                    except FloodWaitError as e:
                        print(f"  ⚠️  Flood! Đợi {e.seconds}s...")
                        await asyncio.sleep(e.seconds + 5)
                        try:
                            await client(InviteToChannelRequest(group_entity, [user_entity]))
                            print(f"  ✅ ADD THÀNH CÔNG (sau flood)")
                            success_list.append(f"{ten_st} ({id_st})")
                        except Exception as re_e:
                            print(f"  ❌ Vẫn thất bại: {re_e}")
                            fail_list.append(f"{ten_st} ({id_st}) - {re_e}")
                    except PeerFloodError:
                        print(f"  ⛔ Tài khoản bị giới hạn spam. Dừng!")
                        fail_list.append(f"{ten_st} ({id_st}) - PeerFlood")
                        break
                    except Exception as e:
                        print(f"  ❌ {e}")
                        fail_list.append(f"{ten_st} ({id_st}) - {e}")

                # ── Chat thường ───────────────────────────────
                elif isinstance(group_entity, Chat):
                    try:
                        await client(AddChatUserRequest(
                            chat_id=group_entity.id,
                            user_id=user_entity,
                            fwd_limit=0
                        ))
                        print(f"  ✅ ADD THÀNH CÔNG (chat thường)")
                        success_list.append(f"{ten_st} ({id_st})")
                    except UserAlreadyParticipantError:
                        print(f"  ⏭️  Đã là thành viên - bỏ qua")
                        skip_list.append(f"{ten_st} ({id_st})")
                    except UserPrivacyRestrictedError:
                        print(f"  ❌ User bật chế độ riêng tư")
                        fail_list.append(f"{ten_st} ({id_st}) - Privacy restricted")
                    except FloodWaitError as e:
                        print(f"  ⚠️  Flood! Đợi {e.seconds}s...")
                        await asyncio.sleep(e.seconds + 5)
                    except PeerFloodError:
                        print(f"  ⛔ Tài khoản bị giới hạn spam. Dừng!")
                        fail_list.append(f"{ten_st} ({id_st}) - PeerFlood")
                        break
                    except Exception as e:
                        print(f"  ❌ {e}")
                        fail_list.append(f"{ten_st} ({id_st}) - {e}")

            except Exception as e:
                print(f"  ❌ Lỗi: {e}")
                fail_list.append(f"{ten_st} ({id_st}) - {e}")

            # Đếm ngược delay (chỉ delay nếu còn group tiếp theo)
            if i < len(can_add_rows):
                wait_sec = random.randint(DELAY_MIN, DELAY_MAX)
                for remaining in range(wait_sec, 0, -1):
                    print(f"  ⏳ Chờ {remaining}s trước group tiếp theo...", end='\r')
                    await asyncio.sleep(1)
                print(" " * 55, end='\r')

    # ── Báo cáo kết quả ──────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  📊 KẾT QUẢ CUỐI CÙNG — {username_input}")
    print("=" * 60)
    print(f"  ✅ Add thành công       : {len(success_list)} group")
    print(f"  ⏭️  Đã là thành viên    : {len(skip_list)} group")
    print(f"  ❌ Thất bại             : {len(fail_list)} group")

    if fail_list:
        print("\n  --- DANH SÁCH THẤT BẠI ---")
        for item in fail_list:
            print(f"    • {item}")

    print("\n" + "=" * 60)
    input("  Bấm Enter để thoát...")


if __name__ == '__main__':
    asyncio.run(main())
