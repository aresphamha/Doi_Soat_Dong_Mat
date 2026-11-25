"""
Module trực quan hóa dữ liệu bằng biểu đồ tương tác Plotly hiện đại.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def render_error_donut_chart(df_error: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ Donut phân tích cơ cấu các loại lỗi chênh lệch.
    """
    if len(df_error) == 0:
        return go.Figure()
        
    fig = px.pie(
        df_error,
        names="Loại Lỗi",
        values="Tổng giá trị (VNĐ)",
        hole=0.55,
        title="<b>Cơ Cấu Giá Trị Theo Phân Loại Lỗi</b>",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hoverinfo="label+value+percent",
        marker=dict(line=dict(color="#ffffff", width=2))
    )
    fig.update_layout(
        showlegend=True,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=380
    )
    return fig


def render_liability_donut_chart(kpis: dict) -> go.Figure:
    """
    Biểu đồ Donut so sánh tỷ trọng phân bổ trách nhiệm tài chính (Kho vs ST vs Hao hụt vs CXD).
    """
    labels = ["Kho DC Chịu", "Siêu Thị Chịu", "Hao Hụt Tự Nhiên", "Chưa Xác Định"]
    values = [kpis["total_val_kho"], kpis["total_val_st"], kpis["total_val_haohut"], kpis["total_val_cxd"]]
    colors = ["#f59e0b", "#8b5cf6", "#10b981", "#94a3b8"]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
        textinfo="percent+label"
    )])
    
    fig.update_layout(
        title="<b>Phân Bổ Trách Nhiệm Đền Bù & Hao Hụt</b>",
        showlegend=False,
        margin=dict(t=40, b=20, l=20, r=20),
        height=380
    )
    return fig


def render_top_stores_bar(df_stores: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ cột ngang Top 10 Siêu thị có chênh lệch cao nhất.
    """
    if len(df_stores) == 0:
        return go.Figure()
        
    df_sorted = df_stores.sort_values(by="Tong_GT", ascending=True)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_sorted["ID ST"] + " - " + df_sorted["Chi nhánh nhận"].str[:25],
        x=df_sorted["Tong_Kho"],
        name="Kho DC chịu",
        orientation="h",
        marker=dict(color="#f59e0b")
    ))
    fig.add_trace(go.Bar(
        y=df_sorted["ID ST"] + " - " + df_sorted["Chi nhánh nhận"].str[:25],
        x=df_sorted["Tong_ST"],
        name="Siêu thị chịu",
        orientation="h",
        marker=dict(color="#8b5cf6")
    ))
    
    fig.update_layout(
        barmode="stack",
        title="<b>Top 10 Siêu Thị Có Giá Trị Chênh Lệch Lớn Nhất (VNĐ)</b>",
        xaxis_title="Giá trị (VNĐ)",
        yaxis_title="",
        margin=dict(t=40, b=30, l=180, r=20),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def render_hierarchy_treemap(df_tree: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ Treemap phân cấp ngành hàng đa tầng: Nhóm hàng -> CLV2 -> CLV3.
    """
    if len(df_tree) == 0:
        return go.Figure()
        
    fig = px.treemap(
        df_tree,
        path=["Nhóm hàng", "CLV2", "CLV3"],
        values="Tong_GT",
        color="Tong_GT",
        color_continuous_scale="Blues",
        title="<b>Phân Bổ Giá Trị Lệch Theo Cấu Trúc Ngành Hàng (Nhóm -> CLV2 -> CLV3)</b>"
    )
    fig.update_traces(root_color="lightgrey")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=420)
    return fig


