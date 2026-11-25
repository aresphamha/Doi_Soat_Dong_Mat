"""
Module phân tích tiến độ Claim, bằng chứng camera video và phản hồi giữa Kho DC & KFM.
"""

import pandas as pd
from typing import Dict, Any


def analyze_claim_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phân tích tỷ lệ DC chấp nhận/từ chối claim và tổng số tiền tương ứng.
    """
    if len(df) == 0:
        return pd.DataFrame()
        
    claim_col = "DC xác nhận" if "DC xác nhận" in df.columns else "Claim_Status"
    summary = df.groupby(claim_col).agg(
        So_Vu=(claim_col, "count"),
        Tong_GT=("Val_Tong_GT", "sum"),
        Kho_Dap_Ung=("Val_Tong_Kho", "sum"),
        ST_Chiu=("Val_Tong_ST", "sum")
    ).reset_index()
    
    total_records = len(df)
    summary["Ty_Le_Vu_Pct"] = summary["So_Vu"].apply(lambda x: (x / total_records * 100.0) if total_records > 0 else 0.0)
    summary.sort_values(by="So_Vu", ascending=False, inplace=True)
    
    summary.rename(columns={
        claim_col: "Trạng thái DC phản hồi",
        "So_Vu": "Số vụ",
        "Tong_GT": "Tổng giá trị (VNĐ)",
        "Kho_Dap_Ung": "Tiền Kho đền bù (VNĐ)",
        "ST_Chiu": "Tiền ST chịu (VNĐ)",
        "Ty_Le_Vu_Pct": "Tỷ lệ số vụ (%)"
    }, inplace=True)
    
    return summary


def analyze_camera_evidence(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Thống kê các trường hợp có video bằng chứng camera mp4 và các lý do camera bị khuất/mờ.
    """
    if len(df) == 0:
        return {
            "has_video_count": 0,
            "no_video_count": 0,
            "cam_issue_count": 0,
            "cam_issue_details": pd.DataFrame()
        }
        
    has_video = df["Link hình ảnh"].apply(lambda x: bool(x and str(x).strip() and str(x).strip() != "nan"))
    has_video_count = int(has_video.sum())
    no_video_count = len(df) - has_video_count
    
    # Quét các ghi chú lỗi camera trong các cột NOTE
    note_cols = [c for c in df.columns if "NOTE" in c.upper()]
    cam_issues = []
    
    for _, row in df.iterrows():
        notes_text = " ".join([str(row[nc]) for nc in note_cols if pd.notna(row[nc])]).lower()
        if any(kw in notes_text for kw in ["khuất cam", "cam mờ", "không coi được cam", "cam xa", "không thấy kiểm"]):
            cam_issues.append({
                "Ngày": row.get("Date_Str", ""),
                "ID ST": row.get("ID ST", ""),
                "PT chuyển hàng": row.get("PT chuyển hàng", ""),
                "Mã hàng": row.get("Mã hàng", ""),
                "Tên SP": row.get("Tên SP", ""),
                "DC xác nhận": row.get("DC xác nhận", ""),
                "Ghi chú Camera": [str(row[nc]) for nc in note_cols if any(kw in str(row[nc]).lower() for kw in ["cam", "kiểm"]) and str(row[nc]) != "nan"]
            })
            
    df_cam_issues = pd.DataFrame(cam_issues)
    if len(df_cam_issues) > 0:
        df_cam_issues["Ghi chú Camera"] = df_cam_issues["Ghi chú Camera"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        
    return {
        "has_video_count": has_video_count,
        "no_video_count": no_video_count,
        "cam_issue_count": len(cam_issues),
        "cam_issue_details": df_cam_issues
    }
