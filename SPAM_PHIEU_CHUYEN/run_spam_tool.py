# -*- coding: utf-8 -*-
"""
Hệ Thống Điều Khiển & Thực Thi Tự Động Toàn Bộ Công Cụ SCM (Cloud Runner & Local CLI)
Kiến trúc Module hóa: Mỗi phân hệ là 1 file con độc lập trong modules/
Tránh xung đột mã nguồn khi nhiều người cùng chỉnh sửa hoặc nâng cấp tính năng.
"""

import os
import sys
import argparse
import asyncio

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import các hàm dùng chung và cấu hình
from modules.common import (
    ROOT_DIR,
    TOOLS_BASE_DIR,
    execute_external_tool
)

# Import từng Module nghiệp vụ độc lập
from modules.tool_thit_ca import run as run_tool_thit_ca
from modules.tool_mat import run as run_tool_mat
from modules.tool_hau_kiem_rau import run as run_tool_hau_kiem_rau
from modules.tool_hau_kiem_thit_ca import run as run_tool_hau_kiem_thit_ca
from modules.tool_hau_kiem_dong_mat import run as run_tool_hau_kiem_dong_mat
from modules.tool_chi_tiet_kho_kho import run as run_tool_chi_tiet_kho_kho
from modules.tool_hau_kiem_kho_kho import run as run_tool_hau_kiem_kho_kho
from modules.tool_spam_tu_chon import run as run_tool_spam_tu_chon


# -------------------------------------------------------------
# CÁC HÀM CẦU NỐI ĐẾN TOOL NGOẠI VI (TOOLS_DOI_SOAT)
# -------------------------------------------------------------
async def run_tool_dong_mat_full(target_date=None, dry_run=False):
    print("\n=======================================================")
    print("❄️ BẮT ĐẦU CHẠY TOOL ĐỐI SOÁT ĐÔNG MÁT GỐC...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Doi_Soat_Dong_Mat.py")
    execute_external_tool(script_path)

