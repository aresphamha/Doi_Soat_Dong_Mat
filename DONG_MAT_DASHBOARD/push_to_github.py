"""
Tự động đồng bộ Báo Cáo Đối Soát Đông Mát lên GitHub & Kích hoạt Web Online (CI/CD)
"""
import os
import sys
import json
from datetime import datetime
import dulwich.porcelain as porcelain
from dulwich.repo import Repo

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) if os.path.basename(os.path.dirname(__file__)) == "DONG_MAT_DASHBOARD" else os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(ROOT_DIR, ".github_config.json")

def load_or_init_config():
    default_config = {
        "github_user": "aresphamha",
        "repo_name": "Doi_Soat_Dong_Mat",
        "branch": "main",
        "token": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
        except Exception:
            pass
    return default_config

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def sync_and_push(custom_message=None):
    print("==============================================================================")
    print("🚀 BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG ĐẨY BÁO CÁO LÊN GITHUB & WEB ONLINE (CI/CD)...")
    print("==============================================================================")
    
    cfg = load_or_init_config()
    gh_user = cfg.get("github_user", "aresphamha")
    repo_name = cfg.get("repo_name", "Doi_Soat_Dong_Mat")
    branch = cfg.get("branch", "main")
    token = cfg.get("token", "").strip()
    
    try:
        repo = porcelain.open_repo(ROOT_DIR)
    except Exception:
        repo = porcelain.init(ROOT_DIR)
        
    # Danh sách các file / thư mục cần theo dõi
    tracked_items = [
        ".gitignore",
        "index.html",
        "Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html",
        "daily_records.js",
        "daily_details",
        "Cap_Nhat_Bao_Cao_Web.bat",
        "Mo_Bao_Cao.bat",
        "LOGIC_HE_THONG_NOI_BO_THAM_KHAO.html",
        "LOGIC_HE_THONG_NOI_BO_THAM_KHAO.md",
        "DONG_MAT_DASHBOARD",
        "LOGIC"
    ]
    
    valid_paths = [p for p in tracked_items if os.path.exists(os.path.join(ROOT_DIR, p))]
    porcelain.add(repo, paths=valid_paths)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = custom_message or f"Cập nhật Báo Cáo Đối Soát Đông Mát - {now_str}"
    
    try:
        porcelain.commit(
            repo, 
            message=msg.encode("utf-8"),
            author=f"{gh_user} <{gh_user}@users.noreply.github.com>".encode("utf-8")
        )
        print(f"📦 Đã tạo bản ghi commit: {msg}")
    except Exception as e:
        if "nothing to commit" in str(e).lower() or "empty" in str(e).lower():
            print("ℹ️ Dữ liệu không thay đổi so với bản trước đó.")
        else:
            print(f"ℹ️ Trạng thái commit: {e}")

    # Kiểm tra token
    if not token:
        print("\n⚠️ CHƯA CÓ GITHUB TOKEN ĐỂ TỰ ĐỘNG ĐẨY LÊN REPO:")
        print(f"   Vui lòng nhập GitHub Personal Access Token của bạn (hoặc dán vào file {CONFIG_FILE})")
        print("   👉 Tạo token tại: https://github.com/settings/tokens (chọn quyền 'repo' & 'workflow')")
        try:
            input_token = input("\n👉 Nhập/Dán GitHub Token của bạn tại đây: ").strip()
            if input_token:
                cfg["token"] = input_token
                save_config(cfg)
                token = input_token
            else:
                print("❌ Chưa nhập token. Bỏ qua bước đẩy lên GitHub.")
                return False
        except Exception:
            return False

    # Đẩy lên GitHub
    remote_url = f"https://{gh_user}:{token}@github.com/{gh_user}/{repo_name}.git"
    print(f"\n📡 Đang đẩy dữ liệu lên GitHub: https://github.com/{gh_user}/{repo_name} ...")
    
    try:
        porcelain.push(repo, remote_location=remote_url, refspecs=[f"refs/heads/{branch}".encode("utf-8")])
        print("==============================================================================")
        print("✅ ĐÃ ĐẨY LÊN GITHUB & KÍCH HOẠT CI/CD THÀNH CÔNG 100%!")
        print(f"🔗 Link mã nguồn Repo: https://github.com/{gh_user}/{repo_name}")
        print(f"🌐 Link Web Báo Cáo Online: https://{gh_user}.github.io/{repo_name}/")
        print("==============================================================================")
        return True
    except Exception as e:
        print(f"\n❌ Lỗi khi đẩy lên GitHub: {e}")
        print("💡 Lưu ý: Hãy đảm bảo bạn đã tạo Repository trên GitHub hoặc Token có quyền 'repo'.")
        return False

if __name__ == "__main__":
    sync_and_push()
