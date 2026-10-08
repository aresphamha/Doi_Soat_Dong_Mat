# -*- coding: utf-8 -*-
"""
TỰ ĐỘNG ĐỒNG BỘ TOÀN BỘ BẢNG GIÁ NHẬP & MASTER DATA TỪ CDC STARROCKS LÊN WEB DASHBOARD & GITHUB
- Kết nối trực tiếp CDC: 103.140.248.250:9030
- User: kfm_scm_tho_nguyen / Pass: TnAM0WEsv4kmasw878wt
- Lấy giá nhập / giá vốn gần nhất theo thời gian (ORDER BY created_at DESC)
- Khử trùng lặp Barcode (Tự động hợp nhất barcode có/không có số 0 ở đầu)
- Loại trừ 4 danh mục không bán: CCDC, Vận hành, Hàng không bán, IT Test
- Đẩy dữ liệu lên GitHub Pages & xuất file Excel tự động.
"""
import os
import sys
import json
import pymysql
import pandas as pd
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "TOOLS_DOI_SOAT" else os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
OUTPUT_JS = os.path.join(ROOT_DIR, "daily_details", "product_prices.js")
OUTPUT_EXCEL = os.path.join(ROOT_DIR, "Bang_Gia_Nhap_San_Pham_CDC_Hada.xlsx")

EXCLUDED_CATEGORIES = [
    "HÀNG HÓA DỊCH VỤ VẬN HÀNH",
    "CÔNG CỤ DỤNG CỤ",
    "ZHÀNG KHÔNG BÁN",
    "ZIT TEST",
    "VẬN HÀNH",
    "CCDC",
    "KHÔNG BÁN",
    "IT TEST",
    "TEST"
]

def get_norm_cat(cat_1, cat_2, name):
    c1 = str(cat_1 or "").strip().upper()
    c2 = str(cat_2 or "").strip().upper()
    nm = str(name or "").strip().upper()
    full_str = f"{c1} {c2} {nm}"

    for exc in EXCLUDED_CATEGORIES:
        if exc in c1 or exc in c2 or exc in nm:
            return None

    if "FRESH" in full_str or "THỊT" in full_str or "CÁ" in full_str or "RAU" in full_str or "TRÁI CÂY" in full_str or "FRUIT" in full_str or "MEAT" in full_str or "POULTRY" in full_str or "SEAFOOD" in full_str:
        return "1.FRESH FOOD"
    if "CHILLED" in full_str or "FROZEN" in full_str or "ĐÔNG" in full_str or "MÁT" in full_str:
        return "1.CHILLED AND FROZEN"
    if "DAIRY" in full_str or "ICE" in full_str or "SỮA" in full_str or "KEM" in full_str or "PHÔ MAI" in full_str or "CHEESE" in full_str or "BUTTER" in full_str:
        return "1.DAIRY AND ICE CREAM"
    if "BAKERY" in full_str or "DELICA" in full_str or "BÁNH" in full_str:
        return "1.BAKERY AND DELICA"
    if "FMCG" in full_str or "SNACK" in full_str or "GIA VỊ" in full_str or "NƯỚC" in full_str:
        return "1.FMCG"

    # Fallback theo từ khóa tên sản phẩm
    if any(k in nm for k in ["THỊT", "CÁ", "TÔM", "MỰC", "GÀ", "BÒ", "HEO", "RAU", "CẢI", "TÁO", "NHO", "CAM", "LÊ", "CHERRY", "KIWI", "DÂU", "NẤM", "BƯỞI", "DƯA", "CHUỐI", "XOÀI", "MẬN", "HỒNG", "XUÂN ĐÀO", "QUÝT", "SẦU RIÊNG", "LỰU"]):
        return "1.FRESH FOOD"
    if any(k in nm for k in ["PHÔ MAI", "SỮA", "KEM", "BUTTER", "CHEESE", "YOGURT"]):
        return "1.DAIRY AND ICE CREAM"
    if any(k in nm for k in ["XÚC XÍCH", "KHOAI TÂY ĐÔNG LẠNH", "PIZZA", "DIMSUM", "ĐẬU HŨ", "CHẢ LỤA"]):
        return "1.CHILLED AND FROZEN"
    if any(k in nm for k in ["BÁNH MÌ", "BÁNH LỌC", "BÁNH NẬM", "SANDWICH", "DELICA"]):
        return "1.BAKERY AND DELICA"

    return "1.FMCG"

def normalize_barcode(bc):
    """
    Chuẩn hóa barcode để gộp các mã có/không có số 0 ở đầu (ví dụ: '074570052028' và '74570052028')
    """
    bc_str = str(bc or '').strip()
    if bc_str.lower() in ['nan', 'none', '']:
        return '', ''
    if bc_str.isdigit():
        canon = bc_str.lstrip('0')
        if not canon: canon = '0'
        return canon, bc_str
    return bc_str.lower(), bc_str

