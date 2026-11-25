# -*- coding: utf-8 -*-
"""
File chạy nhanh Tool Hậu Kiểm Đông Mát.
Được liên kết trực tiếp với modules/tool_hau_kiem_dong_mat.py để đảm bảo chuẩn hóa mã nguồn.
"""
import os
import sys
import asyncio

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from modules.tool_hau_kiem_dong_mat import run

if __name__ == "__main__":
    asyncio.run(run())
