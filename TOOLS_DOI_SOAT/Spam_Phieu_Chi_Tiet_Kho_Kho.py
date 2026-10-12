"""
CÔNG CỤ TỰ ĐỘNG SPAM: PHIẾU CHI TIẾT KHO KHÔ (KHO FGA10101 _ BÌNH THẮNG)
- Lọc theo Ngày Chuyển thực tế (transfer_date) từ ngày cũ nhất đến hết ngày D-1 (hôm qua)
- Bỏ qua ngày hôm nay (chưa đến hạn)
- Gửi ảnh bảng Gradient Xanh lá pastel sang Cam đào pastel vào nhóm DC tra từ Danh_Sach_Chat_ID_Nhom_DC.xlsx
- Tự động tag @SM @TC @GSM và chống spam trùng lặp
"""
import os
import sys
import json
import re
import asyncio
import argparse
from datetime import datetime, timedelta
import pytz
import pymysql
import openpyxl
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR) if os.path.basename(CURRENT_DIR) == 'TOOLS_DOI_SOAT' else CURRENT_DIR

# Import hàm vẽ bảng Pastel Gradient
sys.path.append(CURRENT_DIR)
from table_image_generator import render_pastel_gradient_table

from telethon import TelegramClient

API_ID = '28938971'
API_HASH = '5d392e21b03f0b2f0a1bfdc5ff840b3c'
BOT_TOKEN = '8810108114:AAHWJjis5O3bFyx98-qjOs1PQKTAKMem_zU'
URL_SEND_PHOTO = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'

SESSION_PATH = os.path.join(ROOT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'user_session')

FGA_BRANCHES = {
    '6aabb0a2f426e20007f80123': 'FGA10101 _ Bình Thắng _ Lưu Hàng',
    '6aabb0d73c46470007f935ce': 'FGA10103 _ Bình Thắng _ Khai Trương'
}
FGA_BRANCH_IDS = "('6aabb0a2f426e20007f80123', '6aabb0d73c46470007f935ce')"
HIST_FILE = os.path.join(ROOT_DIR, 'CONFIG_DATA', 'sent_history.json')

def get_db_connection():
    return pymysql.connect(
        host='103.140.248.250',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='TnAM0WEsv4kmasw878wt',
        database='kfm_scm',
        connect_timeout=15,
        read_timeout=30
    )

def load_sent_stores(tool_name, date_str):
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get(date_str, {}).get(tool_name, []))
        except Exception:
            return set()
    return set()

