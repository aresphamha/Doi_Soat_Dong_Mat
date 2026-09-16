# BỘ TOOL SPAM PHIẾU CHUYỂN & HẬU KIỂM TELEGRAM SCM KINGFOODMART

Bộ công cụ tự động hóa nghiệp vụ gửi thông báo, hình ảnh đối soát và phiếu chuyển kho trực tiếp vào các nhóm Telegram Siêu thị Kingfoodmart.

---

## 📁 Cấu Trúc Các Phân Hệ Tool

### 1. 🥩 Chi Tiết Phiếu Chuyển Thịt Cá (`CHI TIẾT THỊT CÁ/`)
- **File chính**: `Spam_Phieu_Chuyen_Thit_Ca.py`
- **File chạy nhanh**: `Chay_Tool_Spam.bat`
- **Chức năng**:
  - Tự động kết nối cơ sở dữ liệu MySQL truy vấn các phiếu chuyển hàng Thịt Cá trong ngày.
  - Sử dụng `dataframe_image` kết xuất bảng chi tiết thành hình ảnh trực quan.
  - Tự động gửi ảnh bảng kê vào nhóm Telegram của từng Siêu thị tương ứng.

### 2. 🥗 Chi Tiết Phiếu Chuyển Hàng Mát (`CHI TIẾT MÁT/`)
- **File chính**: `Spam_Phieu_Chuyen_Hang_Mat.py`
- **Chức năng**:
  - Truy vấn phiếu chuyển hàng Mát từ database.
  - Tạo ảnh phiếu giao nhận và tự động bắn tin nhắn vào Group Telegram nhận hàng mát.

### 3. 🥬 Hậu Kiểm Rau Củ (`HẬU KIỂM RAU/`)
- **File chính**: `Spam_Phieu_Hau_Kiem_Rau_Cu.py`, `prepare.py`, `test_rau_cu.py`
- **File chạy nhanh**: `Chay_Tool_Spam_Hau_Kiem_Rau_Cu.bat`
- **Chức năng**:
  - Quét dữ liệu giao nhận Rau Củ.
  - Gửi thông báo nhắc nhở hậu kiểm, đối soát chênh lệch và kiểm tra camera giao nhận đến các nhóm ST.

### 4. 🐟 Hậu Kiểm Thịt Cá (`HẬU KIỂM THỊ CÁ/`)
- **File chính**: `Spam_Phieu_Hau_Kiem_Thit_Ca.py`
- **File chạy nhanh**: `Chay_Tool_Spam_Hau_Kiem.bat`
- **Chức năng**:
  - Gửi thông báo hậu kiểm chênh lệch và nhắc nhở ST xác nhận phiếu giao nhận Thịt Cá.

---

## ⚙️ Yêu Cầu Cài Đặt Môi Trường

Cần cài đặt các thư viện Python:
```bash
pip install telethon pandas pymysql dataframe_image requests pytz
```
