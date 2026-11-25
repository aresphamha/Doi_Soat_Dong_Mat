"""
Hệ thống cấu hình & hằng số dùng chung cho Dashboard Đối Soát ĐÔNG MÁT.
"""

# 1. URL & Dữ liệu nguồn Google Sheet
GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/edit?gid=1422896115#gid=1422896115"
)

# 2. Cấu hình Cache & Tải dữ liệu
CACHE_TTL_SECONDS = 300  # Tự động nạp mới sau 5 phút nếu có người truy cập
REQUEST_TIMEOUT = 35

# 3. Phân nhóm ngành hàng chính
PRODUCT_GROUPS = ["Tất cả", "MÁT", "ĐÔNG"]

# 4. Danh mục phân loại Lỗi chuẩn
ERROR_CATEGORIES = [
    "DC giao thiếu",
    "DC thao tác sai",
    "DC pick sai",
    "Hao hụt",
    "ST nhập thiếu",
    "Không đạt nhiệt độ",
    "DC giao bù",
    "Hư hỏng",
    "VT giao sai điểm",
    "Lỗi hệ thống",
    "ST kiểm sai QT",
    "ST thông tin sai/không phản hồi"
]

# 5. Bảng màu & Giao diện hiện đại (Theme Tokens)
THEME_COLORS = {
    "primary": "#0284c7",       # Ocean Blue
    "primary_dark": "#0369a1",
    "secondary": "#6366f1",     # Indigo
    "accent": "#f59e0b",        # Amber
    "success": "#10b981",       # Emerald Green
    "danger": "#ef4444",        # Rose Red
    "warning": "#f97316",       # Orange
    "info": "#06b6d4",          # Cyan
    "bg_dark": "#0f172a",       # Slate Dark
    "bg_card": "#ffffff",
    "border": "#e2e8f0",
    "text_main": "#1e293b",
    "text_muted": "#64748b"
}

# 6. Danh sách các cột số cần chuẩn hóa
NUMERIC_COLUMNS = [
    "Số lượng chuyển",
    "Số lượng nhận",
    "Chênh lệch",
    "Hạo hụt tự nhiên",
    "SL trả tồn về ST",
    "SL chênh lệch CXD",
    "% Hao hụt",
    "Giá nhập \n( -VAT)",
    "Giá nhập (-VAT)",
    "Tổng GT",
    "Tổng hao hụt",
    "Tổng ST",
    "Tổng kho",
    "Tổng chưa xác định"
]
