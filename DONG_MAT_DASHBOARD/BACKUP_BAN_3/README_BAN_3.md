# LƯU TRỮ MÃ NGUỒN BẢN 3 (BACKUP_BAN_3)
Thời điểm lưu: 2026-09-17 22:59:46

## 1. Trạng thái Web tại Bản 3:
- **Trang web chính**: `index.html` (Dung lượng: ~6.5 MB, 10.955 dòng).
- **KPI Tổng quan (Tab 1)**:
  - Tổng chênh lệch: `6.967.907.575 đ` (~6.96 tỷ).
  - Lệch số lượng: `1.815.111.411`
  - Đã xử lý: `3.085.922.753 đ` (44.3%)
  - Đang xử lý: `3.879.467.288 đ` (55.7%)
  - Màu sắc: Phông nền Dark Slate dịu mắt (`#161f2e` / `#202b3d`), tiêu đề sặc sỡ nổi bật.
- **Tab 2**: Đối soát chênh lệch & Tiến độ (Master table, Value table, Quantity table, Siêu thị ưu tiên xử lý).
- **Tab 3**: Phân tích đối soát Trung tâm phân phối (DC Cross-Tab, DC Summary, DC Detail).
- **Tab 4**: Telegram SCM (574 nhóm tổng hợp, 26 nhóm khẩn cấp, xuất file txt Chat ID theo từng nhóm, chat drawer phản hồi trực tiếp).
- **Tab 5**: Trạm điều khiển Hybrid Runner (18 công cụ, chọn ngày, chọn chế độ Cloud / Local Runner cổng 5055, Dry-run, Live streaming console log, 25 thẻ công cụ 1-click execution).

## 2. Danh sách thành phần đã lưu:
1. `index.html` & `Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html`: Bản web đối soát hoàn chỉnh đang chạy online.
2. `dashboard_template.html`: Template gốc chứa cấu trúc 5 Tab và 101 hàm JavaScript.
3. `generate_web_report.py`: Script đọc template, tính toán 4 bundles và bơm dữ liệu sinh ra web.
4. `sync_telegram_groups.py` & `telegram_chat_server.py`: Module đồng bộ và backend chat Telegram.
5. `local_runner_service.py`: Local daemon service chạy tool offline ở máy trạm (cổng 5055).
6. `run_spam_tools.yml`: GitHub Actions Cloud Runner workflow chạy tự động trên GitHub.
7. `push_to_github.py`: Script tự động đẩy dữ liệu lên GitHub Pages.
8. Thư mục `daily_details/`: Chứa file `telegram_groups.js` (574 nhóm) và dữ liệu chi tiết từng ngày.
9. Thư mục `SPAM_PHIEU_CHUYEN/` & `TOOLS_DOI_SOAT/`: Toàn bộ các tool nghiệp vụ đối soát và xử lý phiếu chuyển.
10. Thư mục `analytics/`, `config/`, `data/`, `exports/`, `reconciliation/`, `ui/`: Các module phụ trợ hệ thống.
11. `restore_ban_3.py`: Script tự động khôi phục 100% về Bản 3 chỉ với 1 lệnh.

## 3. Cách khôi phục khi cần:
- **Cách 1**: Chỉ cần nhắn cho trợ lý AI: `"khôi phục backup bản 3"` hoặc `"quay về bản 3"`.
- **Cách 2**: Chạy lệnh terminal:
  ```bash
  python "C:/Users/Thu Ha/Doi_Soat_Dong_Mat/DONG_MAT_DASHBOARD/BACKUP_BAN_3/restore_ban_3.py"
  ```
  hoặc trên Google Drive:
  ```bash
  python "g:/My Drive/Đối soát SCM/DONG_MAT_DASHBOARD/BACKUP_BAN_3/restore_ban_3.py"
  ```
