# BỘ TOOL SPAM PHIẾU CHUYỂN & HẬU KIỂM TELEGRAM SCM KINGFOODMART

Hệ thống tự động hóa nghiệp vụ gửi thông báo, hình ảnh đối soát và phiếu chuyển kho trực tiếp vào các nhóm Telegram Siêu thị Kingfoodmart.
Hỗ trợ kích hoạt trực tiếp từ Web Dashboard (Local PC Agent & GitHub Actions Cloud Runner).

---

## 🏗️ Kiến Trúc Module Hóa Step-by-Step (Chống Xung Đột Code)

Toàn bộ các công cụ đã được tách thành **các file module độc lập** trong thư mục `modules/`. File `run_spam_tool.py` đóng vai trò là Controller / Dispatcher điều hướng.
Khi bạn hoặc nhóm phát triển chỉnh sửa code của một ngành hàng bất kỳ (ví dụ: Thịt Cá), **hoàn toàn không ảnh hưởng hay gây lỗi cú pháp chéo** đến các ngành hàng khác (Rau Củ, Kho Khô, Đông Mát).

```text
SPAM_PHIEU_CHUYEN/
├── run_spam_tool.py                  # 🚀 Controller trung tâm (CLI & Runner Dispatcher)
├── modules/                          # 🧩 Các Module Nghiệp Vụ Độc Lập
│   ├── common.py                     # Hàm tiện ích chung (DB, Telegram session, sent history, mapping)
│   ├── tool_thit_ca.py               # 🥩 1. Chi Tiết Thịt Cá
│   ├── tool_mat.py                   # 🥬 2. Chi Tiết Hàng Mát
│   ├── tool_hau_kiem_rau.py          # 🥦 3. Hậu Kiểm Rau Củ
│   ├── tool_hau_kiem_thit_ca.py      # 🐟 4. Hậu Kiểm Thịt Cá
│   ├── tool_hau_kiem_dong_mat.py     # ❄️ 5. Hậu Kiểm Đông Mát
│   ├── tool_chi_tiet_kho_kho.py      # 📦 6. Chi Tiết Kho Khô FGA10101
│   ├── tool_hau_kiem_kho_kho.py      # ⚖️ 7. Hậu Kiểm Kho Khô FGA10101
│   └── tool_spam_tu_chon.py          # 🎯 Studio Spam Tùy Chọn
├── CHI TIẾT THỊT CÁ/                 # Thư mục nghiệp vụ Thịt Cá
├── CHI TIẾT MÁT/                     # Thư mục nghiệp vụ Hàng Mát
├── HẬU KIỂM RAU/                     # Thư mục nghiệp vụ Rau Củ
├── HẬU KIỂM THỊ CÁ/                  # Thư mục nghiệp vụ Hậu Kiểm Thịt Cá
├── HẬU KIỂM ĐÔNG MÁT/                # Thư mục nghiệp vụ Hậu Kiểm Đông Mát
├── KHO KHÔ/                          # Thư mục nghiệp vụ Kho Khô FGA10101
└── CONFIG_DATA/                      # Cấu hình Chat ID, session và lịch sử đã gửi
```

---

## 📁 Danh Sách 7 Phân Hệ Công Cụ

### 1. 🥩 Chi Tiết Phiếu Chuyển Thịt Cá (`modules/tool_thit_ca.py`)
- **Mã chạy**: `--tool thit_ca`
- **Chức năng**: Truy vấn các phiếu chuyển thịt cá đang chuyển (`Status=3`), xuất ảnh bảng và gửi vào nhóm Telegram ST.

### 2. 🥬 Chi Tiết Phiếu Chuyển Hàng Mát (`modules/tool_mat.py`)
- **Mã chạy**: `--tool mat`
- **Chức năng**: Truy vấn phiếu chuyển hàng Mát từ database (`CLA40102/FZA50102`), tạo ảnh và gửi nhắc ST xác nhận.

### 3. 🥦 Hậu Kiểm Rau Củ (`modules/tool_hau_kiem_rau.py`)
- **Mã chạy**: `--tool hau_kiem_rau`
- **Chức năng**: Quét thẻ kho Rau Củ từ Bình Thắng (`FEA20102`), lọc phiếu lệch (`double_checked_status=1, status=5`) và gửi ST giải trình.

### 4. 🐟 Hậu Kiểm Thịt Cá (`modules/tool_hau_kiem_thit_ca.py`)
- **Mã chạy**: `--tool hau_kiem_thit_ca`
- **Chức năng**: Quét biến động thẻ kho Thịt Cá Sóng Thần (`MFA30102`), gửi thông báo nhắc ST xác nhận chênh lệch.

### 5. ❄️ Hậu Kiểm Đông Mát (`modules/tool_hau_kiem_dong_mat.py`)
- **Mã chạy**: `--tool hau_kiem_dong_mat`
- **Chức năng**: Ưu tiên kiểm tra xử lý phiếu treo ngày hôm qua (D-1), nếu hết mới chuyển sang D-0.

### 6. 📦 Chi Tiết Phiếu Chuyển Kho Khô (`modules/tool_chi_tiet_kho_kho.py`)
- **Mã chạy**: `--tool chi_tiet_kho_kho`
- **Kho nguồn**: `FGA10101 _ Bình Thắng _ Lưu Hàng`
- **Chức năng**: Lọc phiếu chuyển FGA10101 đang treo từ ngày cũ nhất đến D-1, xuất bảng Gradient Pastel gửi nhóm DC.

### 7. ⚖️ Hậu Kiểm Kho Khô (`modules/tool_hau_kiem_kho_kho.py`)
- **Mã chạy**: `--tool hau_kiem_kho_kho`
- **Kho nguồn**: `FGA10101 _ Bình Thắng _ Lưu Hàng`
- **Chức năng**: Lọc phiếu Hậu Kiểm FGA10101 lệch từ ngày cũ nhất đến D-1, xuất bảng Gradient Pastel gửi nhóm DC.

---

## ⚡ Các Lệnh Chạy Tổng Hợp Step-by-Step

- **Chạy 5 Tool Tươi Sống tuần tự**:
  ```bash
  python run_spam_tool.py --tool all
  ```
- **Chạy Toàn Bộ 7 Tool tuần tự (Bao gồm cả Kho Khô)**:
  ```bash
  python run_spam_tool.py --tool all_with_kho_kho
  ```
- **Chế độ Chạy Thử (Dry-Run)**:
  ```bash
  python run_spam_tool.py --tool all --dry-run
  ```
