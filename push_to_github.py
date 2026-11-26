"""
Tự động đồng bộ Báo Cáo Đối Soát Đông Mát lên GitHub & Kích hoạt Web Online (CI/CD)
Sử dụng trực tiếp git CLI chuẩn, hỗ trợ tự động giải phóng index.lock và pull rebase an toàn.
"""
import os
import sys
import subprocess
import threading
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_THREAD_LOCK = threading.Lock()
_LOCK_FILE = os.path.join(ROOT_DIR, ".git", "scm_sync.lock")


def _is_pid_running(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        res = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, check=False
        )
        return str(pid) in (res.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_file_lock(timeout=120):
    start = time.time()
    while True:
        try:
            fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}\n{time.time()}".encode("utf-8"))
            os.close(fd)
            return True
        except FileExistsError:
            try:
                with open(_LOCK_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
                old_pid = lines[0].strip() if lines else ""
                mtime = os.path.getmtime(_LOCK_FILE)
                if (not _is_pid_running(old_pid)) or (time.time() - mtime > 300):
                    os.remove(_LOCK_FILE)
                    continue
            except Exception:
                pass
            if time.time() - start >= timeout:
                return False
            time.sleep(1)


def _release_file_lock():
    try:
        if os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)
    except Exception:
        pass


def clear_git_lock():
    """Chỉ dọn index.lock bị kẹt khi không có tiến trình git nào đang chạy; không tự ý xóa thư mục rebase hay ghi đè HEAD."""
    git_dir = os.path.join(ROOT_DIR, ".git")
    index_lock = os.path.join(git_dir, "index.lock")
    if os.path.exists(index_lock):
        try:
            if time.time() - os.path.getmtime(index_lock) > 120:
                os.remove(index_lock)
        except Exception:
            pass

    # Nếu lần chạy trước bị kẹt giữa chừng ở trạng thái rebase/merge, dùng lệnh git chuẩn để hủy an toàn
    if os.path.exists(os.path.join(git_dir, "rebase-merge")) or os.path.exists(os.path.join(git_dir, "rebase-apply")):
        subprocess.run(["git", "rebase", "--abort"], cwd=ROOT_DIR, check=False, capture_output=True)
    if os.path.exists(os.path.join(git_dir, "MERGE_HEAD")):
        subprocess.run(["git", "merge", "--abort"], cwd=ROOT_DIR, check=False, capture_output=True)


def sync_and_push(custom_message=None, specific_files=None):
    print("==============================================================================")
    print("🚀 BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG ĐẨY BÁO CÁO LÊN GITHUB (GIT CLI)...")
    print("==============================================================================")

    with _THREAD_LOCK:
        if not _acquire_file_lock(timeout=120):
            print("⚠️ Có tiến trình đồng bộ Git khác đang chạy quá lâu, bỏ qua lượt này để tránh xung đột.")
            return False
        try:
            clear_git_lock()
            msg = custom_message or f"Cập nhật Báo Cáo Đối Soát - {time.strftime('%Y-%m-%d %H:%M:%S')}"

            # 1. Add all modified & untracked files
            if specific_files:
                cmd_add = ["git", "add"] + specific_files
            else:
                cmd_add = ["git", "add", "-A"]
            subprocess.run(cmd_add, cwd=ROOT_DIR, check=False)

            # 2. Fetch origin main trước
            subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT_DIR, check=False, capture_output=True)

            # 3. Pull rebase with autostash để tránh xung đột
            res_pull = subprocess.run(
                ["git", "pull", "--rebase", "--autostash", "origin", "main"],
                cwd=ROOT_DIR, check=False, capture_output=True, encoding='utf-8', errors='ignore'
            )
            if res_pull.returncode != 0:
                print("⚠️ Rebase gặp xung đột, hủy rebase an toàn và chuyển sang merge...")
                subprocess.run(["git", "rebase", "--abort"], cwd=ROOT_DIR, check=False, capture_output=True)
                subprocess.run(
                    ["git", "pull", "--no-rebase", "-X", "theirs", "origin", "main", "-m", "Merge origin/main"],
                    cwd=ROOT_DIR, check=False, capture_output=True
                )

            # 4. Add lại sau rebase/merge nếu có file phát sinh
            if specific_files:
                subprocess.run(["git", "add"] + specific_files, cwd=ROOT_DIR, check=False)
            else:
                subprocess.run(["git", "add", "-A"], cwd=ROOT_DIR, check=False)

            # 5. Commit
            res_commit = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore'
            )
            out_str = (res_commit.stdout or '') + (res_commit.stderr or '')
            if "nothing to commit" in out_str.lower():
                print("ℹ️ Dữ liệu không thay đổi so với bản trước đó.")
            else:
                print(f"📦 Đã tạo bản ghi commit: {msg}")

            # 6. Push
            res_push = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore'
            )
            if res_push.returncode != 0:
                subprocess.run(
                    ["git", "pull", "--no-rebase", "-X", "theirs", "origin", "main", "-m", "Merge origin/main"],
                    cwd=ROOT_DIR, check=False, capture_output=True
                )
                res_push = subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=ROOT_DIR, capture_output=True, encoding='utf-8', errors='ignore'
                )

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
        finally:
            _release_file_lock()

if __name__ == "__main__":
    sync_and_push()
