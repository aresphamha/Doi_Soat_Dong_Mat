# Script khôi phục toàn bộ mã nguồn về BẢN 1
import os
import shutil

backup_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(backup_dir)

items = ['generate_web_report.py', 'Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html', 'data', 'analytics']

for item in items:
    s_path = os.path.join(backup_dir, item)
    d_path = os.path.join(root_dir, item)
    if os.path.isdir(s_path):
        if os.path.exists(d_path):
            shutil.rmtree(d_path)
        shutil.copytree(s_path, d_path)
        print(f'Restored folder: {item}')
    elif os.path.isfile(s_path):
        shutil.copy2(s_path, d_path)
        print(f'Restored file: {item}')

print('✅ ĐÃ KHÔI PHỤC THÀNH CÔNG VỀ BẢN 1!')
