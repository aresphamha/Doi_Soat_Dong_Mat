# Script khôi phục toàn bộ mã nguồn về BẢN 2 (BACKUP_BAN_2)
import os
import shutil

backup_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_dir = os.path.dirname(backup_dir)
root_dir = os.path.dirname(dashboard_dir)

items = [
    'generate_web_report.py',
    'dashboard_template.html',
    'app.py',
    'Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html',
    'Cap_Nhat_Bao_Cao_Web.bat',
    'Chay_Dashboard_Dong_Mat.bat',
    'requirements.txt',
    'daily_records.js',
    'analytics',
    'config',
    'data',
    'exports',
    'reconciliation',
    'ui',
    'daily_details'
]

print("=" * 60)
print("BẮT ĐẦU KHÔI PHỤC VỀ BACKUP BẢN 2...")
print("=" * 60)

# 1. Khôi phục vào DONG_MAT_DASHBOARD
for item in items:
    s_path = os.path.join(backup_dir, item)
    d_path = os.path.join(dashboard_dir, item)
    if not os.path.exists(s_path):
        continue
    if os.path.isdir(s_path):
        if os.path.exists(d_path):
            shutil.rmtree(d_path)
        shutil.copytree(s_path, d_path)
        print(f' -> [DASHBOARD] Khôi phục thư mục: {item}')
    elif os.path.isfile(s_path):
        shutil.copy2(s_path, d_path)
        print(f' -> [DASHBOARD] Khôi phục file: {item}')

# 2. Đồng bộ các file hiển thị / chạy ra thư mục gốc (Root)
root_sync_items = [
    'Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html',
    'daily_records.js',
    'daily_details',
    'Cap_Nhat_Bao_Cao_Web.bat'
]

for item in root_sync_items:
    s_path = os.path.join(backup_dir, item)
    d_path = os.path.join(root_dir, item)
    if not os.path.exists(s_path):
        continue
    if os.path.isdir(s_path):
        if os.path.exists(d_path):
            shutil.rmtree(d_path)
        shutil.copytree(s_path, d_path)
        print(f' -> [ROOT] Đồng bộ thư mục: {item}')
    elif os.path.isfile(s_path):
        shutil.copy2(s_path, d_path)
        print(f' -> [ROOT] Đồng bộ file: {item}')

print("=" * 60)
print("✅ ĐÃ KHÔI PHỤC THÀNH CÔNG TOÀN BỘ CODE & DỮ LIỆU VỀ BẢN 2!")
print("=" * 60)
