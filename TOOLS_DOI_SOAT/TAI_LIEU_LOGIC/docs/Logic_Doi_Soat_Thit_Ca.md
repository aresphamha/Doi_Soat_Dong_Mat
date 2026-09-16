# TÀI LIỆU LOGIC ĐỐI SOÁT CHÉO DƯ - THIẾU NGÀNH HÀNG THỊT CÁ

Tài liệu này mô tả chi tiết quy trình, nguồn dữ liệu và thuật toán được sử dụng trong Báo Cáo Đối Soát Kho Thịt Cá để ghép cặp (map) các trường hợp thừa/thiếu hàng hóa.

> [!NOTE]
> Việc đối soát chéo nhằm mục đích phát hiện các lỗi vận hành từ Kho/DC (lên nhầm hàng, giao nhầm siêu thị) hoặc lỗi kiểm đếm tại Siêu thị, từ đó tự động cấn trừ số lượng thừa/thiếu để giảm thiểu công sức đối soát thủ công và xác định chính xác số lượng thất thoát thực tế (ròng).

---

## 1. Nguồn Dữ Liệu và Tiền Xử Lý

### 1.1 Lấy dữ liệu từ Database (StarRocks)
Hệ thống kết nối trực tiếp vào cơ sở dữ liệu `kfm_scm` qua IP `103.147.122.103` để lấy dữ liệu phiếu chuyển hàng (transfer tickets) có trạng thái đã hoàn thành (`status = 5`).
- **Dữ liệu Thiếu:** Truy xuất các mặt hàng được xuất từ Kho Thịt Cá gốc (`from_branch_id = '6a34ed56f23028000774139f'`). Số lượng Thiếu = `Số lượng chuyển` - `Số lượng nhận` (> 0).
- **Dữ liệu Thừa:** Truy xuất các mặt hàng được lập phiếu từ Kho Dư ảo (`from_branch_id = '6a34ed8d6607ba000703e235'`). Số lượng Thừa = `Số lượng dư` được ghi nhận trên phiếu.
- Bỏ qua các mã hàng bắt đầu bằng tiền tố `CC` (Công cụ dụng cụ, không phải hàng hóa tiêu dùng).

### 1.2 Layout Vị trí Siêu thị
Hệ thống đọc file `LayoutImportThitCa.xlsx` để lấy tọa độ/vị trí của từng siêu thị trên tuyến đường giao hàng:
- Cột **`STT`** hoặc **`Vị trí`**: Chứa số nguyên đại diện cho thứ tự/khoảng cách.
- Cột **`Chi nhánh nhận`** hoặc **`Siêu thị`**: Chứa tên siêu thị để map với dữ liệu Database.
Hệ thống đã được thiết kế mở để tự động nhận dạng cấu trúc cột dù tiêu đề là "STT/Chi nhánh nhận" hay "Vị trí/Siêu thị".

---

## 2. Thuật Toán Gom Nhóm và Đối Soát (6 Bước)

Trước khi đối soát, toàn bộ dữ liệu Thiếu và Thừa sẽ được gom nhóm (**Group By**) theo 2 trường: **Chi nhánh nhận** và **Mã hàng (SKU)**. Cột `Mã chuyển hàng` (Phiếu chuyển) của Thiếu và Thừa được gộp lại bằng dấu phẩy để lưu vết (traceability) chứ không dùng làm điều kiện ép buộc ghép cặp.

### Bước 1: Khớp Nội Bộ 100% (DC thao tác sai)
- **Điều kiện:** Tại cùng 1 Siêu thị, có ghi nhận cả phiếu Thiếu và phiếu Thừa cho cùng 1 Mã hàng.
- **Tính toán:** Lấy phần giao nhau nhỏ nhất (Min) giữa tổng số lượng Thiếu và tổng số lượng Thừa.
- **Tiêu chí 100%:** Sau khi bù trừ, độ chênh lệch giữa lượng Thiếu và lượng Thừa `(SL Thiếu - SL Thừa)` phải bằng 0 (dung sai <= 0.01 kg).
- **Kết quả:** Hiển thị danh sách các mã hàng mà siêu thị tự cấn trừ được 100% nội bộ. Hiển thị song song `Mã chuyển hàng thiếu` và `Mã chuyển hàng thừa`.

