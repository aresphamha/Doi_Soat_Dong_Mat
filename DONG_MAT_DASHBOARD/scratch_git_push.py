# -*- coding: utf-8 -*-
import subprocess
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

git_exe = r"C:\ProgramData\PC\GitHubDesktop\app-3.5.5\resources\app\git\cmd\git.exe"
cwd = r"g:\My Drive\Đối soát SCM"

def run_git(args):
    cmd = [git_exe] + args
    print(f"👉 Chạy lệnh: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode

print("==============================================================================")
print("🚀 BẮT ĐẦU ĐẨY TOÀN BỘ TOOL & BÁO CÁO LÊN GITHUB VÀ WEB TRỰC TUYẾN...")
print("==============================================================================")

# 1. Git add all
run_git(["add", "-A"])

# 2. Git commit
commit_msg = "Tích hợp toàn bộ Tool Spam Phiếu Chuyển, cập nhật Tab 5 và đồng bộ Báo Cáo Đối Soát Online"
run_git(["commit", "-m", commit_msg])

# 3. Git pull with merge strategy
run_git(["pull", "--no-rebase", "-s", "recursive", "-X", "ours", "origin", "main"])

# 4. Git push
code = run_git(["push", "origin", "main"])

if code == 0:
    print("==============================================================================")
    print("✅ ĐÃ ĐẨY LÊN GITHUB & DEPLOY WEB ONLINE THÀNH CÔNG 100%!")
    print("🔗 GitHub Repo: https://github.com/aresphamha/Doi_Soat_Dong_Mat")
    print("🌐 Web Báo Cáo Trực Tuyến: https://aresphamha.github.io/Doi_Soat_Dong_Mat/")
    print("==============================================================================")
else:
    print("❌ Có lỗi khi push lên GitHub. Kiểm tra log phía trên.")