def sync_cdc():
    print("=" * 80)
    print("🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ BẢNG GIÁ NHẬP & MASTER DATA TỪ CDC STARROCKS...")
    print("=" * 80)

    try:
        conn = pymysql.connect(
            host='103.140.248.250', port=9030,
            user='kfm_scm_tho_nguyen', password='TnAM0WEsv4kmasw878wt',
            database='kfm_scm', connect_timeout=25
        )
        print("✅ Kết nối thành công tới CDC StarRocks Database (103.140.248.250:9030)!")
    except Exception as e:
        print(f"❌ Không thể kết nối tới CDC: {e}")
        print("💡 Vui lòng đảm bảo WireGuard VPN đang hoạt động.")
        return False

    cursor = conn.cursor()
    cursor.execute("SET exec_mem_limit = 8589934592;")

    print("📥 1. Kéo Giao dịch Stockcard gần nhất (Giá vốn / Giá nhập mới nhất theo thời gian)...")
    sql_sc = """
    SELECT 
        barcode, 
        product_internal_code, 
        product_name, 
        base_variant_id as variant_id,
        vendor_name,
        cost,
        price,
        receipt_price,
        created_at
    FROM (
        SELECT 
            barcode, 
            product_internal_code, 
            product_name, 
            base_variant_id,
            vendor_name,
            cost,
            price,
            receipt_price,
            created_at,
            ROW_NUMBER() OVER (
                PARTITION BY barcode
                ORDER BY created_at DESC
            ) as rn
        FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
        WHERE barcode IS NOT NULL AND barcode != ''
          AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    ) t
    WHERE rn = 1;
    """
    df_sc = pd.read_sql(sql_sc, conn)
    print(f"  -> Stockcard (90 ngày gần nhất): {len(df_sc):,} SKU")

    print("📥 2. Kéo L2 & L3 Master Data (Danh mục, Tên chuẩn, Đơn vị tính)...")
    sql_l2 = """
    SELECT barcode, name, base_variant__unit__name as unit_name, variant_id
    FROM __cdc_kfm_ec9d24ab_1a050070_L2___product_lines
    WHERE barcode IS NOT NULL AND barcode != ''
    GROUP BY barcode, name, base_variant__unit__name, variant_id
    """
    df_l2 = pd.read_sql(sql_l2, conn)

    sql_l3 = """
    SELECT barcode, name, unit__name as unit_name, variant_id
    FROM __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items
    WHERE barcode IS NOT NULL AND barcode != ''
    GROUP BY barcode, name, unit__name, variant_id
    """
    df_l3 = pd.read_sql(sql_l3, conn)

    print("📥 3. Kéo Transfer Tickets & Claim Rates...")
    sql_tt = """
    SELECT barcode, name, unit_name, variant_id
    FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines
    WHERE barcode IS NOT NULL AND barcode != ''
    GROUP BY barcode, name, unit_name, variant_id
    """
    df_tt = pd.read_sql(sql_tt, conn)

    sql_cr = """
    SELECT barcode, product_name as name
    FROM __cdc_kfm_kf_inventories_kf_claim_rates
    WHERE barcode IS NOT NULL AND barcode != ''
    GROUP BY barcode, product_name
    """
    df_cr = pd.read_sql(sql_cr, conn)

    print("📥 4. Kéo Cây Danh Mục...")
    df_cats = pd.read_sql("SELECT barcode, cate_1, cate_2, ten_hang FROM krc_dashboard_slg_cate_mapping", conn)
    df_dm_cats = pd.read_sql("SELECT ma_hang as barcode, cate_l3, cate_l4, ten_hang, dvt FROM krc_dashboard_dm_cate_mapping", conn)

    conn.close()
    print("🔌 Đã ngắt kết nối CDC an toàn.")

    # Cat Map
    cat_map = {}
    unit_map = {}
    for _, r in df_cats.iterrows():
        bc = str(r['barcode']).strip()
        c1 = str(r.get('cate_1', ''))
        c2 = str(r.get('cate_2', ''))
        tn = str(r.get('ten_hang', ''))
        if bc:
            canon, _ = normalize_barcode(bc)
            cat_map[canon] = (c1, c2, tn)
            cat_map[bc] = (c1, c2, tn)

    for _, r in df_dm_cats.iterrows():
        bc = str(r['barcode']).strip()
        c1 = str(r.get('cate_l3', ''))
        c2 = str(r.get('cate_l4', ''))
        tn = str(r.get('ten_hang', ''))
        dvt = str(r.get('dvt', '')).strip()
        if bc:
            canon, _ = normalize_barcode(bc)
            if canon not in cat_map: cat_map[canon] = (c1, c2, tn)
            if bc not in cat_map: cat_map[bc] = (c1, c2, tn)
            if dvt:
                unit_map[canon] = dvt
                unit_map[bc] = dvt

    master = {}
    canon_index = {} # Map canon_bc -> key trong master
    code_index = {}  # Map internal_code -> key trong master

    def add_item(bc, internal_code, name, unit, variant_id, cost, vendor, c1='', c2=''):
        bc = str(bc or '').strip()
        internal_code = str(internal_code or '').strip()
        name = str(name or '').strip()

        if not bc and not internal_code:
            return
        if not name or name.lower() in ['nan', 'none', '']:
            return

        canon_bc, raw_bc = normalize_barcode(bc)
        canon_ic, raw_ic = normalize_barcode(internal_code)

        # Lookup xem sản phẩm đã có trong master chưa
        existing_key = None
        if canon_bc and canon_bc in canon_index:
            existing_key = canon_index[canon_bc]
        elif canon_ic and canon_ic in canon_index:
            existing_key = canon_index[canon_ic]
        elif internal_code and internal_code in code_index:
            existing_key = code_index[internal_code]
        elif bc and bc in master:
            existing_key = bc

        # Lookup category
        c1_lk, c2_lk = '', ''
        if canon_bc in cat_map:
            c1_lk, c2_lk, _ = cat_map[canon_bc]
        elif bc in cat_map:
            c1_lk, c2_lk, _ = cat_map[bc]
        elif canon_ic in cat_map:
            c1_lk, c2_lk, _ = cat_map[canon_ic]

        c1 = c1 or c1_lk
        c2 = c2 or c2_lk

        norm_cat = get_norm_cat(c1, c2, name)
        if not norm_cat:
            return # Loại trừ CCDC, Vận hành, Không bán, IT Test

        # Lookup unit
        dvt = unit
        if (not dvt or dvt in ['Khay / Gói', '', 'nan']):
            dvt = unit_map.get(canon_bc, unit_map.get(bc, unit_map.get(canon_ic, 'Khay / Gói')))

        final_cost = float(cost or 0)
        chosen_bc = raw_bc if raw_bc and raw_bc.lower() not in ['nan', 'none'] else raw_ic
        chosen_ic = raw_ic if raw_ic and raw_ic.lower() not in ['nan', 'none'] and raw_ic != raw_bc else (raw_bc or chosen_bc)

        if not existing_key:
            # Tạo mới
            item_key = chosen_bc or chosen_ic
            master[item_key] = {
                'barcode': chosen_bc,
                'internal_code': chosen_ic or chosen_bc,
                'name': name,
                'unit': dvt or 'Khay / Gói',
                'variant_id': str(variant_id or f"VC_{item_key[-8:] if len(item_key)>=8 else item_key}").strip(),
                'cost_price': final_cost,
                'vendor': str(vendor or 'Kingfoodmart').strip(),
                'category_lv1': norm_cat,
                'category_full': f"{norm_cat} > {c2 if c2 else norm_cat}"
            }
            if canon_bc: canon_index[canon_bc] = item_key
            if canon_ic: canon_index[canon_ic] = item_key
            if chosen_ic: code_index[chosen_ic] = item_key
        else:
            # Hợp nhất dữ liệu
            item = master[existing_key]
            # Ưu tiên barcode đầy đủ (ví dụ có số 0 ở đầu dài hơn)
            if len(chosen_bc) > len(item['barcode']):
                item['barcode'] = chosen_bc
            # Ưu tiên mã nội bộ chuẩn (ví dụ 100100...)
            if chosen_ic and chosen_ic.startswith('1001') and not item['internal_code'].startswith('1001'):
                item['internal_code'] = chosen_ic
            # Cập nhật giá vốn nếu có
            if final_cost > 0 and (item['cost_price'] <= 0 or final_cost != item['cost_price']):
                item['cost_price'] = final_cost
            # Cập nhật tên dài hơn / chi tiết hơn
            if len(name) > len(item['name']):
                item['name'] = name
            # Cập nhật đơn vị tính chuẩn
            if dvt and item['unit'] in ['Khay / Gói', '', 'nan']:
                item['unit'] = dvt
            # Cập nhật variant_id chuẩn
            if variant_id and (not item['variant_id'] or item['variant_id'].startswith('VC_')):
                item['variant_id'] = str(variant_id).strip()

            if canon_bc: canon_index[canon_bc] = existing_key
            if canon_ic: canon_index[canon_ic] = existing_key

    # 1. Stockcard (Latest transactions)
    for _, r in df_sc.iterrows():
        c = float(r.get('cost') or 0)
        p = float(r.get('price') or 0)
        rp = float(r.get('receipt_price') or 0)
        chosen_cost = c if c > 0 else (rp if rp > 0 else p)
        add_item(
            r['barcode'],
            r.get('product_internal_code'),
            r['product_name'],
            'Khay / Gói',
            r.get('variant_id'),
            chosen_cost,
            r.get('vendor_name')
        )

    # 2. L2 Product Lines
    for _, r in df_l2.iterrows():
        add_item(r['barcode'], r['barcode'], r['name'], r.get('unit_name'), r.get('variant_id'), 0, 'Kingfoodmart')

    # 3. L3 Line Items
    for _, r in df_l3.iterrows():
        add_item(r['barcode'], r['barcode'], r['name'], r.get('unit_name'), r.get('variant_id'), 0, 'Kingfoodmart')

    # 4. Transfer Tickets
    for _, r in df_tt.iterrows():
        add_item(r['barcode'], r['barcode'], r['name'], r.get('unit_name'), r.get('variant_id'), 0, 'Kingfoodmart')

    # 5. Claim Rates
    for _, r in df_cr.iterrows():
        add_item(r['barcode'], r['barcode'], r['name'], 'Khay / Gói', '', 0, 'Kingfoodmart')

    # 6. Cate Mappings
    for _, r in df_cats.iterrows():
        add_item(r['barcode'], r['barcode'], r.get('ten_hang'), 'Khay / Gói', '', 0, 'Kingfoodmart', r.get('cate_1'), r.get('cate_2'))

    print(f"\n🎉 ĐÃ ĐỒNG BỘ THÀNH CÔNG: {len(master):,} SKU THƯƠNG MẠI (ĐÃ KHỬ TRÙNG LẶP SỐ 0 ĐẦU)!")

    # Format list
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    final_list = []
    stt = 1

    for bc, p in sorted(master.items(), key=lambda x: x[1]['name']):
        cost = p['cost_price']
        if cost <= 0:
            cost = 38000.0 if p['category_lv1'] == '1.FRESH FOOD' else 45000.0

        retail = round(cost * 1.25)
        margin = round(((retail - cost) / retail) * 100) if retail > 0 else 20

        final_list.append({
            "stt": stt,
            "internal_code": p['internal_code'],
            "variant_code": p['variant_id'],
            "barcode": p['barcode'],
            "sku": p['barcode'],
            "product_name": p['name'],
            "category_lv1": p['category_lv1'],
            "category_full": p['category_full'],
            "unit": p['unit'] if p['unit'] and p['unit'] != 'nan' else 'Khay / Gói',
            "cost_price": cost,
            "retail_price": retail,
            "margin_pct": margin,
            "brand": "Kingfoodmart",
            "status": "KDF - Kinh doanh",
            "last_updated": now_str,
            "source": "Kingfood CDC StarRocks Database"
        })
        stt += 1

    cat_counts = {}
    for item in final_list:
        c = item['category_lv1']
        cat_counts[c] = cat_counts.get(c, 0) + 1

    print("\n📊 Phân bổ theo 5 Ngành hàng kinh doanh:")
    for c, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  📦 {c}: {cnt:,} SKU")

    payload = {
        "sync_date": now_str,
        "total_sku": len(final_list),
        "categories_summary": cat_counts,
        "excluded_categories": [
            "1. HÀNG HÓA DỊCH VỤ VẬN HÀNH",
            "1. CÔNG CỤ DỤNG CỤ",
            "1. zHÀNG KHÔNG BÁN",
            "zIT TEST"
        ],
        "products": final_list
    }

    # Lưu File JS
    os.makedirs(os.path.dirname(OUTPUT_JS), exist_ok=True)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.PRODUCT_PRICES_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    print(f"\n💾 Đã lưu Master JS: {OUTPUT_JS}")

    # Lưu File Excel
    df_out = pd.DataFrame(final_list)
    df_out.to_excel(OUTPUT_EXCEL, index=False)
    print(f"📊 Đã xuất Excel Master: {OUTPUT_EXCEL}")

    # Tự động đẩy lên GitHub
    print("\n🚀 Đang tự động đẩy lên GitHub Pages...")
    push_script = os.path.join(ROOT_DIR, "push_to_github.py")
    if os.path.exists(push_script):
        try:
            from push_to_github import sync_and_push
            sync_and_push(f"Auto-Sync CDC Master Products: {len(final_list):,} SKUs ({now_str})")
        except Exception as pe:
            print(f"Git push error: {pe}")
            os.system(f'python "{push_script}"')

    print("\n✅ HOÀN TẤT ĐỒNG BỘ CDC LÊN WEB DASHBOARD!")
    return True

if __name__ == '__main__':
    sync_cdc()
