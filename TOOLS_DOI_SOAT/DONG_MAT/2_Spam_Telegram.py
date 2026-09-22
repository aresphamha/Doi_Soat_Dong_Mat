
# -*- coding: utf-8 -*-
import os
import sys

# Đảm bảo UTF-8 Output tránh UnicodeEncodeError trên Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def safe_prompt(msg="Bấm Enter để tiếp tục..."):
    """Dừng chờ phím an toàn khi chạy terminal, tự động bỏ qua nếu chạy daemon / non-interactive."""
    try:
        if sys.stdin and sys.stdin.isatty():
            input(msg)
    except Exception:
        pass

def find_data_file(filename, default_dir=None):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', filename),
        os.path.join(cur_dir, '..', '..', 'CONFIG_DATA', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ', filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(cur_dir, filename)

import time
import json
import asyncio
from telethon import TelegramClient
import pandas as pd
import requests
import dataframe_image as dfi

def get_history_file():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, '..', '..', 'CONFIG_DATA', 'sent_history.json'),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', 'sent_history.json'),
        os.path.join(cur_dir, 'sent_history.json')
    ]
    for c in candidates:
        if os.path.exists(os.path.dirname(os.path.abspath(c))):
            return os.path.abspath(c)
    return os.path.join(cur_dir, 'sent_history.json')

def load_sent_stores(tool_name, date_str):
    hist_file = get_history_file()
    if os.path.exists(hist_file):
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get(date_str, {}).get(tool_name, []))
        except Exception:
            return set()
    return set()

def record_sent_store(tool_name, date_str, id_st):
    hist_file = get_history_file()
    data = {}
    if os.path.exists(hist_file):
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    if date_str not in data:
        data[date_str] = {}
    if tool_name not in data[date_str]:
        data[date_str][tool_name] = []
    if id_st not in data[date_str][tool_name]:
        data[date_str][tool_name].append(id_st)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(hist_file)), exist_ok=True)
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

api_id = '28938971'
api_hash = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
bot_token = '8810108114:AAHFyBEL_JoNFdn2r3V21zEDtElUBU_nV-E'
url_send_photo = f'https://api.telegram.org/bot{bot_token}/sendPhoto'

