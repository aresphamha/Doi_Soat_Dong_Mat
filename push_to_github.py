"""
Tự động đồng bộ Báo Cáo Đối Soát Đông Mát lên GitHub & Kích hoạt Web Online (CI/CD)
Sử dụng trực tiếp git CLI chuẩn, hỗ trợ tự động giải phóng index.lock và pull rebase an toàn.
"""
import os
import sys
import subprocess
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def clear_git_lock():
    git_dir = os.path.join(ROOT_DIR, ".git")
    for lock_name in ["index.lock", "ORIG_HEAD", "rebase-merge", "rebase-apply"]:
        target = os.path.join(git_dir, lock_name)
        if os.path.exists(target):
            try:
                if lock_name == "ORIG_HEAD":
                    with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                        if not f.read().strip():
                            os.remove(target)
                elif lock_name.endswith(".lock"):
                    os.remove(target)
            except Exception:
                pass
    # Kiểm tra ref origin/main nếu bị rỗng do sập nguồn đột ngột
    origin_main_ref = os.path.join(git_dir, "refs", "remotes", "origin", "main")
    if os.path.exists(origin_main_ref):
        try:
            with open(origin_main_ref, 'r', encoding='utf-8', errors='ignore') as f:
                if not f.read().strip():
                    os.remove(origin_main_ref)
        except Exception:
            pass

def sync_and_push(custom_message=None, specific_files=None):
    print("==============================================================================")
    print("🚀 BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG ĐẨY BÁO CÁO LÊN GITHUB (GIT CLI)...")
    print("==============================================================================")
    clear_git_lock()

    msg = custom_message or f"Cập nhật Báo Cáo Đối Soát - {time.strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        # 1. Add all modified & untracked files
        clear_git_lock()
        if specific_files:
            cmd_add = ["git", "add"] + specific_files
        else:
            cmd_add = ["git", "add", "-A"]
        subprocess.run(cmd_add, cwd=ROOT_DIR, check=False)

        # 2. Pull rebase with autostash để tránh xung đột
        clear_git_lock()
        subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=ROOT_DIR, check=False, capture_output=True, encoding='utf-8', errors='ignore')

        # 3. Add lại sau rebase nếu có file phát sinh
        clear_git_lock()
        subprocess.run(["git", "add", "-A"], cwd=ROOT_DIR, check=False)

        # 4. Commit
        clear_git_lock()
        res_commit = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore')
        out_str = (res_commit.stdout or '') + (res_commit.stderr or '')
        if "nothing to commit" in out_str.lower():
            print("ℹ️ Dữ liệu không thay đổi so với bản trước đó.")
        else:
            print(f"📦 Đã tạo bản ghi commit: {msg}")

        # 5. Pull rebase lần nữa nếu có commit mới từ remote
        clear_git_lock()
        subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=ROOT_DIR, check=False, capture_output=True, encoding='utf-8', errors='ignore')

        # 6. Push
        clear_git_lock()
        res_push = subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore')
        if res_push.returncode == 0:
            print("==============================================================================")
            print("✅ ĐÃ ĐẨY LÊN GITHUB & KÍCH HOẠT CI/CD THÀNH CÔNG 100%!")
            print("🌐 Link Web Báo Cáo Online: https://aresphamha.github.io/Doi_Soat_Dong_Mat/")
            print("==============================================================================")
            return True
        else:
            print(f"⚠️ Push gặp lỗi: {res_push.stderr}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi thực hiện git sync_and_push: {e}")
        return False

if __name__ == "__main__":
    sync_and_push()
