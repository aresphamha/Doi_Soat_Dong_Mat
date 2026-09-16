
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
        os.path.join(cur_dir, '..', '..', 'DONG_MAT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\ĐÔNG MÁT', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\THỊT CÁ', filename),
        os.path.join(r'C:\Users\PC\Desktop\AI\Đối soát\RAU CỦ', filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(cur_dir, filename)

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
    tags = []
    try:
        participants = await asyncio.wait_for(client.get_participants(chat_id), timeout=8)
        for p in participants:
            name = ""
            if p.first_name: name += p.first_name
            if p.last_name: name += " " + p.last_name
            name_upper = name.upper()
            
            if ' TC' in name_upper or '-TC' in name_upper or ' SM' in name_upper or '-SM' in name_upper or ' GSM' in name_upper or '-GSM' in name_upper:
                tags.append(f"[{name}](tg://user?id={p.id})")
    except Exception as e:
        pass
    return " ".join(tags) if tags else "@SM @TC @GSM"

async def main():
    disable_quickedit()
    print("==================================================")
    print("TOOL SPAM TELEGRAM - NGÀNH HÀNG RAU CỦ QUẢ (TỪ GOOGLE SHEET)")
    print("==================================================")
    
    master_excel = find_data_file('Danh sách Siêu thị.xlsx')
    if not os.path.exists(master_excel):
        master_excel = find_data_file('Danh_Sach_Sieu_Thi_Dong_Mat.xlsx')
    
    print(f"Đang đọc danh sách Chat ID tổng từ: {master_excel}...")
    df_chat = pd.read_excel(master_excel, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    
    chat_map = {}
    if 'ID ST TƯƠNG ỨNG' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['ID ST TƯƠNG ỨNG'].astype(str).str.strip(), df_chat['CHAT ID'])))
    if 'ID ST' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['ID ST'].astype(str).str.strip(), df_chat['CHAT ID'])))
    if 'Tên Siêu thị' in df_chat.columns:
        chat_map.update(dict(zip(df_chat['Tên Siêu thị'].astype(str).str.strip(), df_chat['CHAT ID'])))

    print("Đang tải dữ liệu trực tiếp từ Google Sheet (RAU CỦ QUẢ)...")
    url = 'https://docs.google.com/spreadsheets/d/1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM/export?format=xlsx'
    try:
        res = requests.get(url, timeout=30)
        with open('temp_google_sheet_rau_cu.xlsx', 'wb') as f:
            f.write(res.content)
            
        xl = pd.ExcelFile('temp_google_sheet_rau_cu.xlsx')
        sheet_name = [s for s in xl.sheet_names if 'Chênh lệch' in s or 'ST' in s or 'Ch' in s][0]
        df_thieu = xl.parse(sheet_name, header=2) # Dữ liệu bắt đầu từ dòng 3
    except Exception as e:
        print(f"[LỖI] Không thể tải dữ liệu từ Google Sheet: {e}")
        safe_prompt("Bấm Enter để thoát...")
        sys.exit(1)

    col_ngay = 'Ngày' if 'Ngày' in df_thieu.columns else 'Ngày chuyển hàng'
    if col_ngay not in df_thieu.columns or 'ID ST' not in df_thieu.columns:
        print(f"[LỖI] Không tìm thấy cột '{col_ngay}' hoặc 'ID ST' trong sheet '{sheet_name}'.")
        safe_prompt("Bấm Enter để thoát...")
        sys.exit(1)

    # Lọc lấy ngày gần nhất
    df_thieu[col_ngay] = pd.to_datetime(df_thieu[col_ngay], errors='coerce')
    latest_date = df_thieu[col_ngay].dropna().max()
    date_str = latest_date.strftime('%d.%m') if pd.notna(latest_date) else 'Hôm nay'
    
    print(f"Đã lấy dữ liệu của ngày gần nhất: {date_str}")
    df_thieu = df_thieu[df_thieu[col_ngay] == latest_date]

    # Lọc lỗi DC GIAO THIẾU
    if 'Lỗi' in df_thieu.columns:
        df_thieu = df_thieu[df_thieu['Lỗi'].astype(str).str.strip().str.upper() == 'DC GIAO THIẾU']
    else:
        print("[CẢNH BÁO] Không tìm thấy cột 'Lỗi', sẽ lấy toàn bộ dữ liệu của ngày gần nhất.")

    # Loại bỏ khoảng trắng thừa trong ID ST
    df_thieu['ID ST'] = df_thieu['ID ST'].astype(str).str.strip()
    grouped = list(df_thieu.groupby('ID ST'))
    total_st = len(grouped)
    
    date_key = latest_date.strftime('%Y-%m-%d') if pd.notna(latest_date) else time.strftime('%Y-%m-%d')
    already_sent = load_sent_stores('rau_cu', date_key)
    if already_sent:
        print(f"🛡️ [BẢO VỆ CHỐNG TRÙNG] Đã phát hiện {len(already_sent)} ST đã gửi thành công hôm nay ({date_key}). Hệ thống sẽ tự động bỏ qua.", flush=True)

    print(f"📊 Tìm thấy {total_st} Siêu thị bị thiếu hàng (RAU CỦ QUẢ) cần gửi tin báo.", flush=True)

    session_path = find_data_file('user_session').replace('.session', '')
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

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
            print(f"⏭️ [{idx}/{total_st}] [BỎ QUA] Không tìm thấy Chat ID của Siêu thị {id_st}.", flush=True)
            fail_count += 1
            continue
            
        # Loại bỏ khoảng trắng và .0 trong Chat ID
        chat_id_str = str(chat_map[id_st]).replace('.0', '').strip()
        chat_id = int(chat_id_str)
        
        print(f"👉 [{idx}/{total_st}] Đang chuẩn bị ảnh & Tag tên quản lý cho ST {id_st} ({len(group)} dòng hàng)...", flush=True)
        tag_text = await get_tags_for_group(client, chat_id)
        
        caption_text = f'''**RAU CỦ QUẢ**
{date_str}
ST kiểm tra lại giúp Hà sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng

- Với mã hàng nhận thiếu item(nếu có chụp hình QUÊN up trong phiếu) : cung cấp hình ảnh SL thực nhận 

*NOTE*:
 Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM
 
{tag_text}'''

        # Kiểm tra cột số lượng chuyển (file Rau Củ là 'SL chuyển', file Thịt Cá là 'Số lượng chuyển')
        col_sl = 'SL chuyển' if 'SL chuyển' in group.columns else ('Số lượng chuyển' if 'Số lượng chuyển' in group.columns else None)
        cols_to_keep = ['ID ST', 'Mã hàng', 'Tên Hàng', 'ĐVT']
        if col_sl:
            cols_to_keep.append(col_sl)
        cols_exist = [c for c in cols_to_keep if c in group.columns]
        df_slice = group[cols_exist].reset_index(drop=True)
        img_path = f"temp_{id_st}.png"
        
        try:
            # Màu xanh lá mạ (#4CAF50) cho Rau Củ QuẢ
            styled = df_slice.style.set_properties(**{
                'background-color': '#ffffff',
                'color': 'black',
                'border-color': 'gray',
                'border-style': 'solid',
                'border-width': '1px',
                'text-align': 'center',
                'padding': '10px 20px'
            }).set_table_styles([{
                'selector': 'th',
                'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('border', '1px solid gray'), ('padding', '10px 20px')]
            }])
            dfi.export(styled, img_path, table_conversion="matplotlib", dpi=200)
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
                        print(f"✅ [{idx}/{total_st}] [THÀNH CÔNG] Đã tag tên & gửi ảnh RAU CỦ QUẢ cho ST {id_st} (Chat ID: {chat_id})", flush=True)
                        success_count += 1
                        record_sent_store('rau_cu', date_key, id_st)
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
                        print(f"[LỖI] Không thể gửi RAU CỦ QUẢ cho ST {id_st}: {res.text}")
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
    
    xl.close()
    # Đóng và xoá file excel tạm an toàn
    try:
        xl.close()
    except Exception:
        pass
    try:
        if os.path.exists('temp_google_sheet_rau_cu.xlsx'):
            os.remove('temp_google_sheet_rau_cu.xlsx')
    except Exception:
        pass
        
    print("==================================================", flush=True)
    print(f"🎉 HOÀN TẤT RAU CỦ QUẢ! Đã gửi mới: {success_count} ST | Đã bỏ qua vì đã gửi trước đó: {skipped_sent_count} ST | Thất bại: {fail_count} ST.", flush=True)
    print("==================================================", flush=True)
    safe_prompt("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
