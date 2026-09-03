"""
Module bộ lọc đa chiều thông minh Sidebar cho Dashboard ĐÔNG MÁT.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any


def render_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hiển thị giao diện bộ lọc bên Sidebar và trả về DataFrame đã được lọc theo tất cả các tiêu chí.
    """
    st.sidebar.markdown("### 🔍 BỘ LỌC TÌM KIẾM ĐỐI SOÁT")
    
    if len(df) == 0:
        return df
        
    # 1. Lọc theo Ngày (Date Filter)
    available_dates = df["Date_Str"].dropna().unique().tolist()
    # Sắp xếp ngày giảm dần
    sorted_dates = sorted(
        available_dates,
        key=lambda d: pd.to_datetime(d, format="%d/%m/%Y", errors="coerce") or pd.Timestamp.min,
        reverse=True
    )
    
    date_mode = st.sidebar.radio(
        "📅 Chế độ chọn ngày:",
        options=["Ngày mới nhất", "Tất cả các ngày", "Chọn ngày cụ thể"],
        horizontal=True
    )
    
    filtered_df = df.copy()
    
    if date_mode == "Ngày mới nhất" and len(sorted_dates) > 0:
        latest_date = sorted_dates[0]
        filtered_df = filtered_df[filtered_df["Date_Str"] == latest_date]
        st.sidebar.info(f"Đang hiển thị ngày mới nhất: **{latest_date}**")
    elif date_mode == "Chọn ngày cụ thể":
        selected_dates = st.sidebar.multiselect(
            "Chọn các ngày cần đối soát:",
            options=sorted_dates,
            default=sorted_dates[:1] if sorted_dates else []
        )
        if selected_dates:
            filtered_df = filtered_df[filtered_df["Date_Str"].isin(selected_dates)]
            
    # 2. Lọc Phân nhóm ngành hàng (MÁT vs ĐÔNG)
    available_groups = ["Tất cả"] + [g for g in df["Nhóm hàng"].dropna().unique() if g]
    selected_group = st.sidebar.selectbox("🏷️ Phân nhóm hàng:", options=available_groups)
    if selected_group != "Tất cả":
        filtered_df = filtered_df[filtered_df["Nhóm hàng"] == selected_group]
        
    # 3. Lọc theo Phân loại Lỗi
    available_errors = sorted([e for e in df["Lỗi"].dropna().unique() if e])
    selected_errors = st.sidebar.multiselect(
        "⚠️ Phân loại Lỗi phát sinh:",
        options=available_errors,
        placeholder="Chọn loại lỗi cần lọc..."
    )
    if selected_errors:
        filtered_df = filtered_df[filtered_df["Lỗi"].isin(selected_errors)]
        
    # 4. Lọc theo Tình trạng Claim DC
    available_claims = sorted([c for c in df["Claim_Status"].dropna().unique() if c])
    selected_claims = st.sidebar.multiselect(
        "🏢 Tình trạng DC phản hồi (Claim):",
        options=available_claims,
        placeholder="Chọn trạng thái claim..."
    )
    if selected_claims:
        filtered_df = filtered_df[filtered_df["Claim_Status"].isin(selected_claims)]
        
    # 5. Lọc theo Siêu thị
    available_stores = sorted([s for s in df["ID ST"].dropna().unique() if s and s != "nan"])
    selected_stores = st.sidebar.multiselect(
        "🏪 Mã Siêu thị (ID ST):",
        options=available_stores,
        placeholder="Tìm hoặc chọn ID ST..."
    )
    if selected_stores:
        filtered_df = filtered_df[filtered_df["ID ST"].isin(selected_stores)]
        
    # 6. Tìm kiếm tự do theo từ khóa
    search_keyword = st.sidebar.text_input(
        "🔎 Tìm kiếm nhanh (Mã PT, Mã Thùng, Mã Hàng, Tên SP):",
        placeholder="Nhập từ khóa..."
    ).strip().lower()
    
    if search_keyword:
        filtered_df = filtered_df[filtered_df["Search_Index"].str.contains(search_keyword, na=False)]
        
    # Hiển thị số lượng bản ghi thỏa mãn
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"📊 **Kết quả:** `{len(filtered_df):,}` / `{len(df):,}` dòng")
    
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### 🔗 Liên kết Google Sheets")
    st.sidebar.markdown(
        "- 📊 [Đối soát thịt cá T7+T8 (KFM - SCF)](https://docs.google.com/spreadsheets/d/1LI_cqLh_-k8eJzMVHtQr52X1xwLT9U5NeTYhW6NgQlU/edit?gid=1422896115#gid=1422896115)\n"
        "- 📑 [Đối soát ĐÔNG MÁT (Gốc)](https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/edit?gid=1422896115#gid=1422896115)"
    )
        
    return filtered_df
