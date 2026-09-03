"""
Ứng dụng Dashboard Đối Soát ĐÔNG MÁT - Chuyên Sâu & Hiện Đại.
Điểm khởi chạy chính (Main Entrypoint).
"""

import sys
import os
import streamlit as st
import pandas as pd

# Thêm đường dẫn thư mục gốc vào sys.path để import dễ dàng
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 1. Cấu hình Trang Web FIRST
st.set_page_config(
    page_title="Dashboard Đối Soát ĐÔNG MÁT",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Import các module nội bộ
from config.settings import GOOGLE_SHEET_WEB_URL
from data.data_loader import load_cached_raw_data
from data.data_processor import process_dong_mat_dataframe
from analytics.kpi_metrics import (
    calculate_summary_kpis,
    get_error_type_summary,
    get_top_discrepant_stores,
    get_top_discrepant_products,
    get_daily_summary_matrix
)
from analytics.threshold_analytics import (
    determine_case_destination,
    analyze_threshold_metrics,
    get_daily_threshold_breakdown
)
from analytics.claim_analytics import analyze_claim_status, analyze_camera_evidence
from analytics.hierarchy_analysis import get_category_hierarchy_tree, get_clv2_summary
from reconciliation.matching_engine import classify_reconciliation_streams
from ui.styles import inject_custom_css
from ui.sidebar import render_sidebar_filters
from ui.components import render_header_banner, render_kpi_cards, format_dataframe_display
from ui.charts import (
    render_error_donut_chart,
    render_liability_donut_chart,
    render_top_stores_bar,
    render_hierarchy_treemap,
    render_daily_trend_chart,
    render_threshold_pareto_chart,
    render_daily_workload_chart,
    render_destination_stacked_chart,
    render_stores_over_100k_trend_chart
)
from exports.excel_exporter import export_multi_sheet_excel

# 3. Tiêm CSS Design System
inject_custom_css()

# 4. Tải & Xử lý Dữ liệu
with st.spinner("⏳ Đang kết nối và đồng bộ dữ liệu Google Sheets ĐÔNG MÁT..."):
    try:
        df_raw = load_cached_raw_data()
        df_processed = process_dong_mat_dataframe(df_raw)
        df_processed["Destination"] = df_processed.apply(determine_case_destination, axis=1)
    except Exception as e:
        st.error(f"❌ Không thể tải dữ liệu: {e}")
        st.info("Vui lòng kiểm tra kết nối mạng internet hoặc liên kết Google Sheets.")
        st.stop()

# 5. Render Bộ lọc Sidebar
df_filtered = render_sidebar_filters(df_processed)

# 6. Tính toán Chỉ số & Analytics
kpis = calculate_summary_kpis(df_filtered)
df_errors = get_error_type_summary(df_filtered)
df_top_stores = get_top_discrepant_stores(df_filtered, top_n=10)
df_top_prods = get_top_discrepant_products(df_filtered, top_n=10)
df_tree = get_category_hierarchy_tree(df_filtered)
df_clv2 = get_clv2_summary(df_filtered)
claim_summary = analyze_claim_status(df_filtered)
cam_evidence = analyze_camera_evidence(df_filtered)
streams = classify_reconciliation_streams(df_filtered)
df_daily_matrix = get_daily_summary_matrix(df_filtered)

# 7. Render Header & Thẻ KPI
latest_date_str = df_filtered["Date_Str"].iloc[0] if len(df_filtered) > 0 else ""
render_header_banner(
    title="HỆ THỐNG ĐỐI SOÁT CHUYÊN SÂU HÀNG ĐÔNG MÁT",
    subtitle="Dữ liệu tự động cập nhật từ Hệ thống Google Sheets • Sheet Chênh lệch ST",
    data_date=f"Ngày dữ liệu: {latest_date_str}" if latest_date_str else ""
)

render_kpi_cards(kpis)

# 8. Hệ Thống 7 Tab Chuyên Sâu (Báo cáo tổng hợp từng ngày lên đầu tiên)
tab_daily, tab_overview, tab_thresh, tab_details, tab_stream, tab_claim, tab_export = st.tabs([
    "📅 1. Báo Cáo Tổng Hợp Theo Từng Ngày",
    "📈 2. Tổng Quan & Biểu Đồ",
    "🎯 3. Phân Tích Ngưỡng 100k & Tần Suất",
    "📋 4. Chi Tiết Giao Dịch",
    "🔄 5. Phân Luồng Đối Soát 6 Nhóm",
    "⚖️ 6. Trách Nhiệm & Tiến Độ Claim",
    "📥 7. Xuất Báo Cáo Excel"
])

# ==============================================================================
# TAB 1: BÁO CÁO TỔNG HỢP THEO TỪNG NGÀY (DAILY SUMMARY MATRIX)
# ==============================================================================
with tab_daily:
    st.markdown("### 📊 BẢNG BÁO CÁO TỔNG HỢP ĐỐI SOÁT THEO TỪNG NGÀY")
    st.caption("Bảng tổng hợp chi tiết số lượng siêu thị lệch, phân khúc ST lệch >= 100k, điểm nhận trách nhiệm và 3 cấp trạng thái xử lý.")
    
    col_mode1, col_mode2 = st.columns([1, 2])
    with col_mode1:
        view_mode = st.radio(
            "📐 Chế độ xem:",
            options=["📊 Xem Cả Hai (SL & Tiền)", "💰 Xem Theo GIÁ TRỊ (VNĐ)", "📦 Xem Theo SỐ LƯỢNG (Qty)"],
            horizontal=True
        )
    with col_mode2:
        st.info("💡 Ngưỡng **100.000 VNĐ** được tính trên **Tổng tiền chênh lệch của 1 Siêu thị trong 1 Ngày** theo đúng chuẩn SCM.")

    if len(df_daily_matrix) == 0:
        st.warning("⚠️ Không có dữ liệu trong khoảng thời gian hoặc bộ lọc đã chọn.")
    else:
        df_show_matrix = df_daily_matrix.copy()
        if "Date_Parsed" in df_show_matrix.columns:
            df_show_matrix.drop(columns=["Date_Parsed"], inplace=True)
            
        if "GIÁ TRỊ" in view_mode:
            # Chế độ GIÁ TRỊ
            df_val = df_show_matrix[[
                "Tháng", "Ngày", "Tong_Gia_Tri", "Tong_ST", "ST_Over_100k", "Val_Over_100k",
                "ST_Under_100k", "Val_Under_100k", "Val_Kho", "Val_ST", "Val_HaoHut",
                "Val_Da_Xu_Ly", "Val_Dang_Xu_Ly", "Val_Khong_Xu_Ly", "Pct_Da_Xu_Ly"
            ]].copy()
            
            df_val.rename(columns={
                "Tong_Gia_Tri": "Tổng Giá Trị (VNĐ)",
                "Tong_ST": "Tổng ST Lệch",
                "ST_Over_100k": "ST Lệch ≥ 100K",
                "Val_Over_100k": "Tiền Lệch ≥ 100K (VNĐ)",
                "ST_Under_100k": "ST Lệch < 100K",
                "Val_Under_100k": "Tiền Lệch < 100K (VNĐ)",
                "Val_Kho": "Kho ĐÔNG MÁT (VNĐ)",
                "Val_ST": "Siêu Thị (VNĐ)",
                "Val_HaoHut": "Hao Hụt (VNĐ)",
                "Val_Da_Xu_Ly": "🟢 Đã Xử Lý (VNĐ)",
                "Val_Dang_Xu_Ly": "🟡 Đang Xử Lý [ST ≥ 100k] (VNĐ)",
                "Val_Khong_Xu_Ly": "⚪ Không Xử Lý [ST < 100k] (VNĐ)",
                "Pct_Da_Xu_Ly": "% Đã Xử Lý"
            }, inplace=True)
            
            format_dict = {
                "Tổng Giá Trị (VNĐ)": "{:,.0f} đ",
                "Tổng ST Lệch": "{:,.0f}",
                "ST Lệch ≥ 100K": "{:,.0f}",
                "Tiền Lệch ≥ 100K (VNĐ)": "{:,.0f} đ",
                "ST Lệch < 100K": "{:,.0f}",
                "Tiền Lệch < 100K (VNĐ)": "{:,.0f} đ",
                "Kho ĐÔNG MÁT (VNĐ)": "{:,.0f} đ",
                "Siêu Thị (VNĐ)": "{:,.0f} đ",
                "Hao Hụt (VNĐ)": "{:,.0f} đ",
                "🟢 Đã Xử Lý (VNĐ)": "{:,.0f} đ",
                "🟡 Đang Xử Lý [ST ≥ 100k] (VNĐ)": "{:,.0f} đ",
                "⚪ Không Xử Lý [ST < 100k] (VNĐ)": "{:,.0f} đ",
                "% Đã Xử Lý": "{:.1f}%"
            }
            st.dataframe(df_val.style.format(format_dict, na_rep="-"), use_container_width=True, height=450)
        elif "SỐ LƯỢNG" in view_mode:
            # Chế độ SỐ LƯỢNG
            df_qty = df_show_matrix[[
                "Tháng", "Ngày", "Tong_SL_Chuyen", "Tong_SL_Nhan", "Tong_SL_Lech", "Tong_ST",
                "ST_Over_100k", "SL_Over_100k", "ST_Under_100k", "SL_Under_100k",
                "SL_Kho", "SL_ST", "SL_HaoHut", "SL_Da_Xu_Ly", "SL_Dang_Xu_Ly", "SL_Khong_Xu_Ly"
            ]].copy()
            
            df_qty.rename(columns={
                "Tong_SL_Chuyen": "SL Chuyển",
                "Tong_SL_Nhan": "SL Nhận",
                "Tong_SL_Lech": "SL Chênh Lệch",
                "Tong_ST": "Tổng ST Lệch",
                "ST_Over_100k": "ST Lệch ≥ 100K",
                "SL_Over_100k": "SL Lệch ≥ 100K",
                "ST_Under_100k": "ST Lệch < 100K",
                "SL_Under_100k": "SL Lệch < 100K",
                "SL_Kho": "SL Kho ĐÔNG MÁT",
                "SL_ST": "SL Siêu Thị",
                "SL_HaoHut": "SL Hao Hụt",
                "SL_Da_Xu_Ly": "🟢 SL Đã Xử Lý",
                "SL_Dang_Xu_Ly": "🟡 SL Đang Xử Lý [ST ≥ 100k]",
                "SL_Khong_Xu_Ly": "⚪ SL Không Xử Lý [ST < 100k]"
            }, inplace=True)
            
            format_dict = {
                "SL Chuyển": "{:,.2f}",
                "SL Nhận": "{:,.2f}",
                "SL Chênh Lệch": "{:,.2f}",
                "Tổng ST Lệch": "{:,.0f}",
                "ST Lệch ≥ 100K": "{:,.0f}",
                "SL Lệch ≥ 100K": "{:,.2f}",
                "ST Lệch < 100K": "{:,.0f}",
                "SL Lệch < 100K": "{:,.2f}",
                "SL Kho ĐÔNG MÁT": "{:,.2f}",
                "SL Siêu Thị": "{:,.2f}",
                "SL Hao Hụt": "{:,.2f}",
                "🟢 SL Đã Xử Lý": "{:,.2f}",
                "🟡 SL Đang Xử Lý [ST ≥ 100k]": "{:,.2f}",
                "⚪ SL Không Xử Lý [ST < 100k]": "{:,.2f}"
            }
            st.dataframe(df_qty.style.format(format_dict, na_rep="-"), use_container_width=True, height=450)
        else:
            # Chế độ CẢ HAI (SL & Tiền)
            st.dataframe(df_show_matrix, use_container_width=True, height=450)
        
        st.markdown("---")
        
        # DRILL-DOWN CHI TIẾT NGÀY ĐƯỢC CHỌN
        st.markdown("#### 🔍 Xem Chi Tiết Của Một Ngày Cụ Thể:")
        available_days = df_daily_matrix["Ngày"].tolist()
        selected_day = st.selectbox("Chọn ngày đối soát để xem chi tiết:", options=available_days)
        
        if selected_day:
            df_day = df_filtered[df_filtered["Date_Str"] == selected_day]
            
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            with col_d1:
                st.metric("🏢 Số ST phát sinh", f"{df_day['ID ST'].nunique()} siêu thị")
            with col_d2:
                st.metric("📋 Tổng số vụ lệch", f"{len(df_day):,} vụ")
            with col_d3:
                st.metric("⚖️ SL lệch trong ngày", f"{df_day['Qty_Lech'].sum():,.1f}")
            with col_d4:
                st.metric("💰 Tổng tiền lệch ngày", f"{df_day['Val_Tong_GT'].sum():,.0f} đ")
                
            sub_d1, sub_d2 = st.tabs([
                "🏢 Tổng Hợp Theo Siêu Thị Trong Ngày",
                "📋 Danh Sách Từng Dòng Hàng (SKU)"
            ])
            
            with sub_d1:
                df_st_day = df_day.groupby(["ID ST", "Chi nhánh nhận"]).agg(
                    So_Vu=("ID ST", "count"),
                    SL_Lech=("Qty_Lech", "sum"),
                    Tong_GT=("Val_Tong_GT", "sum"),
                    Tong_Kho=("Val_Tong_Kho", "sum"),
                    Tong_ST=("Val_Tong_ST", "sum"),
                    Tong_HaoHut=("Val_Tong_HaoHut", "sum"),
                    Tong_CXD=("Val_Tong_CXD", "sum")
                ).reset_index().sort_values(by="Tong_GT", ascending=False)
                
                df_st_day.rename(columns={
                    "ID ST": "Mã ST",
                    "Chi nhánh nhận": "Tên Siêu Thị",
                    "So_Vu": "Số Vụ",
                    "SL_Lech": "SL Lệch",
                    "Tong_GT": "Tổng Tiền Lệch (VNĐ)",
                    "Tong_Kho": "Kho Chịu (VNĐ)",
                    "Tong_ST": "ST Chịu (VNĐ)",
                    "Tong_HaoHut": "Hao Hụt (VNĐ)",
                    "Tong_CXD": "Chưa XĐ (VNĐ)"
                }, inplace=True)
                
                st.dataframe(
                    df_st_day.style.format({
                        "Số Vụ": "{:,.0f}",
                        "SL_Lech": "{:,.1f}",
                        "Tổng Tiền Lệch (VNĐ)": "{:,.0f} đ",
                        "Kho Chịu (VNĐ)": "{:,.0f} đ",
                        "ST Chịu (VNĐ)": "{:,.0f} đ",
                        "Hao Hụt (VNĐ)": "{:,.0f} đ",
                        "Chưa XĐ (VNĐ)": "{:,.0f} đ"
                    }),
                    use_container_width=True,
                    height=320
                )
                
            with sub_d2:
                st.dataframe(format_dataframe_display(df_day), use_container_width=True, height=360)

# ==============================================================================
# TAB 2: TỔNG QUAN & BIỂU ĐỒ TRỰC QUAN
# ==============================================================================
with tab_overview:
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(render_error_donut_chart(df_errors), use_container_width=True)
    with col_chart2:
        st.plotly_chart(render_liability_donut_chart(kpis), use_container_width=True)
        
    st.markdown("---")
    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        st.plotly_chart(render_top_stores_bar(df_top_stores), use_container_width=True)
    with col_chart4:
        st.plotly_chart(render_hierarchy_treemap(df_tree), use_container_width=True)
        
    st.markdown("---")
    st.plotly_chart(render_daily_trend_chart(df_processed), use_container_width=True)
    
    col_tbl1, col_tbl2 = st.columns(2)
    with col_tbl1:
        st.markdown("##### 🏆 Top 10 Mặt Hàng Lệch Nhiều Nhất")
        st.dataframe(df_top_prods, use_container_width=True, height=280)
    with col_tbl2:
        st.markdown("##### 📦 Cơ Cấu Ngành Hàng Cấp 2 (CLV2)")
        st.dataframe(df_clv2, use_container_width=True, height=280)

# ==============================================================================
# TAB 3: PHÂN TÍCH NGƯỠNG 100K & TẦN SUẤT XỬ LÝ
# ==============================================================================
with tab_thresh:
    st.markdown("### 🎯 PHÂN TÍCH NGƯỠNG GIÁ TRỊ VÀ TẦN SUẤT XỬ LÝ MỖI NGÀY")
    st.caption("Theo dõi số lượng siêu thị phát sinh chênh lệch trên 100k, điểm trả tồn (Kho/ST/Hao hụt/CXD) và phân loại ngày Cao điểm/Trung bình/Thấp điểm.")
    
    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        custom_threshold = st.number_input(
            "⚙️ Cài đặt ngưỡng giá trị (VNĐ):",
            min_value=10000.0,
            max_value=2000000.0,
            value=100000.0,
            step=10000.0,
            format="%.0f"
        )
    with col_ctrl2:
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 12px 18px; border-radius: 10px; border-left: 4px solid #0284c7; margin-top: 5px;">
            <b>Quy tắc phân tích:</b> Bóc tách toàn bộ case chênh lệch thành 2 nhóm: 
            <b>Dưới {custom_threshold:,.0f} đ</b> và <b>Từ {custom_threshold:,.0f} đ trở lên</b>.
        </div>
        """, unsafe_allow_html=True)
        
    # Tính toán theo ngưỡng
    thresh_metrics = analyze_threshold_metrics(df_filtered, threshold=custom_threshold)
    df_daily_th, workload_stats = get_daily_threshold_breakdown(df_filtered, threshold=custom_threshold)
    
    # 1. Thẻ so sánh tỷ trọng Pareto
    st.markdown("#### ⚖️ Tỷ Trọng Case Dưới vs Trên Ngưỡng (Pareto Distribution)")
    col_th1, col_th2, col_th3, col_th4 = st.columns(4)
    with col_th1:
        st.metric(
            label=f"🔴 Case >= {custom_threshold:,.0f} đ (Số vụ)",
            value=f"{thresh_metrics['over_count']:,} vụ",
            delta=f"{thresh_metrics['over_pct_count']:.1f}% tổng số vụ"
        )
    with col_th2:
        st.metric(
            label=f"💰 Giá trị Case >= {custom_threshold:,.0f} đ",
            value=f"{thresh_metrics['over_val']:,.0f} đ",
            delta=f"{thresh_metrics['over_pct_val']:.1f}% tổng tiền"
        )
    with col_th3:
        st.metric(
            label=f"🔵 Case < {custom_threshold:,.0f} đ (Số vụ)",
            value=f"{thresh_metrics['under_count']:,} vụ",
            delta=f"{thresh_metrics['under_pct_count']:.1f}% tổng số vụ"
        )
    with col_th4:
        st.metric(
            label=f"💵 Giá trị Case < {custom_threshold:,.0f} đ",
            value=f"{thresh_metrics['under_val']:,.0f} đ",
            delta=f"{thresh_metrics['under_pct_val']:.1f}% tổng tiền"
        )
        
    # Biểu đồ Pareto so sánh
    st.plotly_chart(render_threshold_pareto_chart(thresh_metrics), use_container_width=True)
    
    st.markdown("---")
    
    # 2. Phân Tích Tần Suất Xử Lý Mỗi Ngày (Cao điểm / Trung bình / Thấp điểm)
    st.markdown("#### 📅 Tần Suất Xử Lý Mỗi Ngày & Khối Lượng Công Việc")
    
    col_wl1, col_wl2, col_wl3, col_wl4 = st.columns(4)
    with col_wl1:
        st.metric(
            label="📊 Trung bình mỗi ngày",
            value=f"{workload_stats['avg_cases']:.0f} case/ngày",
            delta="Mức tải chuẩn"
        )
    with col_wl2:
        st.metric(
            label="🔴 Ngày Cao Điểm nhất",
            value=f"{workload_stats['max_day_name']}",
            delta=f"{workload_stats['max_day_cases']:,} case xử lý"
        )
    with col_wl3:
        st.metric(
            label="🟢 Ngày Thấp Điểm nhất",
            value=f"{workload_stats['min_day_name']}",
            delta=f"{workload_stats['min_day_cases']:,} case xử lý"
        )
    with col_wl4:
        st.metric(
            label="📈 Số ngày Cao điểm / Tổng số ngày",
            value=f"{workload_stats['high_days_count']} ngày",
            delta=f"TB: {workload_stats['med_days_count']} ngày • Ít: {workload_stats['low_days_count']} ngày"
        )
        
    st.plotly_chart(render_daily_workload_chart(df_daily_th, workload_stats), use_container_width=True)
    
    # 3. Biểu đồ Số Siêu Thị > 100k & Phân bổ Điểm Trả Tồn
    st.markdown("---")
    st.markdown("#### 🏢 Thống Kê Số Lượng Siêu Thị & Điểm Trả Tồn (Kho / ST / Hao hụt / CXD)")
    
    col_plot1, col_plot2 = st.columns(2)
    with col_plot1:
        st.plotly_chart(render_stores_over_100k_trend_chart(df_daily_th), use_container_width=True)
    with col_plot2:
        st.plotly_chart(render_destination_stacked_chart(df_daily_th), use_container_width=True)
        
    # 4. Bảng Dữ Liệu Tổng Hợp Theo Từng Ngày Theo Ngưỡng
    st.markdown("#### 📋 Bảng Thống Kê Chi Tiết Từng Ngày Theo Ngưỡng")
    
    df_daily_display = df_daily_th.copy()
    if "Date_Parsed" in df_daily_display.columns:
        df_daily_display.drop(columns=["Date_Parsed"], inplace=True)
        
    df_daily_display.rename(columns={
        "Tổng_Case": "Tổng Số Case",
        "Tổng_Tien": "Tổng Tiền Lệch (VNĐ)",
        "ST_Co_Lech_Tren_100k": f"Số ST Có Lệch > {custom_threshold/1000:.0f}k",
        "Tong_ST_Phat_Sinh": "Tổng ST Phát Sinh",
        "Case_Tren_100k": f"Case > {custom_threshold/1000:.0f}k",
        "Pct_Case_Tren_100k": f"% Case > {custom_threshold/1000:.0f}k",
        "Tien_Tren_100k": f"Tiền > {custom_threshold/1000:.0f}k (VNĐ)",
        "Case_Duoi_100k": f"Case < {custom_threshold/1000:.0f}k",
        "Pct_Case_Duoi_100k": f"% Case < {custom_threshold/1000:.0f}k",
        "Tien_Duoi_100k": f"Tiền < {custom_threshold/1000:.0f}k (VNĐ)",
        "Tra_Ton_Kho": "Trả Về Kho ĐÔNG MÁT",
        "Tra_Ton_ST": "Ghi Nhận Siêu Thị",
        "Tra_Ton_HaoHut": "Ghi Nhận Hao Hụt",
        "Tra_Ton_CXD": "Chưa Xác Định",
        "Phân_Loại_Tần_Suất": "Mức Độ Tải"
    }, inplace=True)
    
    st.dataframe(df_daily_display, use_container_width=True, height=350)
    
    # 5. Tra cứu danh sách Siêu thị có case > threshold theo ngày được chọn
    st.markdown(f"#### 🔍 Tra Cứu Danh Sách Siêu Thị Có Lệch >= {custom_threshold:,.0f} đ Trong Ngày:")
    available_days_list = df_daily_th["Ngày"].tolist()
    if available_days_list:
        selected_drill_day = st.selectbox("Chọn ngày cần xem chi tiết siêu thị:", options=available_days_list)
        df_drill = df_filtered[(df_filtered["Date_Str"] == selected_drill_day) & (df_filtered["Val_Tong_GT"] >= custom_threshold)]
        
        st.info(f"Ngày **{selected_drill_day}** có **{df_drill['ID ST'].nunique()}** Siêu thị phát sinh **{len(df_drill):,}** case lệch >= {custom_threshold:,.0f} đ với tổng giá trị **{df_drill['Val_Tong_GT'].sum():,.0f} VNĐ**.")
        st.dataframe(format_dataframe_display(df_drill), use_container_width=True, height=320)

# ==============================================================================
# TAB 4: CHI TIẾT GIAO DỊCH & BẰNG CHỨNG
# ==============================================================================
with tab_details:
    st.markdown("### 📋 BẢNG CHI TIẾT CÁC VỤ CHÊNH LỆCH")
    st.caption(f"Hiển thị {len(df_filtered):,} dòng dữ liệu thỏa mãn bộ lọc hiện tại.")
    
    df_table = format_dataframe_display(df_filtered)
    st.dataframe(df_table, use_container_width=True, height=520)
    
    excel_fast_bytes = export_multi_sheet_excel(df_filtered, df_errors, streams, kpis)
    st.download_button(
        label="📥 Tải xuống bảng dữ liệu này (Excel)",
        data=excel_fast_bytes,
        file_name="Bao_Cao_Chi_Tiet_Dong_Mat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="fast_excel_download"
    )

# ==============================================================================
# TAB 5: PHÂN LUỒNG ĐỐI SOÁT 6 NHÓM NGHIỆP VỤ
# ==============================================================================
with tab_stream:
    st.markdown("### 🔄 PHÂN TÁCH 6 LUỒNG ĐỐI SOÁT NGHIỆP VỤ")
    st.caption("Tự động bóc tách thành các luồng xử lý riêng biệt phục vụ điều tra kho DC và chốt số liệu.")
    
    sub1, sub2, sub3, sub4, sub5, sub6 = st.tabs([
        f"1. Khớp nội bộ 100% ({len(streams['stream_1_exact'])})",
        f"2. Khớp nội bộ 1 phần ({len(streams['stream_2_partial'])})",
        f"3. Giao nhầm Siêu thị ({len(streams['stream_3_cross'])})",
        f"4. Bù đắp thừa dư ({len(streams['stream_4_surplus_gte'])})",
        f"5. Thiếu ròng DC ({len(streams['stream_5_net_shortage'])})",
        f"6. Trả tồn về DC ({len(streams['stream_6_net_surplus'])})"
    ])
    
    with sub1:
        st.subheader("1. Khớp Nội Bộ 100% (DC thao tác sai / Pick sai mã)")
        st.dataframe(format_dataframe_display(streams["stream_1_exact"]), use_container_width=True)
        
    with sub2:
        st.subheader("2. Khớp Nội Bộ Một Phần (Đã trả tồn một phần về Siêu thị)")
        st.dataframe(format_dataframe_display(streams["stream_2_partial"]), use_container_width=True)
        
    with sub3:
        st.subheader("3. Khớp Chéo Liên Siêu Thị (Giao nhầm cửa hàng lân cận)")
        st.dataframe(format_dataframe_display(streams["stream_3_cross"]), use_container_width=True)
        
    with sub4:
        st.subheader("4. Tổng Dư >= Tổng Thiếu (DC giao bù / Pick dư)")
        st.dataframe(format_dataframe_display(streams["stream_4_surplus_gte"]), use_container_width=True)
        
    with sub5:
        st.subheader("5. Chỉ Ghi Nhận Thiếu Ròng (DC giao thiếu chưa bù)")
        st.dataframe(format_dataframe_display(streams["stream_5_net_shortage"]), use_container_width=True)
        
    with sub6:
        st.subheader("6. Trả Tồn Về DC (Siêu thị nhận thừa đã trả về kho)")
        st.dataframe(format_dataframe_display(streams["stream_6_net_surplus"]), use_container_width=True)

# ==============================================================================
# TAB 6: TRÁCH NHIỆM & TIẾN ĐỘ CLAIM
# ==============================================================================
with tab_claim:
    st.markdown("### ⚖️ THEO DÕI TIẾN ĐỘ CLAIM VÀ ĐIỀU TRA CAMERA")
    
    col_claim1, col_claim2 = st.columns(2)
    with col_claim1:
        st.markdown("##### 🏢 Tình Trạng DC Xác Nhận Claim")
        st.dataframe(claim_summary, use_container_width=True)
        
    with col_claim2:
        st.markdown("##### 📹 Thống Kê Bằng Chứng Video Camera")
        st.markdown(f"""
        - 🎥 **Có video bằng chứng camera**: `{cam_evidence['has_video_count']:,}` vụ
        - ❌ **Không có video camera**: `{cam_evidence['no_video_count']:,}` vụ
        - ⚠️ **Phát hiện sự cố Camera (Khuất cam, mờ cam...)**: `{cam_evidence['cam_issue_count']:,}` vụ
        """)
        
    if cam_evidence["cam_issue_count"] > 0:
        st.markdown("##### 🚨 Danh Sách Các Case Gặp Sự Cố Camera Cần Làm Rõ:")
        st.dataframe(cam_evidence["cam_issue_details"], use_container_width=True, height=260)

# ==============================================================================
# TAB 7: TRUNG TÂM XUẤT BÁO CÁO EXCEL ĐA SHEET
# ==============================================================================
with tab_export:
    st.markdown("### 📥 TRUNG TÂM XUẤT BÁO CÁO EXCEL CHUẨN DOANH NGHIỆP")
    st.info("File Excel xuất ra được tự động phân tách thành 8 Sheet chuẩn, kẻ bảng, căn lề và định dạng tiền tệ đẹp mắt.")
    
    st.markdown("""
    **Các Sheet sẽ được tạo tự động trong tệp:**
    1. `1. Tổng Quan KPI & Lỗi`: Bảng chỉ số điều hành và bảng phân loại lỗi.
    2. `2. Dữ Liệu Chi Tiết`: Toàn bộ các dòng giao dịch theo bộ lọc hiện tại.
    3. `3. Khớp Nội Bộ 100%`: Danh sách DC thao tác sai/pick sai.
    4. `4. Khớp Nội Bộ 1 Phần`: Danh sách đã trả tồn 1 phần về ST.
    5. `5. Giao Nhầm Siêu Thị`: Danh sách giao nhầm cửa hàng.
    6. `6. Bù Đắp Thừa Dư`: Danh sách DC giao bù/pick dư.
    7. `7. Thiếu Ròng`: Danh sách DC giao thiếu chưa bù.
    8. `8. Trả Tồn DC`: Danh sách siêu thị trả tồn về kho.
    """)
    
    excel_multi_bytes = export_multi_sheet_excel(df_filtered, df_errors, streams, kpis)
    st.download_button(
        label="🚀 TẢI XUỐNG BÁO CÁO EXCEL ĐA SHEET (.XLSX)",
        data=excel_multi_bytes,
        file_name=f"Bao_Cao_Doi_Soat_Dong_Mat_{latest_date_str.replace('/', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="master_excel_download"
    )
