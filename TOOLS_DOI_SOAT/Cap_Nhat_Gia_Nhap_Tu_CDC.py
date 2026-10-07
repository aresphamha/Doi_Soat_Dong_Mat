# -*- coding: utf-8 -*-
"""
TỰ ĐỘNG ĐỒNG BỘ TOÀN BỘ BẢNG GIÁ NHẬP TỪ CDC STARROCKS LÊN WEB DASHBOARD & GITHUB
- Kết nối trực tiếp CDC: 103.140.248.250:9030
- User: kfm_scm_tho_nguyen / Pass: TnAM0WEsv4kmasw878wt
- Loại trừ 4 danh mục không bán: CCDC, Vận hành, Hàng không bán, IT Test
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
    "IT TEST"
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

    # Fallback product name
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
    print("🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ GIÁ NHẬP SẢN PHẨM TRỰC TIẾP TỪ CDC STARROCKS...")
    print("=" * 80)

    conn = pymysql.connect(
        host='103.140.248.250', port=9030,
        user='kfm_scm_tho_nguyen', password='TnAM0WEsv4kmasw878wt',
        database='kfm_scm',
        connect_timeout=15
    )

    print("📥 1. Kéo bảng giá nhập krc_cdc_cost_price & krc_sku_prices_temp...")
    df_prices1 = pd.read_sql("SELECT barcode, ten_sp, dvt, cate_2, cate_3, gia_cost, updated_at FROM krc_cdc_cost_price", conn)
    df_prices2 = pd.read_sql("SELECT ma_hang as barcode, don_gia as gia_cost FROM krc_sku_prices_temp", conn)

    print("📥 2. Kéo danh mục ngành hàng krc_dashboard_slg_cate_mapping...")
    df_cats = pd.read_sql("SELECT barcode, cate_1, cate_2, ten_hang FROM krc_dashboard_slg_cate_mapping", conn)

    print("📥 3. Kéo danh sách mã hàng từ transfer ticket lines & L3 line items...")
    sql_lines = """
    SELECT barcode, name, unit_name, variant_id
    FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines
    WHERE barcode IS NOT NULL AND barcode != '' AND name IS NOT NULL AND name != ''
    GROUP BY barcode, name, unit_name, variant_id
    """
    df_lines = pd.read_sql(sql_lines, conn)

    sql_l3 = """
    SELECT barcode, name, unit__name as unit_name, variant_id
    FROM __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items
    WHERE barcode IS NOT NULL AND barcode != '' AND name IS NOT NULL AND name != ''
    GROUP BY barcode, name, unit__name, variant_id
    """
    df_l3 = pd.read_sql(sql_l3, conn)

    conn.close()
    print("🔌 Ngắt kết nối CDC.")

    # Price Map
    price_map = {}
    for _, r in df_prices2.iterrows():
        bc = str(r['barcode']).strip()
        p = float(r['gia_cost'] or 0)
        if bc and p > 0: price_map[bc] = p

    for _, r in df_prices1.iterrows():
        bc = str(r['barcode']).strip()
        p = float(r['gia_cost'] or 0)
        if bc and p > 0: price_map[bc] = p

    # Cat Map
    cat_map = {}
    for _, r in df_cats.iterrows():
        bc = str(r['barcode']).strip()
        c1 = str(r.get('cate_1', ''))
        c2 = str(r.get('cate_2', ''))
        tn = str(r.get('ten_hang', ''))
        if bc: cat_map[bc] = (c1, c2, tn)

    master_products = {}

    def add_product(bc, nm, ut, vid, c1='', c2=''):
        bc = str(bc).strip()
        nm = str(nm).strip()
        if not bc or not nm or bc.lower() in ['nan', 'none', '']: return

        if bc in cat_map:
            c1_lk, c2_lk, tn_lk = cat_map[bc]
            c1 = c1 or c1_lk
            c2 = c2 or c2_lk

        norm_cat = get_norm_cat(c1, c2, nm)
        if not norm_cat: return # Excluded

        pr = price_map.get(bc, 0.0)
        if bc not in master_products:
            master_products[bc] = {
                'barcode': bc,
                'sku': bc,
                'name': nm,
                'unit': ut or 'Khay / Gói',
                'variant_id': vid or f"VC_{bc[-8:] if len(bc) >= 8 else bc}",
                'category_lv1': norm_cat,
                'category_full': f"{norm_cat} > {c2 if c2 else norm_cat}",
                'cost_price': pr
            }
        else:
            if pr > master_products[bc]['cost_price']:
                master_products[bc]['cost_price'] = pr
            if len(nm) > len(master_products[bc]['name']):
                master_products[bc]['name'] = nm
            if ut and master_products[bc]['unit'] in ['Khay / Gói', '']:
                master_products[bc]['unit'] = ut

    # Add from lines
    for _, r in df_lines.iterrows():
        add_product(r['barcode'], r['name'], r.get('unit_name'), r.get('variant_id'))

    # Add from L3
    for _, r in df_l3.iterrows():
        add_product(r['barcode'], r['name'], r.get('unit_name'), r.get('variant_id'))

    # Add from cost price table
    for _, r in df_prices1.iterrows():
        add_product(r['barcode'], r.get('ten_sp'), r.get('dvt'), '', r.get('cate_2'), r.get('cate_3'))

    # Add from category map table
    for _, r in df_cats.iterrows():
        add_product(r['barcode'], r.get('ten_hang'), 'Khay / Gói', '', r.get('cate_1'), r.get('cate_2'))

    print(f"\n✅ Đã trích xuất & làm sạch thành công: {len(master_products):,} SKU thương mại từ CDC!")

    # Format list
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    final_list = []
    stt = 1

    for bc, p in sorted(master_products.items(), key=lambda x: x[1]['name']):
        cost = p['cost_price']
        if cost <= 0:
            cost = 38000.0 if p['category_lv1'] == '1.FRESH FOOD' else 45000.0

        retail = round(cost * 1.25)
        margin = round(((retail - cost) / retail) * 100) if retail > 0 else 20

        final_list.append({
            "stt": stt,
            "internal_code": bc,
            "variant_code": p['variant_id'] if p['variant_id'] else f"VC_{bc[-8:] if len(bc) >= 8 else bc}",
            "barcode": bc,
            "sku": bc,
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

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.PRODUCT_PRICES_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    print(f"\n💾 Đã lưu JavaScript Master Data: {OUTPUT_JS}")

    df_out = pd.DataFrame(final_list)
    df_out.to_excel(OUTPUT_EXCEL, index=False)
    print(f"📊 Đã lưu Excel Master Data: {OUTPUT_EXCEL}")

    print("\n🚀 Đang tự động đẩy lên GitHub Pages...")
    push_script = os.path.join(ROOT_DIR, "push_to_github.py")
    if os.path.exists(push_script):
        os.system(f'python "{push_script}"')

if __name__ == '__main__':
    main()
