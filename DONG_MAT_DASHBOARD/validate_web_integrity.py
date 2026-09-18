import os
import sys
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

def validate_html_file(file_path):
    print(f"\n🔍 [KIỂM TRA CHẤT LƯỢNG] Đang kiểm tra: {os.path.basename(file_path)}...")
    if not os.path.exists(file_path):
        print(f"❌ [LỖI] Không tìm thấy file: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    errors = []
    warnings = []

    # 1. Kiểm tra kích thước file
    size_kb = len(content.encode('utf-8')) / 1024
    print(f"   ℹ️ Dung lượng: {size_kb:.1f} KB")

    # 2. Kiểm tra cân bằng thẻ HTML
    tags_to_check = ['div', 'script', 'main', 'header', 'aside', 'section']
    for tag in tags_to_check:
        open_tags = len(re.findall(rf'<{tag}(?:[\s>])', content, re.IGNORECASE))
        close_tags = len(re.findall(rf'</{tag}>', content, re.IGNORECASE))
        if open_tags != close_tags:
            errors.append(f"Mất cân bằng thẻ <{tag}>: {open_tags} mở vs {close_tags} đóng (Lệch: {open_tags - close_tags})")
        else:
            print(f"   ✅ Thẻ <{tag}> cân bằng chuẩn xác: {open_tags} mở / {close_tags} đóng")

    # 3. Kiểm tra các phần tử cốt lõi (Core DOM Elements)
    critical_ids = [
        'kpi-val-total',
        'kpi-qty-total',
        'bar-seg-done',
        'big-panel-1',
        'big-panel-2',
        'big-panel-3',
        'big-panel-4',
        'big-panel-5',
        'btn-big-tab-1',
        'btn-big-tab-2',
        'btn-big-tab-3',
        'btn-big-tab-4',
        'btn-big-tab-5',
        'storePriorityTable',
        'masterTable',
        'valTable',
        'qtyTable',
        'cloudRunnerBadge',
        'chatDrawer',
        'chatReplyInput',
        'chatSendBtn',
        'runnerEngineSelect'
    ]

    for cid in critical_ids:
        if f'id="{cid}"' not in content and f"id='{cid}'" not in content:
            errors.append(f"Thiếu phần tử DOM cốt lõi: id='{cid}'")

    # 4. Kiểm tra vách ngăn lỗi Error Boundary
    if "console.error(\"[ERROR BOUNDARY]" in content or "[ERROR BOUNDARY]" in content:
        print("   ✅ Đã kích hoạt Vách ngăn lỗi (Error Boundary) bảo vệ từng Tab.")
    else:
        warnings.append("Chưa tìm thấy tiền tố [ERROR BOUNDARY] trong code xử lý.")

    # 5. Kiểm tra liên kết dữ liệu tách rời
    if 'src="daily_details/data_bundles.js"' in content:
        print("   ✅ Đã tích hợp nạp dữ liệu tách rời: daily_details/data_bundles.js")
    elif 'const BUNDLES = {' in content and len(content) > 2000000:
        warnings.append("Dữ liệu BUNDLES vẫn đang nhúng nguyên khối trong file (>2MB).")

    # Báo cáo tổng kết
    if errors:
        print(f"\n❌ PHÁT HIỆN {len(errors)} LỖI NGHIÊM TRỌNG:")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        if warnings:
            print(f"\n⚠️ CẢNH BÁO ({len(warnings)}):")
            for w in warnings:
                print(f"   - {w}")
        print("🎉 [THÀNH CÔNG] File đạt 100% tiêu chuẩn toàn vẹn kiến trúc!")
        return True

if __name__ == "__main__":
    repo_dir = r"C:\Users\Thu Ha\Doi_Soat_Dong_Mat"
    target = os.path.join(repo_dir, "index.html")
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    ok = validate_html_file(target)
    sys.exit(0 if ok else 1)
