# 📖 QUY CHUẨN TRÍCH XUẤT DỮ LIỆU TỪ HỆ THỐNG VẬN HÀNH (PORTAL)
## VÀ CÔNG THỨC TÍNH CHÊNH LỆCH ĐỐI SOÁT SCM ĐÔNG - MÁT

---

## 🔢 1. CÔNG THỨC TÍNH CHÊNH LỆCH CHUẨN:

> **📐 CÔNG THỨC TOÁN HỌC CỐT LÕI:**  
> **`CHÊNH LỆCH = CỘT K (Số lượng chuyển) − CỘT L (Số lượng nhận)`**
> 
> * **Nếu Chênh lệch > 0:** Kho giao thiếu / Siêu thị nhận thiếu.
> * **Nếu Chênh lệch < 0:** Kho giao dư / Siêu thị nhận dư.
> * **Nếu Chênh lệch = 0:** Giao nhận khớp 100%.

---

## 🎯 2. CÁC BỘ LỌC BẮT BUỘC TRÊN WEB PORTAL & QUY TẮC CHUẨN:

### 2.1 Bộ Lọc Trên Web Portal (`DS phiếu chuyển`):
Đường dẫn: **`Vận hành -> Chuyển hàng -> DS phiếu chuyển -> Bấm [Bộ lọc]`**
1. **Nơi chuyển:** Chọn **`CL02`** *(Kho Mát)* hoặc **`FZ02`** *(Kho Đông)*.
2. **Nơi nhận:** Chọn **`Tất cả siêu thị`** *(Chỉ lấy siêu thị có tiền tố `KFM_...`)*.
3. ⭐ **Là PT thùng rổ:** BẮT BUỘC CHỌN **`Không`** *(để loại bỏ 100% vỏ rổ, pallet rỗng)*.
4. **Thời gian:** Chọn khoảng ngày cần đối soát ➔ Bấm **`[Áp dụng]`** ➔ Bấm **`[Xuất file]`** để tải file 41 cột về (`transfer_DDMMYYYY-HHMMSS.xlsx`).

### 2.2 Quy Tắc Tính Toán Nghiệp Vụ Chuẩn:
* **Quy tắc Số Nhận = -1:** Nếu trên hệ thống ghi nhận `SL Nhận = -1` (hoặc âm), tự động chuyển thành `0` và `Chênh lệch = SL Chuyển`.
* **Loại bỏ Quét Thừa:** Chỉ lấy các dòng phát sinh thiếu: `SL Chuyển >= SL Nhận` và `Chênh Lệch > 0`.
* **Dời Ngày Kho Đông:** Phiếu ngày 01/08 và 03/08 được gán về đúng ngày siêu thị nhận hàng thực tế (02/08 và 04/08).
* **Khử Trùng Lặp x2:** Deduplicate theo `(Mã phiếu, Mã hàng, Chi nhánh)` đối với các đợt bị sync đúp.
* 💾 **Bảng Database Tổng Hợp Chuẩn:** `krc_dm_discrepancies_ha_pham` trên StarRocks database `kfm_scm`.

---

## 🔄 3. QUY TRÌNH VẬN HÀNH PHỐI HỢP GIỮA HK VÀ PT:

1. 🛡️ **BƯỚC 1: CỔNG KIỂM TRA ĐIỀU KIỆN (BÊN HK)**  
   Vào màn hình **`DS phiếu hậu kiểm`** để kiểm tra xem các siêu thị **đã hoàn thành hậu kiểm hết 100% chưa** (không còn phiếu tồn ở tab *`Cần hậu kiểm`*).

2. 📦 **BƯỚC 2: XUẤT FILE DATA CHÍNH THỨC (BÊN PT)**  
   Sau khi HK đã hoàn tất ➔ Vào màn hình **`DS phiếu chuyển`**, lọc kho **`FZ02 + CL02`**, chọn ngày cần đối soát và bấm **`[Xuất file]`** để tải file 41 cột về.

3. 🔢 **BƯỚC 3: TRÍCH XUẤT 13 CỘT VÀ TÍNH TOÁN**  
   Hệ thống tự động lọc 13 cột: **A, C, D, H, I, J, K, L, Q, S, T, AE, AF** và lấy **`Cột K − Cột L`** để sinh ra số liệu chênh lệch chính xác 100%!

---

## 📋 4. DANH SÁCH CHI TIẾT 13 CỘT CỐT LÕI (TRONG TỔNG 41 CỘT):

| Ký Hiệu Cột | Thứ Tự | Tên Cột Trên File Excel | Ý Nghĩa Nghiệp Vụ Cốt Lõi |
| :---: | :---: | :--- | :--- |
| **Cột A** | Cột 1 | **`Ngày chuyển hàng`** | Ngày phát sinh chuyển hàng (`27/08/2026`). |
| **Cột C** | Cột 3 | **`Chi nhánh chuyển`** | Kho xuất hàng (`Chill - Miền Đông...` / `Frozen - Miền Đông...`). |
| **Cột D** | Cột 4 | **`Chi nhánh nhận`** | Tên cửa hàng siêu thị nhận hàng (`KFM_HCM_BTA...`). |
| **Cột H** | Cột 8 | **`Mã hàng`** | Mã Barcode SKU sản phẩm (`8938503131810`). |
| **Cột I** | Cột 9 | **`Tên hàng`** | Tên đầy đủ của sản phẩm. |
| **Cột J** | Cột 10 | **`Đơn vị tính`** | Đơn vị tính (`HỘP`, `KG`, `GÓI`...). |
| **⭐ Cột K** | **Cột 11** | **`Số lượng chuyển`** | **SỐ LƯỢNG XUẤT KHO CHÍNH THỨC**. |
| **⭐ Cột L** | **Cột 12** | **`Số lượng nhận`** | **SỐ LƯỢNG SIÊU THỊ THỰC NHẬN**. |
| **Cột Q** | Cột 17 | **`Mã chuyển hàng`** | Mã Phiếu Chuyển gốc (`PT1727704`...). |
| **Cột S** | Cột 19 | **`Mã thùng`** | Barcode mã thùng rổ/pallet (`TRBA231190724`). |
| **Cột T** | Cột 20 | **`Trạng thái`** | Trạng thái phiếu (`Đã nhận`, `Đang chuyển`...). |
| **Cột AE** | Cột 31 | **`Cần hậu kiểm`** | Đánh dấu có cần hậu kiểm không (`Có` / `Không`). |
| **Cột AF** | Cột 32 | **`Đã hậu kiểm`** | Đánh dấu đã hậu kiểm xong chưa (`Có` / `Không`). |
