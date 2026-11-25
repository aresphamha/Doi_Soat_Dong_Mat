"""
Hệ thống CSS & Thiết kế giao diện (Design System) hiện đại cho Dashboard ĐÔNG MÁT.
"""

import streamlit as st


def inject_custom_css():
    """
    Tiêm mã CSS nâng cao vào giao diện Streamlit mang phong cách Glassmorphism hiện đại và chuyên nghiệp.
    """
    css_content = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 1. Header Banner Gradient */
    .dashboard-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
        color: #ffffff;
        padding: 24px 32px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
        margin-bottom: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    
    .dashboard-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .dashboard-subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 6px;
        font-weight: 400;
    }

    /* 2. KPI Cards - Glassmorphism */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .kpi-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
        position: relative;
        overflow: hidden;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
    }

    .kpi-blue::before { background: #0284c7; }
    .kpi-red::before { background: #ef4444; }
    .kpi-green::before { background: #10b981; }
    .kpi-amber::before { background: #f59e0b; }
    .kpi-purple::before { background: #8b5cf6; }

    .kpi-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }

    .kpi-sub {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
    }

    /* 3. Status Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-success { background-color: #d1fae5; color: #065f46; }
    .badge-danger { background-color: #fee2e2; color: #991b1b; }
    .badge-warning { background-color: #fef3c7; color: #92400e; }
    .badge-info { background-color: #e0f2fe; color: #075985; }

    /* 4. Tab Header styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 16px;
        color: #475569;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0284c7 !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }

    /* 5. Custom Button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(2, 132, 199, 0.3) !important;
    }
    </style>
    """
    st.markdown(css_content, unsafe_allow_html=True)
