# Script khôi phục toàn bộ mã nguồn về BẢN 3 (BACKUP_BAN_3)
# Thời điểm sao lưu: 2026-09-17 23:00:00
import os
import shutil

backup_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_dir = os.path.dirname(backup_dir)
root_dir = os.path.dirname(dashboard_dir)

print("=" * 70)
print("BẮT ĐẦU KHÔI PHỤC VỀ BACKUP BẢN 3...")
print("=" * 70)

# Khôi phục file vào DONG_MAT_DASHBOARD
dash_files = [
    ('dashboard_template.html', 'dashboard_template.html'),
    ('generate_web_report.py', 'generate_web_report.py'),
    ('sync_telegram_groups.py', 'sync_telegram_groups.py'),
    ('telegram_chat_server.py', 'telegram_chat_server.py'),
    ('app.py', 'app.py'),
    ('dashboard_Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html', 'Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html'),
]

for src_name, dst_name in dash_files:
    s = os.path.join(backup_dir, src_name)
    d = os.path.join(dashboard_dir, dst_name)
    if os.path.exists(s):
        shutil.copy2(s, d)
        print(f" -> [DASHBOARD FILE] Khôi phục: {dst_name}")

# Khôi phục folder vào DONG_MAT_DASHBOARD
dash_dirs = ['analytics', 'config', 'data', 'exports', 'reconciliation', 'ui']
for d_name in dash_dirs:
    s = os.path.join(backup_dir, d_name)
    d = os.path.join(dashboard_dir, d_name)
    if os.path.exists(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
        print(f" -> [DASHBOARD DIR] Khôi phục: {d_name}/")

# Khôi phục file ra Root
root_files = [
    ('index.html', 'index.html'),
    ('Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html', 'Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html'),
    ('local_runner_service.py', 'local_runner_service.py'),
    ('push_to_github.py', 'push_to_github.py'),
    ('Cap_Nhat_Bao_Cao_Web.bat', 'Cap_Nhat_Bao_Cao_Web.bat'),
    ('Cap_Nhat_Telegram_Realtime.bat', 'Cap_Nhat_Telegram_Realtime.bat'),
    ('Chay_Telegram_Chat_Realtime.bat', 'Chay_Telegram_Chat_Realtime.bat'),
    ('requirements.txt', 'requirements.txt'),
    ('daily_records.js', 'daily_records.js'),
]

for src_name, dst_name in root_files:
    s = os.path.join(backup_dir, src_name)
    d = os.path.join(root_dir, dst_name)
    if os.path.exists(s):
        shutil.copy2(s, d)
        print(f" -> [ROOT FILE] Khôi phục: {dst_name}")

# Khôi phục workflow github
wf_s = os.path.join(backup_dir, 'run_spam_tools.yml')
wf_d = os.path.join(root_dir, '.github', 'workflows', 'run_spam_tools.yml')
if os.path.exists(wf_s):
    os.makedirs(os.path.dirname(wf_d), exist_ok=True)
    shutil.copy2(wf_s, wf_d)
    print(" -> [WORKFLOW] Khôi phục: .github/workflows/run_spam_tools.yml")

# Khôi phục folder ra Root
root_dirs = ['daily_details', 'SPAM_PHIEU_CHUYEN', 'TOOLS_DOI_SOAT']
for d_name in root_dirs:
    s = os.path.join(backup_dir, d_name)
    d = os.path.join(root_dir, d_name)
    if os.path.exists(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
        print(f" -> [ROOT DIR] Khôi phục: {d_name}/")

print("=" * 70)
print("HOÀN TẤT KHÔI PHỤC VỀ BACKUP BẢN 3!")
print("=" * 70)
