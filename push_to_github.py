"""
Tự động đồng bộ Báo Cáo Đối Soát Đông Mát lên GitHub & Kích hoạt Web Online (CI/CD)
Sử dụng trực tiếp git CLI chuẩn, hỗ trợ tự động giải phóng index.lock và pull rebase an toàn.
"""
import os
import sys
import shutil
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
    
    # 1. Xóa toàn bộ thư mục kẹt rebase nếu có
    for dir_name in ["rebase-merge", "rebase-apply"]:
        dp = os.path.join(git_dir, dir_name)
        if os.path.exists(dp):
            try:
                shutil.rmtree(dp, ignore_errors=True)
            except Exception:
                pass

    # 2. Xóa các file lock và ref tạm
    for f_name in ["index.lock", "ORIG_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "MERGE_HEAD"]:
        fp = os.path.join(git_dir, f_name)
        if os.path.exists(fp):
            try:
                if f_name == "ORIG_HEAD":
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        if not f.read().strip():
                            os.remove(fp)
                else:
                    os.remove(fp)
            except Exception:
                pass

    # 3. Đảm bảo HEAD luôn trỏ về refs/heads/main (tránh detached HEAD)
    head_file = os.path.join(git_dir, "HEAD")
    try:
        if os.path.exists(head_file):
            with open(head_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
            if not content.startswith("ref:"):
                with open(head_file, 'w', encoding='utf-8') as f:
                    f.write("ref: refs/heads/main\n")
    except Exception:
        pass

    # 4. Kiểm tra ref origin/main nếu bị rỗng do sập nguồn đột ngột
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

        # 2. Fetch origin main trước
        clear_git_lock()
        subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT_DIR, check=False, capture_output=True)

        # 3. Pull rebase with autostash để tránh xung đột
        clear_git_lock()
        res_pull = subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=ROOT_DIR, check=False, capture_output=True, encoding='utf-8', errors='ignore')
        if res_pull.returncode != 0:
            print("⚠️ Rebase gặp xung đột, chuyển sang chế độ tự động giải phóng và merge...")
            clear_git_lock()
            subprocess.run(["git", "rebase", "--abort"], cwd=ROOT_DIR, check=False, capture_output=True)
            clear_git_lock()
            subprocess.run(["git", "pull", "--no-rebase", "-X", "theirs", "origin", "main", "-m", "Merge origin/main"], cwd=ROOT_DIR, check=False, capture_output=True)

        # 4. Add lại sau rebase/merge nếu có file phát sinh
        clear_git_lock()
        if specific_files:
            subprocess.run(["git", "add"] + specific_files, cwd=ROOT_DIR, check=False)
        else:
            subprocess.run(["git", "add", "-A"], cwd=ROOT_DIR, check=False)

        # 5. Commit
        clear_git_lock()
        res_commit = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore')
        out_str = (res_commit.stdout or '') + (res_commit.stderr or '')
        if "nothing to commit" in out_str.lower():
            print("ℹ️ Dữ liệu không thay đổi so với bản trước đó.")
        else:
            print(f"📦 Đã tạo bản ghi commit: {msg}")

        # 6. Push
        clear_git_lock()
        res_push = subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore')
        if res_push.returncode != 0:
            # Nếu push bị reject, pull merge lần cuối rồi push lại
            clear_git_lock()
            subprocess.run(["git", "pull", "--no-rebase", "-X", "theirs", "origin", "main", "-m", "Merge origin/main"], cwd=ROOT_DIR, check=False, capture_output=True)
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
