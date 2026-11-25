# TÀI LIỆU LOGIC ĐỐI SOÁT CHÉO DƯ - THIẾU NGÀNH HÀNG ĐÔNG MÁT

Tài liệu này mô tả chi tiết quy trình, nguồn dữ liệu và thuật toán được sử dụng trong Báo Cáo Đối Soát Kho cho ngành hàng Đông Mát để ghép cặp (map) các trường hợp thừa/thiếu hàng hóa.

> [!NOTE]
> Khác với Thịt Cá hay Rau Củ, ngành hàng Đông Mát có thêm biến số **"Phân loại"** (Ví dụ: Đông, Mát, Khô...). Do đó, mọi thuật toán đối soát đều phải xét thêm điều kiện "Phân loại" để đảm bảo không map chéo nhầm giữa các loại hàng hóa khác nhiệt độ bảo quản.

---

## 1. Nguồn Dữ Liệu và Tiền Xử Lý

### 1.1 Lấy dữ liệu từ Database (StarRocks)
Hệ thống kết nối trực tiếp vào cơ sở dữ liệu `kfm_scm` qua IP `103.140.248.250` để lấy dữ liệu phiếu chuyển hàng (transfer tickets) có trạng thái đã hoàn thành (`status = 5`).
- **Dữ liệu Thiếu:** Truy xuất các mặt hàng được xuất từ Kho Đông Mát gốc (`from_branch_id = '6a34ed948cd2590007817eb6'`). Số lượng Thiếu = `Số lượng chuyển` - `Số lượng nhận` (> 0).
- **Dữ liệu Thừa:** Truy xuất các mặt hàng được lập phiếu từ Kho Dư ảo của Đông Mát (`from_branch_id = '6a34edab5433ec00085ec5c9'`). Số lượng Thừa = `Số lượng dư` được ghi nhận trên phiếu.
- Bỏ qua các mã hàng bắt đầu bằng tiền tố `CC` (Công cụ dụng cụ).
- Tách tiền tố mã hàng ra để lấy **Phân loại** (Đông, Mát, v.v.).

### 1.2 Layout Vị trí Siêu thị
Hệ thống đọc file Excel chứa thông tin layout để lấy tọa độ/vị trí của từng siêu thị trên tuyến đường:
- Hệ thống hỗ trợ đọc cột **`STT`** hoặc **`Vị trí`** (chứa số thứ tự).
- Hỗ trợ đọc cột **`Chi nhánh nhận`** hoặc **`Siêu thị`** (chứa tên).

---

## 2. Thuật Toán Gom Nhóm và Đối Soát (6 Bước)

Toàn bộ dữ liệu Thiếu và Thừa sẽ được gom nhóm (**Group By**) theo 3 trường cốt lõi: **Phân loại**, **Chi nhánh nhận** và **Mã hàng (SKU)**. Cột `Mã chuyển hàng` (Phiếu chuyển) của Thiếu và Thừa được gộp lại bằng dấu phẩy để lưu vết (traceability) chứ không dùng làm điều kiện ép buộc ghép cặp.

### Bước 1: Khớp Nội Bộ 100% (DC thao tác sai)
- **Điều kiện:** Tại cùng 1 Siêu thị, có ghi nhận cả phiếu Thiếu và phiếu Thừa cho **cùng 1 Mã hàng** và **cùng 1 Phân loại**.
- **Tính toán:** Lấy phần giao nhau nhỏ nhất (Min) giữa tổng số lượng Thiếu và tổng số lượng Thừa.
- **Tiêu chí 100%:** Độ chênh lệch giữa lượng Thiếu và lượng Thừa `(SL Thiếu - SL Thừa)` phải bằng 0 (dung sai <= 0.01 kg).
- **Kết quả:** Hiển thị danh sách tự cấn trừ nội bộ. Gắn kèm 2 cột `Mã chuyển hàng thiếu` và `Mã chuyển hàng thừa`.

### Bước 2: Khớp Nội Bộ Một Phần
- **Điều kiện:** Tương tự Bước 1, nhưng độ chênh lệch giữa lượng Thiếu và lượng Thừa lớn hơn 0.01 kg.
- **Tính toán:** Hệ thống cấn trừ tối đa lượng khả dụng. 
- **Kết quả:** Phần dư hoặc thiếu dôi ra (`Remaining_Shortage`, `Remaining_Surplus`) sẽ được chuyển xuống Bước 3.

### Bước 3: Khớp Chéo Liên ST 1-1
- **Điều kiện:** Lấy phần số lượng Thiếu và Thừa còn sót lại từ Bước 1 và 2. Tìm kiếm các Siêu thị khác nhau có báo Thiếu và báo Thừa cho cùng Mã hàng và Phân loại.
- **Thuật toán Ghép Cặp (Matching):**
  1. Chỉ ghép cặp các siêu thị có lượng Thiếu và Thừa **bằng nhau y hệt** (dung sai <= 0.01 kg).
  2. Tính toán **Khoảng cách Vị trí (Distance)**: `Khoảng cách = |Vị trí ST Thừa - Vị trí ST Thiếu|` dựa vào file Layout.
  3. Chọn siêu thị báo Thiếu có khoảng cách **Gần Nhất** với siêu thị báo Thừa để ghép cặp (ưu tiên giải quyết hàng lộn trên cùng tuyến).
  4. Phân loại xác suất: Rất cao (kề nhau, khoảng cách <= 5), Trung bình (cùng khu, <= 15), Thấp (> 15).

### Bước 4: Tổng Dư ≥ Tổng Thiếu
- **Điều kiện:** Thống kê tổng số lượng Thừa và Thiếu (sau khi trừ hao ở Khớp nội bộ) cho từng Mã hàng (phải xét theo từng Phân loại) trên toàn bộ hệ thống siêu thị.
- **Tiêu chí:** Chỉ lấy các Mã hàng có `Tổng Thừa >= Tổng Thiếu` (và Tổng Thừa > 0).
- **Ý nghĩa:** Khoanh vùng các mặt hàng Đông Mát đang dư dả tổng thể (lượng nhận thực tế lớn hơn hoặc bằng lượng xuất trên hệ thống).

### Bước 5: Chỉ Ghi Nhận Thiếu Ròng
- **Điều kiện:** Các lượng Thiếu của siêu thị mà sau khi chạy qua Bước 1, 2, 3 vẫn **không thể tìm thấy** siêu thị nào báo Thừa để cấn trừ.
- **Ý nghĩa:** Số lượng mất mát / thiếu hụt thực sự không có lý do.

### Bước 6: Chỉ Ghi Nhận Thừa Ròng
- **Điều kiện:** Các lượng Thừa của siêu thị mà sau khi chạy qua Bước 1, 2, 3 vẫn **không có** siêu thị nào báo Thiếu để cấn trừ.
- **Ý nghĩa:** Số lượng dư thực tế trên hệ thống.
