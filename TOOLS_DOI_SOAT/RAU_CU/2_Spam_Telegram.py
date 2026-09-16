import asyncio
from telethon import TelegramClient
import pandas as pd
import requests
import dataframe_image as dfi
import os
import sys

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
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    master_excel = os.path.join(current_dir, 'Danh sách Siêu thị.xlsx')
    
    if not os.path.exists(master_excel):
        print(f"[LỖI] Không tìm thấy file {master_excel}")
        print("Vui lòng đảm bảo file Danh sách Siêu thị.xlsx nằm trong thư mục RAU CỦ.")
        input("Bấm Enter để thoát...")
        sys.exit()

    print("Đang đọc danh sách Chat ID tổng...")
    df_chat = pd.read_excel(master_excel, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['ID ST TƯƠNG ỨNG'], df_chat['CHAT ID']))

    print("Đang tải dữ liệu trực tiếp từ Google Sheet (RAU CỦ QUẢ)...")
    url = 'https://docs.google.com/spreadsheets/d/1XBNLjZLsgaaHDBqVKsbCSYhzD4v-4qMA6rjGXGG4ThM/export?format=xlsx'
    try:
        res = requests.get(url)
        with open('temp_google_sheet_rau_cu.xlsx', 'wb') as f:
            f.write(res.content)
            
        xl = pd.ExcelFile('temp_google_sheet_rau_cu.xlsx')
        sheet_name = [s for s in xl.sheet_names if 'Chênh lệch' in s or 'ST' in s or 'Ch' in s][0]
        df_thieu = xl.parse(sheet_name, header=2) # Dữ liệu bắt đầu từ dòng 3
    except Exception as e:
        print(f"[LỖI] Không thể tải dữ liệu từ Google Sheet: {e}")
        input("Bấm Enter để thoát...")
        sys.exit()

    col_ngay = 'Ngày' if 'Ngày' in df_thieu.columns else 'Ngày chuyển hàng'
    if col_ngay not in df_thieu.columns or 'ID ST' not in df_thieu.columns:
        print(f"[LỖI] Không tìm thấy cột '{col_ngay}' hoặc 'ID ST' trong sheet '{sheet_name}'.")
        input("Bấm Enter để thoát...")
        sys.exit()

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
    
    grouped = df_thieu.groupby('ID ST')

    print("Đang khởi động module quét thành viên...")
    # Dùng chung phiên đăng nhập user_session từ thư mục ĐÔNG MÁT để không phải đăng nhập lại
    session_path = os.path.join(current_dir, '..', 'ĐÔNG MÁT', 'user_session')
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

    success_count = 0
    fail_count = 0
    print(f"Tổng cộng có {len(grouped)} Siêu thị bị thiếu hàng (RAU CỦ QUẢ) cần gửi tin báo.")

    for id_st, group in grouped:
        if id_st not in chat_map:
            print(f"[CẢNH BÁO] Không tìm thấy Chat ID của Siêu thị {id_st} trong file map! Bỏ qua.")
            fail_count += 1
            continue
            
        # Loại bỏ khoảng trắng và .0 trong Chat ID
        chat_id_str = str(chat_map[id_st]).replace('.0', '').strip()
        chat_id = int(chat_id_str)
        
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
            print(f"Lỗi tạo hình ảnh cho ST {id_st}: {e}")
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
                        print(f"[THÀNH CÔNG] Đã tag tên & gửi ảnh RAU CỦ QUẢ cho ST {id_st}.")
                        success_count += 1
                    elif res.status_code == 429:
                        try:
                            error_data = res.json()
                            retry_after = error_data.get("parameters", {}).get("retry_after", 30)
                        except:
                            retry_after = 30
                        print(f"[CẢNH BÁO] Telegram giới hạn tốc độ (Lỗi 429). Tool đang tự động chờ {retry_after} giây rồi gửi tiếp...")
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
    if os.path.exists('temp_google_sheet_rau_cu.xlsx'):
        os.remove('temp_google_sheet_rau_cu.xlsx')
        
    print("==================================================")
    print(f"HOÀN TẤT RAU CỦ QUẢ! Đã gửi: {success_count} ST. Thất bại/Bỏ qua: {fail_count} ST.")
    print("==================================================")
    input("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