def render_daily_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ diễn biến số vụ và giá trị chênh lệch theo dòng thời gian các ngày.
    """
    if len(df) == 0 or "Date_Parsed" not in df.columns:
        return go.Figure()
        
    daily = df.groupby("Date_Str").agg(
        So_Vu=("Lỗi", "count"),
        Tong_GT=("Val_Tong_GT", "sum"),
        Date_Parsed=("Date_Parsed", "first")
    ).reset_index().dropna(subset=["Date_Parsed"])
    
    daily.sort_values(by="Date_Parsed", inplace=True)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["Date_Str"],
        y=daily["Tong_GT"],
        name="Tổng giá trị (VNĐ)",
        marker=dict(color="#0284c7")
    ))
    fig.add_trace(go.Scatter(
        x=daily["Date_Str"],
        y=daily["So_Vu"],
        name="Số vụ chênh lệch",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color="#ef4444", width=3)
    ))
    
    fig.update_layout(
        title="<b>Diễn Biến Chênh Lệch Theo Từng Ngày</b>",
        xaxis=dict(title="Ngày kiểm"),
        yaxis=dict(title="Tổng giá trị (VNĐ)", side="left"),
        yaxis2=dict(title="Số vụ lệch", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=30, l=40, r=40),
        height=350
    )
    return fig


def render_threshold_pareto_chart(tm: dict) -> go.Figure:
    """
    Biểu đồ so sánh Tỷ Trọng Số Vụ vs Tỷ Trọng Giá Trị Tiền (Dưới 100k vs Trên 100k).
    """
    categories = ["Dưới 100k VNĐ", "Từ 100k VNĐ trở lên"]
    pct_counts = [tm["under_pct_count"], tm["over_pct_count"]]
    pct_vals = [tm["under_pct_val"], tm["over_pct_val"]]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=pct_counts,
        name="Tỷ trọng Số lượng Vụ (%)",
        text=[f"{v:.1f}% ({tm['under_count']:,} vụ)" if i == 0 else f"{v:.1f}% ({tm['over_count']:,} vụ)" for i, v in enumerate(pct_counts)],
        textposition="auto",
        marker=dict(color="#0284c7")
    ))
    fig.add_trace(go.Bar(
        x=categories,
        y=pct_vals,
        name="Tỷ trọng Tổng Giá Trị VNĐ (%)",
        text=[f"{v:.1f}% ({tm['under_val']:,.0f} đ)" if i == 0 else f"{v:.1f}% ({tm['over_val']:,.0f} đ)" for i, v in enumerate(pct_vals)],
        textposition="auto",
        marker=dict(color="#ef4444")
    ))
    
    fig.update_layout(
        barmode="group",
        title="<b>So Sánh Tỷ Trọng: Số Vụ Lệch vs Giá Trị Tiền Bị Ảnh Hưởng (Ngưỡng 100k)</b>",
        yaxis=dict(title="Tỷ trọng (%)", range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=30, l=40, r=20),
        height=380
    )
    return fig


def render_daily_workload_chart(df_daily: pd.DataFrame, stats: dict) -> go.Figure:
    """
    Biểu đồ cột Tần Suất Xử Lý Mỗi Ngày phân loại theo màu (🔴 Cao điểm, 🟡 Trung bình, 🟢 Thấp điểm).
    """
    if len(df_daily) == 0:
        return go.Figure()
        
    color_map = {
        "🔴 Cao điểm (Nhiều)": "#ef4444",
        "🟡 Trung bình": "#f59e0b",
        "🟢 Thấp điểm (Ít)": "#10b981"
    }
    
    df_sorted = df_daily.sort_values(by="Date_Parsed", ascending=True) if "Date_Parsed" in df_daily.columns else df_daily
    
    fig = px.bar(
        df_sorted,
        x="Ngày",
        y="Tổng_Case",
        color="Phân_Loại_Tần_Suất",
        color_discrete_map=color_map,
        title="<b>Tần Suất Xử Lý Case Mỗi Ngày & Phân Cấp Khối Lượng Công Việc (Cao điểm / TB / Thấp điểm)</b>",
        text="Tổng_Case",
        labels={"Tổng_Case": "Tổng số case", "Phân_Loại_Tần_Suất": "Mức độ tải"}
    )
    
    # Thêm đường trung bình
    fig.add_hline(
        y=stats["avg_cases"],
        line_dash="dash",
        line_color="#0f172a",
        annotation_text=f"TB: {stats['avg_cases']:.0f} case/ngày",
        annotation_position="top left"
    )
    
    fig.update_traces(textposition="outside")
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=30, l=40, r=20),
        height=400
    )
    return fig


def render_destination_stacked_chart(df_daily: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ cột chồng phân bổ Điểm Trả Tồn (Kho DC, Siêu thị, Hao hụt, CXD) của các case >= 100k theo ngày.
    """
    if len(df_daily) == 0:
        return go.Figure()
        
    df_sorted = df_daily.sort_values(by="Date_Parsed", ascending=True) if "Date_Parsed" in df_daily.columns else df_daily
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_sorted["Ngày"],
        y=df_sorted["Tra_Ton_Kho"],
        name="Kho ĐÔNG MÁT",
        marker=dict(color="#f59e0b")
    ))
    fig.add_trace(go.Bar(
        x=df_sorted["Ngày"],
        y=df_sorted["Tra_Ton_ST"],
        name="Siêu thị",
        marker=dict(color="#8b5cf6")
    ))
    fig.add_trace(go.Bar(
        x=df_sorted["Ngày"],
        y=df_sorted["Tra_Ton_HaoHut"],
        name="Hao hụt tự nhiên",
        marker=dict(color="#10b981")
    ))
    fig.add_trace(go.Bar(
        x=df_sorted["Ngày"],
        y=df_sorted["Tra_Ton_CXD"],
        name="Chưa xác định",
        marker=dict(color="#94a3b8")
    ))
    
    fig.update_layout(
        barmode="stack",
        title="<b>Phân Bổ Điểm Trả Tồn Của Các Case Chênh Lệch >= 100.000 VNĐ Theo Từng Ngày</b>",
        xaxis_title="Ngày kiểm",
        yaxis_title="Số lượng case",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=30, l=40, r=20),
        height=380
    )
    return fig


def render_stores_over_100k_trend_chart(df_daily: pd.DataFrame) -> go.Figure:
    """
    Biểu đồ đường biểu diễn Số Lượng Siêu Thị phát sinh chênh lệch >= 100.000 VNĐ theo từng ngày.
    """
    if len(df_daily) == 0:
        return go.Figure()
        
    df_sorted = df_daily.sort_values(by="Date_Parsed", ascending=True) if "Date_Parsed" in df_daily.columns else df_daily
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_sorted["Ngày"],
        y=df_sorted["Tong_ST_Phat_Sinh"],
        name="Tổng Siêu thị phát sinh lệch",
        marker=dict(color="#cbd5e1")
    ))
    fig.add_trace(go.Scatter(
        x=df_sorted["Ngày"],
        y=df_sorted["ST_Co_Lech_Tren_100k"],
        name="Số Siêu thị có case >= 100k",
        mode="lines+markers+text",
        text=df_sorted["ST_Co_Lech_Tren_100k"],
        textposition="top center",
        line=dict(color="#ef4444", width=3),
        marker=dict(size=8, color="#b91c1c")
    ))
    
    fig.update_layout(
        title="<b>Số Lượng Siêu Thị Phát Sinh Chênh Lệch >= 100.000 VNĐ Mỗi Ngày</b>",
        xaxis_title="Ngày kiểm",
        yaxis_title="Số lượng Siêu thị",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=30, l=40, r=20),
        height=360
    )
    return fig
