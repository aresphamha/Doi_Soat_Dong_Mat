import asyncio
import random
import json
import os
import requests
import pandas as pd
from telethon import TelegramClient

# ============================================================
# CẤU HÌNH
# ============================================================
api_id    = 28938971
api_hash  = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'
session   = 'user_session'

EXCEL_FILE      = 'Danh sách Siêu thị.xlsx'
SAVED_LIST_FILE = 'spam_list_saved.json'

DELAY_MIN = 3
DELAY_MAX = 5
# ============================================================

# Các từ khoá nhận dạng vai trò (trong tên thành viên)
ROLE_KEYWORDS = {
    'SM' : [' SM', '-SM', '_SM'],
    'TC' : [' TC', '-TC', '_TC'],
    'GSM': [' GSM', '-GSM', '_GSM'],
}

async def get_tags_for_group(client, chat_id):
    """
    Quét thành viên group, tìm SM / TC / GSM theo tên,
    trả về chuỗi mention: [Tên](tg://user?id=...)
    Nếu không tìm thấy → giữ nguyên text @SM @TC @GSM
    """
    tags = []
    try:
        participants = await client.get_participants(chat_id)
        for p in participants:
            name = ''
            if p.first_name: name += p.first_name
            if p.last_name:  name += ' ' + p.last_name
            name_upper = name.upper()

            for role, keywords in ROLE_KEYWORDS.items():
                if any(kw in name_upper for kw in keywords):
                    tags.append(f"[{name}](tg://user?id={p.id})")
                    break   # mỗi người chỉ tag 1 lần
    except Exception:
        pass

    return ' '.join(tags) if tags else '@SM @TC @GSM'


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_excel():
    df = pd.read_excel(EXCEL_FILE, dtype=str)
    df = df[df['CHAT ID'].notna() & (df['CHAT ID'].str.strip() != '') & (df['CHAT ID'] != 'nan')]
    df['CHAT ID'] = df['CHAT ID'].str.replace('.0', '', regex=False).str.strip()
    if 'Tên viết tắt' not in df.columns:
        df['Tên viết tắt'] = df['ID ST']
    df['Tên viết tắt'] = df['Tên viết tắt'].fillna('').str.strip()
    df['Tên viết tắt'] = df.apply(
        lambda r: r['ID ST'] if r['Tên viết tắt'] == '' else r['Tên viết tắt'], axis=1
    )
    return df.reset_index(drop=True)

