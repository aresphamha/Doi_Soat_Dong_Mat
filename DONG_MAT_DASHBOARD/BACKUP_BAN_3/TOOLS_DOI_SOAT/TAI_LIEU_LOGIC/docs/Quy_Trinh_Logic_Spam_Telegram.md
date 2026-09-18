# QUY TRÌNH THIẾT LẬP VÀ LOGIC HOẠT ĐỘNG CỦA HỆ THỐNG SPAM TELEGRAM

Tài liệu này mô tả toàn bộ logic và các bước cần thiết để xây dựng một hệ thống tự động gửi tin nhắn báo cáo chênh lệch/đối soát đến hàng loạt nhóm Telegram của siêu thị.

---

## GIAI ĐOẠN 1: CHUẨN BỊ NỀN TẢNG (Chỉ làm 1 lần)

### 1. Tạo Bot Telegram và Lấy Token
Để gửi tin nhắn tự động, bạn cần một Bot Telegram.
- Tìm @BotFather trên Telegram.
- Nhắn lệnh `/newbot`, nhập tên hiển thị và username.
- Lấy `Bot Token` (ví dụ: 8810108114:AAHFy...). Đây là chìa khóa để code điều khiển Bot.

### 2. Thiết lập Nhóm Siêu Thị và Cấp Quyền
- Tạo các nhóm (Groups/Supergroups) cho từng siêu thị.
- Mời Bot vừa tạo vào từng nhóm.
- Phải cấp quyền Gửi tin nhắn (Send Messages) hoặc cho Bot làm Admin.

### 3. Thu Thập Chat ID và Lập Bản Đồ
- Sử dụng tool lấy Chat ID (file 1_Lay_Chat_ID) để lấy mã số ID của tất cả các nhóm mà Bot đang tham gia (VD: -100123456789).
- Dán các Chat ID này vào file Excel trung tâm (VD: `Danh sách Siêu thị.xlsx`).
- Đảm bảo ánh xạ chính xác: Mã Siêu thị (ID ST) <---> Chat ID của siêu thị đó.

---

## GIAI ĐOẠN 2: CHUẨN BỊ NGUỒN DỮ LIỆU ĐỐI SOÁT

Nguồn dữ liệu (thường là Google Sheet) cần có cấu trúc chuẩn để tool đọc được:
1. Cột "Ngày" hoặc "Ngày chuyển hàng": Để tool biết chỉ lấy dữ liệu mới nhất hôm nay.
2. Cột "ID ST" hoặc "Chi nhánh nhận": Để tool biết gửi cho siêu thị nào.
3. Cột "Lỗi": Chứa điều kiện cần gửi cảnh báo (Ví dụ: "DC GIAO THIẾU").
4. Các thông tin chi tiết: Tên hàng, số lượng chuyển, số lượng nhận, chênh lệch...

---

## GIAI ĐOẠN 3: LOGIC HOẠT ĐỘNG CỦA TOOL SPAM (File Python)

Mỗi ngày khi chạy file `Chay_Tool_Spam.bat`, hệ thống sẽ chạy qua 5 bước sau:

### Bước 1: Tải và Làm sạch Dữ liệu
- Tự động truy cập link Google Sheet và tải dữ liệu mới nhất về file tạm (temp).
- Lọc theo cột Ngày: Chỉ giữ lại dữ liệu của ngày gần nhất.
- Lọc theo cột Lỗi: Chỉ giữ lại các dòng có chữ "DC GIAO THIẾU".

### Bước 2: Gom Nhóm Dữ Liệu (Group by)
- Dữ liệu thô đang nằm rải rác từng dòng (1 siêu thị có thể lỗi nhiều mặt hàng).
- Tool dùng lệnh Gom nhóm để gộp tất cả các mặt hàng bị lỗi của cùng 1 siêu thị lại thành một bảng dữ liệu rút gọn.

### Bước 3: Chuyển Đổi Dữ Liệu Thành Hình Ảnh
- Bảng dữ liệu rút gọn của từng siêu thị sẽ được style màu sắc, kẻ viền (ví dụ màu Xanh cho Rau Củ, màu Cam cho Đông Mát).
- Sử dụng thư viện biến đổi (dataframe_image) để chụp bảng này lại và lưu thành 1 file ảnh (temp_image.png).

### Bước 4: Soi Danh Bạ và Gửi Tin (Spam)
- Với mỗi siêu thị, tool dò mã ID ST vào file "Danh sách Siêu thị.xlsx" để tìm Chat ID.
- Nếu có Chat ID: Tool gửi lệnh qua Telegram API chứa lời chào + tag tên Quản lý (nếu có) + hình ảnh bảng dữ liệu.
- Sau mỗi lần gửi, tool nghỉ (sleep) khoảng 2 giây để tránh bị Telegram khóa vì spam quá tốc độ (lỗi Flood Wait 429).

### Bước 5: Báo Cáo Kết Quả
- Chạy xong toàn bộ danh sách, tool in ra báo cáo tổng kết trên màn hình:
  + Tổng số lượng siêu thị có phát sinh lỗi.
  + Số lượng gửi thành công.
  + Số lượng gửi thất bại (kèm lý do và danh sách các siêu thị bị xịt để check lại Chat ID).

---
*Lưu ý: Nếu một siêu thị gửi thất bại báo lỗi "Chat Not Found", có nghĩa là nhóm đã bị xóa, bị nâng cấp lên Supergroup khiến Chat ID thay đổi, hoặc Bot đã bị kích khỏi nhóm. Lúc này cần lấy lại Chat ID mới và cập nhật vào file Excel.*