def disable_quickedit():
    """Tắt tính năng QuickEdit của Windows Console để chuột click vào không bị treo/pause tool"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_stdin = kernel32.GetStdHandle(-10)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(h_stdin, ctypes.byref(mode))
        mode.value &= ~0x0040  # Tắt QuickEdit
        mode.value |= 0x0080   # Bật Extended Flags
        kernel32.SetConsoleMode(h_stdin, mode)
    except Exception:
        pass

async def get_tags_for_group(client, chat_id):
    chat_id_int = int(str(chat_id).replace('.0', '').strip())
    chat_key = str(chat_id_int)
    
    # 1. Nếu client Telegram đang hoạt động (Local PC), thử quét live trước
    if client and hasattr(client, 'is_connected') and client.is_connected():
        try:
            if await client.is_user_authorized():
                participants = await asyncio.wait_for(client.get_participants(chat_id_int), timeout=6)
                tags = []
                for p in participants:
                    name = ""
                    if p.first_name: name += p.first_name
                    if p.last_name: name += " " + p.last_name
                    name_upper = name.upper()
                    if any(r in name_upper for r in [' TC', '-TC', ' SM', '-SM', ' GSM', '-GSM']):
                        tags.append(f"[{name}](tg://user?id={p.id})")
                if tags:
                    res = " ".join(tags)
                    try:
                        tag_file = find_data_file('group_tags_map.json')
                        if os.path.exists(tag_file):
                            with open(tag_file, 'r', encoding='utf-8') as f:
                                t_map = json.load(f)
                            if t_map.get(chat_key) != res:
                                t_map[chat_key] = res
                                with open(tag_file, 'w', encoding='utf-8') as f:
                                    json.dump(t_map, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    return res
        except Exception:
            pass

    # 2. Nếu chạy trên Cloud Runner (không có User session) hoặc quét live lỗi: Đọc từ Tag Map Cache
    tag_file = find_data_file('group_tags_map.json')
    if os.path.exists(tag_file):
        try:
            with open(tag_file, 'r', encoding='utf-8') as f:
                tag_map = json.load(f)
                if chat_key in tag_map and tag_map[chat_key] and tag_map[chat_key] != '@SM @TC @GSM':
                    return tag_map[chat_key]
        except Exception:
            pass

    return "@SM @TC @GSM"

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tool Spam Telegram Đông Mát")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử không gửi tin nhắn thật")
    parser.add_argument("--date", default=None, help="Ngày lọc (YYYY-MM-DD)")
    parser.add_argument("--stores", default="ALL", help="Danh sách mã ST cần gửi")
    args = parser.parse_args()

    disable_quickedit()
    print("==================================================")
    print(f"TOOL SPAM TELEGRAM - NGÀNH HÀNG ĐÔNG MÁT {'[CHẾ ĐỘ CHẠY THỬ / DRY-RUN]' if args.dry_run else ''}")
    print("==================================================")
    
    excel_path = find_data_file('Danh sách Siêu thị.xlsx')
    if not os.path.exists(excel_path):
        excel_path = find_data_file('Danh_Sach_Sieu_Thi_Dong_Mat.xlsx')
    print(f"Đang đọc danh sách Chat ID từ: {excel_path}...")
    df_chat = pd.read_excel(excel_path, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    
    chat_map = {}
    if 'ID ST' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['ID ST'].astype(str).str.strip(), df_chat['CHAT ID'])))
    if 'Tên Siêu thị' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID'])))

    print("Đang tải dữ liệu trực tiếp từ Google Sheet (ĐÔNG MÁT)...")
    url_csv = 'https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/gviz/tq?tqx=out:csv&sheet=Ch%C3%AAnnh%20l%E1%BB%87ch%20ST'
    url_xlsx = 'https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=xlsx'
    cache_file = 'temp_google_sheet_dongmat.xlsx'
    df_thieu = None
    
    # 1. Thử tải CSV siêu tốc (1-2 giây)
    for attempt in range(1, 4):
        try:
            print(f"📥 Đang tải Google Sheet Đông Mát qua CSV (Lần {attempt}/3, timeout 30s)...", flush=True)
            res = requests.get(url_csv, timeout=30)
            res.raise_for_status()
            lines = res.content.decode('utf-8-sig', errors='replace').splitlines()
            if len(lines) > 2:
                import io
                df_thieu = pd.read_csv(io.StringIO('\n'.join(lines[1:])), low_memory=False)
                print(f"⚡ Đã tải thành công qua CSV: {len(df_thieu):,} dòng!", flush=True)
                break
        except Exception as e:
            print(f"⚠️ Thử tải CSV lần {attempt} thất bại: {e}", flush=True)
            time.sleep(1.5)

    # 2. Nếu CSV không được, fallback sang XLSX
    if df_thieu is None:
        for attempt in range(1, 4):
            try:
                print(f"📥 Fallback tải XLSX Google Sheet Đông Mát (Lần {attempt}/3, timeout 90s)...", flush=True)
                res = requests.get(url_xlsx, timeout=90)
                res.raise_for_status()
                with open(cache_file, 'wb') as f:
                    f.write(res.content)
                xl = pd.ExcelFile(cache_file)
                df_thieu = xl.parse('Chênh lệch ST', header=1)
                print("✅ Đã tải và đồng bộ XLSX Đông Mát thành công!", flush=True)
                break
            except Exception as e:
                print(f"⚠️ Cảnh báo tải XLSX lần {attempt}: {e}", flush=True)
                time.sleep(2)

    # 3. Nếu vẫn không được, fallback file cache cục bộ
    if df_thieu is None:
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
            print(f"⚠️ [CHẾ ĐỘ DỰ PHÒNG] Không thể tải mới, tự động đọc file cache sẵn có: {cache_file}", flush=True)
            try:
                xl = pd.ExcelFile(cache_file)
                df_thieu = xl.parse('Chênh lệch ST', header=1)
            except Exception as e:
                print(f"[LỖI] Đọc cache thất bại: {e}")
                safe_prompt("Bấm Enter để thoát...")
                sys.exit(1)
        else:
            print("[LỖI] Không thể tải dữ liệu từ Google Sheet sau các lần thử.")
            safe_prompt("Bấm Enter để thoát...")
            sys.exit(1)

    # Xác định các cột theo Cột A (idx 0 - Ngày), Cột W (idx 22 - Lỗi), Cột D (idx 3 - ID ST)
    col_ngay = df_thieu.columns[0] if len(df_thieu.columns) > 0 else 'Ngày'
    col_id_st = df_thieu.columns[3] if len(df_thieu.columns) > 3 else 'ID ST'
    col_loi = df_thieu.columns[22] if len(df_thieu.columns) > 22 else 'Lỗi'

    # Loại bỏ các dòng không có ID ST hợp lệ
    df_thieu = df_thieu[df_thieu[col_id_st].notna() & (df_thieu[col_id_st].astype(str).str.strip() != '') & (df_thieu[col_id_st].astype(str).str.strip().str.lower() != 'nan')]

    # Lọc lấy ngày
    df_thieu[col_ngay] = pd.to_datetime(df_thieu[col_ngay], errors='coerce')
    if args.date:
        try:
            target_dt = pd.to_datetime(args.date)
            # Kiem tra neu ngay chi dinh co data trong Sheet khong
            df_check = df_thieu[df_thieu[col_ngay] == target_dt]
            if len(df_check) > 0:
                latest_date = target_dt
                print(f"📅 Đã chọn lọc theo ngày chỉ định: {args.date}")
            else:
                # Khong co data cho ngay chi dinh -> lay ngay moi nhat trong Sheet
                latest_date = df_thieu[col_ngay].dropna().max()
                print(f"⚠️ Ngày {args.date} chưa có dữ liệu trong Sheet, tự động lọc ngày mới nhất: {latest_date.strftime('%Y-%m-%d')}")
        except Exception:
            latest_date = df_thieu[col_ngay].dropna().max()
    else:
        latest_date = df_thieu[col_ngay].dropna().max()

    if pd.isna(latest_date):
        print("[LỖI] Không tìm thấy dữ liệu ngày hợp lệ trong Cột A!")
        safe_prompt("Bấm Enter để thoát...")
        sys.exit(1)

    date_str = latest_date.strftime('%d.%m')
    print(f"📅 Ngày dữ liệu: {latest_date.strftime('%Y-%m-%d')} ({date_str})")
    
    # 1. Lọc theo Ngày
    df_thieu = df_thieu[df_thieu[col_ngay] == latest_date]
    print(f"📊 Số dòng sau khi lọc Ngày: {len(df_thieu):,} dòng")

    # 2. Lọc theo Lỗi = 'DC GIAO THIẾU' (Cột W)
    df_thieu = df_thieu[df_thieu[col_loi].astype(str).str.upper().str.contains('DC GIAO THIẾU', na=False)]
    print(f"🎯 Số dòng sau khi lọc Lỗi 'DC GIAO THIẾU' (Cột W): {len(df_thieu):,} dòng")

    # Loại bỏ khoảng trắng thừa trong ID ST
    df_thieu[col_id_st] = df_thieu[col_id_st].astype(str).str.strip()
    
    # Lọc danh sách ST nếu có chỉ định
    if args.stores and str(args.stores).strip().upper() != "ALL":
        target_stores = [s.strip().upper() for s in str(args.stores).split(',') if s.strip()]
        df_thieu = df_thieu[df_thieu[col_id_st].str.upper().isin(target_stores)]
        print(f"🏪 Đã lọc theo danh sách {len(target_stores)} Siêu thị chỉ định: {target_stores}")

    grouped = list(df_thieu.groupby(col_id_st))
    total_st = len(grouped)
    
    date_key = latest_date.strftime('%Y-%m-%d')
    already_sent = load_sent_stores('dong_mat', date_key) if not args.dry_run else set()
    if already_sent:
        print(f"🛡️ [BẢO VỆ CHỐNG TRÙNG] Đã phát hiện {len(already_sent)} ST đã gửi thành công hôm nay ({date_key}). Hệ thống sẽ tự động bỏ qua.", flush=True)

    print(f"📊 Tìm thấy {total_st} Siêu thị bị thiếu hàng (ĐÔNG MÁT) cần gửi tin báo.", flush=True)

    session_file = find_data_file('user_session')
    if session_file.endswith('.session'):
        session_file = session_file[:-8]
    client = TelegramClient(session_file, api_id, api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            print("✅ Đã kết nối phiên Telegram cá nhân (Live Tag Mode).", flush=True)
        else:
            print("ℹ️ Chế độ Tag Quản Lý Ngoại Tuyến (Offline Tag Map Mode).", flush=True)
    except Exception:
        print("ℹ️ Chế độ Tag Quản Lý Ngoại Tuyến (Offline Tag Map Mode).", flush=True)

    success_count = 0
    fail_count = 0
    skipped_sent_count = 0

    for idx, (id_st, group) in enumerate(grouped, 1):
        id_st = str(id_st).strip()
        if id_st in already_sent and not args.dry_run:
            print(f"⏩ [{idx}/{total_st}] [ĐÃ GỬI TRƯỚC ĐÓ] ST {id_st} đã nhận báo cáo hôm nay -> Tự động BỎ QUA tránh spam trùng lặp!", flush=True)
            skipped_sent_count += 1
            continue

        if id_st not in chat_map:
            print(f"⏭️ [{idx}/{total_st}] [BỎ QUA] Không tìm thấy Chat ID của Siêu thị {id_st}.", flush=True)
            fail_count += 1
            continue
            
        chat_id_str = str(chat_map[id_st]).replace('.0', '').strip()
        chat_id = int(chat_id_str)
        
        tag_text = await get_tags_for_group(client, chat_id)
        
        caption_text = f'''**ĐÔNG MÁT**
{date_str}
ST kiểm tra lại giúp Hà sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng

- Với mã hàng nhận thiếu item(nếu có chụp hình QUÊN up trong phiếu) : cung cấp hình ảnh SL thực nhận 

*NOTE*:
 Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM
 
{tag_text}'''

        df_slice = pd.DataFrame({
            'ID ST': group.iloc[:, 3].values,
            'Nhóm hàng': group.iloc[:, 1].values,
            'Mã hàng': [str(x).replace('.0', '') for x in group.iloc[:, 4].values],
            'Tên SP': group.iloc[:, 5].values,
            'ĐVT': group.iloc[:, 6].values,
            'Số lượng chuyển': group.iloc[:, 7].values
        }).reset_index(drop=True)
        img_path = f"temp_{id_st}.png"
        
        if args.dry_run:
            print(f"🔍 [DRY-RUN] [{idx}/{total_st}] ST {id_st} (Chat ID: {chat_id}) - {len(group)} dòng hàng. Tag: {tag_text}", flush=True)
            success_count += 1
            continue

        print(f"👉 [{idx}/{total_st}] Đang chuẩn bị ảnh & Tag tên quản lý cho ST {id_st} ({len(group)} dòng hàng)...", flush=True)
        try:
            dfi.export(df_slice, img_path, table_conversion="matplotlib", dpi=200)
        except Exception as e:
            print(f"❌ [{idx}/{total_st}] Lỗi tạo hình ảnh cho ST {id_st}: {e}", flush=True)
            fail_count += 1
            continue
            
        max_retries = 5
        retry_count = 0
        retry = True
        while retry and retry_count < max_retries:
            retry = False
            try:
                with open(img_path, 'rb') as f:
                    res = requests.post(
                        url_send_photo,
                        files={'photo': f},
                        data={'chat_id': chat_id, 'caption': caption_text, 'parse_mode': 'Markdown'},
                        headers={'Connection': 'close'},
                        timeout=40
                    )
                    if res.status_code == 200:
                        print(f"✅ [{idx}/{total_st}] [THÀNH CÔNG] Đã tag tên & gửi ảnh ĐÔNG MÁT cho ST {id_st} (Chat ID: {chat_id})", flush=True)
                        success_count += 1
                        record_sent_store('dong_mat', date_key, id_st)
                    elif res.status_code == 429:
                        try:
                            error_data = res.json()
                            retry_after = error_data.get("parameters", {}).get("retry_after", 30)
                        except:
                            retry_after = 30
                        print(f"⏳ [{idx}/{total_st}] Telegram giới hạn tốc độ (429). Tự động chờ {retry_after}s...", flush=True)
                        await asyncio.sleep(retry_after)
                        retry = True
                    elif res.status_code == 400 and "too Many Requests" in res.text:
                        import re
                        match = re.search(r'retry after (\d+)', res.text)
                        retry_after = int(match.group(1)) if match else 30
                        print(f"[CẢNH BÁO] Telegram giới hạn tốc độ (Lỗi 400). Tool đang tự động chờ {retry_after} giây rồi gửi tiếp...")
                        await asyncio.sleep(retry_after)
                        retry = True
                    else:
                        print(f"[LỖI] Không thể gửi ĐÔNG MÁT cho ST {id_st}: {res.text}")
                        fail_count += 1
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 3 + retry_count * 2
                    print(f"[MẠNG CHẬP CHỜN] Lỗi kết nối ST {id_st} ({e}). Đang tạo kết nối mới thử lại lần {retry_count}/{max_retries} sau {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    retry = True
                else:
                    print(f"[LỖI] Lỗi kết nối ST {id_st} sau {max_retries} lần thử: {e}")
                    fail_count += 1
        
        if os.path.exists(img_path): os.remove(img_path)
        await asyncio.sleep(3)

    try:
        await client.disconnect()
    except Exception:
        pass
    
    try:
        if os.path.exists('temp_google_sheet_dongmat.xlsx'):
            os.remove('temp_google_sheet_dongmat.xlsx')
    except Exception:
        pass
        
    print("==================================================", flush=True)
    if args.dry_run:
        print(f"🎉 HOÀN TẤT KIỂM TRA (DRY-RUN)! Đã duyệt qua {success_count} Siêu thị hợp lệ (Không gửi tin nhắn).", flush=True)
    else:
        print(f"🎉 HOÀN TẤT ĐÔNG MÁT! Đã gửi mới: {success_count} ST | Đã bỏ qua vì đã gửi trước đó: {skipped_sent_count} ST | Thất bại: {fail_count} ST.", flush=True)
    print("==================================================", flush=True)
    safe_prompt("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
