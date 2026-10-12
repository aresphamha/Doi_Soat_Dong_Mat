import asyncio
import os
import re
import sys
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient, utils
from telethon.tl.functions.messages import GetDialogFiltersRequest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR) if os.path.basename(CURRENT_DIR) == 'TOOLS_DOI_SOAT' else CURRENT_DIR

API_ID = 31209455
API_HASH = 'f636ffaebfaf0bfb52d8709a4cdaaa0e'
SESSION_PATH = os.path.join(ROOT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'user_session')

OUTPUT_FILE = os.path.join(ROOT_DIR, 'Danh_Sach_Chat_ID_Nhom_DC.xlsx')

async def export_dc_chat_ids():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('❌ LỖI: Chưa có quyền truy cập Telegram user_session.')
        return

    print("🔍 Đang lấy danh sách các nhóm trong thư mục DC (176)...")
    res = await client(GetDialogFiltersRequest())
    filters = getattr(res, 'filters', res)

    dc_filter = None
    for f in filters:
        title_obj = getattr(f, 'title', None)
        raw_title = getattr(title_obj, 'text', str(title_obj)) if title_obj else ''
        if 'DC' in raw_title.upper() and getattr(f, 'id', None) is not None:
            dc_filter = f
            print(f"  ✓ Tìm thấy thư mục: '{raw_title}' (ID: {f.id}, Số nhóm cấu hình: {len(f.include_peers)})")
            break

    if not dc_filter:
        print("❌ Không tìm thấy thư mục DC!")
        await client.disconnect()
        return

    # Lập danh sách ID các peer cần lấy
    dc_peer_ids = set()
    for p in dc_filter.include_peers:
        try:
            pid = utils.get_peer_id(p)
            dc_peer_ids.add(pid)
        except Exception:
            pass

    print(f"📦 Đang quét thông tin chi tiết cho {len(dc_peer_ids)} nhóm...")
    
    # Quét dialogs để lấy entity chính xác
    dialog_map = {}
    async for dialog in client.iter_dialogs():
        pid = utils.get_peer_id(dialog.entity)
        if pid in dc_peer_ids:
            dialog_map[pid] = dialog

    rows = []
    stt = 1
    for pid in dc_peer_ids:
        dialog = dialog_map.get(pid)
        if dialog:
            title = dialog.name or ""
            entity = dialog.entity
            ent_type = type(entity).__name__
            members = getattr(entity, 'participants_count', '') or ''
            username = getattr(entity, 'username', '') or ''
        else:
            try:
                entity = await client.get_entity(pid)
                title = getattr(entity, 'title', getattr(entity, 'first_name', str(pid)))
                ent_type = type(entity).__name__
                members = getattr(entity, 'participants_count', '') or ''
                username = getattr(entity, 'username', '') or ''
            except Exception as e:
                title = f"Unknown ({pid})"
                ent_type = "Unknown"
                members = ''
                username = ''

        # Trích xuất mã siêu thị nếu có (ví dụ: A101, A220, B001, ...)
        match = re.search(r'\b([AB]\d{3,4})\b', title, re.IGNORECASE)
        store_code = match.group(1).upper() if match else ""

        rows.append({
            "STT": stt,
            "MÃ SIÊU THỊ": store_code,
            "TÊN NHÓM TELEGRAM": title,
            "CHAT ID (SỐ CHUẨN)": str(pid),
            "LOẠI NHÓM": "Supergroup" if ent_type == "Channel" else "Group",
            "SỐ THÀNH VIÊN": members,
            "USERNAME / LINK": f"@{username}" if username else ""
        })
        stt += 1

    # Sắp xếp theo Mã siêu thị trước, sau đó theo Tên nhóm
    rows.sort(key=lambda x: (x["MÃ SIÊU THỊ"] == "", x["MÃ SIÊU THỊ"], x["TÊN NHÓM TELEGRAM"]))
    # Đánh lại STT sau khi sort
    for i, r in enumerate(rows, 1):
        r["STT"] = i

    df = pd.DataFrame(rows)

    # Ghi ra file Excel với định dạng đẹp mắt
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="NHOM_DC_176")
        ws = writer.sheets["NHOM_DC_176"]

        # Định dạng màu sắc Header
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Segoe UI", size=10)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        for col_num, col_name in enumerate(df.columns, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        # Định dạng các dòng dữ liệu
        for row_num in range(2, len(rows) + 2):
            for col_num in range(1, len(df.columns) + 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.font = regular_font
                cell.border = thin_border
                # STT, Mã ST, Chat ID, Loại nhóm căn giữa
                if col_num in [1, 2, 4, 5, 6]:
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

        # Tự động chỉnh độ rộng cột
        col_widths = {
            1: 8,   # STT
            2: 15,  # MÃ SIÊU THỊ
            3: 45,  # TÊN NHÓM
            4: 20,  # CHAT ID
            5: 15,  # LOẠI NHÓM
            6: 15,  # SỐ THÀNH VIÊN
            7: 22   # USERNAME
        }
        for col_idx, width in col_widths.items():
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        ws.row_dimensions[1].height = 28

    print(f"\n✅ ĐÃ XUẤT THÀNH CÔNG {len(rows)} NHÓM RA FILE EXCEL:")
    print(f"   📁 {OUTPUT_FILE}")

    await client.disconnect()
    return rows

if __name__ == '__main__':
    asyncio.run(export_dc_chat_ids())
