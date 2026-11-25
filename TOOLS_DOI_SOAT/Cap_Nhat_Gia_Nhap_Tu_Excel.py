# -*- coding: utf-8 -*-
"""
TOOL ĐỒNG BỘ TOÀN BỘ BẢNG GIÁ NHẬP TỪ FILE EXCEL (HADA & CDC) LÊN WEB ONLINE
Tự động lọc bỏ 4 danh mục không kinh doanh:
- 1. HÀNG HÓA DỊCH VỤ VẬN HÀNH
- 1. CÔNG CỤ DỤNG CỤ
- 1. zHÀNG KHÔNG BÁN
- zIT TEST
"""
import os
import sys
import glob
import json
from datetime import datetime
import pandas as pd

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

def find_best_input_file():
    patterns = [
        os.path.join(ROOT_DIR, "*hada*.xlsx"),
        os.path.join(ROOT_DIR, "*product*.xlsx"),
        os.path.join(ROOT_DIR, "*gia_nhap*.xlsx"),
        os.path.join(ROOT_DIR, "*danh_sach_san_pham*.xlsx"),
        os.path.join(ROOT_DIR, "*.xlsx")
    ]
    for p in patterns:
        files = glob.glob(p)
        for f in files:
            fname = os.path.basename(f)
            if fname.startswith("~$") or fname.startswith("Bang_Gia_Nhap_San_Pham_CDC_Hada"):
                continue
            return f
    return None

def normalize_category(cat_str, item_name=""):
    cat = str(cat_str or "").strip().upper()
    name = str(item_name or "").strip().upper()
    
    # Check exclusions first
    for exc in EXCLUDED_CATEGORIES:
        if exc in cat or exc in name:
            return None

    if "FRESH" in cat or "THỊT" in cat or "CÁ" in cat or "RAU" in cat or "TRÁI CÂY" in cat or "FRUIT" in cat or "MEAT" in cat or "POULTRY" in cat:
        return "1.FRESH FOOD"
    if "CHILLED" in cat or "FROZEN" in cat or "ĐÔNG" in cat or "MÁT" in cat:
        return "1.CHILLED AND FROZEN"
    if "DAIRY" in cat or "ICE" in cat or "SỮA" in cat or "KEM" in cat or "PHÔ MAI" in cat or "CHEESE" in cat:
        return "1.DAIRY AND ICE CREAM"
    if "BAKERY" in cat or "DELICA" in cat or "BÁNH" in cat or "CHẾ BIẾN" in cat:
        return "1.BAKERY AND DELICA"
    if "FMCG" in cat or "SNACK" in cat or "GIA VỊ" in cat or "NƯỚC" in cat:
        return "1.FMCG"

    # Fallback based on product name keywords
    if any(k in name for k in ["THỊT", "CÁ", "TÔM", "MỰC", "GÀ", "BÒ", "HEO", "RAU", "CẢI", "TÁO", "NHO", "CAM", "LÊ", "CHERRY", "KIWI", "DÂU", "NẤM", "BƯỞI"]):
        return "1.FRESH FOOD"
    if any(k in name for k in ["PHÔ MAI", "SỮA", "KEM", "BUTTER", "CHEESE", "YOGURT"]):
        return "1.DAIRY AND ICE CREAM"
    if any(k in name for k in ["XÚC XÍCH", "KHOAI TÂY ĐÔNG LẠNH", "PIZZA", "DIMSUM", "ĐẬU HŨ", "CHẢ LỤA"]):
        return "1.CHILLED AND FROZEN"
    if any(k in name for k in ["BÁNH MÌ", "BÁNH LỌC", "BÁNH NẬM", "SANDWICH", "DELICA"]):
        return "1.BAKERY AND DELICA"

    return "1.FMCG"

