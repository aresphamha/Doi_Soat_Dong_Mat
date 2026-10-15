# -*- coding: utf-8 -*-
"""
MODULE 6: CHI TIẾT PHIẾU CHUYỂN KHO KHÔ (FGA10101 _ BÌNH THẮNG)
Tự động lọc các phiếu chuyển thực tế từ FGA10101 đang treo đến hết D-1,
kết xuất ảnh bảng Gradient và spam nhắc nhở vào các nhóm Telegram DC.
"""

import os
import sys

from .common import TOOLS_BASE_DIR

async def run(target_date=None, dry_run=False, stores=None):
    print("\n=======================================================")
    print("📦 [MODULE KHO KHÔ] BẮT ĐẦU CHẠY TOOL: CHI TIẾT KHO KHÔ FGA10101...")
    print("=======================================================")
    
    if TOOLS_BASE_DIR not in sys.path:
        sys.path.insert(0, TOOLS_BASE_DIR)
        
    try:
        from Spam_Phieu_Chi_Tiet_Kho_Kho import run_spam_chi_tiet_kho_kho
        await run_spam_chi_tiet_kho_kho(target_date=target_date, dry_run=dry_run, stores=stores)
    except Exception as e:
        print(f"❌ [LỖI THỰC THI TOOL CHI TIẾT KHO KHÔ]: {e}")