async def run_tool_dong_mat_spam(target_date=None, dry_run=False, stores="ALL"):
    print("\n=======================================================")
    print("📨 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO ĐÔNG MÁT...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "2_Spam_Telegram.py")
    extra_args = []
    if dry_run: extra_args.append("--dry-run")
    if target_date: extra_args.extend(["--date", str(target_date)])
    if stores and str(stores).strip().upper() != "ALL": extra_args.extend(["--stores", str(stores).strip()])
    execute_external_tool(script_path, extra_args=extra_args)

async def run_tool_dong_spam(target_date=None, dry_run=False, stores="ALL"):
    print("\n=======================================================")
    print("❄️ BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO HÀNG ĐÔNG (THÁNG 10)...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "2_Spam_Telegram_Dong.py")
    extra_args = []
    if dry_run: extra_args.append("--dry-run")
    if target_date: extra_args.extend(["--date", str(target_date)])
    if stores and str(stores).strip().upper() != "ALL": extra_args.extend(["--stores", str(stores).strip()])
    execute_external_tool(script_path, extra_args=extra_args)

async def run_tool_lay_chat_id():
    print("\n=======================================================")
    print("🆔 BẮT ĐẦU CHẠY TOOL QUÉT & CẬP NHẬT CHAT ID TELEGRAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Lay_Chat_ID.py")
    execute_external_tool(script_path)

async def run_tool_dong_mat_nhom_dong():
    print("\n=======================================================")
    print("🧊 BẮT ĐẦU CHẠY TOOL ĐỐI SOÁT RIÊNG NHÓM ĐÔNG...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "1_Doi_Soat_Nhom_Dong.py")
    execute_external_tool(script_path)

async def run_tool_thit_ca_spam(target_date=None, dry_run=False, stores="ALL"):
    print("\n=======================================================")
    print("🥩 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO THỊT CÁ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "THIT_CA", "Tool_Spam", "2_Spam_Telegram.py")
    extra_args = []
    if dry_run: extra_args.append("--dry-run")
    if target_date: extra_args.extend(["--date", str(target_date)])
    if stores and str(stores).strip().upper() != "ALL": extra_args.extend(["--stores", str(stores).strip()])
    execute_external_tool(script_path, extra_args=extra_args)

async def run_tool_rau_cu_spam(target_date=None, dry_run=False, stores="ALL"):
    print("\n=======================================================")
    print("🥦 BẮT ĐẦU CHẠY TOOL SPAM BÁO CÁO RAU CỦ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "2_Spam_Telegram.py")
    extra_args = []
    if dry_run: extra_args.append("--dry-run")
    if target_date: extra_args.extend(["--date", str(target_date)])
    if stores and str(stores).strip().upper() != "ALL": extra_args.extend(["--stores", str(stores).strip()])
    execute_external_tool(script_path, extra_args=extra_args)

async def run_tool_xoa_tin_nhan():
    print("\n=======================================================")
    print("🗑️ BẮT ĐẦU CHẠY TOOL THU HỒI / XÓA TIN NHẮN ĐÃ SPAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "RAU_CU", "Xoa_Tin_Nhan.py")
    execute_external_tool(script_path)

async def run_tool_tra_cuu_id():
    print("\n=======================================================")
    print("🔍 BẮT ĐẦU CHẠY TOOL TRA CỨU NHANH CHAT ID GROUP...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "3_Tra_Cuu_ID.py")
    execute_external_tool(script_path)

async def run_tool_add_thanh_vien(member=None, chat_ids=None):
    print("\n=======================================================")
    print("👥 BẮT ĐẦU CHẠY TOOL TỰ ĐỘNG THÊM THÀNH VIÊN VÀO GROUP TELEGRAM...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "DONG_MAT", "4_Add_Thanh_Vien.py")
    extra_args = []
    if member:
        extra_args.append(f"--member={member}")
    if chat_ids:
        extra_args.append(f"--chat-ids={chat_ids}")
    execute_external_tool(script_path, extra_args=extra_args)

async def run_tool_xuat_doi_soat_chuan():
    print("\n=======================================================")
    print("📑 BẮT ĐẦU XUẤT FILE BÁO CÁO ĐỐI SOÁT CHUẨN EXCEL...")
    print("=======================================================")
    script_path = os.path.join(os.path.dirname(ROOT_DIR), "xuat_doi_soat_chuan.py")
    execute_external_tool(script_path)

async def run_tool_export_thit_ca():
    print("\n=======================================================")
    print("📈 BẮT ĐẦU CHẠY TOOL XUẤT ĐỐI SOÁT THỊT CÁ...")
    print("=======================================================")
    script_path = os.path.join(TOOLS_BASE_DIR, "THIT_CA", "export_thit_ca.py")
    execute_external_tool(script_path)


# -------------------------------------------------------------
# MAIN CLI CONTROLLER
# -------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Chạy Tool Đối Soát & Spam Phiếu Chuyển SCM")
    parser.add_argument("--tool", choices=[
        "all", "all_with_kho_kho",
        "thit_ca", "mat", "hau_kiem_rau", "hau_kiem_thit_ca", "hau_kiem_dong_mat",
        "chi_tiet_kho_kho", "hau_kiem_kho_kho",
        "dong_mat_sheet", "dong_mat_nhom_dong", "dong_mat_spam", "dong_spam", "dong", "thit_ca_spam", "rau_cu_spam",
        "spam_tu_chon", "xoa_tin_nhan", "lay_chat_id", "tra_cuu_id", "add_thanh_vien",
        "xuat_doi_soat_chuan", "export_thit_ca", "sync_report", "sync_telegram"
    ], default="all", help="Chọn tool cần chạy")
    parser.add_argument("--date", default=None, help="Ngày đối soát (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Chế độ chạy thử không gửi tin nhắn")
    parser.add_argument("--stores", default="ALL", help="Danh sách mã ST cần gửi (ngăn cách bởi dấu phẩy hoặc ALL)")
    parser.add_argument("--message", default=None, help="Nội dung tin nhắn tùy chọn cần spam hoặc username bot")
    parser.add_argument("--no-tags", action="store_true", help="Không tự động tag Quản lý/Trưởng ca")
    parser.add_argument("--photo", default=None, help="Đường dẫn file ảnh đính kèm (nếu có)")
    parser.add_argument("--chat-id-type", "--kho", choices=["dong_mat", "rau_cu", "auto"], default="dong_mat", dest="chat_id_type", help="Chọn File Chat ID Kênh gửi (dong_mat hoặc rau_cu)")
    
    raw_argv = sys.argv[1:]
    clean_argv = []
    i = 0
    while i < len(raw_argv):
        a = raw_argv[i]
        if a in ["--stores", "--message", "--date", "--tool", "--chat-id-type", "--kho", "--photo"] and i + 1 < len(raw_argv):
            clean_argv.append(f"{a}={raw_argv[i+1]}")
            i += 2
            continue
        clean_argv.append(a)
        i += 1

    args = parser.parse_args(clean_argv)
    date_val = args.date.strip() if args.date and args.date.strip() else None
    tag_roles = not args.no_tags
    
    print("==============================================================================")
    print(f"🚀 KHỞI ĐỘNG HỆ THỐNG RUNNER TOOL SCM (Tool: {args.tool}, Date: {date_val or 'Mặc định'}, Dry-run: {args.dry_run})")
    print("==============================================================================")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Nhóm Phiếu Chuyển & Hậu Kiểm Tươi Sống
        if args.tool == "thit_ca":
            loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
        elif args.tool == "mat":
            loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
        elif args.tool == "hau_kiem_rau":
            loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
        elif args.tool == "hau_kiem_thit_ca":
            loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
        elif args.tool == "hau_kiem_dong_mat":
            loop.run_until_complete(run_tool_hau_kiem_dong_mat(date_val, args.dry_run))
        
        # Nhóm Kho Khô (FGA10101)
        elif args.tool == "chi_tiet_kho_kho":
            loop.run_until_complete(run_tool_chi_tiet_kho_kho(date_val, args.dry_run, args.stores))
        elif args.tool == "hau_kiem_kho_kho":
            loop.run_until_complete(run_tool_hau_kiem_kho_kho(date_val, args.dry_run, args.stores))
        
        # Nhóm Chạy Tổng Hợp Step-by-Step
        elif args.tool == "all":
            print("\n🌟 CHẠY STEP-BY-STEP TẤT CẢ 5 TOOL PHIẾU CHUYỂN & HẬU KIỂM TƯƠI SỐNG:")
            loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
            loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_dong_mat(date_val, args.dry_run))
        
        elif args.tool == "all_with_kho_kho":
            print("\n🌟 CHẠY STEP-BY-STEP TOÀN BỘ 7 TOOL (BAO GỒM CẢ KHO KHÔ):")
            loop.run_until_complete(run_tool_thit_ca(date_val, args.dry_run))
            loop.run_until_complete(run_tool_mat(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_rau(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_thit_ca(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_dong_mat(date_val, args.dry_run))
            loop.run_until_complete(run_tool_chi_tiet_kho_kho(date_val, args.dry_run))
            loop.run_until_complete(run_tool_hau_kiem_kho_kho(date_val, args.dry_run))

        # Nhóm Phân Hệ Báo Cáo Đông Mát & Rau Củ
        elif args.tool == "dong_mat_sheet":
            loop.run_until_complete(run_tool_dong_mat_full(date_val, args.dry_run))
        elif args.tool == "dong_mat_nhom_dong":
            loop.run_until_complete(run_tool_dong_mat_nhom_dong())
        elif args.tool == "dong_mat_spam":
            loop.run_until_complete(run_tool_dong_mat_spam(date_val, args.dry_run, args.stores))
        elif args.tool in ["dong_spam", "dong"]:
            loop.run_until_complete(run_tool_dong_spam(date_val, args.dry_run, args.stores))
        elif args.tool == "thit_ca_spam":
            loop.run_until_complete(run_tool_thit_ca_spam(date_val, args.dry_run, args.stores))
        elif args.tool == "rau_cu_spam":
            loop.run_until_complete(run_tool_rau_cu_spam(date_val, args.dry_run, args.stores))
        elif args.tool == "spam_tu_chon":
            loop.run_until_complete(run_tool_spam_tu_chon(args.stores, args.message, tag_roles, args.dry_run, args.photo, args.chat_id_type))
        elif args.tool == "xoa_tin_nhan":
            loop.run_until_complete(run_tool_xoa_tin_nhan())
        elif args.tool == "lay_chat_id":
            loop.run_until_complete(run_tool_lay_chat_id())
        elif args.tool == "tra_cuu_id":
            loop.run_until_complete(run_tool_tra_cuu_id())
        elif args.tool == "add_thanh_vien":
            loop.run_until_complete(run_tool_add_thanh_vien(member=args.message, chat_ids=args.stores if args.stores != 'ALL' else ''))
        elif args.tool == "xuat_doi_soat_chuan":
            loop.run_until_complete(run_tool_xuat_doi_soat_chuan())
        elif args.tool == "export_thit_ca":
            loop.run_until_complete(run_tool_export_thit_ca())
        elif args.tool == "sync_telegram":
            print("📱 Đang quét và đồng bộ dữ liệu Realtime từ các nhóm Telegram...")
            import subprocess
            sync_script = os.path.join(os.path.dirname(ROOT_DIR), "DONG_MAT_DASHBOARD", "sync_telegram_groups.py")
            subprocess.run([sys.executable, sync_script], check=True)
        elif args.tool == "sync_report":
            print("📊 Đang khởi tạo tái xuất bản Báo Cáo Web Đối Soát...")
            dashboard_dir = os.path.join(os.path.dirname(ROOT_DIR), "DONG_MAT_DASHBOARD")
            sys.path.insert(0, dashboard_dir)
            from generate_web_report import generate_web_report
            generate_web_report()

    finally:
        loop.close()

    print("\n==============================================================================")
    print("🎉 TẤT CẢ TÁC VỤ ĐÃ HOÀN THÀNH!")
    print("==============================================================================")

if __name__ == "__main__":
    main()
