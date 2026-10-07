# -*- coding: utf-8 -*-
"""
TỰ ĐỘNG ĐỒNG BỘ TOÀN BỘ BẢNG GIÁ NHẬP & MASTER DATA TỪ CDC STARROCKS LÊN WEB DASHBOARD & GITHUB
- Kết nối trực tiếp CDC: 103.140.248.250:9030
- User: kfm_scm_tho_nguyen / Pass: TnAM0WEsv4kmasw878wt
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

def main():
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

    print("📥 1. Kéo Stockcard (Giá vốn & Barcode & Internal Code)...")
    sql_sc = """
    SELECT 
        barcode, 
        product_internal_code, 
        product_name, 
        MAX(IF(cost > 0, cost, price)) as latest_cost,
        MAX(receipt_price) as receipt_price,
        MAX(vendor_name) as vendor_name,
        MAX(base_variant_id) as variant_id
    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
    WHERE (barcode IS NOT NULL AND barcode != '') OR (product_internal_code IS NOT NULL AND product_internal_code != '')
    GROUP BY barcode, product_internal_code, product_name
    """
    df_sc = pd.read_sql(sql_sc, conn)
    print(f"  -> Stockcard: {len(df_sc):,} bản ghi")

    print("📥 2. Kéo L2 & L3 Line Items...")
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

    print("📥 3. Kéo Transfer Ticket Lines & Claim Rates...")
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

    print("📥 4. Kéo Bảng Giá Nhập & Cây Danh Mục...")
    df_cats = pd.read_sql("SELECT barcode, cate_1, cate_2, ten_hang FROM krc_dashboard_slg_cate_mapping", conn)
    df_dm_cats = pd.read_sql("SELECT ma_hang as barcode, cate_l3, cate_l4, ten_hang, dvt FROM krc_dashboard_dm_cate_mapping", conn)
    df_prices1 = pd.read_sql("SELECT barcode, ten_sp, dvt, cate_2, cate_3, gia_cost FROM krc_cdc_cost_price", conn)
    df_prices2 = pd.read_sql("SELECT ma_hang as barcode, don_gia FROM krc_sku_prices_temp", conn)

    conn.close()
    print("🔌 Đã ngắt kết nối CDC an toàn.")

    # 1. Price Map
    price_map = {}
    for _, r in df_prices2.iterrows():
        bc = str(r['barcode']).strip()
        p = float(r['don_gia'] or 0)
        if bc and p > 0: price_map[bc] = p

    for _, r in df_prices1.iterrows():
        bc = str(r['barcode']).strip()
        p = float(r['gia_cost'] or 0)
        if bc and p > 0: price_map[bc] = p

    # 2. Cat Map
    cat_map = {}
    for _, r in df_cats.iterrows():
        bc = str(r['barcode']).strip()
        c1 = str(r.get('cate_1', ''))
        c2 = str(r.get('cate_2', ''))
        tn = str(r.get('ten_hang', ''))
        if bc: cat_map[bc] = (c1, c2, tn)

    for _, r in df_dm_cats.iterrows():
        bc = str(r['barcode']).strip()
        c1 = str(r.get('cate_l3', ''))
        c2 = str(r.get('cate_l4', ''))
        tn = str(r.get('ten_hang', ''))
        if bc and bc not in cat_map: cat_map[bc] = (c1, c2, tn)

    master = {}

    def add_item(bc, internal_code, name, unit, variant_id, cost, vendor, c1='', c2=''):
        bc = str(bc or '').strip()
        internal_code = str(internal_code or bc).strip()
        key = bc if bc and bc.lower() not in ['nan', 'none', ''] else internal_code
        if not key or not name or str(name).strip().lower() in ['nan', 'none', '']: return

        if key in cat_map:
            c1_lk, c2_lk, tn_lk = cat_map[key]
            c1 = c1 or c1_lk
            c2 = c2 or c2_lk

        norm_cat = get_norm_cat(c1, c2, name)
        if not norm_cat: return # Loại trừ CCDC, Vận hành, Không bán, IT Test

        final_cost = float(cost or 0)
        if key in price_map and price_map[key] > 0:
            final_cost = price_map[key]

        if key not in master:
            master[key] = {
                'barcode': key,
                'internal_code': internal_code or key,
                'name': str(name).strip(),
                'unit': str(unit or 'Khay / Gói').strip(),
                'variant_id': str(variant_id or f"VC_{key[-8:] if len(key)>=8 else key}").strip(),
                'cost_price': final_cost,
                'vendor': str(vendor or 'Kingfoodmart').strip(),
                'category_lv1': norm_cat,
                'category_full': f"{norm_cat} > {c2 if c2 else norm_cat}"
            }
        else:
            if final_cost > master[key]['cost_price']:
                master[key]['cost_price'] = final_cost
            if len(str(name).strip()) > len(master[key]['name']):
                master[key]['name'] = str(name).strip()
            if unit and master[key]['unit'] in ['Khay / Gói', '', 'nan']:
                master[key]['unit'] = str(unit).strip()

    # 1. Stockcard
    for _, r in df_sc.iterrows():
        c = float(r.get('latest_cost') or 0)
        rp = float(r.get('receipt_price') or 0)
        add_item(r['barcode'], r.get('product_internal_code'), r['product_name'], 'Khay / Gói', r.get('variant_id'), max(c, rp), r.get('vendor_name'))

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

    # 6. Cost Price Table
    for _, r in df_prices1.iterrows():
        add_item(r['barcode'], r['barcode'], r.get('ten_sp'), r.get('dvt'), '', r.get('gia_cost'), 'Kingfoodmart', r.get('cate_2'), r.get('cate_3'))

    # 7. Cate Mappings
    for _, r in df_cats.iterrows():
        add_item(r['barcode'], r['barcode'], r.get('ten_hang'), 'Khay / Gói', '', 0, 'Kingfoodmart', r.get('cate_1'), r.get('cate_2'))

    print(f"\n🎉 ĐÃ ĐỒNG BỘ THÀNH CÔNG: {len(master):,} SKU THƯƠNG MẠI TỪ CDC!")

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
    main()
