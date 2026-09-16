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
        # Timeout 8s tránh treo nếu nhóm quá đông hoặc mạng lag
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
    print("TOOL SPAM TELEGRAM - NGÀNH HÀNG THỊT CÁ (TỪ GOOGLE SHEET)")
    print("==================================================")
    
    import os
    # Đường dẫn tương đối từ thư mục THỊT CÁ/Tool_Spam tới file Excel ở ĐÔNG MÁT
    current_dir = os.path.dirname(os.path.abspath(__file__))
    master_excel = os.path.join(current_dir, '..', '..', 'ĐÔNG MÁT', 'Danh sách Siêu thị.xlsx')
    
    print("Đang đọc danh sách Chat ID tổng...")
    df_chat = pd.read_excel(master_excel, dtype=str)
    df_chat = df_chat[df_chat['CHAT ID'].notna() & (df_chat['CHAT ID'] != 'nan')]
    chat_map = dict(zip(df_chat['ID ST'], df_chat['CHAT ID']))

    print("Đang tải dữ liệu trực tiếp từ Google Sheet...")
    url = 'https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=xlsx'
    try:
        res = requests.get(url)
        with open('temp_google_sheet.xlsx', 'wb') as f:
            f.write(res.content)
            
        xl = pd.ExcelFile('temp_google_sheet.xlsx')
        df_thieu = xl.parse('Chênh lệch ST', header=1) # Dữ liệu bắt đầu từ dòng 2
    except Exception as e:
        print(f"[LỖI] Không thể tải dữ liệu từ Google Sheet: {e}")
        input("Bấm Enter để thoát...")
        sys.exit()

    if 'Ngày' not in df_thieu.columns or 'ID ST' not in df_thieu.columns:
        print("[LỖI] Cấu trúc Sheet 'Chênh lệch ST' không đúng, thiếu cột Ngày hoặc ID ST!")
        input("Bấm Enter để thoát...")
        sys.exit()

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
    grouped = df_thieu.groupby('ID ST')
    
    client = TelegramClient('user_session', api_id, api_hash)
    await client.start()

    success_count = 0
    fail_count = 0

    for id_st, group in grouped:
        id_st = str(id_st).strip()
        if id_st not in chat_map:
            print(f"[BỎ QUA] Không có Chat ID của Siêu thị {id_st}.")
            fail_count += 1
            continue
            
        chat_id = int(chat_map[id_st])
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
            print(f"Lỗi tạo hình cho ST {id_st}: {e}")
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
                        print(f"[THÀNH CÔNG] Đã tag tên & gửi ảnh cho ST {id_st}.")
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
    
    # Xoá file excel rác
    if os.path.exists('temp_google_sheet.xlsx'):
        os.remove('temp_google_sheet.xlsx')
        
    print("==================================================")
    print(f"HOÀN TẤT! Đã gửi thành công: {success_count} ST.")
    print("==================================================")
    input("Bấm Enter để kết thúc...")

if __name__ == '__main__':
    asyncio.run(main())
