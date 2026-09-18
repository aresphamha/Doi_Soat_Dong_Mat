# HƯỚNG DẪN CẤU HÌNH VÀ VẬN HÀNH HỆ THỐNG GỬI BÁO CÁO TELEGRAM (SCM SERVER)

Tài liệu này tổng hợp thông tin cấu hình, sơ đồ thư mục và quy trình vận hành hệ thống gửi báo cáo qua Telegram từ máy chủ SCM.

---

## 1. THÔNG TIN MÁY CHỦ SCM

*   **Hệ điều hành:** Ubuntu 24.04 LTS
*   **Cấu hình phần cứng:** 2 CPU / 4GB RAM / 38GB Disk (trống khoảng ~36GB)
*   **Môi trường:** Python 3.12.3 (đã kiểm tra kết nối được tới `api.telegram.org`)
*   **Múi giờ:** UTC+7 (Múi giờ Việt Nam)
*   **Thư mục làm việc:** `/opt/scm`

### Thông tin đăng nhập SSH:
*   **Địa chỉ IP:** `192.168.100.51` (SSH Port: `22`)
*   **Tài khoản:** `scm`
*   **Mật khẩu mặc định:** `ScmVM@260731`
    > **⚠️ QUAN TRỌNG:**
    > **Thay đổi mật khẩu ngay lần đầu đăng nhập:** Sau khi SSH vào, hãy gõ lệnh `passwd` để đổi mật khẩu mới.
*   **Quyền Sudo:** Tài khoản `scm` đã được cấu hình quyền `sudo` không cần nhập lại mật khẩu.
*   **Kết nối mạng:**
    *   Nếu máy tính của bạn nằm trong cùng mạng LAN `192.168.100.x`:
        ```bash
        ssh scm@192.168.100.51
        ```
    *   Nếu không kết nối được qua LAN, vui lòng báo lại quản trị viên để mở quyền truy cập qua **Console Hyper-V**.

---

## 2. CẤU TRÚC THƯ MỤC LÀM VIỆC (`/opt/scm`)

Tại thư mục `/opt/scm` có các thành phần chính sau:

| Thư mục / File | Mô tả / Công dụng |
| :--- | :--- |
| `venv/` | Môi trường ảo Python độc lập (đã cài sẵn thư viện `requests`). |
| `.env` | File cấu hình chứa Token của Bot và ID nhóm chat (đang để trống). |
| `telegram_notify.py` | Script chứa hàm gửi tin nhắn (có sẵn tính năng xử lý lỗi định dạng HTML của Telegram). |
| `scm_report.py` | Script mẫu chạy job. Bạn sẽ sửa hàm `build_report()` tại đây theo nội dung cần gửi. |
| `logs/` | Nơi lưu trữ file nhật ký (logs) của các job chạy tự động theo lịch. |

---

## 3. QUY TRÌNH THIẾT LẬP & CHẠY THỬ

Thực hiện tuần tự các bước sau bằng dòng lệnh (Terminal):

### Bước 1: Điền Token và Chat ID
Sử dụng công cụ `nano` để chỉnh sửa file cấu hình môi trường:
```bash
nano /opt/scm/.env
```
Nhập thông tin token và chat ID của bạn vào:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```
*(Ấn `Ctrl + O` -> `Enter` để lưu, sau đó `Ctrl + X` để thoát).*

> **⚠️ CẢNH BÁO:**
> File `.env` chứa token bảo mật quan trọng. Hãy đảm bảo quyền truy cập file là `600` (`chmod 600 /opt/scm/.env`) và tuyệt đối **không** commit file này lên các hệ thống Git công khai.

### Bước 2: Gửi thử tin nhắn kiểm tra
Chạy script gửi tin nhắn test trực tiếp bằng Python trong môi trường ảo `venv`:
```bash
/opt/scm/venv/bin/python /opt/scm/telegram_notify.py "test tu may SCM"
```

### Bước 3: Chạy thử Job Báo Cáo
Chạy file script báo cáo mẫu để đảm bảo logic tạo báo cáo và định dạng hoạt động chính xác:
```bash
/opt/scm/venv/bin/python /opt/scm/scm_report.py
```

---

## 4. CẤU HÌNH LỊCH CHẠY TỰ ĐỘNG (SYSTEMD TIMER)

Sau khi kiểm tra các bước trên chạy thành công và nội dung báo cáo trong `scm_report.py` đã đúng yêu cầu, bạn tiến hành kích hoạt lịch chạy tự động lúc **08:00 sáng mỗi ngày**:

### Kích hoạt timer:
```bash
sudo systemctl enable --now scm-report.timer
```

### Kiểm tra trạng thái và lịch chạy tiếp theo:
```bash
systemctl list-timers scm-report.timer
```

### Xem log lịch sử chạy gần nhất:
```bash
journalctl -u scm-report.service -n 50
```

---

## 5. CÀI ĐẶT THÊM THƯ VIỆN BỔ SUNG

Nếu cần import thêm các thư viện Python khác để phục vụ cho việc xử lý dữ liệu (ví dụ: `pandas`, `openpyxl`, ...), hãy sử dụng công cụ `pip` của chính môi trường ảo `venv`:

```bash
/opt/scm/venv/bin/pip install <ten-thu-vien>
```
*(Ví dụ: `/opt/scm/venv/bin/pip install pandas openpyxl`)*
