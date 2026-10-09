# -*- coding: utf-8 -*-
"""
Hệ thống cấu hình & hằng số dùng chung cho Dashboard ĐỐI SOÁT ĐÔNG MÁT & THỊT CÁ.
"""

# 1. URL & Dữ liệu nguồn Google Sheet

# --- NHÓM 1: ĐỐI SOÁT ĐÔNG - MÁT ---
# 1.1 Sheet Đối soát ĐÔNG MÁT (KFM - SCF) tháng 28.07 - 09.2026 (Gốc)
GOOGLE_SHEET_DONG_MAT_T7_T9_URL = (
    "https://docs.google.com/spreadsheets/d/1X9qz2tznJhctfdmFcyhPol6qnnR7igDdvcwzvTUZRlg"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_DONG_MAT_T7_T9_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1X9qz2tznJhctfdmFcyhPol6qnnR7igDdvcwzvTUZRlg"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.2 Sheet Đối soát MÁT (KFM - SCF) tháng 10
GOOGLE_SHEET_MAT_T10_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_MAT_T10_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.3 Sheet Đối soát ĐÔNG (KFM - SCF) tháng 10
GOOGLE_SHEET_DONG_T10_URL = (
    "https://docs.google.com/spreadsheets/d/1i-tjKSZMnZ4YZUAA7FVRFbyvr0PcvF_gosJvJZT2ARA"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_DONG_T10_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1i-tjKSZMnZ4YZUAA7FVRFbyvr0PcvF_gosJvJZT2ARA"
    "/edit?gid=1422896115#gid=1422896115"
)


# --- NHÓM 2: ĐỐI SOÁT THỊT CÁ ---
# 1.4 Sheet Đối Soát Thịt Cá Tháng 7 + 8 (KFM - SCF)
GOOGLE_SHEET_THIT_CA_T7_T8_URL = (
    "https://docs.google.com/spreadsheets/d/1LI_cqLh_-k8eJzMVHtQr52X1xwLT9U5NeTYhW6NgQlU"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_THIT_CA_T7_T8_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1LI_cqLh_-k8eJzMVHtQr52X1xwLT9U5NeTYhW6NgQlU"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.5 Sheet Đối Soát Thịt Cá 28.08 - 09.26 (KFM - SCF)
GOOGLE_SHEET_THIT_CA_2808_0926_URL = (
    "https://docs.google.com/spreadsheets/d/1X6x-VeSon0e23l8cNc_iQ2YOBNqzojeiTRZDGPiYUt0"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_THIT_CA_2808_0926_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1X6x-VeSon0e23l8cNc_iQ2YOBNqzojeiTRZDGPiYUt0"
    "/edit?gid=1422896115#gid=1422896115"
)

# 1.6 Sheet Đối Soát Thịt Cá Tháng 10.26 (KFM - SCF)
GOOGLE_SHEET_THIT_CA_T10_URL = (
    "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to"
    "/export?format=csv&gid=1422896115"
)
GOOGLE_SHEET_THIT_CA_T10_WEB_URL = (
    "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to"
    "/edit?gid=1422896115#gid=1422896115"
)

# Backward-compatibility alias constants
GOOGLE_SHEET_URL = GOOGLE_SHEET_DONG_MAT_T7_T9_URL
GOOGLE_SHEET_WEB_URL = GOOGLE_SHEET_DONG_MAT_T7_T9_WEB_URL
GOOGLE_SHEET_THIT_CA_URL = GOOGLE_SHEET_THIT_CA_T7_T8_URL
GOOGLE_SHEET_THIT_CA_WEB_URL = GOOGLE_SHEET_THIT_CA_T7_T8_WEB_URL
GOOGLE_SHEET_THIT_CA_NEW_URL = GOOGLE_SHEET_THIT_CA_T10_URL
GOOGLE_SHEET_THIT_CA_NEW_WEB_URL = GOOGLE_SHEET_THIT_CA_T10_WEB_URL

GOOGLE_SHEETS_SOURCE_MAP = {
    "dong_mat_t7_t9": {
        "title": "Đối soát ĐÔNG MÁT 28.07 - 09.2026 (Gốc)",
        "csv_url": GOOGLE_SHEET_DONG_MAT_T7_T9_URL,
        "web_url": GOOGLE_SHEET_DONG_MAT_T7_T9_WEB_URL,
        "group": "ĐÔNG MÁT"
    },
    "mat_t10": {
        "title": "Đối soát MÁT tháng 10 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_MAT_T10_URL,
        "web_url": GOOGLE_SHEET_MAT_T10_WEB_URL,
        "group": "MÁT"
    },
    "dong_t10": {
        "title": "Đối soát ĐÔNG tháng 10 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_DONG_T10_URL,
        "web_url": GOOGLE_SHEET_DONG_T10_WEB_URL,
        "group": "ĐÔNG"
    },
    "thit_ca_t7_t8": {
        "title": "Đối soát thịt cá tháng 7 + 8 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_THIT_CA_T7_T8_URL,
        "web_url": GOOGLE_SHEET_THIT_CA_T7_T8_WEB_URL,
        "group": "THỊT CÁ"
    },
    "thit_ca_2808_0926": {
        "title": "Đối soát thịt cá tháng 28.08 - 09.26 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_THIT_CA_2808_0926_URL,
        "web_url": GOOGLE_SHEET_THIT_CA_2808_0926_WEB_URL,
        "group": "THỊT CÁ"
    },
    "thit_ca_t10": {
        "title": "Đối soát thịt cá tháng 10.26 (KFM - SCF)",
        "csv_url": GOOGLE_SHEET_THIT_CA_T10_URL,
        "web_url": GOOGLE_SHEET_THIT_CA_T10_WEB_URL,
        "group": "THỊT CÁ"
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
