# -*- coding: utf-8 -*-
"""
File chạy nhanh Tool Hậu Kiểm Kho Khô FGA10101.
Được liên kết trực tiếp với modules/tool_hau_kiem_kho_kho.py để đảm bảo chuẩn hóa mã nguồn.
"""
import os
import sys
import asyncio

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import argparse
from modules.tool_hau_kiem_kho_kho import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-date', '--date', type=str, default=None, dest='date')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--stores', type=str, default=None)
    parser.add_argument('--force', '--resend', action='store_true')
    args = parser.parse_args()
    asyncio.run(run(target_date=args.date, dry_run=args.dry_run, stores=args.stores, force=args.force))

