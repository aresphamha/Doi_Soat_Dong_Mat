# -*- coding: utf-8 -*-
"""
Hệ thống cấu hình & hằng số dùng chung cho Dashboard ĐỐI SOÁT ĐÔNG MÁT.
"""

# 1. URL & Dữ liệu nguồn Google Sheet
# 1.1 Link Google Sheet Gốc (Đông Mát)
GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.2 Link Google Sheet Đối Soát Thịt Cá Tháng 7 + 8 (KFM - SCF)
GOOGLE_SHEET_THIT_CA_URL = (
    "https://docs.google.com/spreadsheets/d/1LI_cqLh_-k8eJzMVHtQr52X1xwLT9U5NeTYhW6NgQlU"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_THIT_CA_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1LI_cqLh_-k8eJzMVHtQr52X1xwLT9U5NeTYhW6NgQlU"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.3 Link Google Sheet Đối Soát Thịt Cá 28.08 - 09.26 (KFM - SCF) MỚI
GOOGLE_SHEET_THIT_CA_NEW_URL = (
    "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_THIT_CA_NEW_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to"
    "/edit?gid=1422896115#gid=1422896115"
)

GOOGLE_SHEETS_SOURCE_MAP = {
    "dong_mat_goc": {
        "title": "Đối soát ĐÔNG MÁT (Gốc)",
        "csv_url": GOOGLE_SHEET_URL,
        "web_url": GOOGLE_SHEET_WEB_URL,
    },
    "thit_ca_t7_t8": {
        "title": "Đối soát thịt cá tháng 7 + 8 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_THIT_CA_URL,
        "web_url": GOOGLE_SHEET_THIT_CA_WEB_URL,
    },
    "thit_ca_2808_0926": {
        "title": "Đối soát thịt cá tháng 28.08 - 09.26 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_THIT_CA_NEW_URL,
        "web_url": GOOGLE_SHEET_THIT_CA_NEW_WEB_URL,
    }
}

CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT = 35
PRODUCT_GROUPS = ["Tất cả", "THỊT CÁ", "MÁT", "ĐÔNG"]

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

THEME_COLORS = {
    "primary": "#0284c7",
    "primary_dark": "#0369a1",
    "secondary": "#6366f1",
    "accent": "#f59e0b",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#f97316",
    "info": "#06b6d4",
    "bg_dark": "#0f172a",
    "bg_card": "#ffffff",
    "border": "#e2e8f0",
    "text_main": "#1e293b",
    "text_muted": "#64748b"
}

NUMERIC_COLUMNS = [
    "Số lượng chuyển",
    "Số lượng nhận",
    "Chênh lệch",
    "Hao hụt tự nhiên",
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
