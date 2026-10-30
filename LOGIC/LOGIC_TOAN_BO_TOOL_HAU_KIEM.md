# 📘 TÀI LIỆU TOÀN DIỆN: HỆ THỐNG & LOGIC TOÀN BỘ CÔNG CỤ HẬU KIỂM SCM
*(Dành cho việc chuyển giao sang máy mới, tài khoản mới hoặc trợ lý AI Antigravity mới vận hành độc lập)*

---

## 📌 1. TỔNG QUAN HỆ THỐNG 4 TOOL HẬU KIỂM SCM

Hệ thống Hậu Kiểm SCM Kingfoodmart gồm **4 phân hệ chính** tương ứng với các ngành hàng:

| Phân hệ | Mã Tool CLI | Kho nguồn xuất phát | Bảng DB tra cứu | Kênh Telegram nhận tin |
|:---|:---:|:---|:---|:---:|
| **1. Hậu Kiểm Rau Củ** | `hau_kiem_rau` | `FEA20102` (Bình Thắng) | `__cdc_kfm_kf_inventories_kf_transfer_items` | Nhóm Rau Củ ST (`chat_id_rc`) |
| **2. Hậu Kiểm Thịt Cá** | `hau_kiem_thit_ca` | `MFA30102` (Sóng Thần), `SCF` | `__cdc_kfm_kf_inventories_kf_transfer_items` | Nhóm Thịt Cá / ĐM ST (`chat_id_dm`) |
| **3. Hậu Kiểm Đông Mát** | `hau_kiem_dong_mat` | `CLA40102`, `FZA50102` | `__cdc_kfm_kf_inventories_kf_transfer_items` | Nhóm Đông Mát ST (`chat_id_dm`) |
| **4. Hậu Kiểm Kho Khô** | `hau_kiem_kho_kho` | `FGA10101`, `FGA10103`, `SCF`, Vệ Tinh | `__cdc_kfm_kf_inventories_kf_transfer_items` | Nhóm DC Siêu thị (`chat_id_dc`) |

---

## 🗄️ 2. THÔNG TIN KẾT NỐI HỆ THỐNG & CƠ SỞ DỮ LIỆU

### A. Cơ sở dữ liệu CDC MySQL:
* **Host**: `103.140.248.250`
* **Port**: `9030`
* **User**: `kfm_scm_tho_nguyen`
* **Password**: `TnAM0WEsv4kmasw878wt`
* **Database**: `kfm_scm`
* **Bảng chính chứa phiếu**: `__cdc_kfm_kf_inventories_kf_transfer_items`
* **Bảng tra cứu tên Siêu thị / Kho**: `__cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard`

### B. Telegram API & Bot:
* **Telegram API ID**: `28938971`
* **Telegram API Hash**: `5d392e21b03f0b2f0a1bfdc5ff840b3c`
* **Telegram Bot Token**: `8810108114:AAER-s5oEc3pAoggenGm0R5fjA3xMDdQswM`
* **Cơ chế gửi 2 lớp (Fail-Safe)**:
  1. *Lớp 1*: Gửi bằng Bot Telegram qua `requests.post(https://api.telegram.org/bot<TOKEN>/sendPhoto)`.
  2. *Lớp 2 (Dự phòng)*: Nếu Bot gặp lỗi (ví dụ chưa add bot vào group, hoặc group riêng tư), tự động fallback chuyển sang tài khoản người dùng cá nhân Telethon User Client (`user_session.session`) để gửi trực tiếp.

---

## 🧠 3. ĐIỀU KIỆN & QUY TẮC LỌC PHIẾU CẦN HẬU KIỂM

### Định nghĩa trạng thái trên WMS:
* `t.double_check_code IS NOT NULL AND t.double_check_code != ''`: Có phát sinh phiếu Hậu Kiểm.
* `t.double_checked_status = 1`: **CẦN HẬU KIỂM** (Siêu thị chưa quét xác nhận hoặc quét dở dang -> **CẦN SPAM NHẮC NHỞ**).
* `t.double_checked_status = 3`: **ĐÃ HẬU KIỂM XONG** (Đã quét đối soát hoàn tất -> **BỎ QUA KHÔNG SPAM**).
* `t.status IN (3, 5)`: Phiếu ở trạng thái hợp lệ để xử lý (`status=5` là đã nhận hàng/đã giao, `status=3` là đang giao).