def load_saved():
    if os.path.exists(SAVED_LIST_FILE):
        with open(SAVED_LIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_saved(data):
    with open(SAVED_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_id_st(input_str, df):
    input_str = input_str.strip().upper()
    if input_str == 'ALL':
        return list(range(len(df))), []
    id_map = {}
    for idx, row in df.iterrows():
        key = str(row['ID ST']).strip().upper()
        id_map.setdefault(key, []).append(idx)
    selected, not_found = [], []
    for part in [p.strip() for p in input_str.split(',') if p.strip()]:
        if part in id_map:
            selected.extend(id_map[part])
        else:
            not_found.append(part)
    return sorted(set(selected)), not_found

def show_list(df, selected):
    print()
    print(f"  [  ]  {'STT':<4} {'ID ST':<7} {'TÊN VIẾT TẮT':<18} {'TÊN SIÊU THỊ'}")
    print(f"  ----  {'-'*4} {'-'*7} {'-'*18} {'-'*33}")
    for idx, row in df.iterrows():
        chon = '[✅]' if idx in selected else '[  ]'
        vt   = str(row.get('Tên viết tắt', row['ID ST']))[:17]
        ten  = str(row['Tên Siêu thị'])[:33]
        print(f"  {chon}  {idx+1:<4} {row['ID ST']:<7} {vt:<18} {ten}")
    print()

# ══════════════════════════════════════════════════════════════
# BƯỚC 1: CHỌN GROUP
# ══════════════════════════════════════════════════════════════
def buoc_chon_group(df):
    selected = set()
    saved    = load_saved()

    while True:
        clear()
        print("=" * 60)
        print("  BƯỚC 1/3 — CHỌN GROUP CẦN SPAM")
        print("=" * 60)
        print(f"  Tổng: {len(df)} group  |  Đã chọn: {len(selected)} group")
        print()
        print("  [1] Xem danh sách + nhập ID ST")
        print("  [2] Chọn tất cả")
        print("  [3] Tải danh sách đã lưu")
        print("  [4] Lưu danh sách hiện tại")
        print("  [5] Xem group đã chọn / Bỏ chọn")
        print()
        print("  [0] ▶  TIẾP THEO: SOẠN TIN NHẮN")
        print()
        c = input("  Chọn: ").strip()

        # ── [1] Nhập ID ST ────────────────────────────────────
        if c == '1':
            clear()
            show_list(df, selected)
            print("─" * 60)
            print("  Nhập ID ST cần chọn, cách nhau dấu PHẨY")
            print("  Ví dụ:  A101,A102,A205,A210")
            print("  all = chọn tất cả  |  Enter = bỏ qua")
            print("─" * 60)
            inp = input("  → ").strip().upper()
            if inp == 'ALL':
                selected = set(range(len(df)))
                print(f"  ✅ Đã chọn tất cả {len(df)} group!")
            elif inp:
                indices, not_found = parse_id_st(inp, df)
                selected.update(indices)
                added = [df.iloc[i]['ID ST'] for i in indices]
                print(f"  ✅ Đã thêm {len(indices)} group: {', '.join(added)}")
                if not_found:
                    print(f"  ⚠️  Không tìm thấy: {', '.join(not_found)}")
            input("\n  Bấm Enter để tiếp tục...")

        # ── [2] Tất cả ────────────────────────────────────────
        elif c == '2':
            selected = set(range(len(df)))
            print(f"  ✅ Đã chọn tất cả {len(df)} group!")
            input("  Bấm Enter để tiếp tục...")

        # ── [3] Tải danh sách đã lưu ─────────────────────────
        elif c == '3':
            if not saved:
                print("  ⚠️  Chưa có danh sách nào được lưu.")
            else:
                print("\n  Danh sách đã lưu:")
                keys = list(saved.keys())
                for i, k in enumerate(keys, 1):
                    print(f"    [{i}] {k}  ({len(saved[k])} group)")
                sel = input("\n  Chọn số: ").strip()
                try:
                    key = keys[int(sel) - 1]
                    selected = set(saved[key])
                    print(f"  ✅ Đã tải '{key}' ({len(selected)} group).")
                except:
                    print("  ❌ Không hợp lệ.")
            input("  Bấm Enter để tiếp tục...")

        # ── [4] Lưu danh sách ─────────────────────────────────
        elif c == '4':
            if not selected:
                print("  ⚠️  Chưa chọn group nào.")
            else:
                name = input("  Đặt tên danh sách: ").strip()
                if name:
                    saved[name] = sorted(selected)
                    save_saved(saved)
                    print(f"  ✅ Đã lưu '{name}' ({len(selected)} group).")
                else:
                    print("  ❌ Tên không hợp lệ.")
            input("  Bấm Enter để tiếp tục...")

        # ── [5] Xem / Bỏ chọn ────────────────────────────────
        elif c == '5':
            if not selected:
                print("  ⚠️  Chưa chọn group nào.")
                input("  Bấm Enter để tiếp tục...")
            else:
                clear()
                print(f"\n  {len(selected)} group đã chọn:\n")
                for i in sorted(selected):
                    row = df.iloc[i]
                    vt  = str(row.get('Tên viết tắt', row['ID ST']))
                    print(f"    ✅ {row['ID ST']:<7} {vt:<18} {row['Tên Siêu thị']}")
                print()
                bo = input("  Nhập ID ST cần BỎ CHỌN (Enter = giữ nguyên): ").strip().upper()
                if bo:
                    indices, _ = parse_id_st(bo, df)
                    for i in indices:
                        selected.discard(i)
                    print(f"  ✅ Đã bỏ chọn {len(indices)} group.")
                input("  Bấm Enter để tiếp tục...")

        # ── [0] Tiếp tục ──────────────────────────────────────
        elif c == '0':
            if not selected:
                print("  ⚠️  Chưa chọn group nào! Vui lòng chọn ít nhất 1.")
                input("  Bấm Enter để tiếp tục...")
            else:
                return sorted(selected)

# ══════════════════════════════════════════════════════════════
# BƯỚC 2: SOẠN TIN NHẮN (qua Notepad)
# ══════════════════════════════════════════════════════════════
def buoc_soan_tin():
    import subprocess, tempfile, time

    TEMP_FILE = 'tin_nhan_temp.txt'

    while True:
        clear()
        print("=" * 60)
        print("  BƯỚC 2/3 — SOẠN TIN NHẮN")
        print("=" * 60)
        print()
        print("  📝 Notepad sẽ tự mở ra.")
        print()
        print("  Trong Notepad bạn có thể:")
        print("    ✅ Gõ trực tiếp")
        print("    ✅ COPY từ Telegram / Zalo rồi CTRL+V để dán")
        print("    ✅ Xoá, sửa thoải mái")
        print("    ✅ Emoji, ký tự đặc biệt đều OK")
        print()
        print("  ⚠️  Soạn xong → Lưu (Ctrl+S) → Đóng Notepad")
        print("      → Tool sẽ tự đọc nội dung.")
        print()
        input("  Bấm Enter để mở Notepad...")

        # Tạo file tạm với hướng dẫn
        with open(TEMP_FILE, 'w', encoding='utf-8') as f:
            f.write("[ XOÁ DÒNG HƯỚNG DẪN NÀY VÀ SOẠN NỘI DUNG TIN NHẮN BÊN DƯỚI ]\n")
            f.write("[ Tag @SM @TC @GSM sẽ tự động thêm vào cuối, KHÔNG cần gõ ]\n\n")

        # Mở Notepad và đợi user đóng
        proc = subprocess.Popen(['notepad.exe', TEMP_FILE])
        print("\n  ⏳ Đang chờ bạn soạn tin và đóng Notepad...")
        proc.wait()  # Đợi cho đến khi Notepad đóng

        # Đọc nội dung
        try:
            with open(TEMP_FILE, 'r', encoding='utf-8') as f:
                noi_dung = f.read()
        except:
            with open(TEMP_FILE, 'r', encoding='utf-8-sig') as f:
                noi_dung = f.read()

        # Bỏ các dòng hướng dẫn nếu còn sót
        lines = [l for l in noi_dung.splitlines()
                 if not l.startswith('[ XOÁ') and not l.startswith('[ Tag')]
        # Bỏ dòng trống đầu và cuối
        while lines and lines[0].strip() == '':
            lines.pop(0)
        while lines and lines[-1].strip() == '':
            lines.pop()

        noi_dung = '\n'.join(lines)

        if not noi_dung.strip():
            print("\n  ⚠️  Nội dung trống! Vui lòng soạn lại.")
            input("  Bấm Enter để mở lại Notepad...")
            continue

        # Xem trước
        clear()
        print("=" * 60)
        print("  📋 XEM TRƯỚC TIN SẼ GỬI:")
        print("=" * 60)
        print()
        print(noi_dung)
        print()
        print("@SM @TC @GSM")
        print()
        print("─" * 60)
        ok = input("  Nội dung OK? (y = tiếp tục / n = soạn lại): ").strip().lower()
        if ok == 'y':
            # Xoá file tạm
            try:
                os.remove(TEMP_FILE)
            except:
                pass
            return noi_dung

# ══════════════════════════════════════════════════════════════
# BƯỚC 3: GỬI TIN
# ══════════════════════════════════════════════════════════════
async def gui_tin(chat_id, text):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    res = requests.post(url, data={
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    })
    return res.status_code == 200, res.json()

async def buoc_gui(df, selected_indices, noi_dung):
    selected_df = df.iloc[selected_indices].reset_index(drop=True)

    clear()
    print("=" * 60)
    print("  BƯỚC 3/3 — XÁC NHẬN & GỬI")
    print("=" * 60)
    print(f"\n  Sẽ gửi đến {len(selected_df)} group")
    est = len(selected_df) * ((DELAY_MIN + DELAY_MAX) // 2)
    print(f"  Ước tính: ~{est // 60} phút {est % 60} giây\n")

    for i, row in selected_df.iterrows():
        vt = str(row.get('Tên viết tắt', row['ID ST']))
        print(f"    • {row['ID ST']:<7} {vt}")

    print()
    go = input("  ▶  Bắt đầu gửi? (y/n): ").strip().lower()
    if go != 'y':
        print("  Đã hủy.")
        input("  Bấm Enter để thoát...")
        return

    print()
    success, fail = [], []

    print("  🔌 Đang khởi động Telethon để quét tên SM/TC/GSM...")
    async with TelegramClient(session, api_id, api_hash) as client:
        print("  ✅ Đăng nhập thành công!\n")

        for i, row in selected_df.iterrows():
            id_st   = str(row['ID ST'])
            chat_id = int(row['CHAT ID'])
            vt      = str(row.get('Tên viết tắt', id_st))

            print(f"[{i+1}/{len(selected_df)}] {id_st} | {vt}")

            # Quét thành viên lấy tag SM/TC/GSM đúng tên
            print(f"  🔍 Đang quét thành viên...", end='\r')
            tag_text = await get_tags_for_group(client, chat_id)
            print(f"  🏷️  Tag: {tag_text[:60]}")

            full_text = f"{noi_dung}\n\n{tag_text}"
            ok, resp = await gui_tin(chat_id, full_text)

            if ok:
                print(f"  ✅ Gửi thành công")
                success.append(id_st)
            else:
                desc = resp.get('description', str(resp))
                if 'retry after' in desc.lower():
                    wait = int(''.join(filter(str.isdigit, desc.split('retry after')[-1])))
                    print(f"  ⚠️  Flood! Đợi {wait}s...")
                    await asyncio.sleep(wait + 2)
                    ok2, _ = await gui_tin(chat_id, full_text)
                    if ok2:
                        print(f"  ✅ Gửi thành công (sau flood)")
                        success.append(id_st)
                    else:
                        print(f"  ❌ Thất bại")
                        fail.append(id_st)
                else:
                    print(f"  ❌ Lỗi: {desc}")
                    fail.append(id_st)

            if i + 1 < len(selected_df):
                wait_sec = random.randint(DELAY_MIN, DELAY_MAX)
                for r in range(wait_sec, 0, -1):
                    print(f"  ⏳ Chờ {r}s...", end='\r')
                    await asyncio.sleep(1)
                print(" " * 30, end='\r')

    print("\n" + "=" * 60)
    print(f"  ✅ Thành công: {len(success)}/{len(selected_df)}")
    print(f"  ❌ Thất bại : {len(fail)}")
    if fail:
        print(f"     {', '.join(fail)}")
    print("=" * 60)
    input("\n  Bấm Enter để thoát...")

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
async def main():
    clear()
    print("=" * 60)
    print("   TOOL SPAM TELEGRAM — TÙY CHỌN GROUP")
    print("=" * 60)
    print()

    try:
        df = load_excel()
        print(f"  ✅ Đã tải {len(df)} group từ '{EXCEL_FILE}'")
    except Exception as e:
        print(f"  ❌ Không đọc được file: {e}")
        input("Bấm Enter để thoát...")
        return

    input("  Bấm Enter để bắt đầu...")

    # Bước 1: Chọn group
    selected_indices = buoc_chon_group(df)

    # Bước 2: Soạn tin nhắn
    noi_dung = buoc_soan_tin()

    # Bước 3: Gửi tin
    await buoc_gui(df, selected_indices, noi_dung)


if __name__ == '__main__':
    asyncio.run(main())
