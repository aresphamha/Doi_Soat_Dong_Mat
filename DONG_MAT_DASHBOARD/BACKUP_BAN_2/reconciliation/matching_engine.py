"""
Module động cơ đối soát phân luồng 6 nhóm nghiệp vụ chuyên sâu cho Hàng Đông Mát.
"""

import pandas as pd
from typing import Dict


def classify_reconciliation_streams(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Phân tách dữ liệu chênh lệch thành 6 luồng đối soát nghiệp vụ chuẩn.
    """
    if len(df) == 0:
        empty_df = pd.DataFrame()
        return {
            "stream_1_exact": empty_df,
            "stream_2_partial": empty_df,
            "stream_3_cross": empty_df,
            "stream_4_surplus_gte": empty_df,
            "stream_5_net_shortage": empty_df,
            "stream_6_net_surplus": empty_df,
        }
        
    df_work = df.copy()
    
    # 1. Luồng 1: Khớp nội bộ 100% (DC thao tác sai)
    mask_stream_1 = (
        (df_work["Lỗi"].str.contains("thao tác sai", case=False, na=False)) |
        (df_work["Lỗi"].str.contains("pick sai", case=False, na=False))
    )
    df_stream_1 = df_work[mask_stream_1].copy()
    
    # 2. Luồng 2: Khớp nội bộ một phần (Đã trả tồn một phần về ST)
    mask_stream_2 = (
        (df_work["SL trả tồn về ST_Num"] > 0) |
        (df_work["PT Trả tồn về ST"].str.strip() != "")
    ) & (~mask_stream_1)
    df_stream_2 = df_work[mask_stream_2].copy()
    
    # 3. Luồng 3: Khớp chéo liên Siêu thị 1-1 (DC giao nhầm CH)
    mask_stream_3 = (
        (df_work["Lỗi"].str.contains("giao sai điểm", case=False, na=False)) |
        (df_work["Search_Index"].str.contains("giao nhầm", case=False, na=False)) |
        (df_work["Search_Index"].str.contains("nhầm", case=False, na=False))
    ) & (~mask_stream_1) & (~mask_stream_2)
    df_stream_3 = df_work[mask_stream_3].copy()
    
    # 4. Luồng 4: Tổng Dư >= Tổng Thiếu (DC giao bù hoặc pick dư)
    mask_stream_4 = (
        (df_work["Lỗi"].str.contains("giao bù", case=False, na=False)) |
        (df_work["PT DC pick dư"].str.strip() != "")
    ) & (~mask_stream_1) & (~mask_stream_2) & (~mask_stream_3)
    df_stream_4 = df_work[mask_stream_4].copy()
    
    # 5. Luồng 6: Trả tồn về DC / Thừa ròng
    mask_stream_6 = (
        (df_work["PT trả tồn về DC"].str.strip() != "")
    ) & (~mask_stream_1) & (~mask_stream_2) & (~mask_stream_3) & (~mask_stream_4)
    df_stream_6 = df_work[mask_stream_6].copy()
    
    # 6. Luồng 5: Chỉ ghi nhận Thiếu ròng (DC giao thiếu còn lại)
    classified_indices = set(df_stream_1.index) | set(df_stream_2.index) | set(df_stream_3.index) | set(df_stream_4.index) | set(df_stream_6.index)
    df_stream_5 = df_work[~df_work.index.isin(classified_indices)].copy()
    
    return {
        "stream_1_exact": df_stream_1,
        "stream_2_partial": df_stream_2,
        "stream_3_cross": df_stream_3,
        "stream_4_surplus_gte": df_stream_4,
        "stream_5_net_shortage": df_stream_5,
        "stream_6_net_surplus": df_stream_6,
    }