### Chi tiết logic từng ngành hàng:

#### 1. Hậu Kiểm Rau Củ (`hau_kiem_rau`):
* **Kho nguồn**: `6aa77d8ff426e20007f7f451` (`FEA20102 _ Bình Thắng _ Quá Cảnh`)
* **Điều kiện**: `double_checked_status = 1 AND status = 5`
* **Thời gian**: Mặc định từ đầu ngày đến hết ngày hiện tại (hoặc ngày chỉ định).
* **Nhóm nhận**: File `Danh_Sach_Sieu_Thi_Rau_Cu.xlsx` hoặc cột `chat_id_rc` trong `CONFIG_DATA_STORES.json`.

#### 2. Hậu Kiểm Thịt Cá (`hau_kiem_thit_ca`):
* **Kho nguồn**: `6aabb4d0e493030007272a3f` (`MFA30102 _ Sóng Thần _ Quá Cảnh`), `6a34ed56f23028000774139f` (`MeatFish - Miền Đông - SCF`)
* **Điều kiện**: `double_checked_status = 1 AND status = 5`
* **Thời gian**: Mặc định ngày hiện tại.
* **Nhóm nhận**: File `Danh sách Siêu thị.xlsx` hoặc cột `chat_id_dm` trong `CONFIG_DATA_STORES.json`.

#### 3. Hậu Kiểm Đông Mát (`hau_kiem_dong_mat`):
* **Kho nguồn**: `6aa6a1eedf3d880007871f3f` (`CLA40102`), `6aa77de130fded00073d4521` (`FZA50102`), `6a34ee2aebb48c000760d803` (`CL02`), `6a34ec8d77173000073e64e2` (`FZ02`).
* **Quy tắc ưu tiên (Rule D-1)**:
  * Nếu không chỉ định ngày, hệ thống quét **ngày hôm qua (D-1)** trước. Nếu D-1 còn phiếu treo thì spam D-1.
  * Nếu D-1 đã hết sạch phiếu treo, tự động chuyển sang quét ngày hôm nay (D-0).

#### 4. Hậu Kiểm Kho Khô (`hau_kiem_kho_kho`):
* **Kho nguồn**:
  * `6aabb0a2f426e20007f80123`: `FGA10101 _ Bình Thắng _ Lưu Hàng`
  * `6aabb0d73c46470007f935ce`: `FGA10103 _ Bình Thắng _ Khai Trương`
  * `6aa77de130fded00073d4521`: `Kho Khô FGA Vệ Tinh`
  * `6a34ed56f23028000774139f`: `MeatFish - Miền Đông - SCF - Quá Cảnh`
* **Điều kiện**: `double_check_code != '' AND double_checked_status = 1 AND status IN (3, 5)`
* **Thời gian**: Quét toàn bộ phiếu đang treo từ ngày cũ nhất đến hiện tại.
* **Nhóm nhận**: Bắt buộc gửi vào **Nhóm Telegram DC** của ST (tra từ `Danh_Sach_Chat_ID_Nhom_DC.xlsx` hoặc `CONFIG_DATA_STORES.json` cột `chat_id_dc`).
* **Định dạng bảng**: Ảnh bảng Gradient Pastel (Xanh ngọc pastel sang Cam đào pastel) sinh từ `table_image_generator.py`.
* **Cú pháp caption chuẩn**:
  * Nếu 1 phiếu: `⚠️ Siêu thị còn 1 phiếu hậu kiểm kho khô chưa nhận ngày dd.mm.`
  * Nếu nhiều phiếu cùng ngày: `⚠️ Siêu thị còn X phiếu hậu kiểm kho khô chưa nhận ngày dd.mm.`
  * Nếu nhiều phiếu khác ngày: `⚠️ Siêu thị còn X phiếu hậu kiểm kho khô chưa nhận từ ngày dd.mm đến dd.mm.`
  * Tự động tag: `@SM @TC @GSM` hoặc tag trực tiếp ID Quản lý/Trưởng ca trong group.

