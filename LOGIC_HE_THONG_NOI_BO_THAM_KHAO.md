# 📖 QUY CHUẨN 13 CỘT CỐT LÕI TỪ FILE PHIẾU CHUYỂN (PT)
## VÀ CÔNG THỨC TÍNH CHÊNH LỆCH ĐỐI SOÁT SCM

> **Công thức cốt lõi:**  
> $$\text{CHÊNH LỆCH} = \text{CỘT K (Số lượng chuyển)} - \text{CỘT L (Số lượng nhận)}$$

---

## 📋 DANH SÁCH CHI TIẾT 13 CỘT CẦN QUAN TÂM (TRONG TỔNG 41 CỘT)

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

---

## 🔄 QUY TRÌNH PHỐI HỢP VẬN HÀNH GIỮA HK VÀ PT:

1. **Bước 1 (Cổng kiểm tra điều kiện bên HK):**  
   Vào **`DS phiếu hậu kiểm`** để kiểm tra xem các siêu thị **đã hoàn thành hậu kiểm hết 100% chưa** (không còn phiếu tồn ở tab *`Cần hậu kiểm`*).
   
2. **Bước 2 (Xuất dữ liệu chính thức bên PT):**  
   Sau khi HK đã hoàn tất ➡️ Vào **`DS phiếu chuyển`**, lọc kho `FZ02 + CL02`, chọn ngày cần đối soát và bấm **`[Xuất file]`** để tải file 41 cột về.
   
3. **Bước 3 (Tính toán chênh lệch):**  
   Hệ thống trích xuất 13 cột: **A, C, D, H, I, J, K, L, Q, S, T, AE, AF** và áp dụng công thức:  
   $$\text{Chênh Lệch} = \text{Cột K} - \text{Cột L}$$

---

## 📊 KẾT QUẢ NGÀY 27/08/2026 TỪ FILE `transfer_30082026-020035.xlsx`:

* **Kho Mát (Chill):** Chuyển `107.613,00` | Nhận `106.502,62` | **Lệch: `1.110,38`** *(470 dòng lệch / 223 phiếu PT)*.
* **Kho Đông (Frozen):** Chuyển `15.936,00` | Nhận `15.008,00` | **Lệch: `928,00`** *(80 dòng lệch / 77 phiếu PT)*.
* 🌟 **TỔNG CỘNG ĐÔNG + MÁT:** Chuyển **`123.549,00`** | Nhận **`121.510,62`** | **Tổng Lệch (K - L): `2.038,38`** *(550 dòng lệch / 300 phiếu PT)*.
