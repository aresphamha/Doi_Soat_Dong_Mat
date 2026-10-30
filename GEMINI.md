# 🤖 HƯỚNG DẪN & QUY TẮC BẮT BUỘC CHO AI ASSISTANT (ANTIGRAVITY)

---

## 📌 PHẦN 1: QUY TẮC TỰ ĐỘNG ĐẨY CODE LÊN GITHUB (AUTO GIT PUSH)

Mỗi khi hoàn thành bất kỳ tác vụ nào liên quan đến code trong dự án này (chỉnh sửa file, thêm tính năng mới, sửa lỗi, cập nhật cấu hình, v.v.):
1. **BẮT BUỘC TỰ ĐỘNG CHẠY:**
   * `git pull --rebase origin main` (nếu cần để đồng bộ với GitHub)
   * `git add -u` (hoặc add các file thay đổi liên quan)
   * `git commit -m "<mô tả thay đổi ngắn gọn bằng tiếng Việt>"`
   * `git push origin main`
2. **MỤC ĐÍCH:**
   * Đảm bảo mọi thay đổi trên máy tính lập tức được đưa lên GitHub Repository (`aresphamha/Doi_Soat_Dong_Mat`).
   * Máy chủ **GitHub Actions Cloud Runner** và trang web **GitHub Pages** luôn chạy trên phiên bản code mới nhất, không bao giờ bị lệch dữ liệu hoặc lỗi token/mã cũ.
   * Người dùng không cần phải nhắc hay chạy lệnh push thủ công.

---

## 🧠 PHẦN 2: HỆ THỐNG VẬN HÀNH TOÀN BỘ CÔNG CỤ HẬU KIỂM SCM
*(Tài liệu chi tiết xem tại `LOGIC/LOGIC_TOAN_BO_TOOL_HAU_KIEM.md`)*

### 1. Danh sách 4 Tool Hậu Kiểm Đang Có:
* **Hậu Kiểm Kho Khô (`--tool hau_kiem_kho_kho`)**:
  * Kho nguồn: `FGA10101`, `FGA10103`, `SCF`, `Vệ Tinh`.
  * Điều kiện: `double_check_code != '' AND double_checked_status = 1 AND status IN (3, 5)`.
  * Kênh gửi: Nhóm **Telegram DC** của Siêu thị (`Danh_Sach_Chat_ID_Nhom_DC.xlsx` / `CONFIG_DATA_STORES.json` - `chat_id_dc`).
  * Định dạng: Ảnh bảng Gradient pastel (Xanh pastel sang Cam đào) + Tag Quản lý/Trưởng ca.
* **Hậu Kiểm Rau Củ (`--tool hau_kiem_rau`)**:
  * Kho nguồn: `FEA20102` (Bình Thắng Quá Cảnh).
  * Điều kiện: `double_checked_status = 1 AND status = 5`.
  * Kênh gửi: Nhóm Telegram Rau Củ (`chat_id_rc`).
* **Hậu Kiểm Thịt Cá (`--tool hau_kiem_thit_ca`)**:
  * Kho nguồn: `MFA30102` (Sóng Thần Quá Cảnh), `SCF`.
  * Điều kiện: `double_checked_status = 1 AND status = 5`.
  * Kênh gửi: Nhóm Telegram Thịt Cá / Đông Mát (`chat_id_dm`).
* **Hậu Kiểm Đông Mát (`--tool hau_kiem_dong_mat`)**:
  * Kho nguồn: `CLA40102`, `FZA50102`, `CL02`, `FZ02`.
  * Điều kiện: `double_checked_status = 1 AND status = 5`. Ưu tiên D-1 trước, nếu hết mới sang D-0.
  * Kênh gửi: Nhóm Telegram Đông Mát (`chat_id_dm`).

### 2. Nguyên Tắc Trạng Thái Phiếu (WMS CDC DB `103.140.248.250:9030`):
* `double_checked_status = 1`: **CẦN HẬU KIỂM** (Đang treo, chưa hoàn tất -> CẦN SPAM NHẮC NHỞ).
* `double_checked_status = 3`: **ĐÃ HẬU KIỂM XONG** (Đã quét đối soát xong -> BỎ QUA KHÔNG SPAM).

### 3. Cú Pháp CLI Chạy Tool (Tại thư mục gốc dự án):
```bash
# Chạy Hậu Kiểm Kho Khô:
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho

# Chạy thử không gửi tin (Dry-run):
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho --dry-run

# Lọc theo danh sách Siêu thị hoặc Mã phiếu PT chỉ định:
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho --stores "A107,A108,VHT,A269" --force

# Chạy toàn bộ tất cả công cụ:
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool all_with_kho_kho
```

### 4. Thiết Lập Trên Máy Mới / Tài Khoản Mới:
* Thư viện yêu cầu: `pip install pymysql openpyxl telethon requests pillow pandas dataframe_image pytz`
* Session Telegram: Đặt file `user_session.session` tại thư mục gốc hoặc `SPAM_PHIEU_CHUYEN/CONFIG_DATA/` (có cơ chế dự phòng tự động giải mã từ `session_b64.txt`).
* Nếu mở Siêu thị mới: Thêm thông tin vào `CONFIG_DATA_STORES.json` và bổ sung mapping trong `TOOLS_DOI_SOAT/Spam_Phieu_Hau_Kiem_Kho_Kho.py`.
