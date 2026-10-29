"""
CÔNG CỤ TỰ ĐỘNG SPAM: PHIẾU HẬU KIỂM KHO KHÔ (KHO FGA10101 _ BÌNH THẮNG)
- Lọc theo phiếu Hậu kiểm (double_checked_status = 1, status = 5) từ ngày cũ nhất đến hết ngày D-1 (hôm qua)
- Bỏ qua ngày hôm nay
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
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", '8810108114:AAER-s5oEc3pAoggenGm0R5fjA3xMDdQswM')
URL_SEND_PHOTO = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'

SESSION_PATH = os.path.join(ROOT_DIR, 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'SPAM_PHIEU_CHUYEN', 'CONFIG_DATA', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(ROOT_DIR, 'DONG_MAT_DASHBOARD', 'user_session')
if not os.path.exists(SESSION_PATH + '.session'):
    SESSION_PATH = os.path.join(CURRENT_DIR, 'user_session')

FGA_BRANCHES = {
    '6aabb0a2f426e20007f80123': 'FGA10101 _ Bình Thắng _ Lưu Hàng',
    '6aabb0d73c46470007f935ce': 'FGA10103 _ Bình Thắng _ Khai Trương',
    '6aa77de130fded00073d4521': 'Kho Khô FGA Vệ Tinh',
    '6a34ed56f23028000774139f': 'MeatFish - Miền Đông - SCF - Quá Cảnh'
}
FGA_BRANCH_IDS = "('6aabb0a2f426e20007f80123', '6aabb0d73c46470007f935ce', '6aa77de130fded00073d4521', '6a34ed56f23028000774139f')"
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
    store_fallbacks = {}

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

    # Nhóm DC được phát hiện bổ sung chuẩn từ Telegram
    dc_code_map['OPS'] = '-4879460816'     # DC-OPS (Opal Skyline)
    dc_code_map['THD'] = '-1002012247830'  # DC-THD (229A Tân Hòa Đông)
    dc_code_map['A164'] = '-5114128163'    # DC - A164 (Opal Boulevard)
    dc_code_map['A215'] = '-1004387715043' # DC - A215 (Thạnh Xuân 14)
    dc_code_map['VH4'] = '-4806936749'     # VH4 - DC (S07.02 Vinhomes Grand Park)
    dc_code_map['A161'] = '-5100652138'    # DC - A161 (The Park Residence)
    dc_code_map['A254'] = '-1003932058795' # DC - A254 (Phú Cường Home)
    dc_code_map['A265'] = '-1004390985524' # DC - A265 (Nguyễn Tư Giản)
    st_to_code['KFM_HCM_Q12 - 310/10 Khu Phố 1 Thạnh Xuân 14'] = 'A215'
    st_to_code['310/10 Khu Phố 1 Thạnh Xuân 14'] = 'A215'
    st_to_code['Thạnh Xuân 14'] = 'A215'
    st_to_code['KFM_HCM_TDU - S07.02 Vinhomes Grand Park'] = 'VH4'
    st_to_code['S07.02 Vinhomes Grand Park'] = 'VH4'
    st_to_code['KFM_HCM_NBE - A2.SH28-30 The Park Residence'] = 'A161'
    st_to_code['A2.SH28-30 The Park Residence'] = 'A161'
    st_to_code['KFM_HCM_Q12 - S.06 Chung Cư Phú Cường Home'] = 'A254'
    st_to_code['S.06 Chung Cư Phú Cường Home'] = 'A254'
    st_to_code['Phú Cường Home'] = 'A254'
    st_to_code['KFM_HCM_GVA - 232 Nguyễn Tư Giản'] = 'A265'
    st_to_code['232 Nguyễn Tư Giản'] = 'A265'
    st_to_code['Nguyễn Tư Giản'] = 'A265'

    # 2. Đọc mapping Siêu thị -> Mã ST & Chat ID DC/ĐM từ CONFIG_DATA_STORES.json
    stores_json = os.path.join(ROOT_DIR, 'CONFIG_DATA_STORES.json')
    if os.path.exists(stores_json):
        try:
            with open(stores_json, 'r', encoding='utf-8') as f:
                stores = json.load(f)
                for s in stores:
                    sid = s.get('id', '').strip().upper()
                    sname = s.get('name', '').strip()
                    cid_dc = str(s.get('chat_id_dc', '')).strip()
                    cid_dm = str(s.get('chat_id_dm', '')).strip()

                    if sid:
                        store_fallbacks[sid] = {'chat_id_dc': cid_dc, 'chat_id_dm': cid_dm, 'name': sname}
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

    return st_to_code, dc_code_map, dc_title_map, store_fallbacks

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

async def run_spam_hau_kiem_kho_kho(target_date=None, dry_run=False, stores=None, force=False):
    print("\n=======================================================")
    print("⚖️ BẮT ĐẦU CHẠY TOOL: PHIẾU HẬU KIỂM KHO KHÔ (FGA BÌNH THẮNG)")
    print("=======================================================")

    st_to_code, dc_code_map, dc_title_map, store_fallbacks = load_store_and_dc_chat_mappings()
    print(f"📋 Đã tải {len(dc_code_map)} Chat ID DC và {len(st_to_code)} mapping Siêu thị.")

    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_now = datetime.now(vn_tz)
    vn_today_date = vn_now.date()
    today_str = vn_now.strftime('%d.%m')
    date_iso = vn_now.strftime('%Y-%m-%d')

    # Xác định ngày đối soát (target_date)
    target_start_date = None
    if target_date and str(target_date).strip() and str(target_date).strip().upper() != 'ALL':
        try:
            target_end_date = datetime.strptime(str(target_date).strip(), '%Y-%m-%d').date()
            target_start_date = target_end_date - timedelta(days=2)
            date_filter_msg = f"Từ {target_start_date.strftime('%d/%m/%Y')} đến hết {target_end_date.strftime('%d/%m/%Y')}"
        except Exception:
            target_end_date = vn_today_date
            date_filter_msg = f"Toàn bộ phiếu Cần Hậu Kiểm đến hết hôm nay ({vn_today_date.strftime('%d/%m/%Y')})"
    else:
        # Mặc định quét TOÀN BỘ phiếu đang treo trong tab "Cần hậu kiểm" trên WMS đến hiện tại
        target_end_date = vn_today_date
        date_filter_msg = f"Toàn bộ phiếu Cần Hậu Kiểm trên WMS đến hiện tại ({vn_today_date.strftime('%d/%m/%Y')})"

    print(f"⏰ Thời điểm chạy (VN): {vn_now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🎯 Lọc phiếu HẬU KIỂM: {date_filter_msg}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
        SELECT branch_id, branch_name 
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard 
        WHERE branch_name IS NOT NULL AND branch_name != ''
        GROUP BY branch_id, branch_name
        """)
        id_to_name = {bid: bname for bid, bname in cur.fetchall() if bname}

        # QUERY CHUẨN 100% VỚI TAB "CẦN HẬU KIỂM" TRÊN WMS:
        # Lọc các phiếu Hậu kiểm kho khô FGA chưa quét xong (double_checked_status = 1) và đang trong trạng thái xử lý (status = 3 hoặc 5)
        sql = f"""
        SELECT 
            t.double_check_code,
            t.code,
            t.from_branch_id,
            t.to_branch_id,
            t.received_date,
            t.transfer_date,
            t.created_at,
            t.double_checked_status,
            t.status
        FROM __cdc_kfm_kf_inventories_kf_transfer_items t
        WHERE t.from_branch_id IN {FGA_BRANCH_IDS}
          AND t.double_check_code IS NOT NULL AND t.double_check_code != ''
          AND t.status IN (3, 5)
          AND t.double_checked_status = 1
        ORDER BY t.created_at DESC
        """
        cur.execute(sql)
        tickets = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ [LỖI KẾT NỐI DATABASE]: {e}")
        return


    # Lọc theo ngày trong cửa sổ đối soát chuẩn WMS
    pending_hk = []
    for hk_code, pt_code, from_id, to_id, rcv_str, tdate_str, cat, dc_stt, stt in tickets:
        # Mốc ngày đối soát ưu tiên theo received_date (khớp thời gian tạo phiếu HK trên WMS)
        eval_date = None
        if rcv_str:
            try:
                rcv_utc = datetime.fromisoformat(rcv_str.replace('Z', '+00:00'))
                eval_date = rcv_utc.astimezone(vn_tz).date()
            except Exception:
                pass
        if not eval_date and tdate_str:
            try:
                td_utc = datetime.fromisoformat(tdate_str.replace('Z', '+00:00'))
                eval_date = td_utc.astimezone(vn_tz).date()
            except Exception:
                pass
        if not eval_date and cat:
            eval_date = pytz.UTC.localize(cat).astimezone(vn_tz).date()

        if eval_date and (target_start_date is None or eval_date >= target_start_date) and eval_date <= target_end_date:
            st_name = id_to_name.get(to_id, f"ST_{to_id}")
            
            # Tra mã ST
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

            pending_hk.append({
                'hk_code': hk_code,
                'pt_code': pt_code,
                'from_branch_id': from_id,
                'st_name': st_name,
                'st_code': st_code,
                'to_id': to_id,
                'transfer_date': eval_date,
                'transfer_date_str': eval_date.strftime('%d/%m/%Y'),
                'transfer_date_short': eval_date.strftime('%d.%m')
            })

    # Lọc theo danh sách Siêu thị / Phiếu yêu cầu nếu có truyền vào
    if stores and str(stores).strip() and str(stores).strip().upper() != 'ALL':
        raw_list = [s.strip() for s in re.split(r'[,;\n\r\t]+', str(stores)) if s.strip()]
        target_set = set(s.upper() for s in raw_list)
        filtered_pending = []
        for p in pending_hk:
            p_code = (p.get('st_code') or '').upper()
            p_name = (p.get('st_name') or '').upper()
            p_hk = (p.get('hk_code') or '').upper()
            p_pt = (p.get('pt_code') or '').upper()
            
            matched = False
            p_addr = p_name.split('-')[-1].strip() if '-' in p_name else p_name
            for t in target_set:
                t_addr = t.split('-')[-1].strip() if '-' in t else t
                if (t in [p_code, p_hk, p_pt] or 
                    t in p_name or p_name in t or 
                    (len(t_addr) > 5 and (t_addr in p_name or t_addr in p_addr or p_addr in t_addr))):
                    matched = True
                    break
            if matched:
                filtered_pending.append(p)
        print(f"🎯 Đã lọc theo danh sách yêu cầu ({stores}): Giữ lại {len(filtered_pending)}/{len(pending_hk)} phiếu.")
        pending_hk = filtered_pending

    print(f"📊 Tìm thấy ĐÚNG {len(pending_hk)} phiếu HẬU KIỂM KHO KHÔ cần xử lý.")
    if len(pending_hk) == 0:
        print("✅ Tuyệt vời! Không có phiếu Hậu Kiểm Kho Khô nào bị tồn đọng (hoặc không khớp bộ lọc).")
        return

    # Gom nhóm theo Siêu thị
    grouped = {}
    for p in pending_hk:
        grouped.setdefault(p['st_name'], []).append(p)

    print(f"🏪 Tổng số Siêu thị có phiếu hậu kiểm treo: {len(grouped)}")

    # Khởi động Telegram client
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("⚠️ Session Telegram chưa được xác thực. Vui lòng chạy Dang_Nhap_Telegram.py trước!")
        await client.disconnect()
        return

    sent_today = load_sent_stores('hau_kiem_kho_kho', date_iso)

    success_count = 0
    fail_count = 0

    headers = ["Mã Hậu Kiểm", "Phiếu chuyển gốc", "Ngày chuyển", "Nơi chuyển", "Nơi nhận", "Trạng thái"]

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
                # Trích xuất phần địa chỉ trong ngoặc đơn của tên nhóm Telegram
                m_sub = re.search(r'\((.*?)\)', t)
                if m_sub:
                    sub_kw = m_sub.group(1).strip()
                    if len(sub_kw) > 4 and sub_kw in addr_clean:
                        chat_id_raw = cid
                        break

        # Fallback tới cấu hình ST (nhóm DC hoặc nhóm ABA Đông Mát/Thịt Cá của ST đó)
        if not chat_id_raw and st_code in store_fallbacks:
            sinfo = store_fallbacks[st_code]
            if sinfo.get('chat_id_dc'):
                chat_id_raw = sinfo['chat_id_dc']
            elif sinfo.get('chat_id_dm'):
                chat_id_raw = sinfo['chat_id_dm']

        if not chat_id_raw:
            print(f"⚠️ [LOẠI BỎ - KHÔNG CÓ GROUP DC] Siêu thị: {st_name} (Mã: {st_code or 'N/A'}) - Bỏ qua vì không có nhóm DC.")
            fail_count += 1
            continue

        try:
            chat_id = int(str(chat_id_raw).strip())
        except Exception:
            fail_count += 1
            continue

        if not force and str(chat_id) in sent_today:
            print(f"⏩ [ĐÃ GỬI TRƯỚC ĐÓ] Bỏ qua ST: {st_name} ({chat_id}) - Dùng --force nếu muốn gửi lại.")
            continue

        # Sắp xếp phiếu của ST theo ngày chuyển tăng dần (cũ nhất lên đầu)
        group.sort(key=lambda x: x['transfer_date'])
        oldest_d = group[0]['transfer_date_short']
        newest_d = group[-1]['transfer_date_short']
        total_p = len(group)

        # Xây dựng cú pháp Caption chuẩn theo yêu cầu:
        if total_p == 1:
            ticket_clause = f"còn 1 phiếu hậu kiểm kho khô chưa nhận ngày {oldest_d}."
        else:
            if oldest_d == newest_d:
                ticket_clause = f"còn {total_p} phiếu hậu kiểm kho khô chưa nhận ngày {oldest_d}."
            else:
                ticket_clause = f"còn {total_p} phiếu hậu kiểm kho khô chưa nhận từ ngày {oldest_d} đến {newest_d}."

        if dry_run:
            print(f"🔍 [DRY-RUN] Sẽ gửi đến {st_name} (Mã: {st_code}, CID: {chat_id}): {total_p} phiếu [{ticket_clause}]")
            continue

        tag_text = await get_tags_for_group(client, chat_id)
        caption = f"**PHIẾU HẬU KIỂM KHO KHÔ**\n{today_str}\n⚠️ Siêu thị {ticket_clause}\nSiêu thị kiểm tra HOÀN THÀNH phiếu HẬU KIỂM KHO KHÔ gấp nhé team\n{tag_text}"

        # Tạo ảnh bảng Gradient Pastel
        rows = []
        for item in group:
            from_name = FGA_BRANCHES.get(item.get('from_branch_id'), 'FGA10101 _ Bình Thắng _ Lưu Hàng')
            rows.append([
                item['hk_code'],
                item['pt_code'],
                item['transfer_date_str'],
                from_name,
                item['st_name'],
                "Cần hậu kiểm"
            ])

        img_path = os.path.join(CURRENT_DIR, f"temp_hk_khokho_{abs(chat_id)}.png")
        try:
            render_pastel_gradient_table(headers, rows, img_path)
            
            sent_ok = False
            # 1. Thử gửi qua Telegram Bot API
            try:
                with open(img_path, 'rb') as f:
                    resp = requests.post(
                        URL_SEND_PHOTO,
                        data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                        files={'photo': f},
                        timeout=25
                    )
                res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})
                
                # Xử lý Supergroup migration
                if resp.status_code == 400 and res_json.get('parameters', {}).get('migrate_to_chat_id'):
                    new_cid = res_json['parameters']['migrate_to_chat_id']
                    print(f"🔄 [CHUYỂN SUPERGROUP] ST {st_name} đổi sang Chat ID: {new_cid}. Đang gửi lại ngay...", flush=True)
                    chat_id = new_cid
                    with open(img_path, 'rb') as f_mig:
                        resp = requests.post(
                            URL_SEND_PHOTO,
                            data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                            files={'photo': f_mig},
                            timeout=25
                        )
                    res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})
                
                # Xử lý lỗi Markdown parse entities
                if resp.status_code == 400 and "can't parse entities" in res_json.get('description', '').lower():
                    print(f"⚠️ [MARKDOWN ERROR] Thử gửi lại dạng Plain Text cho ST {st_name}...", flush=True)
                    plain_caption = caption.replace('**', '').replace('__', '')
                    with open(img_path, 'rb') as f_plain:
                        resp = requests.post(
                            URL_SEND_PHOTO,
                            data={'chat_id': chat_id, 'caption': plain_caption},
                            files={'photo': f_plain},
                            timeout=25
                        )
                    res_json = resp.json() if resp.status_code == 200 else (resp.json() if resp.text.startswith('{') else {})

                if resp.status_code == 200 and res_json.get('ok'):
                    sent_ok = True
                else:
                    err_desc = res_json.get('description', f'HTTP {resp.status_code}')
                    print(f"⚠️ [BOT TELEGRAM BÁO LỖI] ST: {st_name} ({chat_id}): {err_desc}. Đang chuyển sang Telethon User Client...", flush=True)
            except Exception as ex_bot:
                print(f"⚠️ [LỖI KẾT NỐI BOT] {st_name}: {ex_bot}. Đang chuyển sang Telethon User Client...", flush=True)

            # 2. Dự phòng: Gửi qua Telethon User Client nếu Bot API thất bại
            if not sent_ok:
                try:
                    await client.send_file(int(chat_id), img_path, caption=caption)
                    sent_ok = True
                    print(f"✅ [GỬI THÀNH CÔNG QUA USER CLIENT] ST: {st_name} ({chat_id})", flush=True)
                except Exception as ex_user:
                    try:
                        plain_caption = caption.replace('**', '').replace('__', '')
                        await client.send_file(int(chat_id), img_path, caption=plain_caption)
                        sent_ok = True
                        print(f"✅ [GỬI THÀNH CÔNG QUA USER CLIENT (PLAIN TEXT)] ST: {st_name} ({chat_id})", flush=True)
                    except Exception as ex_user2:
                        print(f"❌ [LỖI USER CLIENT] ST: {st_name} ({chat_id}): {ex_user2}", flush=True)

            if os.path.exists(img_path):
                os.remove(img_path)

            if sent_ok:
                record_sent_store('hau_kiem_kho_kho', date_iso, str(chat_id))
                print(f"🚀 [ĐÃ GỬI THÀNH CÔNG] ST: {st_name} ({chat_id}) - {total_p} phiếu")
                success_count += 1
            else:
                fail_count += 1

            await asyncio.sleep(1.5)
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
    parser.add_argument('--target-date', type=str, default=None, help='Ngày đối soát (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Chạy thử không gửi tin')
    parser.add_argument('--stores', type=str, default=None, help='Danh sách mã ST hoặc tên ST cần spam (cách nhau bởi dấu phẩy)')
    parser.add_argument('--force', '--resend', action='store_true', help='Bỏ qua kiểm tra lịch sử đã gửi hôm nay, gửi lại toàn bộ')
    args = parser.parse_args()
    asyncio.run(run_spam_hau_kiem_kho_kho(target_date=args.target_date, dry_run=args.dry_run, stores=args.stores, force=args.force))