def record_sent_store(tool_name, date_str, store_id):
    data = {}
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.setdefault(date_str, {}).setdefault(tool_name, [])
    if str(store_id) not in data[date_str][tool_name]:
        data[date_str][tool_name].append(str(store_id))
    try:
        os.makedirs(os.path.dirname(os.path.abspath(HIST_FILE)), exist_ok=True)
        with open(HIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_store_and_dc_chat_mappings():
    st_to_code = {}
    dc_code_map = {}
    dc_title_map = {}

    # 1. Đọc ánh xạ từ Danh_Sach_Chat_ID_Nhom_DC.xlsx
    excel_dc = os.path.join(ROOT_DIR, 'Danh_Sach_Chat_ID_Nhom_DC.xlsx')
    if os.path.exists(excel_dc):
        try:
            wb = openpyxl.load_workbook(excel_dc, read_only=True)
            ws = wb.active
            header = [cell.value for cell in next(ws.iter_rows(max_row=1))]
            code_idx = header.index("MÃ SIÊU THỊ") if "MÃ SIÊU THỊ" in header else 1
            title_idx = header.index("TÊN NHÓM TELEGRAM") if "TÊN NHÓM TELEGRAM" in header else 2
            cid_idx = header.index("CHAT ID (SỐ CHUẨN)") if "CHAT ID (SỐ CHUẨN)" in header else 3
            for row in ws.iter_rows(min_row=2, values_only=True):
                c = str(row[code_idx]).strip().upper() if row[code_idx] is not None else ''
                cid = str(row[cid_idx]).strip() if row[cid_idx] is not None else ''
                title = str(row[title_idx]).strip().lower() if row[title_idx] is not None else ''
                if c and c != '---' and cid:
                    dc_code_map[c] = cid
                if cid and title:
                    dc_title_map[title] = cid
            wb.close()
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc file Excel DC: {e}")

    # 2. Đọc mapping Siêu thị -> Mã ST & Chat ID DC từ CONFIG_DATA_STORES.json
    stores_json = os.path.join(ROOT_DIR, 'CONFIG_DATA_STORES.json')
    if os.path.exists(stores_json):
        try:
            with open(stores_json, 'r', encoding='utf-8') as f:
                stores = json.load(f)
                for s in stores:
                    sid = s.get('id', '').strip().upper()
                    sname = s.get('name', '').strip()
                    cid_dc = str(s.get('chat_id_dc', '')).strip()

                    if sid:
                        if sname:
                            st_to_code[sname] = sid
                            clean_sname = sname.replace(' - MINI', '').replace(' - WIN', '').replace(' - SUPER', '').strip()
                            st_to_code[clean_sname] = sid
                            parts = sname.split('-')
                            if len(parts) > 1:
                                st_to_code[parts[-1].strip()] = sid
                        if cid_dc and sid not in dc_code_map:
                            dc_code_map[sid] = cid_dc
        except Exception:
            pass

    return st_to_code, dc_code_map, dc_title_map

async def get_tags_for_group(client, chat_id):
    tags = []
    try:
        participants = await client.get_participants(int(chat_id))
        for p in participants:
            name = (p.first_name or '') + (' ' + p.last_name if p.last_name else '')
            name_upper = name.upper()
            if any(role in name_upper for role in [' TC', '-TC', ' SM', '-SM', ' GSM', '-GSM']):
                tags.append(f"[{name}](tg://user?id={p.id})")
    except Exception:
        pass
    return " ".join(tags) if tags else "@SM @TC @GSM"

async def run_spam_chi_tiet_kho_kho(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("📦 BẮT ĐẦU CHẠY TOOL: PHIẾU CHI TIẾT KHO KHÔ (FGA10101 & FGA10103)")
    print("=======================================================")

    st_to_code, dc_code_map, dc_title_map = load_store_and_dc_chat_mappings()
    print(f"📋 Đã tải {len(dc_code_map)} Chat ID DC và {len(st_to_code)} mapping Siêu thị.")

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_now = datetime.now(vn_tz)
    vn_today_date = vn_now.date()
    today_str = vn_now.strftime('%d.%m')
    date_iso = vn_now.strftime('%Y-%m-%d')

    print(f"⏰ Thời điểm chạy (VN): {vn_now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🎯 Lọc Ngày Chuyển (transfer_date): Từ ngày cũ nhất còn treo đến hết D-1 (< {vn_today_date.strftime('%d/%m/%Y')})")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Lấy tên siêu thị từ stockcard
        cur.execute("""
        SELECT branch_id, branch_name 
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard 
        WHERE branch_name IS NOT NULL AND branch_name != ''
        GROUP BY branch_id, branch_name
        """)
        id_to_name = {bid: bname for bid, bname in cur.fetchall() if bname}

        # Query phiếu chuyển của kho FGA10101 & FGA10103
        sql = f"""
        SELECT 
            t.code,
            t.from_branch_id,
            t.to_branch_id,
            t.transfer_date,
            t.created_at,
            t.status
        FROM __cdc_kfm_kf_inventories_kf_transfer_items t
        WHERE t.from_branch_id IN {FGA_BRANCH_IDS}
          AND t.status = 3
        """
        cur.execute(sql)
        tickets = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ [LỖI KẾT NỐI DATABASE]: {e}")
        return

    # Lọc theo transfer_date < hôm nay
    pending_tickets = []
    for code, from_id, to_id, tdate_str, cat, stt in tickets:
        td_date = None
        if tdate_str:
            try:
                td_utc = datetime.fromisoformat(tdate_str.replace('Z', '+00:00'))
                td_date = td_utc.astimezone(vn_tz).date()
            except Exception:
                pass

        cat_date = pytz.UTC.localize(cat).astimezone(vn_tz).date() if cat else None
        target_eval_date = td_date or cat_date

        if target_eval_date and target_eval_date < vn_today_date:
            st_name = id_to_name.get(to_id, f"ST_{to_id}")
            
            # Trích xuất mã ST
            st_code = st_to_code.get(st_name)
            if not st_code:
                parts = st_name.split('-')
                st_code = st_to_code.get(parts[-1].strip())
            if not st_code:
                m = re.search(r'\b([AB]\d{3,4})\b', st_name, re.IGNORECASE)
                st_code = m.group(1).upper() if m else ""
            if not st_code:
                for sname, sid in st_to_code.items():
                    if len(sname) > 4 and (sname.lower() in st_name.lower() or st_name.lower() in sname.lower()):
                        st_code = sid
                        break

            pending_tickets.append({
                'code': code,
                'from_branch_id': from_id,
                'st_name': st_name,
                'st_code': st_code,
                'to_id': to_id,
                'transfer_date': target_eval_date,
                'transfer_date_str': target_eval_date.strftime('%d/%m/%Y'),
                'transfer_date_short': target_eval_date.strftime('%d.%m')
            })

    print(f"📊 Tìm thấy {len(pending_tickets)} phiếu Chi Tiết Kho Khô tồn đọng cần xử lý.")
    if len(pending_tickets) == 0:
        print("✅ Tuyệt vời! Không có phiếu Chi Tiết Kho Khô nào bị tồn đọng.")
        return

    # Gom nhóm theo Siêu thị
    grouped = {}
    for p in pending_tickets:
        grouped.setdefault(p['st_name'], []).append(p)

    print(f"🏪 Tổng số Đích nhận có phiếu chuyển treo: {len(grouped)}")

    # Khởi động Telegram client
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Vui lòng chạy Dang_Nhap_Telegram.py trước!")
        await client.disconnect()
        return

    sent_today = load_sent_stores('chi_tiet_kho_kho', date_iso)

    success_count = 0
    fail_count = 0

    headers = ["Mã phiếu chuyển", "Ngày chuyển", "Nơi chuyển", "Nơi nhận", "Trạng thái"]

    for st_name, group in grouped.items():
        st_code = group[0]['st_code']
        chat_id_raw = dc_code_map.get(st_code) if st_code else None
        
        # Nếu chưa có theo mã, thử tìm mờ theo tên nhóm DC
        if not chat_id_raw:
            parts = st_name.split('-')
            addr = parts[-1].strip().lower() if len(parts) > 1 else st_name.lower()
            addr_clean = re.sub(r'^(mini|win|super)\s*', '', addr).strip()
            for t, cid in dc_title_map.items():
                if len(addr_clean) > 4 and addr_clean in t:
                    chat_id_raw = cid
                    break

        if not chat_id_raw:
            print(f"⚠️ [LOẠI BỎ - KHÔNG CÓ GROUP DC] Siêu thị: {st_name} (Mã: {st_code or 'N/A'}) - Bỏ qua vì không có nhóm DC.")
            fail_count += 1
            continue

        try:
            chat_id = int(str(chat_id_raw).strip())
        except Exception:
            fail_count += 1
            continue

        if str(chat_id) in sent_today:
            print(f"⏩ [ĐÃ GỬI TRƯỚC ĐÓ] Bỏ qua ST: {st_name} ({chat_id})")
            continue

        # Sắp xếp phiếu của ST theo ngày chuyển tăng dần (cũ nhất lên đầu)
        group.sort(key=lambda x: x['transfer_date'])
        oldest_d = group[0]['transfer_date_short']
        newest_d = group[-1]['transfer_date_short']
        total_p = len(group)

        # Xây dựng cú pháp Caption chuẩn theo yêu cầu:
        if total_p == 1:
            ticket_clause = f"còn 1 phiếu chi tiết kho khô chưa nhận ngày {oldest_d}."
        else:
            if oldest_d == newest_d:
                ticket_clause = f"còn {total_p} phiếu chi tiết kho khô chưa nhận ngày {oldest_d}."
            else:
                ticket_clause = f"còn {total_p} phiếu chi tiết kho khô chưa nhận từ ngày {oldest_d} đến {newest_d}."

        tag_text = await get_tags_for_group(client, chat_id)
        caption = f"**PHIẾU CHI TIẾT KHO KHÔ**\n{today_str}\n⚠️ Siêu thị {ticket_clause}\nSiêu thị kiểm tra HOÀN THÀNH phiếu CHI TIẾT KHO KHÔ gấp nhé team\n{tag_text}"

        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {st_name} (Mã: {st_code}, CID: {chat_id}): {total_p} phiếu [{ticket_clause}]")
            continue

        # Tạo ảnh bảng Gradient Pastel
        rows = []
        for item in group:
            from_name = FGA_BRANCHES.get(item.get('from_branch_id'), 'FGA10101 _ Bình Thắng _ Lưu Hàng')
            rows.append([
                item['code'],
                item['transfer_date_str'],
                from_name,
                item['st_name'],
                "Đang chuyển"
            ])

        img_path = os.path.join(CURRENT_DIR, f"temp_ct_khokho_{chat_id}.png")
        try:
            render_pastel_gradient_table(headers, rows, img_path)
            
            with open(img_path, 'rb') as f:
                resp = requests.post(
                    URL_SEND_PHOTO,
                    data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                    files={'photo': f},
                    timeout=20
                )
            if os.path.exists(img_path):
                os.remove(img_path)

            res_json = resp.json() if resp.status_code == 200 else {}
            if resp.status_code == 200 and res_json.get('ok'):
                record_sent_store('chi_tiet_kho_kho', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI THÀNH CÔNG] ST: {st_name} ({chat_id}) - {total_p} phiếu")
                success_count += 1
            else:
                err_desc = res_json.get('description', f'HTTP {resp.status_code}')
                print(f"❌ [LỖI TELEGRAM] ST: {st_name} ({chat_id}): {err_desc}")
                fail_count += 1

            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ [LỖI XỬ LÝ] ST {st_name}: {e}")
            fail_count += 1
            if os.path.exists(img_path): os.remove(img_path)

    await client.disconnect()
    print("=======================================================")
    print(f"🎉 HOÀN TẤT! Đã gửi: {success_count} ST. Lỗi/Bỏ qua: {fail_count} ST.")
    print("=======================================================")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Chạy thử không gửi tin')
    args = parser.parse_args()
    asyncio.run(run_spam_chi_tiet_kho_kho(dry_run=args.dry_run))