def process_excel(file_path):
    print(f"📂 Đang đọc dữ liệu từ file: {file_path}")
    excel_data = pd.read_excel(file_path, sheet_name=None)
    
    extracted_items = []
    seen_skus = set()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    for sheet_name, df in excel_data.items():
        if df.empty or len(df.columns) < 2:
            continue
        print(f"  🔍 Xử lý sheet: [{sheet_name}] ({len(df)} dòng)...")
        
        # Normalize column names
        cols = {str(c).strip().lower(): c for c in df.columns}
        
        # Identify columns
        col_sku = next((cols[c] for c in cols if any(k in c for k in ['mã hàng', 'mã nội bộ', 'sku', 'mã sp', 'mã sản phẩm'])), None)
        col_name = next((cols[c] for c in cols if any(k in c for k in ['tên hàng', 'tên sản phẩm', 'tên sp', 'product_name'])), None)
        col_price = next((cols[c] for c in cols if any(k in c for k in ['giá nhập', 'đơn giá', 'giá vốn', 'cost', 'max of giá', 'giá gần nhất'])), None)
        col_unit = next((cols[c] for c in cols if any(k in c for k in ['đvt', 'đơn vị tính', 'unit'])), None)
        col_cat = next((cols[c] for c in cols if any(k in c for k in ['danh mục', 'ngành hàng', 'nhóm hàng', 'category'])), None)
        col_barcode = next((cols[c] for c in cols if any(k in c for k in ['barcode', 'mã vạch'])), None)
        col_brand = next((cols[c] for c in cols if any(k in c for k in ['thương hiệu', 'brand', 'nhãn hiệu'])), None)
        col_variant = next((cols[c] for c in cols if any(k in c for k in ['mã phiên bản', 'variant'])), None)

        if not col_sku or not col_name:
            # Maybe column A is SKU and column B is Name
            if len(df.columns) >= 2:
                col_sku = df.columns[0]
                col_name = df.columns[1]
                if len(df.columns) >= 3 and not col_unit: col_unit = df.columns[2]
            else:
                continue

        for _, row in df.iterrows():
            sku_val = str(row.get(col_sku, '')).strip()
            name_val = str(row.get(col_name, '')).strip()
            
            if not sku_val or sku_val.lower() in ['nan', 'none', 'mã hàng', 'sku', 'mã nội bộ', '']:
                continue
            if not name_val or name_val.lower() in ['nan', 'none', '']:
                continue
                
            # Filter category
            cat_raw = str(row.get(col_cat, '') if col_cat else '')
            cat_norm = normalize_category(cat_raw, name_val)
            if not cat_norm:
                # Excluded category
                continue

            # Clean price
            price_val = 0
            if col_price and pd.notna(row.get(col_price)):
                try:
                    p_str = str(row[col_price]).replace(',', '').replace(' ', '').replace('VNĐ', '').replace('đ', '').strip()
                    price_val = float(p_str)
                except Exception:
                    price_val = 0

            # Default price fallback if missing based on name
            if price_val <= 0:
                price_val = 45000 # Placeholder standard cost

            unit_val = str(row.get(col_unit, '') if col_unit and pd.notna(row.get(col_unit)) else 'Khay / Hộp').strip()
            barcode_val = str(row.get(col_barcode, '') if col_barcode and pd.notna(row.get(col_barcode)) else sku_val).strip()
            brand_val = str(row.get(col_brand, '') if col_brand and pd.notna(row.get(col_brand)) else 'Kingfoodmart').strip()
            variant_val = str(row.get(col_variant, '') if col_variant and pd.notna(row.get(col_variant)) else ('VC_' + sku_val[-8:])).strip()

            sku_clean = sku_val.split('.')[0] if sku_val.endswith('.0') else sku_val

            if sku_clean in seen_skus:
                continue
            seen_skus.add(sku_clean)

            retail_price = round(price_val * 1.25)
            margin_pct = round(((retail_price - price_val) / retail_price) * 100) if retail_price > 0 else 20

            extracted_items.append({
                "stt": len(extracted_items) + 1,
                "internal_code": sku_clean,
                "variant_code": variant_val,
                "barcode": barcode_val if barcode_val != 'nan' else sku_clean,
                "sku": sku_clean,
                "product_name": name_val,
                "category_lv1": cat_norm,
                "category_full": f"{cat_norm} > {name_val.split('-')[0].strip() if '-' in name_val else cat_norm}",
                "unit": unit_val if unit_val != 'nan' else 'Gói',
                "cost_price": price_val,
                "retail_price": retail_price,
                "margin_pct": margin_pct,
                "brand": brand_val if brand_val != 'nan' else 'Kingfoodmart',
                "status": "KDF - Kinh doanh",
                "last_updated": now_str,
                "source": "Kingfood Hada & CDC Master Data"
            })

    print(f"\n✅ Đã trích xuất & làm sạch thành công: {len(extracted_items):,} SKU thương mại hợp lệ!")
    
    # Categories breakdown
    cat_counts = {}
    for item in extracted_items:
        c = item['category_lv1']
        cat_counts[c] = cat_counts.get(c, 0) + 1

    for c, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  📦 {c}: {cnt:,} SKU")

    # Save to product_prices.js
    payload = {
        "sync_date": now_str,
        "total_sku": len(extracted_items),
        "categories_summary": cat_counts,
        "excluded_categories": [
            "1. HÀNG HÓA DỊCH VỤ VẬN HÀNH",
            "1. CÔNG CỤ DỤNG CỤ",
            "1. zHÀNG KHÔNG BÁN",
            "zIT TEST"
        ],
        "products": extracted_items
    }

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.PRODUCT_PRICES_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    print(f"💾 Đã lưu JavaScript Master Data: {OUTPUT_JS}")

    # Save to Excel
    df_out = pd.DataFrame(extracted_items)
    df_out.to_excel(OUTPUT_EXCEL, index=False)
    print(f"📊 Đã lưu Excel Master Data: {OUTPUT_EXCEL}")

    return len(extracted_items)

def main():
    print("=" * 80)
    print("🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ GIÁ NHẬP SẢN PHẨM TỪ FILE EXCEL HADA / CDC...")
    print("=" * 80)

    input_file = sys.argv[1] if len(sys.argv) > 1 else find_best_input_file()
    if not input_file or not os.path.exists(input_file):
        print("❌ Không tìm thấy file Excel nào trong thư mục để nạp giá.")
        print("👉 Vui lòng kéo thả file Excel từ Kingfood Hada / CDC vào thư mục dự án và chạy lại tool!")
        return

    count = process_excel(input_file)
    if count > 0:
        print("\n🚀 Đang tự động đẩy lên GitHub Pages...")
        push_script = os.path.join(ROOT_DIR, "push_to_github.py")
        if os.path.exists(push_script):
            os.system(f'python "{push_script}"')

if __name__ == '__main__':
    main()
