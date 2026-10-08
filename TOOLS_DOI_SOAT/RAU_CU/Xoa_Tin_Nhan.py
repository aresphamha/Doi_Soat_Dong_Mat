
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
import pandas as pd
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient

api_id   = 28938971
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'

current_dir  = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(current_dir, '..', 'ĐÔNG MÁT', 'user_session')

BOT_ID        = 8810108114
TU_KHOA       = ['RAU CU', 'RAU CỦ', 'HẬU KIỂM', 'HAU KIEM']
SO_TIN_QUET   = 30

async def main():
    print("=" * 55)
    print("  XOÁ TIN NHẮN BOT - RAU CỦ QUẢ")
    print("=" * 55)

    excel_path = os.path.join(current_dir, 'Danh sách Siêu thị.xlsx')
    df = pd.read_excel(excel_path, dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'] != 'nan')]
    df['CHAT ID'] = df['CHAT ID'].str.replace('.0', '', regex=False).str.strip()
    df = df.reset_index(drop=True)

    print(f"  Tổng group: {len(df)}\n")

    xoa_dc, khong_co, loi = [], [], []

    async with TelegramClient(session_path, api_id, api_hash) as client:
        print("  ✅ Đăng nhập thành công!\n")

        for idx, row in df.iterrows():
            id_st   = str(row.get('ID ST TƯƠNG ỨNG', row.get('ID ST', '')))
            chat_id = int(row['CHAT ID'])

            print(f"[{idx+1}/{len(df)}] {id_st} | Chat: {chat_id}", end=' ... ')

            try:
                entity = await client.get_entity(chat_id)
                to_del = []

                async for msg in client.iter_messages(entity, limit=SO_TIN_QUET):
                    # Xác định sender
                    sid = None
                    try:
                        sid = msg.sender_id or (msg.from_id.user_id if msg.from_id else None)
                    except:
                        pass

                    if sid != BOT_ID:
                        continue

                    # Kiểm tra nội dung (caption có thể không tồn tại)
                    txt = (getattr(msg, 'text', '') or '') + (getattr(msg, 'caption', '') or '')
                    txt = txt.upper()
                    if any(kw.upper() in txt for kw in TU_KHOA):
                        to_del.append(msg.id)

                if to_del:
                    await client.delete_messages(entity, to_del)
                    print(f"🗑️  Đã xoá {len(to_del)} tin")
                    xoa_dc.append(id_st)
                else:
                    print(f"ℹ️  Không có tin")
                    khong_co.append(id_st)

            except Exception as e:
                print(f"❌ Lỗi: {str(e)[:50]}")
                loi.append(id_st)

            await asyncio.sleep(0.3)

    print("\n" + "=" * 55)
    print(f"  🗑️  Đã xoá  : {len(xoa_dc)} group")
    print(f"  ℹ️  Không có: {len(khong_co)} group")
    print(f"  ❌ Lỗi     : {len(loi)} group")
    if loi:
        print(f"     {', '.join(loi)}")
    print("=" * 55)

asyncio.run(main())
