# QUY TRÌNH & LOGIC ĐỐI SOÁT ĐÔNG MÁT (6 ĐIỀU KIỆN)

Tài liệu này mô tả chi tiết quy trình xử lý và logic đối soát số liệu hàng dư - thiếu của nhóm hàng ĐÔNG MÁT.

---

## I. NGUỒN DỮ LIỆU ĐẦU VÀO
1. **Dữ liệu Thiếu (Google Sheet):** Lấy từ sheet báo cáo của ngày đối soát. Xác định số lượng thiếu qua cột `Chênh lệch` (chỉ lấy giá trị > 0).
2. **Dữ liệu Dư (Excel):** Lấy từ file báo cáo dư tương ứng của ngày đối soát. Xác định số lượng dư qua cột `Số lượng chuyển` (lấy giá trị tuyệt đối).
3. **Dữ liệu Layout:** Sử dụng file `Layout MD.xlsx` (Sheet `layout Mát`) để xác định tọa độ (`VỊ trí`) của từng siêu thị nhằm tính toán độ lệch địa lý khi giao nhận.

---

## II. CHI TIẾT LOGIC 6 ĐIỀU KIỆN (6 SHEETS)

### SHEET 1: Khớp nội bộ 100%
* **Mô tả:** Khớp số lượng dư và thiếu phát sinh tại **cùng một siêu thị** đối với **cùng một mã hàng**.
* **Điều kiện:**
  * Trùng `Chi nhánh nhận` (Siêu thị) và trùng `Mã hàng`.
  * Độ lệch số lượng tuyệt đối giữa Dư và Thiếu không quá `0.01 kg`:
    $$\left| \text{SL Dư} - \text{SL Thiếu} \right| \le 0.01$$
* **Thông tin lỗi:** Gán cứng lỗi là `"DC thao tác sai"`.

---

### SHEET 2: Khớp nội bộ một phần
* **Mô tả:** Có phát sinh cả dư và thiếu tại **cùng một siêu thị** đối với **cùng một mã hàng** nhưng số lượng lệch nhau đáng kể.
* **Điều kiện:**
  * Trùng `Chi nhánh nhận` (Siêu thị) và trùng `Mã hàng`.
  * Độ lệch số lượng tuyệt đối lớn hơn `0.01 kg`:
    $$\left| \text{SL Dư} - \text{SL Thiếu} \right| > 0.01$$
* **Cách xử lý:** Hệ thống lấy phần nhỏ hơn làm lượng khớp nội bộ (sẽ được trừ đi trước khi tính toán khớp chéo). Phần chênh lệch còn lại được đưa vào tính toán cho các bước sau.
* **Thông tin lỗi:** Gán cứng lỗi là `"DC thao tác sai"`.

---

### SHEET 3: Khớp chéo liên siêu thị 1-1
* **Mô tả:** Khớp số lượng dư của siêu thị này với số lượng thiếu của siêu thị khác đối với cùng một mã hàng.
* **Điều kiện & Ưu tiên:**
  * Khác `Chi nhánh nhận` nhưng trùng `Mã hàng`.
  * Lượng dư còn lại của siêu thị $A$ khớp với lượng thiếu còn lại của siêu thị $B$ (lệch không quá `0.01 kg`).
  * **Quy tắc ưu tiên Layout:** Nếu một siêu thị Thừa có thể ghép cặp với nhiều siêu thị Thiếu có cùng lượng lệch, hệ thống sẽ tra cứu tọa độ từ file Layout và chọn siêu thị có khoảng cách vị trí ngắn nhất để ghép đôi:
    $$\text{Độ lệch vị trí} = \left| \text{Vị trí ST Dư} - \text{Vị trí ST Thiếu} \right| \rightarrow \text{Tối thiểu}$$
* **Phân loại khả năng nhầm:**
  * Độ lệch vị trí $\le 5$: `"Rất cao (Vị trí kề nhau)"`
  * Độ lệch vị trí $\le 15$: `"Trung bình (Cùng khu)"`
  * Độ lệch vị trí $> 15$: `"Thấp (Trùng hợp số lượng)"`
  * Không có dữ liệu vị trí: `"Không xác định (Thiếu Layout)"`
* **Thông tin lỗi:** Gán cứng lỗi là `"DC giao nhầm CH"`.

---

### SHEET 4: Tổng Dư >= Tổng Thiếu
* **Mô tả:** Nhóm các mã hàng có tổng lượng dư trên toàn hệ thống lớn hơn hoặc bằng tổng lượng thiếu (sau khi đã loại bỏ các dòng đã khớp ở Sheet 1, 2, 3).
* **Đặc điểm:** Hệ thống gom nhóm và tính tổng lượng thừa ròng còn lại để bù đắp cho lượng thiếu của các cửa hàng khác nhau trên diện rộng.

---

### SHEET 5: Chỉ ghi nhận Thiếu ròng
* **Mô tả:** Danh sách các siêu thị bị thiếu hàng thực tế đối với các mã hàng sau khi đã chạy qua toàn bộ các bước khớp chéo và bù trừ ở trên mà vẫn không tìm thấy lượng dư đối ứng.

---

### SHEET 6: Chỉ ghi nhận Thừa ròng
* **Mô tả:** Danh sách các siêu thị nhận dư hàng thực tế đối với các mã hàng sau khi đã chạy qua toàn bộ các bước khớp chéo và bù trừ ở trên mà vẫn không tìm thấy lượng thiếu đối ứng.
