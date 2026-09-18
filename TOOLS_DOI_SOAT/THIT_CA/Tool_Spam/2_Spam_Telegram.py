
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
        os.path.join(cur_dir, filename + '.session'),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', filename + '.session'),
        os.path.join(cur_dir, '..', filename),
        os.path.join(cur_dir, '..', filename + '.session'),
        os.path.join(cur_dir, '..', '..', 'DONG_MAT', filename),
        os.path.join(cur_dir, '..', '..', 'DONG_MAT', filename + '.session'),
        os.path.join(cur_dir, '..', '..', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', '..', 'CONFIG_DATA', filename + '.session'),
        os.path.join(cur_dir, '..', '..', 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', filename),
        os.path.join(cur_dir, '..', '..', 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', filename + '.session'),
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
        os.path.join(cur_dir, 'sent_history.json'),
        os.path.join(cur_dir, '..', '..', 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'sent_history.json'),
        os.path.join(cur_dir, '..', '..', 'CONFIG_DATA', 'sent_history.json'),
        os.path.join(cur_dir, '..', 'CONFIG_DATA', 'sent_history.json')
    ]
    for c in candidates:
        if os.path.exists(c):
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
    tags = []
    try:
        if not await client.is_user_authorized():
            return "@SM @TC @GSM"
        participants = await asyncio.wait_for(client.get_participants(chat_id), timeout=8)
        for p in participants:
            name = ""
            if p.first_name: name += p.first_name
            if p.last_name: name += " " + p.last_name
            name_upper = name.upper()
            
            if ' TC' in name_upper or '-TC' in name_upper or ' SM' in name_upper or '-SM' in name_upper or ' GSM' in name_upper or '-GSM' in name_upper:
                tags.append(f"[{name}](tg://user?id={p.id})")
    except Exception:
        pass
    return " ".join(tags) if tags else "@SM @TC @GSM"

async def main():
    disable_quickedit()
    print("==================================================")
    print("TOOL SPAM TELEGRAM - NGÀNH HÀNG THỊT CÁ (TỪ GOOGLE SHEET)")
    print("==================================================")
    
    master_excel = find_data_file('Danh sách Siêu thị.xlsx')
    if not os.path.exists(master_excel):
        master_excel = find_data_file('Danh_Sach_Sieu_Thi_Dong_Mat.xlsx')
    
    print(f"Đang đọc danh sách Chat ID tổng từ: {master_excel}...")
    df_chat = pd.read_excel(master_excel, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    
    # Map linh hoạt theo cả ID ST lẫn Tên Siêu thị
    chat_map = {}
    if 'ID ST' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['ID ST'].astype(str).str.strip(), df_chat['CHAT ID'])))
    if 'Tên Siêu thị' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID'])))

    print("Đang tải dữ liệu trực tiếp từ Google Sheet...")
    url = 'https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=xlsx'
    download_success = False
    cache_file = 'temp_google_sheet.xlsx'
    
    for attempt in range(1, 4):
        try:
            print(f"📥 Đang kết nối tải Google Sheet Thịt Cá (Lần {attempt}/3, timeout 90s)...", flush=True)
            res = requests.get(url, timeout=90)
            res.raise_for_status()
            with open(cache_file, 'wb') as f:
                f.write(res.content)
            download_success = True
            print("✅ Đã tải và đồng bộ Google Sheet Thịt Cá thành công!", flush=True)
            break
        except Exception as e:
            print(f"⚠️ Cảnh báo tải lần {attempt}: {e}", flush=True)
            time.sleep(2)
            
    if not download_success:
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
            print(f"⚠️ [CHẾ ĐỘ DỰ PHÒNG] Không thể tải mới do mạng chậm, tự động sử dụng file cache sẵn có: {cache_file}", flush=True)
        else:
            print(f"[LỖI] Không thể tải dữ liệu từ Google Sheet sau 3 lần thử: {e}")
            safe_prompt("Bấm Enter để thoát...")
            sys.exit(1)

    try:
        xl = pd.ExcelFile(cache_file)
        df_thieu = xl.parse('Chênh lệch ST', header=1) # Dữ liệu bắt đầu từ dòng 2
    except Exception as e:
        print(f"[LỖI] Đọc dữ liệu file Excel thất bại: {e}")
        safe_prompt("Bấm Enter để thoát...")
        sys.exit(1)

    if 'Ngày' not in df_thieu.columns or 'ID ST' not in df_thieu.columns:
        print("[LỖI] Cấu trúc Sheet 'Chênh lệch ST' không đúng, thiếu cột Ngày hoặc ID ST!")
        safe_prompt("Bấm Enter để thoát...")
        sys.exit(1)

    # Lọc lấy ngày mới nhất
    df_thieu['Ngày'] = pd.to_datetime(df_thieu['Ngày'], errors='coerce')
    latest_date = df_thieu['Ngày'].max()
    print(f"Ngày có dữ liệu mới nhất trong Sheet là: {latest_date.strftime('%Y-%m-%d')}")
    
    # Chỉ lấy các dòng của ngày mới nhất, có ID ST, và cột Lỗi là "DC GIAO THIẾU"
    df_thieu = df_thieu[(df_thieu['Ngày'] == latest_date) & (df_thieu['ID ST'].notna())]
    if 'Lỗi' in df_thieu.columns:
        df_thieu = df_thieu[df_thieu['Lỗi'].astype(str).str.contains('DC GIAO THIẾU', case=False, na=False)]
    else:
        print("[CẢNH BÁO] Không tìm thấy cột 'Lỗi' trong file để lọc 'DC GIAO THIẾU'!")
    
    # Chuẩn hoá ID ST bằng cách xoá khoảng trắng thừa để không bị trùng lặp nhóm
    df_thieu['ID ST'] = df_thieu['ID ST'].astype(str).str.strip()
    grouped = list(df_thieu.groupby('ID ST'))
    total_st = len(grouped)
    
    date_key = latest_date.strftime('%Y-%m-%d')
    already_sent = load_sent_stores('thit_ca', date_key)
    if already_sent:
        print(f"🛡️ [BẢO VỆ CHỐNG TRÙNG] Đã phát hiện {len(already_sent)} ST đã gửi thành công hôm nay ({date_key}). Hệ thống sẽ tự động bỏ qua.", flush=True)

    print(f"📊 Tìm thấy {total_st} Siêu thị phát sinh lỗi 'DC GIAO THIẾU' cần gửi thông báo.", flush=True)
    
    session_file = find_data_file('user_session')
    if session_file.endswith('.session'):
        session_file = session_file[:-8]
    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()
    if await client.is_user_authorized():
        print("✅ Đã kết nối phiên đăng nhập Telegram cá nhân để Tag tên quản lý.", flush=True)
    else:
        print("ℹ️ Phiên Telegram cá nhân chưa xác thực (hoặc không có session). Sẽ dùng tag mặc định.", flush=True)

    success_count = 0
    fail_count = 0
    skipped_sent_count = 0

    for idx, (id_st, group) in enumerate(grouped, 1):
        id_st = str(id_st).strip()
        if id_st in already_sent:
            print(f"⏩ [{idx}/{total_st}] [ĐÃ GỬI TRƯỚC ĐÓ] ST {id_st} đã nhận báo cáo hôm nay -> Tự động BỎ QUA tránh spam trùng lặp!", flush=True)
            skipped_sent_count += 1
            continue

        if id_st not in chat_map:
            print(f"⏭️ [{idx}/{total_st}] [BỎ QUA] Không tìm thấy Chat ID cho Siêu thị {id_st}.", flush=True)
            fail_count += 1
            continue
            
        chat_id = int(chat_map[id_st])
        print(f"👉 [{idx}/{total_st}] Đang chuẩn bị ảnh & Tag tên quản lý cho ST {id_st} ({len(group)} dòng hàng)...", flush=True)
        tag_text = await get_tags_for_group(client, chat_id)
        
        date_str = latest_date.strftime('%d.%m')
        caption_text = f'''**THỊT CÁ**
{date_str}
ST kiểm tra lại giúp Hà sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng

- Với mã hàng nhận thiếu item(nếu có chụp hình QUÊN up trong phiếu) : cung cấp hình ảnh SL thực nhận 

*NOTE*:
 Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM
 
{tag_text}'''

        cols_to_keep = ['ID ST', 'Mã hàng', 'Tên Hàng', 'ĐVT', 'Số lượng chuyển']
        cols_exist = [c for c in cols_to_keep if c in group.columns]
        df_slice = group[cols_exist].reset_index(drop=True)
        img_path = f"temp_{id_st}.png"
        
        try:
            styled = df_slice.style.set_properties(**{
                'background-color': '#ffffff', 'color': 'black', 'border-color': 'gray',
                'border-style': 'solid', 'border-width': '1px', 'text-align': 'center', 'padding': '10px 20px'
            }).set_table_styles([{
                'selector': 'th', 'props': [('background-color', '#ff6600'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('border', '1px solid gray'), ('padding', '10px 20px')]
            }])
            dfi.export(styled, img_path, table_conversion="matplotlib", dpi=200)
        except Exception as e:
            print(f"❌ [{idx}/{total_st}] Lỗi tạo hình cho ST {id_st}: {e}", flush=True)
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
                        print(f"✅ [{idx}/{total_st}] [THÀNH CÔNG] Đã gửi ảnh & Tag tên vào Group ST {id_st} (Chat ID: {chat_id})", flush=True)
                        success_count += 1
                        record_sent_store('thit_ca', date_key, id_st)
                    elif res.status_code == 429:
                        try:
                            error_data = res.json()
                            retry_after = error_data.get("parameters", {}).get("retry_after", 30)
                        except:
                            retry_after = 30
                        print(f"⏳ [{idx}/{total_st}] Telegram giới hạn tốc độ (429). Tự động chờ {retry_after}s...", flush=True)
                        await asyncio.sleep(retry_after)
                        retry = True
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
                        print(f"[LỖI] Không thể gửi cho ST {id_st}: {res.text}")
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

    await client.disconnect()
    
    # Đóng và xoá file excel tạm an toàn
    try:
        xl.close()
    except Exception:
        pass
    try:
        if os.path.exists('temp_google_sheet.xlsx'):
            os.remove('temp_google_sheet.xlsx')
    except Exception:
        pass
        
    print("==================================================", flush=True)
    print(f"🎉 HOÀN TẤT! Đã gửi mới: {success_count} ST | Đã bỏ qua vì đã gửi trước đó: {skipped_sent_count} ST | Thất bại: {fail_count} ST.", flush=True)
    print("==================================================", flush=True)
    safe_prompt("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