### Bước 2: Khớp Nội Bộ Một Phần
- **Điều kiện:** Tương tự Bước 1, nhưng độ chênh lệch giữa lượng Thiếu và lượng Thừa lớn hơn 0.01 kg.
- **Tính toán:** Hệ thống vẫn cấn trừ tối đa lượng khả dụng. 
- **Kết quả:** Ghi nhận số lượng đã cấn trừ. Phần dư hoặc thiếu dôi ra (`Remaining_Shortage`, `Remaining_Surplus`) sẽ được chuyển xuống Bước 3.

### Bước 3: Khớp Chéo Liên ST 1-1
- **Điều kiện:** Lấy phần số lượng Thiếu và Thừa còn sót lại từ Bước 1 và 2. Tìm kiếm các Siêu thị khác nhau có báo Thiếu và báo Thừa cho cùng 1 Mã hàng.
- **Thuật toán Ghép Cặp (Matching):**
  1. Chỉ ghép cặp các siêu thị có lượng Thiếu và Thừa **bằng nhau y hệt** (dung sai <= 0.01 kg).
  2. Tính toán **Khoảng cách Vị trí (Distance)**: `Khoảng cách = |Vị trí ST Thừa - Vị trí ST Thiếu|` dựa vào file Layout.
  3. Chọn siêu thị báo Thiếu có khoảng cách **Gần Nhất** với siêu thị báo Thừa để ghép cặp (ưu tiên giải quyết hàng lộn trên cùng 1 xe / cùng tuyến).
  4. Đánh giá xác suất: 
     - *Rất cao (Vị trí kề nhau)*: Khoảng cách <= 5.
     - *Trung bình (Cùng khu)*: Khoảng cách <= 15.
     - *Thấp (Trùng hợp số lượng)*: Khoảng cách > 15 hoặc không có Vị trí.
- **Kết quả:** Các cặp siêu thị được ghép với nhau. Trừ đi lượng Thiếu/Thừa đã khớp. Phần còn lại chuyển xuống các bước sau.

### Bước 4: Tổng Dư ≥ Tổng Thiếu
- **Điều kiện:** Thống kê tổng số lượng Thừa và Thiếu (sau khi trừ hao ở Khớp nội bộ) cho từng Mã hàng trên toàn bộ hệ thống siêu thị.
- **Tiêu chí:** Chỉ lấy các Mã hàng có `Tổng Thừa >= Tổng Thiếu` (và Tổng Thừa > 0).
- **Ý nghĩa:** Khoanh vùng các mặt hàng đang có xu hướng dư dả tổng thể (lượng nhận thực tế lớn hơn hoặc bằng lượng xuất trên hệ thống), đảm bảo không bị thất thoát ở khía cạnh tổng cục.

### Bước 5: Chỉ Ghi Nhận Thiếu Ròng
- **Điều kiện:** Các lượng Thiếu của siêu thị mà sau khi chạy qua Bước 1, 2, 3 vẫn **không thể tìm thấy** siêu thị nào báo Thừa để cấn trừ.
- **Ý nghĩa:** Đây là số lượng hàng hóa thực sự bị mất mát / thiếu hụt mà không có lý do. Đây là con số cuối cùng dùng để xử lý đền bù hoặc phạt.

### Bước 6: Chỉ Ghi Nhận Thừa Ròng
- **Điều kiện:** Các lượng Thừa của siêu thị mà sau khi chạy qua Bước 1, 2, 3 vẫn **không có** siêu thị nào báo Thiếu để cấn trừ.
- **Ý nghĩa:** Kho/DC xuất dư hàng đi mà hệ thống không ghi nhận, là con số Thừa thực tế trên toàn mạng lưới siêu thị.

---
> [!TIP]
> Thuật toán này đã được gỡ bỏ ràng buộc khắt khe về "Phiếu chuyển hàng", giúp phát hiện 100% các ca cấn trừ nội bộ dù siêu thị sử dụng mã phiếu thiếu và mã phiếu thừa khác nhau (phiếu MF01 vs Phiếu Kho Dư ảo). Mọi mã phiếu liên quan đều được nối (join) và hiển thị song song ở các bảng kết quả để người dùng dễ dàng tra soát.
