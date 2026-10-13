# -*- coding: utf-8 -*-
"""
MODULE 7: HẬU KIỂM KHO KHÔ (FGA10101 _ BÌNH THẮNG)
Tự động lọc các phiếu Hậu Kiểm từ FGA10101 đang treo đến hết D-1,
kết xuất ảnh bảng Gradient và spam nhắc nhở vào các nhóm Telegram DC.
"""

import os
import sys

from .common import TOOLS_BASE_DIR

async def run(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("⚖️ [MODULE HẬU KIỂM KHO KHÔ] BẮT ĐẦU CHẠY TOOL: HẬU KIỂM KHO KHÔ FGA10101...")
    print("=======================================================")
    
    if TOOLS_BASE_DIR not in sys.path:
        sys.path.insert(0, TOOLS_BASE_DIR)
        
    try:
        from Spam_Phieu_Hau_Kiem_Kho_Kho import run_spam_hau_kiem_kho_kho
        await run_spam_hau_kiem_kho_kho(target_date=target_date, dry_run=dry_run)
    except Exception as e:
        print(f"❌ [LỖI THỰC THI TOOL HẬU KIỂM KHO KHÔ]: {e}")