---

## 💻 4. HƯỚNG DẪN CÀI ĐẶT TRÊN MÁY MỚI / TÀI KHOẢN MỚI

Khi chuyển sang máy tính mới hoặc cài đặt lại từ đầu:

### Bước 1: Cài đặt thư viện Python cần thiết
```bash
pip install pymysql openpyxl telethon requests pillow pandas dataframe_image pytz
```

### Bước 2: Chuẩn bị session Telegram
File session `user_session.session` phải nằm tại một trong các vị trí:
1. Thư mục gốc dự án: `user_session.session`
2. `SPAM_PHIEU_CHUYEN/CONFIG_DATA/user_session.session`
3. Hoặc tự động khôi phục từ file Base64 `session_b64.txt`.

*(Nếu là nick mới hoàn toàn chưa đăng nhập, chỉ cần chạy `python Dang_Nhap_Telegram.py` để đăng nhập 1 lần duy nhất bằng số điện thoại).*

---

## 🚀 5. BỘ LỆNH ĐIỀU KHIỂN CLI CHUẨN

Tất cả các công cụ đều được điều khiển qua file trung tâm `SPAM_PHIEU_CHUYEN/run_spam_tool.py`:

### A. Chạy từng Tool đơn lẻ:
```bash
# 1. Hậu kiểm Kho Khô
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho

# 2. Hậu kiểm Rau Củ
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_rau

# 3. Hậu kiểm Thịt Cá
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_thit_ca

# 4. Hậu kiểm Đông Mát
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_dong_mat
```

### B. Chạy chế độ Thử Nghiệm (Dry-Run - Không gửi thật):
```bash
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho --dry-run
```

### C. Lọc theo danh sách Siêu thị hoặc Mã phiếu cụ thể:
```bash
# Lọc theo mã Siêu thị:
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho --stores "A107,A108,VHT,A269" --force

# Lọc theo danh sách mã Phiếu chuyển (PT):
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool hau_kiem_kho_kho --stores "PT2066192,PT2066177" --force
```

### D. Chạy gộp toàn bộ:
```bash
# Chạy cả 4 tool Hậu kiểm + Chi tiết tươi sống:
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool all

# Chạy toàn bộ 7 tool (bao gồm cả Kho Khô):
python SPAM_PHIEU_CHUYEN/run_spam_tool.py --tool all_with_kho_kho
```

---

## 🔄 6. QUY TẮC CẬP NHẬT KHI CÓ SIÊU THỊ MỚI KHAI TRƯƠNG

Khi Kingfoodmart mở thêm siêu thị mới (ví dụ `A265`, `A269`):
1. **Tìm Chat ID DC trên Telegram**: Tra cứu trong nhóm Telegram cá nhân với từ khóa tên ST hoặc địa chỉ (Ví dụ: `Blue Sky Tower` -> Chat ID `-1004330559619`).
2. **Cập nhật vào `CONFIG_DATA_STORES.json`**:
   ```json
   {
     "id": "A269",
     "name": "KFM_HCM_TDU - TMDV B10-1 Chung Cư Blue Sky Tower",
     "short": "A269",
     "chat_id_dm": "",
     "chat_id_rc": "",
     "chat_id_dc": "-1004330559619"
   }
   ```
3. **Cập nhật mapping bổ sung trong `TOOLS_DOI_SOAT/Spam_Phieu_Hau_Kiem_Kho_Kho.py`**:
   ```python
   dc_code_map['A269'] = '-1004330559619'
   st_to_code['KFM_HCM_TDU - TMDV B10-1 Chung Cư Blue Sky Tower'] = 'A269'
   st_to_code['Blue Sky Tower'] = 'A269'
   ```
4. **Tự động đẩy code lên GitHub**: Tuân thủ quy tắc `git pull --rebase origin main` -> `git add -u` -> `git commit` -> `git push origin main`.
