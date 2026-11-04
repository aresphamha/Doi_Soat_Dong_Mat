# -*- coding: utf-8 -*-
"""
Hệ thống truy vấn và đồng bộ 3 danh mục Phiếu Treo SCM từ CDC Database:
1. DS Phiếu Chuyển: trạng thái 'ĐANG CHUYỂN' (status = 3)
2. DS YC Xử Lý Phiếu Chuyển: trạng thái 'MỚI' (status = 1) và 'ĐANG XỬ LÝ' (status = 3)
3. DS Phiếu Hậu Kiểm: trạng thái 'CẦN HẬU KIỂM' (double_checked_status = 1)

Xuất dữ liệu sang file daily_details/pending_tickets.js phục vụ Tab 7 trên Web Dashboard.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
import pymysql

vn_tz = timezone(timedelta(hours=7))

# Mapping nhóm ngành hàng theo mã kho / tên kho
WAREHOUSE_CATEGORIES = {
    # Kho Khô
    '6aabb0a2f426e20007f80123': 'Kho Khô (FGA)',
    '6aabb0d73c46470007f935ce': 'Kho Khô (FGA)',
    '6aa77de130fded00073d4521': 'Kho Khô (Vệ Tinh)',
    '6234219eb35d1d00073793ab': 'Kho Khô (Seedlog)',
    '62342407b35d1d0007379692': 'Kho Khô (Seedlog KT)',
    '6ab13e28361da10007bc829f': 'Kho Khô (Long Biên)',
    
    # Rau Củ
    '6aabb3f3f426e20007f81559': 'Rau Củ (FEA)',
    '5fdc170ebd89c10006f15b7c': 'Rau Củ (KRC Cũ)',
    '6aabb45fd18e9d00073200a4': 'Rau Củ (Bánh Tươi)',
    '6a3e383fe20b440007640326': 'Rau Củ (Bánh Tươi Cũ)',
    
    # Thịt Cá
    '6aabb4d0e493030007272a3f': 'Thịt Cá (MFA)',
    '6a34ed56f23028000774139f': 'Thịt Cá (SCF/MF01)',
    '6acda3bafe8e0c0007012c06': 'Thịt Cá (Onelife)',
    
    # Đông Mát
    '6aa6a1eedf3d880007871f3f': 'Đông Mát (CLA/Mát)',
    '6a34ee2aebb48c000760d803': 'Đông Mát (Chill SCF)',
    '6aa77de130fded00073d4521': 'Đông Mát (FZA/Đông)',
    '6a34ec8d77173000073e64e2': 'Đông Mát (Frozen SCF)',
}

def detect_category(branch_id, branch_name):
    bid = str(branch_id or '').strip()
    if bid in WAREHOUSE_CATEGORIES:
        return WAREHOUSE_CATEGORIES[bid]
    bname = str(branch_name or '').upper()
    if any(k in bname for k in ['FGA', 'SEEDLOG', 'KHÔ', 'DRY']):
        return 'Kho Khô'
    if any(k in bname for k in ['RAU', 'FEA', 'KRC', 'BÁNH TƯƠI']):
        return 'Rau Củ'
    if any(k in bname for k in ['THỊT', 'CÁ', 'MFA', 'MEAT', 'FISH']):
        return 'Thịt Cá'
    if any(k in bname for k in ['CLA', 'FZA', 'CHILL', 'FROZEN', 'ĐÔNG', 'MÁT', 'LẠNH']):
        return 'Đông Mát'
    return 'Khác'

def get_db_connection():
    return pymysql.connect(
        host='103.140.248.250',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='TnAM0WEsv4kmasw878wt',
        database='kfm_scm',
        connect_timeout=15,
        read_timeout=60
    )

def fetch_and_build_pending_tickets():
    start_t = time.time()
    print("⏳ [Pending Tickets] Đang kết nối CDC Database 103.140.248.250:9030...")
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Branch names mapping
    cur.execute("""
    SELECT branch_id, branch_name 
    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard 
    WHERE branch_name IS NOT NULL AND branch_name != ''
    GROUP BY branch_id, branch_name
    """)
    branch_names = dict(cur.fetchall())

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stores_json_path = os.path.join(root_dir, 'CONFIG_DATA_STORES.json')
    if os.path.exists(stores_json_path):
        try:
            with open(stores_json_path, 'r', encoding='utf-8') as f:
                for s in json.load(f):
                    sid, sname = s.get('id', ''), s.get('name', '')
                    if sid and sname:
                        branch_names[sid] = sname
        except Exception:
            pass

    HEX_DC_MAPPING = {
        '6aa6a22bdf3d880007872063': 'CLA40104 _ Sóng Thần _ Chờ Đối Soát',
        '6aabb14ef426e20007f805da': 'FGA10104 _ Bình Thắng _ Chờ Đối Soát',
        '6aabb403055d2e0007eb9ded': 'FEA20104 _ Bình Thắng _ Chờ Đối Soát',
        '6aabb4e6e493030007272a95': 'MFA30104 _ Sóng Thần _ Chờ Đối Soát',
        '6aa77e599d7b1b00070121f5': 'CLB40104 _ Long Biên _ Chờ Đối Soát',
        '6aa77de130fded00073d4521': 'CLB40102 _ Long Biên _ Quá Cảnh',
        '6a34ed8d6607ba000703e235': 'MeatFish - Miền Đông - SCF - Quá Cảnh',
        '6aa6a1eedf3d880007871f3f': 'CLA40102 _ Sóng Thần _ Quá Cảnh',
        '6aabb0a2f426e20007f80123': 'FGA10101 _ Bình Thắng _ Lưu Hàng',
        '6a4f0127f163350007c29221': 'KFM_HCM_TDU - BS08 Vinhomes Grand Park'
    }
    for hid, hname in HEX_DC_MAPPING.items():
        branch_names[hid] = hname

    def get_name(bid):
        if not bid: return '---'
        bstr = str(bid).strip()
        return branch_names.get(bstr, bstr)

    def format_dt(dt_val):
        if not dt_val: return '---'
        try:
            if isinstance(dt_val, datetime):
                return dt_val.strftime('%d/%m/%Y %H:%M')
            dt_str = str(dt_val).replace('Z', '+00:00')
            dt_obj = datetime.fromisoformat(dt_str)
            if dt_obj.tzinfo:
                dt_vn = dt_obj.astimezone(vn_tz)
            else:
                dt_vn = dt_obj + timedelta(hours=7)
            return dt_vn.strftime('%d/%m/%Y %H:%M')
        except Exception:
            return str(dt_val)[:16]

    # 2. DS Phiếu Chuyển: 'ĐANG CHUYỂN' (status = 3)
    print("📦 [Pending Tickets] Truy vấn DS Phiếu Chuyển (status = 3)...")
    cur.execute("""
    SELECT 
        code,
        from_branch_id,
        to_branch_id,
        transfer_date,
        created_at,
        total_sku,
        sku,
        total_transfer_quantity,
        total_received_quantity,
        status,
        double_check_code
    FROM __cdc_kfm_kf_inventories_kf_transfer_items
    WHERE status = 3 AND (created_at >= '2026-10-01' OR transfer_date >= '2026-10-01')
    ORDER BY created_at DESC
    """)
    pt_list = []
    for r in cur.fetchall():
        code, from_id, to_id, t_date, c_at, tot_sku, sku, tot_qty, rcv_qty, stt, hk_code = r
        from_name = get_name(from_id)
        to_name = get_name(to_id)
        cat = detect_category(from_id, from_name)
        sku_val = int(tot_sku) if tot_sku is not None and tot_sku > 0 else (int(sku) if sku else 0)
        qty_val = round(float(tot_qty), 2) if tot_qty is not None else 0.0
        pt_list.append({
            'code': str(code or ''),
            'from_id': str(from_id or ''),
            'from_name': from_name,
            'to_id': str(to_id or ''),
            'to_name': to_name,
            'category': cat,
            'transfer_date': format_dt(t_date or c_at),
            'created_at': format_dt(c_at),
            'sku': sku_val,
            'quantity': qty_val,
            'status_code': 3,
            'status_text': 'Đang chuyển',
            'hk_code': str(hk_code or '')
        })

    # 3. DS YC Xử Lý Phiếu Chuyển: 'MỚI' (status = 1) và 'ĐANG XỬ LÝ' (status = 3)
    print("📋 [Pending Tickets] Truy vấn DS YC Xử Lý Phiếu Chuyển (status IN (1, 3))...")
    cur.execute("""
    SELECT 
        code,
        status,
        total_sku_created,
        total_sku,
        total_created_quantity,
        total_confirm_quantity,
        from_pt_code,
        pt_transfer_date,
        pt_from_branch,
        handled_pt_code,
        from_branch,
        to_branch,
        created_at
    FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets
    WHERE status IN (1, 3)
      AND created_at >= '2026-10-01'
      AND NOT (status = 3 AND total_sku_created >= total_sku AND total_sku > 0)
    ORDER BY created_at DESC
    """)
    to_list = []
    for r in cur.fetchall():
        code, stt, sku_cr, tot_sku, qty_cr, qty_conf, from_pt, pt_tdate, pt_from_b, handled_pt, from_b, to_b, c_at = r
        stt_int = int(stt) if stt is not None else 1
        stt_text = 'Mới' if stt_int == 1 else ('Đang xử lý' if stt_int == 3 else 'Khác')
        pt_from_name = get_name(pt_from_b)
        from_name = get_name(from_b)
        to_name = get_name(to_b)
        cat = detect_category(pt_from_b, pt_from_name)
        if cat == 'Khác':
            cat = detect_category(from_b, from_name)
        sku_val = int(tot_sku) if tot_sku else (int(sku_cr) if sku_cr else 0)
        qty_cr_val = round(float(qty_cr), 2) if qty_cr is not None else 0.0
        qty_conf_val = round(float(qty_conf), 2) if qty_conf is not None else 0.0
        to_list.append({
            'code': str(code or ''),
            'status_code': stt_int,
            'status_text': stt_text,
            'category': cat,
            'sku': sku_val,
            'qty_created': qty_cr_val,
            'qty_confirmed': qty_conf_val,
            'from_pt_code': str(from_pt or ''),
            'pt_transfer_date': format_dt(pt_tdate),
            'pt_from_name': pt_from_name,
            'handled_pt_code': str(handled_pt or ''),
            'from_name': from_name,
            'to_name': to_name,
            'created_at': format_dt(c_at)
        })

    # 4. DS Phiếu Hậu Kiểm: 'CẦN HẬU KIỂM' (double_checked_status = 1)
    print("⚖️ [Pending Tickets] Truy vấn DS Phiếu Hậu Kiểm (double_checked_status = 1)...")
    cur.execute("""
    SELECT 
        double_check_code,
        code,
        from_branch_id,
        to_branch_id,
        received_date,
        transfer_date,
        created_at,
        total_sku,
        sku,
        total_transfer_quantity,
        total_received_quantity,
        status,
        double_checked_status
    FROM __cdc_kfm_kf_inventories_kf_transfer_items
    WHERE double_checked_status = 1 AND double_check_code IS NOT NULL AND double_check_code != ''
    ORDER BY created_at DESC
    """)
    hk_list = []
    for r in cur.fetchall():
        hk_code, pt_code, from_id, to_id, rcv_date, t_date, c_at, tot_sku, sku, tot_qty, rcv_qty, stt, dc_stt = r
        from_name = get_name(from_id)
        to_name = get_name(to_id)
        cat = detect_category(from_id, from_name)
        sku_val = int(tot_sku) if tot_sku else (int(sku) if sku else 0)
        qty_val = round(float(tot_qty), 2) if tot_qty is not None else 0.0
        rcv_qty_val = round(float(rcv_qty), 2) if rcv_qty is not None else 0.0
        hk_list.append({
            'double_check_code': str(hk_code or ''),
            'pt_code': str(pt_code or ''),
            'from_id': str(from_id or ''),
            'from_name': from_name,
            'to_id': str(to_id or ''),
            'to_name': to_name,
            'category': cat,
            'received_date': format_dt(rcv_date or c_at),
            'created_at': format_dt(c_at),
            'sku': sku_val,
            'transfer_qty': qty_val,
            'received_qty': rcv_qty_val,
            'status_code': int(stt) if stt is not None else 0,
            'status_text': 'Đã nhận' if stt == 5 else ('Đang chuyển' if stt == 3 else f'Trạng thái {stt}'),
            'hk_status_text': 'Cần hậu kiểm'
        })

    conn.close()

    vn_now_str = datetime.now(vn_tz).strftime('%d/%m/%Y %H:%M:%S')
    data_res = {
        'updated_at': vn_now_str,
        'summary': {
            'pt_dang_chuyen_count': len(pt_list),
            'to_yeu_cau_count': len(to_list),
            'to_moi_count': sum(1 for x in to_list if x['status_code'] == 1),
            'to_dang_xu_ly_count': sum(1 for x in to_list if x['status_code'] == 3),
            'hk_can_hau_kiem_count': len(hk_list),
            'total_pending': len(pt_list) + len(to_list) + len(hk_list)
        },
        'pt_dang_chuyen': pt_list,
        'to_yeu_cau': to_list,
        'hk_can_hau_kiem': hk_list
    }

    # Xuất ra pending_tickets.js
    json_str = json.dumps(data_res, ensure_ascii=False, separators=(',', ':'))
    js_content = f"window.PENDING_TICKETS_DATA = {json_str};\n"

    target_files = [
        os.path.join(root_dir, 'daily_details', 'pending_tickets.js'),
        os.path.join(root_dir, 'DONG_MAT_DASHBOARD', 'daily_details', 'pending_tickets.js'),
        r"C:\Users\Thu Ha\Doi_Soat_Dong_Mat\daily_details\pending_tickets.js"
    ]

    for p in target_files:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(js_content)
        except Exception:
            pass

    elapsed = time.time() - start_t
    print(f"🎉 [Pending Tickets] Đã đồng bộ thành công {data_res['summary']['total_pending']} phiếu treo ({elapsed:.2f}s):")
    print(f"   - 🚚 DS Phiếu Chuyển (Đang chuyển): {len(pt_list)} phiếu")
    print(f"   - 📋 DS YC Xử Lý (Mới & Đang xử lý): {len(to_list)} yêu cầu (Mới: {data_res['summary']['to_moi_count']}, ĐXL: {data_res['summary']['to_dang_xu_ly_count']})")
    print(f"   - ⚖️ DS Phiếu Hậu Kiểm (Cần hậu kiểm): {len(hk_list)} phiếu")
    return data_res

if __name__ == '__main__':
    fetch_and_build_pending_tickets()
