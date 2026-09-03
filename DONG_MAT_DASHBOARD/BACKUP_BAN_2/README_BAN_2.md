# LƯU TRỮ MÃ NGUỒN BẢN 2 (BACKUP_BAN_2)
Thời điểm lưu: 2026-08-30 00:32:00

## Danh sách thành phần đã lưu trong BẢN 2:
1. `generate_web_report.py`: Script sinh toàn bộ dữ liệu báo cáo HTML, nén JS tách theo từng ngày (lazy-load), chuẩn hóa cột AD-AG, logic tính toán lệch.
2. `dashboard_template.html`: Giao diện Dashboard Web tương tác thời gian thực, 11 biểu đồ, phân tích Cross-Tab, bộ lọc đa năng, popup xem chi tiết ngày và chi tiết case DC.
3. `Bao_Cao_Doi_Soat_Dong_Mat_Hang_Ngay.html`: File báo cáo hoàn chỉnh được build sẵn.
4. `app.py`: Phiên bản Streamlit Dashboard.
5. Thư mục `analytics/`: Các mô đun phân tích threshold, KPI metrics, hierarchy analysis, claim analytics.
6. Thư mục `data/`: `data_loader.py`, `data_processor.py` (xử lý dữ liệu chuẩn hóa 4 cột AD-AG).
7. Thư mục `exports/`, `reconciliation/`, `ui/`, `config/`: Toàn bộ các module hỗ trợ dashboard.
8. Thư mục `daily_details/` & `daily_records.js`: Dữ liệu chi tiết từng ngày và danh sách các ngày đối soát.
9. Các file khởi chạy `.bat`: `Cap_Nhat_Bao_Cao_Web.bat`, `Chay_Dashboard_Dong_Mat.bat`, `requirements.txt`.

## Cách khôi phục khi cần:
- **Cách 1**: Chỉ cần nhắn cho AI trợ lý: `"khôi phục backup bản 2"` hoặc `"quay về bản 2"`.
- **Cách 2**: Chạy lệnh terminal:
  ```bash
  python "g:/My Drive/Đối soát SCM/DONG_MAT_DASHBOARD/BACKUP_BAN_2/restore_ban_2.py"
  ```
