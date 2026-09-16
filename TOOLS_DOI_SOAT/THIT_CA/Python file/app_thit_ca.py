import streamlit as st
import pandas as pd
import numpy as np
import io
import requests
import pymysql

# DB connection helper for StarRocks database
def get_connection():
    return pymysql.connect(
        host='103.147.122.103',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm',
    )

def fetch_data_to_df(sql_query):
    conn = get_connection()
    try:
        df = pd.read_sql(sql_query, conn)
        return df
    finally:
        conn.close()


# Cấu hình trang web
st.set_page_config(page_title="Dashboard Đối Soát Kho", page_icon="📊", layout="wide")

st.sidebar.title("Cài đặt chung")
khu_vuc_selected = st.sidebar.radio("Khu vực đối soát:", ["Thịt Cá", "Rau Củ Quả", "Đông Mát"])


def render_thit_ca():

    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115"
    file_layout = "LayoutImportThitCa.xlsx"
    shortage_condition = "i.from_branch_id = '6a34ed56f23028000774139f'"
    surplus_condition = "i.from_branch_id = '6a34ed8d6607ba000703e235'"
    kho_name = "Kho Thịt Cá"
    kho_code = "MF01"
    icon = "🥩"
    khu_vuc = "Thịt Cá"

    def get_excel_bytes(df):
        output = io.BytesIO()
        df_to_export = df.copy()
        if isinstance(df_to_export.columns, pd.MultiIndex):
            df_to_export.columns = [' - '.join(str(c) for c in col if c).strip() for col in df_to_export.columns.values]
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_to_export.to_excel(writer, index=False)
        return output.getvalue()
    
    def display_df_with_download(styled_df, filename, height=None):
        if height:
            st.dataframe(styled_df, use_container_width=True, height=height)
        else:
            st.dataframe(styled_df, use_container_width=True)
        df_raw = styled_df.data if hasattr(styled_df, 'data') else styled_df
        try:
            excel_data = get_excel_bytes(df_raw)
            st.download_button(label="📥 Tải xuống Excel", data=excel_data, file_name=f"{filename}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=filename)
        except Exception as e:
            st.error(f"Lỗi xuất Excel: {e}")
    
    st.title(f"{icon} Báo Cáo Đối Soát {kho_name}")
    st.markdown("Dữ liệu tự động cập nhật từ Hệ thống Google Sheets")
    
    # Hàm làm sạch số lượng chênh lệch (Đơn vị nhỏ: cái, kg, hộp)
    def clean_qty(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Ở cột số lượng, dấu phẩy thường là phân cách thập phân (VD: 5,5 -> 5.5) hoặc dấu chấm cũng vậy (VD: -1.000 -> -1.0)
            # Không có số lượng hàng nghìn trên 1 dòng ở {kho_name.lower()}, nên ta quy về dạng chuẩn
            x = x.replace(',', '.')
            # Nếu có nhiều dấu chấm (lỗi định dạng), chỉ giữ lại dấu chấm cuối cùng
            if x.count('.') > 1:
                parts = x.split('.')
                x = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(x)
        except:
            return 0.0
    
    # Hàm làm sạch giá trị tiền tệ (Đơn vị lớn: VNĐ)
    def clean_val(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Xử lý tiền tệ VNĐ (VD: -2.045.634 hoặc -2,045,634.00 hoặc -13.914.047,04)
            num_dots = x.count('.')
            num_commas = x.count(',')
            if num_dots > 0 and num_commas > 0:
                last_dot = x.rfind('.')
                last_comma = x.rfind(',')
                if last_comma > last_dot: # Định dạng VN: 1.234.567,89
                    x = x.replace('.', '').replace(',', '.')
                else: # Định dạng EN: 1,234,567.89
                    x = x.replace(',', '')
            elif num_dots > 1: # Nhiều dấu chấm: 1.234.567 -> bỏ chấm
                x = x.replace('.', '')
            elif num_commas > 1: # Nhiều dấu phẩy: 1,234,567 -> bỏ phẩy
                x = x.replace(',', '')
            elif num_dots == 1:
                # Nếu chỉ có 1 dấu chấm, xem nó là thập phân hay hàng nghìn (VD: -13914047.04 hay 16.000 VNĐ)
                parts = x.split('.')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace('.', '') # 16.000 -> 16000 VNĐ
                else:
                    pass # 12.5 -> 12.5
            elif num_commas == 1:
                parts = x.split(',')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace(',', '') # 16,000 -> 16000 VNĐ
                else:
                    x = x.replace(',', '.') # 12,5 -> 12.5
        try:
            return float(x)
        except:
            return 0.0
    
    def clean_number(x):
        # Hàm dự phòng giữ nguyên tương thích ngược
        return clean_val(x)
    
    # HÀM XỬ LÝ SỐ AN TOÀN CHO BÁO CÁO
    def to_numeric(series):
        if series.dtype == 'object':
            return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return pd.to_numeric(series, errors='coerce').fillna(0)
    
    @st.cache_data(ttl=1)  # Tự động tải lại sau mỗi 1 giây để test
    def load_data_thit_ca_v2(url):
        
        
        def read_csv_with_retry(url, max_retries=3):
            import time
            for i in range(max_retries):
                try:
                    response = requests.get(url, timeout=30, verify=False)
                    response.raise_for_status()
                    # Google Sheets CSV exports are UTF-8 encoded
                    content = response.content.decode('utf-8')
                                    # Dynamic header finding
                    lines = content.split('\n')
                    header_idx = 1
                    for idx, line in enumerate(lines[:10]):
                        if 'Số lượng chuyển' in line or 'Mã hàng' in line:
                            header_idx = idx
                            break
                    return pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
                except Exception as e:
                    if i == max_retries - 1:
                        raise e
                    time.sleep(2)
                    
        df = read_csv_with_retry(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Rename columns to standard ones if needed
        df.rename(columns={
            'ST': 'ID ST',
            'SL chênh lệch CXD': 'SL chênh lệch CXD'
        }, inplace=True)
        
        # Clean numeric columns
        qty_cols = ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Qty_N', 'Qty_O', 'Qty_P', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']
        
        # Clean money columns
        for col in ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', f'Tổng {kho_name.lower()}', 'Tổng chưa xác định']:
            matched_cols = [c for c in df.columns if col.lower() in c.lower()]
            for c in matched_cols:
                df[c] = df[c].apply(clean_val)
                
        df['Số lượng chuyển'] = df['Số lượng chuyển'].apply(clean_qty)
        df['Số lượng nhận'] = df['Số lượng nhận'].apply(clean_qty)
        df['Chênh lệch'] = df['Chênh lệch'].apply(clean_qty)
        
        if 'Chi nhánh nhận' in df.columns:
            df['Chi nhánh nhận'] = df['Chi nhánh nhận'].astype(str).str.replace(',', '.', regex=False)
                
        # Lọc lý do chênh lệch
        df['LyDo_HaoHut'] = df['Hao hụt'].astype(str).str.strip().str.lower()
        df['LyDo_SieuThi'] = df['Siêu thị'].astype(str).str.strip().str.lower()
        
        col_kho_list = [c for c in df.columns if f'{kho_name.upper()}' in c.upper() or 'KHO TH' in c.upper() or 'KHO RAU' in c.upper() or 'KRC' in c.upper()]
        col_kho = col_kho_list[0] if col_kho_list else None
        if col_kho:
            df['LyDo_Kho'] = df[col_kho].astype(str).str.strip().str.lower()
        else:
            df['LyDo_Kho'] = ''
        df['LyDo_Loi'] = df['Lỗi'].astype(str).str.strip().str.lower() if 'Lỗi' in df.columns else ''
        
        col_hao_hut_qty = 'Hạo hụt tự nhiê' if 'Hạo hụt tự nhiê' in df.columns else ('Hạo hụt tự nhiên' if 'Hạo hụt tự nhiên' in df.columns else None)
        df['Qty_N'] = df[col_hao_hut_qty].apply(clean_qty) if col_hao_hut_qty else df['Tổng hao hụt']
        df['Qty_O'] = df['SL trả tồn về ST'].apply(clean_qty) if 'SL trả tồn về ST' in df.columns else df['Tổng ST']
        df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_qty) if 'SL chênh lệch CXD' in df.columns else 0.0
        
        # Kết hợp các cột tổng chênh lệch
        col_total_kho_list = [c for c in df.columns if f'{kho_name}' in c or f'Tổng {kho_name.lower()}' in c or 'Tổng kho rau' in c.lower()]
        col_total_kho = col_total_kho_list[0] if col_total_kho_list else None
        col_total_cxd = [c for c in df.columns if 'Tổng chưa xác định' in c or 'chưa xác định' in c][0]
        
        df['Hao hụt'] = np.where(df['LyDo_HaoHut'].str.contains('hao hụt'), df['Qty_N'], 0)
        df['BS_ST'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị'), df['Qty_O'], 0)
        df['ST_NhapThieu'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        df['ST_SaiQT'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & ~df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        
        import unicodedata
        lydo_kho_nfc = pd.Series([unicodedata.normalize('NFC', str(x)) if pd.notna(x) else '' for x in df['LyDo_Kho']], index=df.index)
        
        kho_lower_nfc = unicodedata.normalize('NFC', kho_name.lower())
        df['Kho_Rau'] = np.where(lydo_kho_nfc.str.contains(kho_lower_nfc) | lydo_kho_nfc.str.contains('kho rau') | lydo_kho_nfc.str.contains('krc'), df['Qty_P'], 0)
        df['CXD'] = np.where(lydo_kho_nfc.str.contains('chưa xác định'), df['Qty_P'], 0)
        
        if col_total_kho:
            df['Tổng kho rau'] = df[col_total_kho].apply(clean_val)
        else:
            df['Tổng kho rau'] = 0.0
        df['Tổng chưa xác định'] = df[col_total_cxd].apply(clean_val)
        
        # Parse dates strictly (Google Sheets sends dates in MM/DD/YYYY format)
        if 'Ngày' in df.columns:
            date_col = 'Ngày'
        elif 'Ngày chuyển hàng' in df.columns:
            date_col = 'Ngày chuyển hàng'
        elif 'Thời gian' in df.columns:
            date_col = 'Thời gian'
        elif 'Ngành' in df.columns:
            date_col = 'Ngành'
        else:
            date_col = 'Ngày'
        
        df['Ngày_parsed'] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
        df['Ngày_str'] = df['Ngày_parsed'].dt.strftime('%d/%m/%Y')
        df['Ngày'] = df['Ngày_parsed']
        df = df[df['Ngày_parsed'].notna()]
        
        # Categories & SKU
        clv2_col = 'CLV2' if 'CLV2' in df.columns else ('Loại hàng' if 'Loại hàng' in df.columns else 'Unnamed: 0')
        df['CLV2'] = df[clv2_col].fillna('Chưa phân loại')
        
        clv4_col = 'CLV4' if 'CLV4' in df.columns else 'CLV2'
        df['CLV4'] = df[clv4_col].fillna('Chưa phân loại')
        
        ten_hang_col = [c for c in df.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
        df['SKU_Full'] = df['Mã hàng'].fillna('').astype(str) + " - " + df[ten_hang_col].fillna('').astype(str)
        
        return df
    
    # HÀM TÍNH TOÁN NĂNG SUẤT DAILY MỚI
    def calculate_daily_metrics(data, group_by_col='CLV2'):
        if data.empty:
            return pd.DataFrame(columns=[
                group_by_col, 'SL chuyển', 'SL chênh lệch', 'GT chênh lệch', 
                'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 
                'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'Số lượng hao hụt', 
                'GT hao hụt', 'Tỷ lệ hao hụt', 'SL bs ST', 'GT bs ST', 
                'SL bs kho rau', 'GT bs kho rau', 'Đang xử lý', 'GT Đang xử lý', 
                'Chưa xử lý', 'GT Chưa xử lý', 'Không xử lý (WRITE OFF)', 'Giá trị WRITE OFF',
                'Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 'GT Lỗi ST (Nhập thiếu)', 'GT Lỗi ST (Sai QT)'
            ])
        
        df = data.copy()
        df['SL_chuyen_num'] = to_numeric(df['Số lượng chuyển'])
        df['CL_num'] = to_numeric(df['Chênh lệch'])
        df['GT_num'] = to_numeric(df['Tổng GT'])
        df['HH_qty'] = to_numeric(df['Hao hụt'])
        df['HH_val'] = to_numeric(df['Tổng hao hụt'])
        df['ST_qty'] = to_numeric(df['BS_ST'])
        df['ST_val'] = to_numeric(df['Tổng ST'])
        df['Kho_qty'] = to_numeric(df['Kho_Rau'])
        df['Kho_val'] = to_numeric(df['Tổng kho rau'])
        df['CXD_qty'] = to_numeric(df['CXD'])
        df['CXD_val'] = to_numeric(df['Tổng chưa xác định'])
        
        df['ST_NhapThieu_qty'] = to_numeric(df['ST_NhapThieu']) if 'ST_NhapThieu' in df.columns else 0.0
        df['ST_SaiQT_qty'] = to_numeric(df['ST_SaiQT']) if 'ST_SaiQT' in df.columns else 0.0
        
        price_col = 'Giá nhập \n( -VAT)' if 'Giá nhập \n( -VAT)' in df.columns else None
        if price_col:
            df['ST_NhapThieu_val'] = df['ST_NhapThieu_qty'] * to_numeric(df[price_col])
            df['ST_SaiQT_val'] = df['ST_SaiQT_qty'] * to_numeric(df[price_col])
        else:
            df['ST_NhapThieu_val'] = 0.0
            df['ST_SaiQT_val'] = 0.0
            
        df['Xuly_clean'] = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        
        groups = df.groupby(group_by_col, dropna=False)
        rows = []
        
        for g_name, g_df in groups:
            cl_df = g_df[g_df['CL_num'].abs() > 0]
            sl_chuyen = g_df['SL_chuyen_num'].sum()
            sl_cl = g_df['CL_num'].sum()
            gt_cl = g_df['GT_num'].sum()
            
            sl_st_cl = cl_df['ID ST'].nunique()
            sl_line_cl = len(cl_df)
            sl_line_hh = len(g_df[g_df['HH_qty'].abs() > 0])
            
            done_df = g_df[g_df['Xuly_clean'].str.contains('hoàn thành')]
            sl_line_done = len(done_df)
            tyle_line_done = f"{(sl_line_done / sl_line_cl * 100):.2f}%" if sl_line_cl > 0 else "0.00%"
            
            sl_hh = g_df['HH_qty'].sum()
            gt_hh = g_df['HH_val'].sum()
            tyle_hh = f"{(sl_hh / sl_chuyen * 100):.2f}%" if sl_chuyen > 0 else "0.00%"
            
            sl_bs_st = g_df['ST_qty'].sum()
            gt_bs_st = g_df['ST_val'].sum()
            sl_bs_kho = g_df['Kho_qty'].sum()
            gt_bs_kho = g_df['Kho_val'].sum()
            
            sl_st_nhap = g_df['ST_NhapThieu_qty'].sum()
            sl_st_sai = g_df['ST_SaiQT_qty'].sum()
            gt_st_nhap = g_df['ST_NhapThieu_val'].sum()
            gt_st_sai = g_df['ST_SaiQT_val'].sum()
            
            # Đang xử lý
            dang_xl_df = g_df[g_df['Xuly_clean'].str.contains('đang chuyển') | g_df['Xuly_clean'].str.contains('đang xử lý')]
            sl_dang_xl = dang_xl_df['CL_num'].sum()
            gt_dang_xl = dang_xl_df['GT_num'].sum()
            
            # Không xử lý (Write Off)
            write_off_df = g_df[g_df['Xuly_clean'].str.contains('không xử lý') | g_df['Xuly_clean'].str.contains('write of')]
            sl_write_off = write_off_df['CL_num'].sum()
            gt_write_off = write_off_df['GT_num'].sum()
            
            # Chưa xử lý
            chua_xl_df = g_df[~g_df['Xuly_clean'].str.contains('hoàn thành') & 
                              ~g_df['Xuly_clean'].str.contains('đang chuyển') & 
                              ~g_df['Xuly_clean'].str.contains('đang xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('không xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('write of')]
            sl_chua_xl = chua_xl_df['CL_num'].sum()
            gt_chua_xl = chua_xl_df['GT_num'].sum()
            
            row = {
                group_by_col: g_name,
                'SL chuyển': sl_chuyen,
                'SL chênh lệch': sl_cl,
                'GT chênh lệch': gt_cl,
                'SL ST chênh lệch': sl_st_cl,
                'SL line chênh lệch': sl_line_cl,
                'SL line hao hụt': sl_line_hh,
                'SL line đã xử lý': sl_line_done,
                'Tỷ lệ line đã xử lý': tyle_line_done,
                'Số lượng hao hụt': sl_hh,
                'GT hao hụt': gt_hh,
                'Tỷ lệ hao hụt': tyle_hh,
                'SL bs ST': sl_bs_st,
                'GT bs ST': gt_bs_st,
                'SL bs kho rau': sl_bs_kho,
                'GT bs kho rau': gt_bs_kho,
                'Đang xử lý': sl_dang_xl,
                'GT Đang xử lý': gt_dang_xl,
                'Chưa xử lý': sl_chua_xl,
                'GT Chưa xử lý': gt_chua_xl,
                'Không xử lý (WRITE OFF)': sl_write_off,
                'Giá trị WRITE OFF': gt_write_off,
                'Lỗi ST (Nhập thiếu)': sl_st_nhap,
                'Lỗi ST (Sai QT)': sl_st_sai,
                'GT Lỗi ST (Nhập thiếu)': gt_st_nhap,
                'GT Lỗi ST (Sai QT)': gt_st_sai
            }
            rows.append(row)
            
        return pd.DataFrame(rows)
    
    # HÀM HIỂN THỊ BẢNG DAILY
    def display_daily_table(df, cols, title_prefix, group_by_col='CLV2'):
        if df.empty:
            st.info("Không có dữ liệu.")
            return
        df_to_show = df.copy()
        for col in cols:
            if col not in df_to_show.columns:
                df_to_show[col] = 0.0
        df_to_show = df_to_show[cols]
        format_custom_table_with_total(df_to_show, group_by_col, title_prefix)
    
    # HÀM TÍNH TỔNG QUAN DAILY DẠNG TEXT
    def compute_daily_summary(df, date_str):
        if df.empty:
            return None
        
        cl_qty = to_numeric(df['Chênh lệch'])
        gt_val = to_numeric(df['Tổng GT'])
        
        total_items = cl_qty.abs().sum()
        total_value = gt_val.abs().sum()
        
        xuly_clean = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        df_done = df[xuly_clean.str.contains('hoàn thành')]
        
        ret_qty = to_numeric(df_done['Kho_Rau']).abs().sum()
        bs_qty = to_numeric(df_done['BS_ST']).abs().sum()
        lost_qty = to_numeric(df_done['Hao hụt']).abs().sum()
        
        processed_qty = ret_qty + bs_qty + lost_qty
        remaining_qty = total_items - processed_qty
        if remaining_qty < 0:
            remaining_qty = 0.0
            
        return {
            'date': date_str,
            'total_items': int(total_items),
            'total_value': total_value,
            'processed': int(processed_qty),
            'return': int(ret_qty),
            'bs': int(bs_qty),
            'lost': int(lost_qty),
            'remaining': int(remaining_qty)
        }
    
    # Insight Generators y hệt bên Kho Rau
    def generate_insights(df_raw, table_type, df_grouped=None, df_metrics=None, date_str=None):
        if df_raw.empty and (df_grouped is None or df_grouped.empty):
            return "Không có dữ liệu trong kỳ báo cáo này."
        
        def get_hh_insight():
            if df_metrics is not None and not df_metrics.empty and 'Số lượng chuyển' in df_metrics.columns and 'Số lượng hao hụt' in df_metrics.columns:
                tong_chuyen = df_metrics['Số lượng chuyển'].sum()
                tong_hh = df_metrics['Số lượng hao hụt'].sum()
                if tong_chuyen > 0:
                    return f"\n- Tỷ lệ hao hụt ghi nhận: {round((tong_hh / tong_chuyen) * 100, 2)}%."
            return ""
        
        try:
            if table_type == "Bảng 1":
                df_raw_tmp = df_raw.copy()
                df_raw_tmp['Chênh_lệch_num'] = to_numeric(df_raw_tmp['Chênh lệch'])
                df_raw_tmp['Kho_Rau_num'] = to_numeric(df_raw_tmp['Kho_Rau'])
                df_raw_tmp['BS_ST_num'] = to_numeric(df_raw_tmp['BS_ST'])
                
                total_lines = len(df_raw_tmp)
                total_chenh_lech = df_raw_tmp['Chênh_lệch_num'].sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                msg = f"Trong kỳ có tổng cộng {total_lines} dòng phát sinh chênh lệch (Tổng chênh lệch: {fmt(total_chenh_lech)}).\n"
                msg += "\n- Phân tích 3 nhóm ngành hàng (CLV4) phát sinh chênh lệch cao nhất:\n"
                
                clv4_lines = df_raw_tmp['CLV4'].value_counts()
                top3_clv4 = clv4_lines.head(3)
                
                for clv4, lines in top3_clv4.items():
                    sub_df = df_raw_tmp[df_raw_tmp['CLV4'] == clv4]
                    sub_cl = sub_df['Chênh_lệch_num'].sum()
                    sub_kr = sub_df['Kho_Rau_num'].sum()
                    msg += f"  + [{clv4}]: {lines} dòng (Tổng chênh lệch: {fmt(sub_cl)} | Trả về {kho_name.lower()}: {fmt(sub_kr)})\n"
                    
                msg += "\n- Phân bổ trả về Siêu Thị (ST):\n"
                st_by_clv4 = df_raw_tmp.groupby('CLV4')['BS_ST_num'].sum().sort_values(ascending=False)
                st_by_clv4 = st_by_clv4[st_by_clv4 > 0]
                
                if not st_by_clv4.empty:
                    top_st_clv4 = st_by_clv4.index[0]
                    top_st_val = st_by_clv4.iloc[0]
                    total_st = st_by_clv4.sum()
                    if top_st_val > (total_st * 0.3) and len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST tập trung nhiều nhất ở nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                    elif len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST nằm rải rác lẻ tẻ (cao nhất là [{top_st_clv4}] với {fmt(top_st_val)}).\n"
                    else:
                        msg += f"  Số lượng trả về ST thuộc về nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                else:
                    msg += "  Không phát sinh số lượng chênh lệch trả về ST trong kỳ.\n"
                    
                msg += "  -> Nguyên nhân: Do ST thao tác sai nên phải tạo lại thôi."
                msg += get_hh_insight()
                return msg
                
            elif table_type == "Bảng 1.1":
                if df_grouped is not None and not df_grouped.empty:
                    top_nguon = df_grouped.iloc[0]['Nguồn xác nhận']
                    top_sl = df_grouped.iloc[0]['Tổng ({kho_name.lower()} + ST)'] if 'Tổng ({kho_name.lower()} + ST)' in df_grouped.columns else df_grouped.iloc[0]['Tổng (Kho Rau + ST)']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    if top_nguon == 'Check camera':
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Việc dựa phần lớn vào Check camera cho thấy tình trạng ST báo thiếu/dư hàng nhưng không cung cấp đủ hình ảnh xác thực đang khá cao. Cần nhắc nhở ST tuân thủ quy định chụp hình."
                    else:
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là dựa vào [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Điều này phản ánh cơ sở dữ liệu chính yếu mà DC dùng để đối soát và phân bổ lượng hàng chênh lệch trong kỳ."
                
            elif table_type == "Bảng 2.1_New":
                if df_metrics is not None and not df_metrics.empty:
                    t_cl = df_metrics['SL chênh lệch'].sum()
                    if t_cl > 0:
                        l_st_nhap = df_metrics.get('Lỗi ST (Nhập thiếu)', pd.Series([0])).sum()
                        l_st_sai = df_metrics.get('Lỗi ST (Sai QT)', pd.Series([0])).sum()
                        l_st_tong = l_st_nhap + l_st_sai
                        pct_st = (l_st_tong / t_cl) * 100
                        pct_nhap = (l_st_nhap / t_cl) * 100
                        pct_sai = (l_st_sai / t_cl) * 100
                        
                        giao_thieu_5 = df_metrics.get('<= 5%', pd.Series([0])).sum()
                        giao_thieu_10 = df_metrics.get('5-10%', pd.Series([0])).sum()
                        giao_thieu_15 = df_metrics.get('10-15%', pd.Series([0])).sum()
                        giao_thieu_15_plus = df_metrics.get('> 15%', pd.Series([0])).sum()
                        
                        pct_5 = (giao_thieu_5 / t_cl) * 100
                        pct_10 = (giao_thieu_10 / t_cl) * 100
                        pct_15 = (giao_thieu_15 / t_cl) * 100
                        pct_15_plus = (giao_thieu_15_plus / t_cl) * 100
                        
                        d_str = "kỳ báo cáo"
                        if date_str and date_str != "Tất cả các ngày":
                            try:
                                d_str = "ngày " + date_str.split('/')[0] + "." + date_str.split('/')[1]
                            except:
                                d_str = "ngày " + str(date_str)
                                
                        def get_top_clv4(col):
                            if col in df_metrics.columns and df_metrics[col].max() > 0:
                                top_row = df_metrics.loc[df_metrics[col].idxmax()]
                                return f"[{top_row['CLV4']}] - {int(top_row[col])} item"
                            return ""
                            
                        top_5_clv4 = get_top_clv4('<= 5%')
                        top_10_clv4 = get_top_clv4('5-10%')
                        top_15_clv4 = get_top_clv4('10-15%')
                        top_15_plus_clv4 = get_top_clv4('> 15%')
                                
                        msg = f"Hàng KG có số lượng nhập nhưng phát sinh chênh lệch ghi nhận {d_str}\n"
                        msg += f"- Lỗi ST chiếm {pct_st:.1f}%: trong đó nhập sót {pct_nhap:.1f}% và sai QT chiếm {pct_sai:.1f}%\n"
                        if l_st_sai > 0:
                            msg += f"  + SL ST sai QT: {int(l_st_sai)}\n"
                        msg += f"- Giao thiếu:\n"
                        msg += f"  + Nhóm <= 5%: {pct_5:.1f}%\n"
                        if top_5_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_5_clv4}\n"
                        msg += f"  + Nhóm 5 - 10%: {pct_10:.1f}%\n"
                        if top_10_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_10_clv4}\n"
                        msg += f"  + Nhóm 10 - 15%: {pct_15:.1f}%\n"
                        if top_15_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_15_clv4}\n"
                        msg += f"  + Nhóm > 15%: {pct_15_plus:.1f}%"
                        if top_15_plus_clv4: msg += f"\n    -> Nhóm lệch nhiều nhất: {top_15_plus_clv4}"
                        return msg
                return "Chưa có đủ dữ liệu để đánh giá."
                
            elif table_type == "Bảng 2.1":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                return f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh." + get_hh_insight()
                
            elif table_type == "Bảng 3":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                base_msg = f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh."
                
                df_kr = df_raw.copy()
                df_kr['Kho_Rau_num'] = to_numeric(df_kr['Kho_Rau'])
                kr_by_clv4 = df_kr.groupby('CLV4')['Kho_Rau_num'].sum().sort_values(ascending=False)
                kr_by_clv4 = kr_by_clv4[kr_by_clv4 > 0]
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                if not kr_by_clv4.empty:
                    top3 = kr_by_clv4.head(3)
                    top3_msg = "\n- Top nhóm ngành hàng (CLV4) đang có lượng chênh lệch trả về {kho_name.lower()} cao nhất:\n"
                    for i, (clv4, val) in enumerate(top3.items(), 1):
                        top3_msg += f"  {i}. {clv4}: {fmt(val)}\n"
                else:
                    top3_msg = "\n- Không ghi nhận hàng Pack nào có chênh lệch trả về {kho_name.lower()} trong kỳ."
                    
                return base_msg + top3_msg.rstrip() + get_hh_insight()
                
            elif table_type == "Bảng 2.2":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                sum_kr = to_numeric(df_raw['Kho_Rau']).sum()
                sum_st = to_numeric(df_raw['BS_ST']).sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                return (f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n"
                        f"- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh.\n"
                        f"- Vấn đề chênh lệch này được phân bổ xử lý như sau:\n"
                        f"  + Trả về ST (Số lượng: {fmt(sum_st)}): Lý do là DC giao bù do ban đầu giao sai điểm.\n"
                        f"  + Trả {kho_name.lower()} (Số lượng: {fmt(sum_kr)}): Do có ST khác nhận dư số này và có ST nhận thiếu."
                        f"{get_hh_insight()}")
                
            elif table_type == "Bảng 4":
                if df_grouped is not None and not df_grouped.empty:
                    top_sku = df_grouped.iloc[0]['Mã & Tên hàng']
                    top_hh = df_grouped.iloc[0]['Tổng số lượng hao hụt']
                    
                    clv4_counts = df_raw['CLV4'].value_counts()
                    top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                    
                    return f"- Top 3 ngành hàng (CLV4) phát sinh hao hụt nhiều nhất: {top3_clv4_str}.\n- Mã hàng có sản lượng hao hụt nghiêm trọng nhất là [{top_sku}] (Hao hụt: {top_hh} KG).\n- Khuyến nghị: Cần ưu tiên kiểm tra chất lượng thực tế và quy trình đóng gói đối với mã hàng này."
    
            elif table_type == "Bảng 6":
                if df_grouped is not None and not df_grouped.empty:
                    top_dc = df_grouped.iloc[0]['DC xác nhận']
                    top_loi = df_grouped.iloc[0]['Lỗi'] if 'Lỗi' in df_grouped.columns else ('Nhom_Loi' if 'Nhom_Loi' in df_grouped.columns else 'Không phân loại')
                    top_sl = df_grouped.iloc[0]['Tổng số lượng']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    return f"- Dựa trên xác nhận của DC, lỗi [{top_loi}] được ghi nhận nhiều nhất từ [{top_dc}] với tổng số lượng trả về {kho_name.lower()} là {fmt(top_sl)}.\n- Khuyến nghị: DC cần kiểm tra lại quy trình xuất hàng và kiểm đếm để giảm thiểu tình trạng này."
    
        except Exception as e:
            return "Chưa đủ dữ liệu để tạo nhận xét tự động."
            
        return ""
    
    def render_dc_feedback_progress_report(df, tab_id=""):
        st.write("---")
        
        if df.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi.")
            return
            
        # Tính toán daily summary (Toàn hệ thống)
        df['GT_chuyen_temp'] = to_numeric(df.get('Số lượng chuyển', pd.Series(0, index=df.index))) * to_numeric(df.get('Giá trị ĐV', pd.Series(0, index=df.index)))
        daily_summary = df.groupby('Ngày_str').agg(
            SL_chuyen=('Số lượng chuyển', lambda x: to_numeric(x).sum()),
            SL_chenh_lech=('Chênh lệch', lambda x: to_numeric(x).sum()),
            GT_chuyen=('GT_chuyen_temp', 'sum'),
            GT_chenh_lech=('Tổng GT', lambda x: to_numeric(x).sum())
        ).reset_index()
    
        df_dc = df[to_numeric(df.get('Kho_Rau', pd.Series(0, index=df.index))) > 0].copy()
        df_dc['SL_CXD'] = to_numeric(df_dc.get('Kho_Rau', pd.Series(0, index=df_dc.index)))
        df_dc['GT_CXD'] = to_numeric(df_dc.get('Tổng kho rau', pd.Series(0, index=df_dc.index)))
            
        if df_dc.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi trong kỳ báo cáo này.")
            return
            
        df_dc['DC_Xac_Nhan'] = df_dc['DC xác nhận'].fillna('Chưa xác nhận')
        df_dc['DC_Xac_Nhan'] = df_dc['DC_Xac_Nhan'].apply(lambda x: 'Chưa xác nhận' if str(x).strip() == '' else x)
        loi_col = 'Lỗi' if 'Lỗi' in df_dc.columns else ('LyDo_Loi' if 'LyDo_Loi' in df_dc.columns else None)
        if loi_col:
            df_dc['Nhom_Loi'] = df_dc[loi_col].fillna('Không phân loại').replace('', 'Không phân loại')
        else:
            df_dc['Nhom_Loi'] = 'Không phân loại'
        df_dc['Chi_Tiet_Loi'] = 'Không ghi chú'
        
        df_chua_xn = df_dc[df_dc['DC_Xac_Nhan'] == 'Chưa xác nhận']
        tong_chua_xn = df_chua_xn['SL_CXD'].sum()
        tong_gt_chua_xn = df_chua_xn['GT_CXD'].sum()
        
        top_loi_name = "Không có"
        if not df_chua_xn.empty:
            loi_sum = df_chua_xn.groupby('Nhom_Loi')['SL_CXD'].sum()
            if not loi_sum.empty and loi_sum.max() > 0:
                top_loi_name = f"{loi_sum.idxmax()} ({int(loi_sum.max())} item)"
                
        # Hiển thị Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🔴 Tổng chờ DC xác nhận", value=f"{int(tong_chua_xn)} item", delta=f"{format_vn(tong_gt_chua_xn)} VNĐ", delta_color="off")
        with col2:
            st.metric(label="🔥 Top 1 Lỗi chờ phản hồi", value=top_loi_name)
        
        st.write("### 📌 Bảng chi tiết (Tiến độ DC)")
        tab_ngay, tab_loi = st.tabs(["📅 Góc nhìn 1: Theo Ngày", "⚠️ Góc nhìn 2: Theo Nhóm Lỗi"])
        
        # Góc nhìn 1
        with tab_ngay:
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_ngay = pd.pivot_table(df_dc, values='SL_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            dc_cols = [c for c in pivot_ngay.columns if c != 'Ngày_str']
            pivot_ngay['SL {kho_name.upper()}'] = pivot_ngay[dc_cols].sum(axis=1)
            
            final_ngay = pd.merge(daily_summary[['Ngày_str', 'SL_chuyen', 'SL_chenh_lech']], pivot_ngay, on='Ngày_str', how='right')
            sorted_dc_cols = [c for c in dc_cols if c != 'Chưa xác nhận']
            sorted_dc_cols.sort()
            if 'Chưa xác nhận' in dc_cols:
                sorted_dc_cols = ['Chưa xác nhận'] + sorted_dc_cols
                
            col_order = ['Ngày_str', 'SL_chuyen', 'SL_chenh_lech', 'SL {kho_name.upper()}'] + sorted_dc_cols
            final_ngay = final_ngay[[c for c in col_order if c in final_ngay.columns]]
            
            final_ngay['% Chưa xác nhận'] = final_ngay.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay['% Tiến độ phản hồi'] = final_ngay.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'SL_chuyen': 'SL chuyển',
                'SL_chenh_lech': 'SL chênh lệch'
            }, inplace=True)
            format_custom_table_with_total(final_ngay, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_ngay_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_ngay_gt['GT {kho_name.upper()}'] = pivot_ngay_gt[dc_cols].sum(axis=1)
            final_ngay_gt = pd.merge(daily_summary[['Ngày_str', 'GT_chuyen', 'GT_chenh_lech']], pivot_ngay_gt, on='Ngày_str', how='right')
            
            col_order_gt = ['Ngày_str', 'GT_chuyen', 'GT_chenh_lech', 'GT {kho_name.upper()}'] + sorted_dc_cols
            final_ngay_gt = final_ngay_gt[[c for c in col_order_gt if c in final_ngay_gt.columns]]
            
            final_ngay_gt['% Chưa xác nhận'] = final_ngay_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay_gt['% Tiến độ phản hồi'] = final_ngay_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay_gt.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'GT_chuyen': 'GT chuyển (VNĐ)',
                'GT_chenh_lech': 'GT chênh lệch (VNĐ)'
            }, inplace=True)
            format_custom_table_with_total(final_ngay_gt, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_GT_{tab_id}")
            
        # Góc nhìn 2
        with tab_loi:
            df_dc['Nhóm Lỗi & Chi tiết'] = df_dc['Nhom_Loi'] + " | " + df_dc['Chi_Tiet_Loi']
            
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_loi = pd.pivot_table(df_dc, values='SL_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi['SL {kho_name.upper()}'] = pivot_loi[dc_cols].sum(axis=1)
            col_order_loi = ['Nhóm Lỗi & Chi tiết', 'SL {kho_name.upper()}'] + sorted_dc_cols
            pivot_loi = pivot_loi[[c for c in col_order_loi if c in pivot_loi.columns]]
            
            pivot_loi['% Chưa xác nhận'] = pivot_loi.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi['% Tiến độ phản hồi'] = pivot_loi.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_loi_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi_gt['GT {kho_name.upper()}'] = pivot_loi_gt[dc_cols].sum(axis=1)
            pivot_loi_gt = pivot_loi_gt[[c for c in col_order_loi if c in pivot_loi_gt.columns]]
            pivot_loi_gt.rename(columns={'SL {kho_name.upper()}': 'GT {kho_name.upper()}'}, inplace=True)
            
            pivot_loi_gt['% Chưa xác nhận'] = pivot_loi_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi_gt['% Tiến độ phản hồi'] = pivot_loi_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi_gt, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_GT_{tab_id}")
    
    # Format màu đỏ cho số chênh lệch
    def color_red_for_chenhlech(val):
        color = 'red' if isinstance(val, (int, float)) and val > 0 else ''
        return f'color: {color}'
    
    # Format số theo chuẩn Việt Nam (1.000.000,00)
    def format_vn(val):
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float, np.integer, np.floating)):
            if val == int(val):
                return f"{int(val):,}".replace(',', '.')
            else:
                formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                if formatted.endswith(',00'):
                    return formatted[:-3]
                return formatted
        return val
    
    def format_money(val):
        if val >= 1000000:
            return f"{val/1000000:.1f} triệu".replace('.', ',')
        elif val >= 1000:
            return f"{val/1000:.1f} ngàn".replace('.', ',')
        return format_vn(val)
    
    def format_custom_table_with_total(df, name_col, title_prefix):
        if df.empty: return
        
        tong_df = pd.DataFrame(index=[0])
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                tong_df[col] = df[col].sum()
            else:
                tong_df[col] = ''
                
        tuples = []
        for col in df.columns:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    total_str = f"🟡 {format_vn(val)}"
                else:
                    total_str = f"🟡 {str(val)}"
            else:
                total_str = '⭐ TỔNG' if col == name_col else ''
                
            tuples.append((total_str, col))
            
        df_renamed = df.copy()
        df_renamed.columns = pd.MultiIndex.from_tuples(tuples)
        styler = df_renamed.style.format(format_vn).hide(axis="index")
        display_df_with_download(styler, f"Daily_{title_prefix}")
    
    # ==========================================
    # GIAO DIỆN CHIA TAB
    # ==========================================
    
    
    try:
        df_all = load_data_thit_ca_v2(data_url)
        st.sidebar.success(f"Tải dữ liệu từ Google Sheets thành công!")
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu Google Sheets: {e}")
        st.stop()
    
    tab_main, tab_daily, tab_dc = st.tabs(["📊 Báo Cáo Tổng Quan", "📈 Báo Cáo Năng Suất Daily", "👨‍🔧 Tiến Độ DC Phản Hồi"])
    
    # ==========================================
    # TRANG 1: BÁO CÁO TỔNG QUAN
    # ==========================================
    with tab_main:
        # Nút Cập nhật dữ liệu mới nhất
        if st.button('🔄 Cập nhật dữ liệu mới nhất'):
            st.cache_data.clear()
            st.rerun()
            
        df_active = df_all.copy()
    
        # Process Dataframes
        pivot_ngay_sum = df_active.groupby('Ngày_str')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_ngay = pivot_ngay_sum.fillna(0).reset_index()
        
        pivot_ngay['Ngày_dt'] = pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay = pivot_ngay.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        # Tính phần trăm đã phân bổ / chênh lệch cho từng ngày
        sum_dist = pivot_ngay['Hao hụt'] + pivot_ngay['BS_ST'] + pivot_ngay['Kho_Rau'] + pivot_ngay['CXD']
        pct_vals = np.where(pivot_ngay['Chênh lệch'].abs() > 0, (sum_dist / pivot_ngay['Chênh lệch'].abs()) * 100, 0.0)
        pivot_ngay['% Cột Tổng'] = [f"{v:.2f}%".replace('.', ',') for v in pct_vals]
    
        tong_row_ngay = pivot_ngay.sum(numeric_only=True).to_frame().T
        tong_row_ngay['Ngày_str'] = 'Tổng'
        
        # Tính phần trăm đã phân bổ / chênh lệch cho hàng Tổng
        total_sum_dist = tong_row_ngay['Hao hụt'].iloc[0] + tong_row_ngay['BS_ST'].iloc[0] + tong_row_ngay['Kho_Rau'].iloc[0] + tong_row_ngay['CXD'].iloc[0]
        total_cl = abs(tong_row_ngay['Chênh lệch'].iloc[0])
        total_pct = (total_sum_dist / total_cl) * 100 if total_cl > 0 else 0.0
        tong_row_ngay['% Cột Tổng'] = f"{total_pct:.2f}%".replace('.', ',')
    
        pivot_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        tong_row_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
    
        # Theo ngày (Giá trị)
        pivot_ngay_val = df_active.groupby('Ngày_str')[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_ngay_val['Ngày_dt'] = pd.to_datetime(pivot_ngay_val['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay_val = pivot_ngay_val.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        tong_row_ngay_val = pivot_ngay_val.sum(numeric_only=True).to_frame().T
        if not tong_row_ngay_val.empty: tong_row_ngay_val['Ngày_str'] = 'Tổng'
    
        pivot_ngay_val.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
            'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
            'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
        }, inplace=True)
        if not tong_row_ngay_val.empty:
            tong_row_ngay_val.rename(columns={
                'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
                'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
                'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
                'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
            }, inplace=True)
    
        # Theo CLV2
        pivot_clv2_sum = df_active.groupby('CLV2', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
        pivot_clv2_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('CLV2', dropna=False).size().rename('Số lượng line')
        pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
        pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
        pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False)
        
        tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
        tong_row_clv2['CLV2'] = 'Tổng'
    
        # Top 5 CLV4
        clv4_sum = df_active.groupby('CLV4', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
        clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
        pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)
    
        # Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
        pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line chênh lệch')
        pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line nhập=0')
    
        pivot_qty = pivot_qty_sum.join(pivot_qty_count).join(pivot_qty_nhap0).fillna(0).reset_index()
        pivot_qty.rename(columns={
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty['Tỷ lệ (%)'] = np.where(pivot_qty['Số lượng chuyển'] > 0, (pivot_qty['Chênh lệch'] / pivot_qty['Số lượng chuyển']) * 100, 0)
        pivot_qty['Abs_ChenhLech'] = pivot_qty['Chênh lệch'].abs()
        pivot_qty = pivot_qty.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty['SL line chênh lệch'] = pivot_qty['SL line chênh lệch'].astype(int)
        pivot_qty['SL line nhập=0'] = pivot_qty['SL line nhập=0'].astype(int)
        pivot_qty.insert(3, 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', pivot_qty['SL line nhập=0'].astype(str) + " / " + pivot_qty['SL line chênh lệch'].astype(str))
        pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        # Bảng GIÁ TRỊ Chi tiết Từng Ngày - Siêu Thị
        pivot_val_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)
    
        # Thẻ thông tin (Metrics)
        st.write("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng số lượng chuyển", format_vn(df_active['Số lượng chuyển'].sum()))
        with col2:
            st.metric("Tổng số lượng nhận", format_vn(df_active['Số lượng nhận'].sum()))
        with col3:
            st.metric("TỔNG CHÊNH LỆCH", format_vn(df_active['Chênh lệch'].sum()))
    
        def create_multiindex_headers(df, tong_df):
            if df.empty or tong_df.empty: return df
            tuples = []
            for i, col in enumerate(df.columns):
                if col in tong_df.columns:
                    val = tong_df.iloc[0][col]
                    if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                        if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                            tuples.append((f"🟡 {format_vn(val)}", col))
                        else:
                            tuples.append((f"🟡 {str(val)}", col))
                    else:
                        tuples.append(('⭐ TỔNG' if i == 0 else '', col))
                else:
                    tuples.append(('⭐ TỔNG' if i == 0 else '', col))
            df_new = df.copy()
            df_new.columns = pd.MultiIndex.from_tuples(tuples)
            return df_new
    
        pivot_ngay_renamed = create_multiindex_headers(pivot_ngay, tong_row_ngay)
        pivot_ngay_val_renamed = create_multiindex_headers(pivot_ngay_val, tong_row_ngay_val)
        pivot_clv2_renamed = create_multiindex_headers(pivot_clv2, tong_row_clv2)
    
        # Layout các bảng
        st.write("---")
        st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
        
        if not pivot_ngay.empty:
            top_day = pivot_ngay.sort_values(by='Chênh lệch', ascending=False).iloc[0]
            st.info(f"🔹 **Ngày biến động nhất**: **{top_day['Ngày_str']}** ghi nhận mức chênh lệch cao nhất ({format_vn(top_day['Chênh lệch'])} item).")
    
        tab_ngay_qty, tab_ngay_val = st.tabs(["📊 Số lượng (Từng Ngày)", "💰 Giá trị (Từng Ngày)"])
    
        with tab_ngay_qty:
            display_df_with_download(pivot_ngay_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_ngay_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_Theo_Ngay_So_Luong")
    
        with tab_ngay_val:
            display_df_with_download(pivot_ngay_val_renamed.style.format(format_vn), "Tong_Hop_Theo_Ngay_Gia_Tri")
    
        st.write("---")
        col4, col5 = st.columns(2)
        with col4:
            st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
            if not pivot_clv4.empty:
                top_clv4 = pivot_clv4.iloc[0]
                st.info(f"🔹 **Mã hàng (CLV4) cảnh báo đỏ**: **{top_clv4['CLV4']}** đang dẫn đầu với mức chênh lệch {format_vn(top_clv4['Chênh lệch'])}.")
            display_df_with_download(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), "Top_5_CLV4")
        with col5:
            st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
            if not pivot_clv2.empty:
                top_clv2 = pivot_clv2.iloc[0]
                st.info(f"🔹 **Ngành hàng (CLV2) trọng điểm**: **{top_clv2['CLV2']}** chiếm số lượng chênh lệch cao nhất ({format_vn(top_clv2['Chênh lệch'])}).")
            display_df_with_download(pivot_clv2_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_clv2_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_CLV2")
    
        st.write("---")
        # Sort dates chronologically
        sorted_dates_dt = sorted(pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce').dropna().unique())
        sorted_dates = [d.strftime('%d/%m/%Y') for d in sorted_dates_dt if d.strftime('%d/%m/%Y') != 'Tổng']
        dates = ["Tất cả các ngày"] + sorted_dates
    
        # 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)
        st.subheader("🛒 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)")
        item_qty_sum = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        item_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST chênh lệch')
        item_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_item = item_qty_sum.join(item_qty_count).join(item_qty_nhap0).fillna(0).reset_index()
        pivot_qty_item.rename(columns={
            'CLV4': 'Mã hàng (CLV4)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_item['Tỷ lệ (%)'] = np.where(pivot_qty_item['Số lượng chuyển'] > 0, (pivot_qty_item['Chênh lệch'] / pivot_qty_item['Số lượng chuyển']) * 100, 0)
        pivot_qty_item['Abs_ChenhLech'] = pivot_qty_item['Chênh lệch'].abs()
        pivot_qty_item = pivot_qty_item.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_item['SL ST chênh lệch'] = pivot_qty_item['SL ST chênh lệch'].astype(int)
        pivot_qty_item['SL ST nhập=0'] = pivot_qty_item['SL ST nhập=0'].astype(int)
        pivot_qty_item.insert(2, 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', pivot_qty_item['SL ST nhập=0'].astype(str) + " / " + pivot_qty_item['SL ST chênh lệch'].astype(str))
        pivot_qty_item = pivot_qty_item[['Ngày_str', 'Mã hàng (CLV4)', 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        pivot_val_item = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_item.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'CLV4': 'Mã hàng (CLV4)'}, inplace=True)
    
        selected_date_item = st.selectbox("🔍 Lọc theo Ngày (Mã hàng):", dates)
        if selected_date_item != "Tất cả các ngày":
            filtered_qty_item = pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item]
            filtered_val_item = pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item]
        else:
            filtered_qty_item = pivot_qty_item
            filtered_val_item = pivot_val_item
    
        tong_qty_item = pd.DataFrame() if filtered_qty_item.empty else filtered_qty_item.sum(numeric_only=True).to_frame().T
        if not tong_qty_item.empty: tong_qty_item['Ngày_str'] = 'Tổng'
        filtered_qty_item_renamed = create_multiindex_headers(filtered_qty_item, tong_qty_item)
    
        tong_val_item = pd.DataFrame() if filtered_val_item.empty else filtered_val_item.sum(numeric_only=True).to_frame().T
        if not tong_val_item.empty: tong_val_item['Ngày_str'] = 'Tổng'
        filtered_val_item_renamed = create_multiindex_headers(filtered_val_item, tong_val_item)
    
        tab3, tab4 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (Mã Hàng)", "💰 Chi Tiết GIÁ TRỊ (Mã Hàng)"])
        with tab3:
            display_df_with_download(filtered_qty_item_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_item_renamed.columns if 'Chênh lệch' in c[1]]), "Chi_Tiet_SL_CLV4", height=600)
        with tab4:
            display_df_with_download(filtered_val_item_renamed.style.format(format_vn), "Chi_Tiet_GT_CLV4", height=600)
    
        # 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)
        st.write("---")
        st.subheader("🏷️ 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)")
        sku_qty_sum = df_active.groupby(['Ngày_str', 'SKU_Full'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        sku_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST chênh lệch')
        sku_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_sku = sku_qty_sum.join(sku_qty_count).join(sku_qty_nhap0).fillna(0).reset_index()
        pivot_qty_sku.rename(columns={
            'SKU_Full': 'Mã hàng (SKU)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_sku['Tỷ lệ (%)'] = np.where(pivot_qty_sku['Số lượng chuyển'] > 0, (pivot_qty_sku['Chênh lệch'] / pivot_qty_sku['Số lượng chuyển']) * 100, 0)
        pivot_qty_sku['Abs_ChenhLech'] = pivot_qty_sku['Chênh lệch'].abs()
        pivot_qty_sku = pivot_qty_sku.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_sku['SL ST chênh lệch'] = pivot_qty_sku['SL ST chênh lệch'].astype(int)
        pivot_qty_sku['SL ST nhập=0'] = pivot_qty_sku['SL ST nhập=0'].astype(int)
    with tab_daily:
        st.subheader(f"{icon} Đối Soát Chéo Dư - Thiếu {kho_name}")
        st.markdown("Hệ thống tự động kết nối StarRocks qua VPN để đối soát chéo lượng hàng thừa/thiếu hàng ngày.")
    
        import datetime
        # Date selection
        selected_date = st.date_input("Chọn ngày đối soát (Daily):", datetime.date(2026, 7, 22), key="meat_fish_date_picker")
        date_str = selected_date.strftime('%Y-%m-%d')
    
        if True: # Tự động chạy khi thay đổi ngày
            with st.spinner("Đang tải dữ liệu và tính toán đối soát chéo..."):
                try:
                    # 1. Fetch branch mapping
                    sql_branches = """
                    SELECT branch_id, branch_code, branch_name
                    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
                    WHERE branch_name IS NOT NULL AND branch_name != ''
                    GROUP BY branch_id, branch_code, branch_name
                    """
                    df_branches = fetch_data_to_df(sql_branches)
                    id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
    
                    # 2. Fetch shortages (MF01)
                    sql_mf01 = f"""
                    SELECT 
                        i.to_branch_id,
                        i.code as `Mã chuyển hàng`,
                        IFNULL(c.code, i.double_check_code) as `Mã thùng`,
                        l.barcode as `Mã hàng`,
                        l.name as `Tên hàng`,
                        l.unit__name as `ĐVT`,
                        CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                        CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
                    FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                    INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                    LEFT JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines c 
                        ON c._parent_id = l._root_id 
                        AND c._index = CAST(SPLIT_PART(l._parent_id, char(31), 2) AS INT)
                    WHERE {shortage_condition}
                      AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                      AND i.status = 5
                      AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                    """
                    df_mf01 = fetch_data_to_df(sql_mf01)
                    
                    if df_mf01.empty:
                        st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho {kho_code} ngày {selected_date.strftime('%d/%m/%Y')}.")
                    else:
                        df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
                        df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
                        
                        
                        df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
                        
                        # 3. Fetch surpluses (MF02)
                        sql_mf02 = f"""
                        SELECT 
                            i.to_branch_id,
                            i.code as `Mã chuyển hàng`,
                            i.double_check_code as `Mã thùng`,
                            i.note as `Ghi chú chuyển (phiếu)`,
                            i.created_by,
                            l.description,
                            l.reason,
                            l.barcode as `Mã hàng`,
                            l.name as `Tên hàng`,
                            l.unit__name as `ĐVT`,
                            CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`,
                            CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `SL_chuyen_du`
                        FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                        INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                        WHERE {surplus_condition}
                          AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                          AND i.status = 5
                          AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                        """
                        df_mf02 = fetch_data_to_df(sql_mf02)
                        df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
                        
                        if khu_vuc == "Rau Củ Quả":
                            import re
                            def extract_date(text):
                                if pd.isna(text): return None
                                match = re.search(r'(?<!\d)(\d{1,2})[\./-](\d{1,2})(?!\d)', str(text))
                                if match:
                                    try:
                                        d, m = int(match.group(1)), int(match.group(2))
                                        return f"{selected_date.year}-{m:02d}-{d:02d}"
                                    except:
                                        pass
                                return None
                            
                            df_mf02['Note_Date'] = df_mf02['Ghi chú chuyển (phiếu)'].apply(extract_date)
                            df_mf02['Desc_Date'] = df_mf02['description'].apply(extract_date)
                            df_mf02['Final_Date'] = df_mf02['Note_Date'].fillna(df_mf02['Desc_Date'])
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            
                            mask_exclude = mask_non_sys & (df_mf02['Final_Date'].notna()) & (df_mf02['Final_Date'] != date_str)
                            df_mf02 = df_mf02[~mask_exclude].copy()
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            df_mf02.loc[mask_non_sys, 'SL_du'] = df_mf02.loc[mask_non_sys, 'SL_chuyen_du']
                        
                        df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()
    
                        # 4. Clean surplus crate code
                        def extract_surplus_crate(row):
                            val = str(row.get('Ghi chú chuyển (phiếu)', '')).strip()
                            if not val or val == 'nan':
                                return str(row['Mã thùng']).strip()
                            prefix = str(row['Mã chuyển hàng']).strip()
                            if prefix and val.startswith(prefix):
                                res = val[len(prefix):].strip()
                                if res: return res
                            import re
                            m = re.search(r'của thùng\s+([A-Z0-9_-]+)', val, flags=re.IGNORECASE)
                            if m: return m.group(1).strip()
                            m = re.search(r'(TRB[A-Z0-9_-]+|PT[A-Z0-9_-]+)', val)
                            if m: return m.group(1).strip()
                            return str(row['Mã thùng']).strip()
                            
                        if not df_surplus.empty:
                            df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
                        else:
                            df_surplus['Mã thùng'] = ""
    
                        # 5. Load layout
                        # file_layout already set based on khu_vuc
                        layout_df = pd.read_excel(file_layout, sheet_name=0)
                        
                        # Normalize columns
                        if 'Chi nhánh nhận' in layout_df.columns and 'STT' in layout_df.columns:
                            layout_df.rename(columns={'STT': 'Vị trí', 'Chi nhánh nhận': 'Siêu thị'}, inplace=True)
                        elif 'Siêu thị' not in layout_df.columns:
                            layout_df = pd.read_excel(file_layout, sheet_name=0, header=None)
                            if len(layout_df.columns) >= 3:
                                layout_df.rename(columns={0: 'Vị trí', 1: 'Mã', 2: 'Siêu thị'}, inplace=True)
                        
                        store_to_pos = {}
                        if 'Siêu thị' in layout_df.columns and 'Vị trí' in layout_df.columns:
                            for _, row in layout_df.iterrows():
                                try:
                                    st_name = str(row['Siêu thị']).strip().upper()
                                    pos_val = int(row['Vị trí'])
                                    store_to_pos[st_name] = pos_val
                                except (ValueError, TypeError):
                                    pass
    
                        # Clean barcodes and exclude 'CC' prefixes
                        df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
                        df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
                        df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
                        df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()
    
                        # 6. Group shortage & surplus
                        diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                            'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                            'Chênh lệch': 'sum',
                            'ĐVT': 'first',
                            'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                            'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                        }).reset_index()
                        diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu', 'Mã chuyển hàng': 'Mã chuyển hàng thiếu'}, inplace=True)
                        
                        
                        
                        if not df_surplus.empty:
                            du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                                'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                                'SL_du': 'sum',
                                'ĐVT': 'first',
                                'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                                'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                            }).reset_index()
                            du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
                        else:
                            du_grouped = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa'])
    
                        # Merge for internal matching
                        merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
                        merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
                        try:
                            ten_hang_col = [c for c in df_all.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
                            sku_mapping = dict(zip(df_all['Mã hàng'].astype(str).str.strip(), df_all[ten_hang_col]))
                            merged_internal['Tên hàng'] = merged_internal['Mã hàng'].astype(str).str.strip().map(sku_mapping).fillna(merged_internal['Tên hàng'])
                            merged_internal['Tên hàng'] = merged_internal['Tên hàng'].replace({'nan': '', 'None': ''})
                        except:
                            pass
                        merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
                        merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
                        merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('kg')
                        merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
                        merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()
    
                        # Step 1: Khớp nội bộ 100%
                        df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
                        
                        loi_text = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                        df_exact['Lỗi'] = loi_text
                        df_exact = df_exact[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
                        df_exact.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Lỗi']
                        df_exact['SL Thiếu'] = df_exact['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_exact['SL Thừa'] = df_exact['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Step 2: Khớp nội bộ một phần
                        df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
                        df_partial['Dif'] = df_partial['Chênh lệch'] - df_partial['SL_du']
                        df_partial['Lỗi'] = loi_text
                        df_partial = df_partial[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Dif', 'Lỗi']]
                        df_partial.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Chênh lệch thừa - thiếu', 'Lỗi']
                        df_partial['SL Thiếu'] = df_partial['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_partial['SL Thừa'] = df_partial['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Remainder calculation
                        merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
                        merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']
                        
                        rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 3: Khớp chéo liên siêu thị
                        cross_matches = []
                        skus_shortage = rem_shortages['Mã hàng'].unique()
                        skus_surplus = rem_surpluses['Mã hàng'].unique()
                        common_skus = set(skus_shortage).intersection(skus_surplus)
                        
                        matched_sho_keys = set()
                        matched_sur_keys = set()
                        
                        for sku in common_skus:
                            sku_shortages = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
                            sku_surpluses = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
                            
                            for idx_sur, row_sur in sku_surpluses.iterrows():
                                sur_qty = row_sur['Remaining_Surplus']
                                sur_store = row_sur['Chi nhánh nhận']
                                sur_crate = row_sur['Mã thùng thừa']
                                sur_transfer = row_sur['Mã chuyển hàng thừa']
                                sku_name = row_sur['Tên hàng']
                                dvt = row_sur['ĐVT']
                                pos_sur = store_to_pos.get(str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store, None)
                                
                                matching_shortages = []
                                for idx_sho, row_sho in sku_shortages.iterrows():
                                    sho_qty = row_sho['Remaining_Shortage']
                                    if abs(sur_qty - sho_qty) <= 0.01:
                                        matching_shortages.append(row_sho)
                                
                                if len(matching_shortages) > 0:
                                    best_match = None
                                    best_dist = 9999
                                    for sho_row in matching_shortages:
                                        sho_store = sho_row['Chi nhánh nhận']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        if pos_sur is not None and pos_sho is not None:
                                            dist = abs(pos_sur - pos_sho)
                                            if dist < best_dist:
                                                best_dist = dist
                                                best_match = sho_row
                                        else:
                                            if best_match is None:
                                                best_match = sho_row
                                    
                                    if best_match is not None:
                                        sho_store = best_match['Chi nhánh nhận']
                                        sho_qty = best_match['Remaining_Shortage']
                                        sho_crate = best_match['Mã thùng thiếu']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        
                                        prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                                        cross_matches.append({
                                            'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                                            'Vị trí Dư': pos_sur if pos_sur is not None else '-', 'Mã Thùng Thừa': sur_crate,
                                            'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                                            'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                                            'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                                            'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                                            'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                                        })
                                        matched_sur_keys.add((sur_store, sku))
                                        matched_sho_keys.add((sho_store, sku))
                                        
                        df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
                            'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 
                            'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 
                            'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
                        ])
                        
                        # Exclude matched from remainder
                        for index, row in rem_shortages.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
                                rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
                        for index, row in rem_surpluses.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
                                rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
                                
                        rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 4: Tổng Dư >= Tổng Thiếu
                        if not rem_shortages.empty or not rem_surpluses.empty:
                            sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
                            sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
                            sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Mã hàng', 'Tên hàng'], how='outer')
                            sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
                            sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
                            sku_totals['Dif'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
                            
                            df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
                            
                            sur_details, sho_details = [], []
                            for idx, row in df_total_gte.iterrows():
                                sku = row['Mã hàng']
                                sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
                                sur_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Surplus']:.3f} kg)" for _, r in sku_sur.iterrows()]))
                                sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
                                sho_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Shortage']:.3f} kg)" for _, r in sku_sho.iterrows()]) if len(sku_sho) > 0 else "Không có")
                            
                            if not df_total_gte.empty:
                                df_total_gte['Chi tiết ST nhận Dư'] = sur_details
                                df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
                                df_total_gte = df_total_gte[['Mã hàng', 'Tên hàng', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Dif']]
                                df_total_gte.columns = ['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)']
                            else:
                                df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
                        else:
                            df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
    
                        # Step 5: Chỉ có thiếu ròng
                        if not rem_shortages.empty:
                            df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
                            df_only_diff.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
                        else:
                            df_only_diff = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
                        
                        # Step 6: Chỉ có thừa ròng
                        if not rem_surpluses.empty:
                            df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Remaining_Surplus']].copy()
                            df_only_du.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)']
                        else:
                            df_only_du = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)'])
    
                        # Display KPIs
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ff4b4b; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ 100%</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ff4b4b;">{len(df_exact)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ffaa00; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ MỘT PHẦN</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ffaa00;">{len(df_partial)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #00c0f2; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP CHÉO LIÊN ST 1-1</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #00c0f2;">{len(df_cross)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c4:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #2ebd59; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">THIẾU RÒNG / THỪA RÒNG</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #2ebd59;">{len(df_only_diff)} / {len(df_only_du)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
    
                        st.write("---")
                        # Export Excel to Memory for Download Button
                        output_excel = io.BytesIO()
                        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                            df_shortage.to_excel(writer, sheet_name='0. Dữ liệu Thiếu Raw', index=False)
                            df_surplus.to_excel(writer, sheet_name='0. Dữ liệu Thừa Raw', index=False)
                            df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
                            df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
                            df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
                            df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
                            df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
                            df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
                        
                        st.download_button(
                            label="📥 Tải Xuống Báo Cáo Đối Soát Chéo Excel",
                            data=output_excel.getvalue(),
                            file_name=f"Doi_Soat_Cheo_Thit_Ca_{date_str}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
    
                        # Tab presentation
                        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
                            "1. Khớp nội bộ 100%", 
                            "2. Khớp nội bộ một phần", 
                            "3. Khớp chéo liên ST 1-1", 
                            "4. Tổng Dư >= Tổng Thiếu", 
                            "5. Chỉ ghi nhận Thiếu ròng", 
                            "6. Chỉ ghi nhận Thừa ròng"
                        ])
                        
                        with sub_tab1:
                            loi_text_display = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                            st.subheader(f"1. Danh sách Khớp nội bộ 100% ({loi_text_display})")
                            st.dataframe(df_exact, use_container_width=True)
                        with sub_tab2:
                            st.subheader("2. Danh sách Khớp nội bộ một phần")
                            st.dataframe(df_partial, use_container_width=True)
                        with sub_tab3:
                            st.subheader("3. Danh sách Khớp chéo liên ST 1-1 (DC giao nhầm CH)")
                            st.dataframe(df_cross, use_container_width=True)
                        with sub_tab4:
                            st.subheader("4. Danh sách Tổng Dư >= Tổng Thiếu")
                            st.dataframe(df_total_gte, use_container_width=True)
                        with sub_tab5:
                            st.subheader("5. Danh sách Chỉ ghi nhận Thiếu ròng (Siêu thị nhận thiếu)")
                            st.dataframe(df_only_diff, use_container_width=True)
                        with sub_tab6:
                            st.subheader("6. Danh sách Chỉ ghi nhận Thừa ròng (Siêu thị nhận thừa)")
                            st.dataframe(df_only_du, use_container_width=True)
    
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi chạy đối soát: {e}")
                    st.exception(e)
    
    
    with tab_dc:
        st.header("👨‍🔧 Theo Dõi Tiến Độ Xử Lý & Phản Hồi Của DC")
        render_dc_feedback_progress_report(df_active, "Tab_3")
    

def render_rau_cu():

    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_code = 'HCM010002')"
    surplus_condition = "i.from_branch_id = '6982f5f1d360600007807f7b'"
    kho_name = "Kho Rau Củ"
    kho_code = "KRC"
    icon = "🥬"
    khu_vuc = "Rau Củ Quả"

    def get_excel_bytes(df):
        output = io.BytesIO()
        df_to_export = df.copy()
        if isinstance(df_to_export.columns, pd.MultiIndex):
            df_to_export.columns = [' - '.join(str(c) for c in col if c).strip() for col in df_to_export.columns.values]
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_to_export.to_excel(writer, index=False)
        return output.getvalue()
    
    def display_df_with_download(styled_df, filename, height=None):
        if height:
            st.dataframe(styled_df, use_container_width=True, height=height)
        else:
            st.dataframe(styled_df, use_container_width=True)
        df_raw = styled_df.data if hasattr(styled_df, 'data') else styled_df
        try:
            excel_data = get_excel_bytes(df_raw)
            st.download_button(label="📥 Tải xuống Excel", data=excel_data, file_name=f"{filename}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=filename)
        except Exception as e:
            st.error(f"Lỗi xuất Excel: {e}")
    
    st.title(f"{icon} Báo Cáo Đối Soát {kho_name}")
    st.markdown("Dữ liệu tự động cập nhật từ Hệ thống Google Sheets")
    
    # Hàm làm sạch số lượng chênh lệch (Đơn vị nhỏ: cái, kg, hộp)
    def clean_qty(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Ở cột số lượng, dấu phẩy thường là phân cách thập phân (VD: 5,5 -> 5.5) hoặc dấu chấm cũng vậy (VD: -1.000 -> -1.0)
            # Không có số lượng hàng nghìn trên 1 dòng ở {kho_name.lower()}, nên ta quy về dạng chuẩn
            x = x.replace(',', '.')
            # Nếu có nhiều dấu chấm (lỗi định dạng), chỉ giữ lại dấu chấm cuối cùng
            if x.count('.') > 1:
                parts = x.split('.')
                x = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(x)
        except:
            return 0.0
    
    # Hàm làm sạch giá trị tiền tệ (Đơn vị lớn: VNĐ)
    def clean_val(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Xử lý tiền tệ VNĐ (VD: -2.045.634 hoặc -2,045,634.00 hoặc -13.914.047,04)
            num_dots = x.count('.')
            num_commas = x.count(',')
            if num_dots > 0 and num_commas > 0:
                last_dot = x.rfind('.')
                last_comma = x.rfind(',')
                if last_comma > last_dot: # Định dạng VN: 1.234.567,89
                    x = x.replace('.', '').replace(',', '.')
                else: # Định dạng EN: 1,234,567.89
                    x = x.replace(',', '')
            elif num_dots > 1: # Nhiều dấu chấm: 1.234.567 -> bỏ chấm
                x = x.replace('.', '')
            elif num_commas > 1: # Nhiều dấu phẩy: 1,234,567 -> bỏ phẩy
                x = x.replace(',', '')
            elif num_dots == 1:
                # Nếu chỉ có 1 dấu chấm, xem nó là thập phân hay hàng nghìn (VD: -13914047.04 hay 16.000 VNĐ)
                parts = x.split('.')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace('.', '') # 16.000 -> 16000 VNĐ
                else:
                    pass # 12.5 -> 12.5
            elif num_commas == 1:
                parts = x.split(',')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace(',', '') # 16,000 -> 16000 VNĐ
                else:
                    x = x.replace(',', '.') # 12,5 -> 12.5
        try:
            return float(x)
        except:
            return 0.0
    
    def clean_number(x):
        # Hàm dự phòng giữ nguyên tương thích ngược
        return clean_val(x)
    
    # HÀM XỬ LÝ SỐ AN TOÀN CHO BÁO CÁO
    def to_numeric(series):
        if series.dtype == 'object':
            return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return pd.to_numeric(series, errors='coerce').fillna(0)
    
    @st.cache_data(ttl=600)
    def load_data_rau_cu_v2(url):
        
        
        def read_csv_with_retry(url, max_retries=3):
            import time
            for i in range(max_retries):
                try:
                    response = requests.get(url, timeout=30, verify=False)
                    response.raise_for_status()
                    # Google Sheets CSV exports are UTF-8 encoded
                    content = response.content.decode('utf-8')
                                    # Dynamic header finding
                    lines = content.split('\n')
                    header_idx = 1
                    for idx, line in enumerate(lines[:10]):
                        if 'Số lượng chuyển' in line or 'Mã hàng' in line:
                            header_idx = idx
                            break
                    return pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
                except Exception as e:
                    if i == max_retries - 1:
                        raise e
                    time.sleep(2)
                    
        df = read_csv_with_retry(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Rename columns to standard ones if needed
        df.rename(columns={
            'ST': 'ID ST',
            'SL chênh lệch CXD': 'SL chênh lệch CXD'
        }, inplace=True)
        
        # Clean numeric columns
        qty_cols = ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Qty_N', 'Qty_O', 'Qty_P', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']
        
        # Clean money columns
        for col in ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', f'Tổng {kho_name.lower()}', 'Tổng chưa xác định']:
            matched_cols = [c for c in df.columns if col.lower() in c.lower()]
            for c in matched_cols:
                df[c] = df[c].apply(clean_val)
                
        df['Số lượng chuyển'] = df['Số lượng chuyển'].apply(clean_qty)
        df['Số lượng nhận'] = df['Số lượng nhận'].apply(clean_qty)
        df['Chênh lệch'] = df['Chênh lệch'].apply(clean_qty)
        
        if 'Chi nhánh nhận' in df.columns:
            df['Chi nhánh nhận'] = df['Chi nhánh nhận'].astype(str).str.replace(',', '.', regex=False)
                
        # Lọc lý do chênh lệch
        df['LyDo_HaoHut'] = df['Hao hụt'].astype(str).str.strip().str.lower()
        df['LyDo_SieuThi'] = df['Siêu thị'].astype(str).str.strip().str.lower()
        
        col_kho_list = [c for c in df.columns if f'{kho_name.upper()}' in c.upper() or 'KHO TH' in c.upper() or 'KHO RAU' in c.upper() or 'KRC' in c.upper()]
        col_kho = col_kho_list[0] if col_kho_list else None
        if col_kho:
            df['LyDo_Kho'] = df[col_kho].astype(str).str.strip().str.lower()
        else:
            df['LyDo_Kho'] = ''
        df['LyDo_Loi'] = df['Lỗi'].astype(str).str.strip().str.lower() if 'Lỗi' in df.columns else ''
        
        col_hao_hut_qty = 'Hạo hụt tự nhiê' if 'Hạo hụt tự nhiê' in df.columns else ('Hạo hụt tự nhiên' if 'Hạo hụt tự nhiên' in df.columns else None)
        df['Qty_N'] = df[col_hao_hut_qty].apply(clean_qty) if col_hao_hut_qty else df['Tổng hao hụt']
        df['Qty_O'] = df['SL trả tồn về ST'].apply(clean_qty) if 'SL trả tồn về ST' in df.columns else df['Tổng ST']
        df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_qty) if 'SL chênh lệch CXD' in df.columns else 0.0
        
        # Kết hợp các cột tổng chênh lệch
        col_total_kho_list = [c for c in df.columns if f'{kho_name}' in c or f'Tổng {kho_name.lower()}' in c or 'Tổng kho rau' in c.lower()]
        col_total_kho = col_total_kho_list[0] if col_total_kho_list else None
        col_total_cxd = [c for c in df.columns if 'Tổng chưa xác định' in c or 'chưa xác định' in c][0]
        
        df['Hao hụt'] = np.where(df['LyDo_HaoHut'].str.contains('hao hụt'), df['Qty_N'], 0)
        df['BS_ST'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị'), df['Qty_O'], 0)
        df['ST_NhapThieu'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        df['ST_SaiQT'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & ~df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        
        import unicodedata
        lydo_kho_nfc = pd.Series([unicodedata.normalize('NFC', str(x)) if pd.notna(x) else '' for x in df['LyDo_Kho']], index=df.index)
        
        kho_lower_nfc = unicodedata.normalize('NFC', kho_name.lower())
        df['Kho_Rau'] = np.where(lydo_kho_nfc.str.contains(kho_lower_nfc) | lydo_kho_nfc.str.contains('kho rau') | lydo_kho_nfc.str.contains('krc'), df['Qty_P'], 0)
        df['CXD'] = np.where(lydo_kho_nfc.str.contains('chưa xác định'), df['Qty_P'], 0)
        
        if col_total_kho:
            df['Tổng kho rau'] = df[col_total_kho].apply(clean_val)
        else:
            df['Tổng kho rau'] = 0.0
        df['Tổng chưa xác định'] = df[col_total_cxd].apply(clean_val)
        
        # Parse dates strictly (Google Sheets sends dates in MM/DD/YYYY format)
        if 'Ngày' in df.columns:
            date_col = 'Ngày'
        elif 'Ngày chuyển hàng' in df.columns:
            date_col = 'Ngày chuyển hàng'
        elif 'Thời gian' in df.columns:
            date_col = 'Thời gian'
        elif 'Ngành' in df.columns:
            date_col = 'Ngành'
        else:
            date_col = 'Ngày'
        
        df['Ngày_parsed'] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
        df['Ngày_str'] = df['Ngày_parsed'].dt.strftime('%d/%m/%Y')
        df['Ngày'] = df['Ngày_parsed']
        df = df[df['Ngày_parsed'].notna()]
        
        # Categories & SKU
        clv2_col = 'CLV2' if 'CLV2' in df.columns else ('Loại hàng' if 'Loại hàng' in df.columns else 'Unnamed: 0')
        df['CLV2'] = df[clv2_col].fillna('Chưa phân loại')
        
        clv4_col = 'CLV4' if 'CLV4' in df.columns else 'CLV2'
        df['CLV4'] = df[clv4_col].fillna('Chưa phân loại')
        
        ten_hang_col = [c for c in df.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
        df['SKU_Full'] = df['Mã hàng'].fillna('').astype(str) + " - " + df[ten_hang_col].fillna('').astype(str)
        
        return df
    
    # HÀM TÍNH TOÁN NĂNG SUẤT DAILY MỚI
    def calculate_daily_metrics(data, group_by_col='CLV2'):
        if data.empty:
            return pd.DataFrame(columns=[
                group_by_col, 'SL chuyển', 'SL chênh lệch', 'GT chênh lệch', 
                'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 
                'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'Số lượng hao hụt', 
                'GT hao hụt', 'Tỷ lệ hao hụt', 'SL bs ST', 'GT bs ST', 
                'SL bs kho rau', 'GT bs kho rau', 'Đang xử lý', 'GT Đang xử lý', 
                'Chưa xử lý', 'GT Chưa xử lý', 'Không xử lý (WRITE OFF)', 'Giá trị WRITE OFF',
                'Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 'GT Lỗi ST (Nhập thiếu)', 'GT Lỗi ST (Sai QT)'
            ])
        
        df = data.copy()
        df['SL_chuyen_num'] = to_numeric(df['Số lượng chuyển'])
        df['CL_num'] = to_numeric(df['Chênh lệch'])
        df['GT_num'] = to_numeric(df['Tổng GT'])
        df['HH_qty'] = to_numeric(df['Hao hụt'])
        df['HH_val'] = to_numeric(df['Tổng hao hụt'])
        df['ST_qty'] = to_numeric(df['BS_ST'])
        df['ST_val'] = to_numeric(df['Tổng ST'])
        df['Kho_qty'] = to_numeric(df['Kho_Rau'])
        df['Kho_val'] = to_numeric(df['Tổng kho rau'])
        df['CXD_qty'] = to_numeric(df['CXD'])
        df['CXD_val'] = to_numeric(df['Tổng chưa xác định'])
        
        df['ST_NhapThieu_qty'] = to_numeric(df['ST_NhapThieu']) if 'ST_NhapThieu' in df.columns else 0.0
        df['ST_SaiQT_qty'] = to_numeric(df['ST_SaiQT']) if 'ST_SaiQT' in df.columns else 0.0
        
        price_col = 'Giá nhập \n( -VAT)' if 'Giá nhập \n( -VAT)' in df.columns else None
        if price_col:
            df['ST_NhapThieu_val'] = df['ST_NhapThieu_qty'] * to_numeric(df[price_col])
            df['ST_SaiQT_val'] = df['ST_SaiQT_qty'] * to_numeric(df[price_col])
        else:
            df['ST_NhapThieu_val'] = 0.0
            df['ST_SaiQT_val'] = 0.0
            
        df['Xuly_clean'] = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        
        groups = df.groupby(group_by_col, dropna=False)
        rows = []
        
        for g_name, g_df in groups:
            cl_df = g_df[g_df['CL_num'].abs() > 0]
            sl_chuyen = g_df['SL_chuyen_num'].sum()
            sl_cl = g_df['CL_num'].sum()
            gt_cl = g_df['GT_num'].sum()
            
            sl_st_cl = cl_df['ID ST'].nunique()
            sl_line_cl = len(cl_df)
            sl_line_hh = len(g_df[g_df['HH_qty'].abs() > 0])
            
            done_df = g_df[g_df['Xuly_clean'].str.contains('hoàn thành')]
            sl_line_done = len(done_df)
            tyle_line_done = f"{(sl_line_done / sl_line_cl * 100):.2f}%" if sl_line_cl > 0 else "0.00%"
            
            sl_hh = g_df['HH_qty'].sum()
            gt_hh = g_df['HH_val'].sum()
            tyle_hh = f"{(sl_hh / sl_chuyen * 100):.2f}%" if sl_chuyen > 0 else "0.00%"
            
            sl_bs_st = g_df['ST_qty'].sum()
            gt_bs_st = g_df['ST_val'].sum()
            sl_bs_kho = g_df['Kho_qty'].sum()
            gt_bs_kho = g_df['Kho_val'].sum()
            
            sl_st_nhap = g_df['ST_NhapThieu_qty'].sum()
            sl_st_sai = g_df['ST_SaiQT_qty'].sum()
            gt_st_nhap = g_df['ST_NhapThieu_val'].sum()
            gt_st_sai = g_df['ST_SaiQT_val'].sum()
            
            # Đang xử lý
            dang_xl_df = g_df[g_df['Xuly_clean'].str.contains('đang chuyển') | g_df['Xuly_clean'].str.contains('đang xử lý')]
            sl_dang_xl = dang_xl_df['CL_num'].sum()
            gt_dang_xl = dang_xl_df['GT_num'].sum()
            
            # Không xử lý (Write Off)
            write_off_df = g_df[g_df['Xuly_clean'].str.contains('không xử lý') | g_df['Xuly_clean'].str.contains('write of')]
            sl_write_off = write_off_df['CL_num'].sum()
            gt_write_off = write_off_df['GT_num'].sum()
            
            # Chưa xử lý
            chua_xl_df = g_df[~g_df['Xuly_clean'].str.contains('hoàn thành') & 
                              ~g_df['Xuly_clean'].str.contains('đang chuyển') & 
                              ~g_df['Xuly_clean'].str.contains('đang xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('không xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('write of')]
            sl_chua_xl = chua_xl_df['CL_num'].sum()
            gt_chua_xl = chua_xl_df['GT_num'].sum()
            
            row = {
                group_by_col: g_name,
                'SL chuyển': sl_chuyen,
                'SL chênh lệch': sl_cl,
                'GT chênh lệch': gt_cl,
                'SL ST chênh lệch': sl_st_cl,
                'SL line chênh lệch': sl_line_cl,
                'SL line hao hụt': sl_line_hh,
                'SL line đã xử lý': sl_line_done,
                'Tỷ lệ line đã xử lý': tyle_line_done,
                'Số lượng hao hụt': sl_hh,
                'GT hao hụt': gt_hh,
                'Tỷ lệ hao hụt': tyle_hh,
                'SL bs ST': sl_bs_st,
                'GT bs ST': gt_bs_st,
                'SL bs kho rau': sl_bs_kho,
                'GT bs kho rau': gt_bs_kho,
                'Đang xử lý': sl_dang_xl,
                'GT Đang xử lý': gt_dang_xl,
                'Chưa xử lý': sl_chua_xl,
                'GT Chưa xử lý': gt_chua_xl,
                'Không xử lý (WRITE OFF)': sl_write_off,
                'Giá trị WRITE OFF': gt_write_off,
                'Lỗi ST (Nhập thiếu)': sl_st_nhap,
                'Lỗi ST (Sai QT)': sl_st_sai,
                'GT Lỗi ST (Nhập thiếu)': gt_st_nhap,
                'GT Lỗi ST (Sai QT)': gt_st_sai
            }
            rows.append(row)
            
        return pd.DataFrame(rows)
    
    # HÀM HIỂN THỊ BẢNG DAILY
    def display_daily_table(df, cols, title_prefix, group_by_col='CLV2'):
        if df.empty:
            st.info("Không có dữ liệu.")
            return
        df_to_show = df.copy()
        for col in cols:
            if col not in df_to_show.columns:
                df_to_show[col] = 0.0
        df_to_show = df_to_show[cols]
        format_custom_table_with_total(df_to_show, group_by_col, title_prefix)
    
    # HÀM TÍNH TỔNG QUAN DAILY DẠNG TEXT
    def compute_daily_summary(df, date_str):
        if df.empty:
            return None
        
        cl_qty = to_numeric(df['Chênh lệch'])
        gt_val = to_numeric(df['Tổng GT'])
        
        total_items = cl_qty.abs().sum()
        total_value = gt_val.abs().sum()
        
        xuly_clean = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        df_done = df[xuly_clean.str.contains('hoàn thành')]
        
        ret_qty = to_numeric(df_done['Kho_Rau']).abs().sum()
        bs_qty = to_numeric(df_done['BS_ST']).abs().sum()
        lost_qty = to_numeric(df_done['Hao hụt']).abs().sum()
        
        processed_qty = ret_qty + bs_qty + lost_qty
        remaining_qty = total_items - processed_qty
        if remaining_qty < 0:
            remaining_qty = 0.0
            
        return {
            'date': date_str,
            'total_items': int(total_items),
            'total_value': total_value,
            'processed': int(processed_qty),
            'return': int(ret_qty),
            'bs': int(bs_qty),
            'lost': int(lost_qty),
            'remaining': int(remaining_qty)
        }
    
    # Insight Generators y hệt bên Kho Rau
    def generate_insights(df_raw, table_type, df_grouped=None, df_metrics=None, date_str=None):
        if df_raw.empty and (df_grouped is None or df_grouped.empty):
            return "Không có dữ liệu trong kỳ báo cáo này."
        
        def get_hh_insight():
            if df_metrics is not None and not df_metrics.empty and 'Số lượng chuyển' in df_metrics.columns and 'Số lượng hao hụt' in df_metrics.columns:
                tong_chuyen = df_metrics['Số lượng chuyển'].sum()
                tong_hh = df_metrics['Số lượng hao hụt'].sum()
                if tong_chuyen > 0:
                    return f"\n- Tỷ lệ hao hụt ghi nhận: {round((tong_hh / tong_chuyen) * 100, 2)}%."
            return ""
        
        try:
            if table_type == "Bảng 1":
                df_raw_tmp = df_raw.copy()
                df_raw_tmp['Chênh_lệch_num'] = to_numeric(df_raw_tmp['Chênh lệch'])
                df_raw_tmp['Kho_Rau_num'] = to_numeric(df_raw_tmp['Kho_Rau'])
                df_raw_tmp['BS_ST_num'] = to_numeric(df_raw_tmp['BS_ST'])
                
                total_lines = len(df_raw_tmp)
                total_chenh_lech = df_raw_tmp['Chênh_lệch_num'].sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                msg = f"Trong kỳ có tổng cộng {total_lines} dòng phát sinh chênh lệch (Tổng chênh lệch: {fmt(total_chenh_lech)}).\n"
                msg += "\n- Phân tích 3 nhóm ngành hàng (CLV4) phát sinh chênh lệch cao nhất:\n"
                
                clv4_lines = df_raw_tmp['CLV4'].value_counts()
                top3_clv4 = clv4_lines.head(3)
                
                for clv4, lines in top3_clv4.items():
                    sub_df = df_raw_tmp[df_raw_tmp['CLV4'] == clv4]
                    sub_cl = sub_df['Chênh_lệch_num'].sum()
                    sub_kr = sub_df['Kho_Rau_num'].sum()
                    msg += f"  + [{clv4}]: {lines} dòng (Tổng chênh lệch: {fmt(sub_cl)} | Trả về {kho_name.lower()}: {fmt(sub_kr)})\n"
                    
                msg += "\n- Phân bổ trả về Siêu Thị (ST):\n"
                st_by_clv4 = df_raw_tmp.groupby('CLV4')['BS_ST_num'].sum().sort_values(ascending=False)
                st_by_clv4 = st_by_clv4[st_by_clv4 > 0]
                
                if not st_by_clv4.empty:
                    top_st_clv4 = st_by_clv4.index[0]
                    top_st_val = st_by_clv4.iloc[0]
                    total_st = st_by_clv4.sum()
                    if top_st_val > (total_st * 0.3) and len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST tập trung nhiều nhất ở nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                    elif len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST nằm rải rác lẻ tẻ (cao nhất là [{top_st_clv4}] với {fmt(top_st_val)}).\n"
                    else:
                        msg += f"  Số lượng trả về ST thuộc về nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                else:
                    msg += "  Không phát sinh số lượng chênh lệch trả về ST trong kỳ.\n"
                    
                msg += "  -> Nguyên nhân: Do ST thao tác sai nên phải tạo lại thôi."
                msg += get_hh_insight()
                return msg
                
            elif table_type == "Bảng 1.1":
                if df_grouped is not None and not df_grouped.empty:
                    top_nguon = df_grouped.iloc[0]['Nguồn xác nhận']
                    top_sl = df_grouped.iloc[0]['Tổng ({kho_name.lower()} + ST)'] if 'Tổng ({kho_name.lower()} + ST)' in df_grouped.columns else df_grouped.iloc[0]['Tổng (Kho Rau + ST)']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    if top_nguon == 'Check camera':
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Việc dựa phần lớn vào Check camera cho thấy tình trạng ST báo thiếu/dư hàng nhưng không cung cấp đủ hình ảnh xác thực đang khá cao. Cần nhắc nhở ST tuân thủ quy định chụp hình."
                    else:
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là dựa vào [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Điều này phản ánh cơ sở dữ liệu chính yếu mà DC dùng để đối soát và phân bổ lượng hàng chênh lệch trong kỳ."
                
            elif table_type == "Bảng 2.1_New":
                if df_metrics is not None and not df_metrics.empty:
                    t_cl = df_metrics['SL chênh lệch'].sum()
                    if t_cl > 0:
                        l_st_nhap = df_metrics.get('Lỗi ST (Nhập thiếu)', pd.Series([0])).sum()
                        l_st_sai = df_metrics.get('Lỗi ST (Sai QT)', pd.Series([0])).sum()
                        l_st_tong = l_st_nhap + l_st_sai
                        pct_st = (l_st_tong / t_cl) * 100
                        pct_nhap = (l_st_nhap / t_cl) * 100
                        pct_sai = (l_st_sai / t_cl) * 100
                        
                        giao_thieu_5 = df_metrics.get('<= 5%', pd.Series([0])).sum()
                        giao_thieu_10 = df_metrics.get('5-10%', pd.Series([0])).sum()
                        giao_thieu_15 = df_metrics.get('10-15%', pd.Series([0])).sum()
                        giao_thieu_15_plus = df_metrics.get('> 15%', pd.Series([0])).sum()
                        
                        pct_5 = (giao_thieu_5 / t_cl) * 100
                        pct_10 = (giao_thieu_10 / t_cl) * 100
                        pct_15 = (giao_thieu_15 / t_cl) * 100
                        pct_15_plus = (giao_thieu_15_plus / t_cl) * 100
                        
                        d_str = "kỳ báo cáo"
                        if date_str and date_str != "Tất cả các ngày":
                            try:
                                d_str = "ngày " + date_str.split('/')[0] + "." + date_str.split('/')[1]
                            except:
                                d_str = "ngày " + str(date_str)
                                
                        def get_top_clv4(col):
                            if col in df_metrics.columns and df_metrics[col].max() > 0:
                                top_row = df_metrics.loc[df_metrics[col].idxmax()]
                                return f"[{top_row['CLV4']}] - {int(top_row[col])} item"
                            return ""
                            
                        top_5_clv4 = get_top_clv4('<= 5%')
                        top_10_clv4 = get_top_clv4('5-10%')
                        top_15_clv4 = get_top_clv4('10-15%')
                        top_15_plus_clv4 = get_top_clv4('> 15%')
                                
                        msg = f"Hàng KG có số lượng nhập nhưng phát sinh chênh lệch ghi nhận {d_str}\n"
                        msg += f"- Lỗi ST chiếm {pct_st:.1f}%: trong đó nhập sót {pct_nhap:.1f}% và sai QT chiếm {pct_sai:.1f}%\n"
                        if l_st_sai > 0:
                            msg += f"  + SL ST sai QT: {int(l_st_sai)}\n"
                        msg += f"- Giao thiếu:\n"
                        msg += f"  + Nhóm <= 5%: {pct_5:.1f}%\n"
                        if top_5_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_5_clv4}\n"
                        msg += f"  + Nhóm 5 - 10%: {pct_10:.1f}%\n"
                        if top_10_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_10_clv4}\n"
                        msg += f"  + Nhóm 10 - 15%: {pct_15:.1f}%\n"
                        if top_15_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_15_clv4}\n"
                        msg += f"  + Nhóm > 15%: {pct_15_plus:.1f}%"
                        if top_15_plus_clv4: msg += f"\n    -> Nhóm lệch nhiều nhất: {top_15_plus_clv4}"
                        return msg
                return "Chưa có đủ dữ liệu để đánh giá."
                
            elif table_type == "Bảng 2.1":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                return f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh." + get_hh_insight()
                
            elif table_type == "Bảng 3":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                base_msg = f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh."
                
                df_kr = df_raw.copy()
                df_kr['Kho_Rau_num'] = to_numeric(df_kr['Kho_Rau'])
                kr_by_clv4 = df_kr.groupby('CLV4')['Kho_Rau_num'].sum().sort_values(ascending=False)
                kr_by_clv4 = kr_by_clv4[kr_by_clv4 > 0]
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                if not kr_by_clv4.empty:
                    top3 = kr_by_clv4.head(3)
                    top3_msg = "\n- Top nhóm ngành hàng (CLV4) đang có lượng chênh lệch trả về {kho_name.lower()} cao nhất:\n"
                    for i, (clv4, val) in enumerate(top3.items(), 1):
                        top3_msg += f"  {i}. {clv4}: {fmt(val)}\n"
                else:
                    top3_msg = "\n- Không ghi nhận hàng Pack nào có chênh lệch trả về {kho_name.lower()} trong kỳ."
                    
                return base_msg + top3_msg.rstrip() + get_hh_insight()
                
            elif table_type == "Bảng 2.2":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                sum_kr = to_numeric(df_raw['Kho_Rau']).sum()
                sum_st = to_numeric(df_raw['BS_ST']).sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                return (f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n"
                        f"- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh.\n"
                        f"- Vấn đề chênh lệch này được phân bổ xử lý như sau:\n"
                        f"  + Trả về ST (Số lượng: {fmt(sum_st)}): Lý do là DC giao bù do ban đầu giao sai điểm.\n"
                        f"  + Trả {kho_name.lower()} (Số lượng: {fmt(sum_kr)}): Do có ST khác nhận dư số này và có ST nhận thiếu."
                        f"{get_hh_insight()}")
                
            elif table_type == "Bảng 4":
                if df_grouped is not None and not df_grouped.empty:
                    top_sku = df_grouped.iloc[0]['Mã & Tên hàng']
                    top_hh = df_grouped.iloc[0]['Tổng số lượng hao hụt']
                    
                    clv4_counts = df_raw['CLV4'].value_counts()
                    top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                    
                    return f"- Top 3 ngành hàng (CLV4) phát sinh hao hụt nhiều nhất: {top3_clv4_str}.\n- Mã hàng có sản lượng hao hụt nghiêm trọng nhất là [{top_sku}] (Hao hụt: {top_hh} KG).\n- Khuyến nghị: Cần ưu tiên kiểm tra chất lượng thực tế và quy trình đóng gói đối với mã hàng này."
    
            elif table_type == "Bảng 6":
                if df_grouped is not None and not df_grouped.empty:
                    top_dc = df_grouped.iloc[0]['DC xác nhận']
                    top_loi = df_grouped.iloc[0]['Lỗi'] if 'Lỗi' in df_grouped.columns else ('Nhom_Loi' if 'Nhom_Loi' in df_grouped.columns else 'Không phân loại')
                    top_sl = df_grouped.iloc[0]['Tổng số lượng']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    return f"- Dựa trên xác nhận của DC, lỗi [{top_loi}] được ghi nhận nhiều nhất từ [{top_dc}] với tổng số lượng trả về {kho_name.lower()} là {fmt(top_sl)}.\n- Khuyến nghị: DC cần kiểm tra lại quy trình xuất hàng và kiểm đếm để giảm thiểu tình trạng này."
    
        except Exception as e:
            return "Chưa đủ dữ liệu để tạo nhận xét tự động."
            
        return ""
    
    def render_dc_feedback_progress_report(df, tab_id=""):
        st.write("---")
        
        if df.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi.")
            return
            
        # Tính toán daily summary (Toàn hệ thống)
        df['GT_chuyen_temp'] = to_numeric(df.get('Số lượng chuyển', pd.Series(0, index=df.index))) * to_numeric(df.get('Giá trị ĐV', pd.Series(0, index=df.index)))
        daily_summary = df.groupby('Ngày_str').agg(
            SL_chuyen=('Số lượng chuyển', lambda x: to_numeric(x).sum()),
            SL_chenh_lech=('Chênh lệch', lambda x: to_numeric(x).sum()),
            GT_chuyen=('GT_chuyen_temp', 'sum'),
            GT_chenh_lech=('Tổng GT', lambda x: to_numeric(x).sum())
        ).reset_index()
    
        df_dc = df[to_numeric(df.get('Kho_Rau', pd.Series(0, index=df.index))) > 0].copy()
        df_dc['SL_CXD'] = to_numeric(df_dc.get('Kho_Rau', pd.Series(0, index=df_dc.index)))
        df_dc['GT_CXD'] = to_numeric(df_dc.get('Tổng kho rau', pd.Series(0, index=df_dc.index)))
            
        if df_dc.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi trong kỳ báo cáo này.")
            return
            
        df_dc['DC_Xac_Nhan'] = df_dc['DC xác nhận'].fillna('Chưa xác nhận')
        df_dc['DC_Xac_Nhan'] = df_dc['DC_Xac_Nhan'].apply(lambda x: 'Chưa xác nhận' if str(x).strip() == '' else x)
        loi_col = 'Lỗi' if 'Lỗi' in df_dc.columns else ('LyDo_Loi' if 'LyDo_Loi' in df_dc.columns else None)
        if loi_col:
            df_dc['Nhom_Loi'] = df_dc[loi_col].fillna('Không phân loại').replace('', 'Không phân loại')
        else:
            df_dc['Nhom_Loi'] = 'Không phân loại'
        df_dc['Chi_Tiet_Loi'] = 'Không ghi chú'
        
        df_chua_xn = df_dc[df_dc['DC_Xac_Nhan'] == 'Chưa xác nhận']
        tong_chua_xn = df_chua_xn['SL_CXD'].sum()
        tong_gt_chua_xn = df_chua_xn['GT_CXD'].sum()
        
        top_loi_name = "Không có"
        if not df_chua_xn.empty:
            loi_sum = df_chua_xn.groupby('Nhom_Loi')['SL_CXD'].sum()
            if not loi_sum.empty and loi_sum.max() > 0:
                top_loi_name = f"{loi_sum.idxmax()} ({int(loi_sum.max())} item)"
                
        # Hiển thị Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🔴 Tổng chờ DC xác nhận", value=f"{int(tong_chua_xn)} item", delta=f"{format_vn(tong_gt_chua_xn)} VNĐ", delta_color="off")
        with col2:
            st.metric(label="🔥 Top 1 Lỗi chờ phản hồi", value=top_loi_name)
        
        st.write("### 📌 Bảng chi tiết (Tiến độ DC)")
        tab_ngay, tab_loi = st.tabs(["📅 Góc nhìn 1: Theo Ngày", "⚠️ Góc nhìn 2: Theo Nhóm Lỗi"])
        
        # Góc nhìn 1
        with tab_ngay:
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_ngay = pd.pivot_table(df_dc, values='SL_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            dc_cols = [c for c in pivot_ngay.columns if c != 'Ngày_str']
            pivot_ngay['SL {kho_name.upper()}'] = pivot_ngay[dc_cols].sum(axis=1)
            
            final_ngay = pd.merge(daily_summary[['Ngày_str', 'SL_chuyen', 'SL_chenh_lech']], pivot_ngay, on='Ngày_str', how='right')
            sorted_dc_cols = [c for c in dc_cols if c != 'Chưa xác nhận']
            sorted_dc_cols.sort()
            if 'Chưa xác nhận' in dc_cols:
                sorted_dc_cols = ['Chưa xác nhận'] + sorted_dc_cols
                
            col_order = ['Ngày_str', 'SL_chuyen', 'SL_chenh_lech', 'SL {kho_name.upper()}'] + sorted_dc_cols
            final_ngay = final_ngay[[c for c in col_order if c in final_ngay.columns]]
            
            final_ngay['% Chưa xác nhận'] = final_ngay.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay['% Tiến độ phản hồi'] = final_ngay.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'SL_chuyen': 'SL chuyển',
                'SL_chenh_lech': 'SL chênh lệch'
            }, inplace=True)
            format_custom_table_with_total(final_ngay, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_ngay_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_ngay_gt['GT {kho_name.upper()}'] = pivot_ngay_gt[dc_cols].sum(axis=1)
            final_ngay_gt = pd.merge(daily_summary[['Ngày_str', 'GT_chuyen', 'GT_chenh_lech']], pivot_ngay_gt, on='Ngày_str', how='right')
            
            col_order_gt = ['Ngày_str', 'GT_chuyen', 'GT_chenh_lech', 'GT {kho_name.upper()}'] + sorted_dc_cols
            final_ngay_gt = final_ngay_gt[[c for c in col_order_gt if c in final_ngay_gt.columns]]
            
            final_ngay_gt['% Chưa xác nhận'] = final_ngay_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay_gt['% Tiến độ phản hồi'] = final_ngay_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay_gt.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'GT_chuyen': 'GT chuyển (VNĐ)',
                'GT_chenh_lech': 'GT chênh lệch (VNĐ)'
            }, inplace=True)
            format_custom_table_with_total(final_ngay_gt, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_GT_{tab_id}")
            
        # Góc nhìn 2
        with tab_loi:
            df_dc['Nhóm Lỗi & Chi tiết'] = df_dc['Nhom_Loi'] + " | " + df_dc['Chi_Tiet_Loi']
            
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_loi = pd.pivot_table(df_dc, values='SL_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi['SL {kho_name.upper()}'] = pivot_loi[dc_cols].sum(axis=1)
            col_order_loi = ['Nhóm Lỗi & Chi tiết', 'SL {kho_name.upper()}'] + sorted_dc_cols
            pivot_loi = pivot_loi[[c for c in col_order_loi if c in pivot_loi.columns]]
            
            pivot_loi['% Chưa xác nhận'] = pivot_loi.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi['% Tiến độ phản hồi'] = pivot_loi.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_loi_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi_gt['GT {kho_name.upper()}'] = pivot_loi_gt[dc_cols].sum(axis=1)
            pivot_loi_gt = pivot_loi_gt[[c for c in col_order_loi if c in pivot_loi_gt.columns]]
            pivot_loi_gt.rename(columns={'SL {kho_name.upper()}': 'GT {kho_name.upper()}'}, inplace=True)
            
            pivot_loi_gt['% Chưa xác nhận'] = pivot_loi_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi_gt['% Tiến độ phản hồi'] = pivot_loi_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi_gt, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_GT_{tab_id}")
    
    # Format màu đỏ cho số chênh lệch
    def color_red_for_chenhlech(val):
        color = 'red' if isinstance(val, (int, float)) and val > 0 else ''
        return f'color: {color}'
    
    # Format số theo chuẩn Việt Nam (1.000.000,00)
    def format_vn(val):
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float, np.integer, np.floating)):
            if val == int(val):
                return f"{int(val):,}".replace(',', '.')
            else:
                formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                if formatted.endswith(',00'):
                    return formatted[:-3]
                return formatted
        return val
    
    def format_money(val):
        if val >= 1000000:
            return f"{val/1000000:.1f} triệu".replace('.', ',')
        elif val >= 1000:
            return f"{val/1000:.1f} ngàn".replace('.', ',')
        return format_vn(val)
    
    def format_custom_table_with_total(df, name_col, title_prefix):
        if df.empty: return
        
        tong_df = pd.DataFrame(index=[0])
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                tong_df[col] = df[col].sum()
            else:
                tong_df[col] = ''
                
        tuples = []
        for col in df.columns:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    total_str = f"🟡 {format_vn(val)}"
                else:
                    total_str = f"🟡 {str(val)}"
            else:
                total_str = '⭐ TỔNG' if col == name_col else ''
                
            tuples.append((total_str, col))
            
        df_renamed = df.copy()
        df_renamed.columns = pd.MultiIndex.from_tuples(tuples)
        styler = df_renamed.style.format(format_vn).hide(axis="index")
        display_df_with_download(styler, f"Daily_{title_prefix}")
    
    # ==========================================
    # GIAO DIỆN CHIA TAB
    # ==========================================
    
    
    try:
        df_all = load_data_rau_cu_v2(data_url)
        st.sidebar.success(f"Tải dữ liệu từ Google Sheets thành công!")
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu Google Sheets: {e}")
        st.stop()
    
    tab_main, tab_daily, tab_dc = st.tabs(["📊 Báo Cáo Tổng Quan", "📈 Báo Cáo Năng Suất Daily", "👨‍🔧 Tiến Độ DC Phản Hồi"])
    
    # ==========================================
    # TRANG 1: BÁO CÁO TỔNG QUAN
    # ==========================================
    with tab_main:
        # Nút Cập nhật dữ liệu mới nhất
        if st.button('🔄 Cập nhật dữ liệu mới nhất'):
            st.cache_data.clear()
            st.rerun()
            
        df_active = df_all.copy()
    
        # Process Dataframes
        pivot_ngay_sum = df_active.groupby('Ngày_str')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_ngay = pivot_ngay_sum.fillna(0).reset_index()
        
        pivot_ngay['Ngày_dt'] = pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay = pivot_ngay.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        # Tính phần trăm đã phân bổ / chênh lệch cho từng ngày
        sum_dist = pivot_ngay['Hao hụt'] + pivot_ngay['BS_ST'] + pivot_ngay['Kho_Rau'] + pivot_ngay['CXD']
        pct_vals = np.where(pivot_ngay['Chênh lệch'].abs() > 0, (sum_dist / pivot_ngay['Chênh lệch'].abs()) * 100, 0.0)
        pivot_ngay['% Cột Tổng'] = [f"{v:.2f}%".replace('.', ',') for v in pct_vals]
    
        tong_row_ngay = pivot_ngay.sum(numeric_only=True).to_frame().T
        tong_row_ngay['Ngày_str'] = 'Tổng'
        
        # Tính phần trăm đã phân bổ / chênh lệch cho hàng Tổng
        total_sum_dist = tong_row_ngay['Hao hụt'].iloc[0] + tong_row_ngay['BS_ST'].iloc[0] + tong_row_ngay['Kho_Rau'].iloc[0] + tong_row_ngay['CXD'].iloc[0]
        total_cl = abs(tong_row_ngay['Chênh lệch'].iloc[0])
        total_pct = (total_sum_dist / total_cl) * 100 if total_cl > 0 else 0.0
        tong_row_ngay['% Cột Tổng'] = f"{total_pct:.2f}%".replace('.', ',')
    
        pivot_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        tong_row_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
    
        # Theo ngày (Giá trị)
        pivot_ngay_val = df_active.groupby('Ngày_str')[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_ngay_val['Ngày_dt'] = pd.to_datetime(pivot_ngay_val['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay_val = pivot_ngay_val.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        tong_row_ngay_val = pivot_ngay_val.sum(numeric_only=True).to_frame().T
        if not tong_row_ngay_val.empty: tong_row_ngay_val['Ngày_str'] = 'Tổng'
    
        pivot_ngay_val.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
            'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
            'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
        }, inplace=True)
        if not tong_row_ngay_val.empty:
            tong_row_ngay_val.rename(columns={
                'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
                'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
                'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
                'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
            }, inplace=True)
    
        # Theo CLV2
        pivot_clv2_sum = df_active.groupby('CLV2', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
        pivot_clv2_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('CLV2', dropna=False).size().rename('Số lượng line')
        pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
        pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
        pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False)
        
        tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
        tong_row_clv2['CLV2'] = 'Tổng'
    
        # Top 5 CLV4
        clv4_sum = df_active.groupby('CLV4', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
        clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
        pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)
    
        # Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
        pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line chênh lệch')
        pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line nhập=0')
    
        pivot_qty = pivot_qty_sum.join(pivot_qty_count).join(pivot_qty_nhap0).fillna(0).reset_index()
        pivot_qty.rename(columns={
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty['Tỷ lệ (%)'] = np.where(pivot_qty['Số lượng chuyển'] > 0, (pivot_qty['Chênh lệch'] / pivot_qty['Số lượng chuyển']) * 100, 0)
        pivot_qty['Abs_ChenhLech'] = pivot_qty['Chênh lệch'].abs()
        pivot_qty = pivot_qty.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty['SL line chênh lệch'] = pivot_qty['SL line chênh lệch'].astype(int)
        pivot_qty['SL line nhập=0'] = pivot_qty['SL line nhập=0'].astype(int)
        pivot_qty.insert(3, 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', pivot_qty['SL line nhập=0'].astype(str) + " / " + pivot_qty['SL line chênh lệch'].astype(str))
        pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        # Bảng GIÁ TRỊ Chi tiết Từng Ngày - Siêu Thị
        pivot_val_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)
    
        # Thẻ thông tin (Metrics)
        st.write("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng số lượng chuyển", format_vn(df_active['Số lượng chuyển'].sum()))
        with col2:
            st.metric("Tổng số lượng nhận", format_vn(df_active['Số lượng nhận'].sum()))
        with col3:
            st.metric("TỔNG CHÊNH LỆCH", format_vn(df_active['Chênh lệch'].sum()))
    
        def create_multiindex_headers(df, tong_df):
            if df.empty or tong_df.empty: return df
            tuples = []
            for i, col in enumerate(df.columns):
                if col in tong_df.columns:
                    val = tong_df.iloc[0][col]
                    if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                        if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                            tuples.append((f"🟡 {format_vn(val)}", col))
                        else:
                            tuples.append((f"🟡 {str(val)}", col))
                    else:
                        tuples.append(('⭐ TỔNG' if i == 0 else '', col))
                else:
                    tuples.append(('⭐ TỔNG' if i == 0 else '', col))
            df_new = df.copy()
            df_new.columns = pd.MultiIndex.from_tuples(tuples)
            return df_new
    
        pivot_ngay_renamed = create_multiindex_headers(pivot_ngay, tong_row_ngay)
        pivot_ngay_val_renamed = create_multiindex_headers(pivot_ngay_val, tong_row_ngay_val)
        pivot_clv2_renamed = create_multiindex_headers(pivot_clv2, tong_row_clv2)
    
        # Layout các bảng
        st.write("---")
        st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
        
        if not pivot_ngay.empty:
            top_day = pivot_ngay.sort_values(by='Chênh lệch', ascending=False).iloc[0]
            st.info(f"🔹 **Ngày biến động nhất**: **{top_day['Ngày_str']}** ghi nhận mức chênh lệch cao nhất ({format_vn(top_day['Chênh lệch'])} item).")
    
        tab_ngay_qty, tab_ngay_val = st.tabs(["📊 Số lượng (Từng Ngày)", "💰 Giá trị (Từng Ngày)"])
    
        with tab_ngay_qty:
            display_df_with_download(pivot_ngay_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_ngay_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_Theo_Ngay_So_Luong")
    
        with tab_ngay_val:
            display_df_with_download(pivot_ngay_val_renamed.style.format(format_vn), "Tong_Hop_Theo_Ngay_Gia_Tri")
    
        st.write("---")
        col4, col5 = st.columns(2)
        with col4:
            st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
            if not pivot_clv4.empty:
                top_clv4 = pivot_clv4.iloc[0]
                st.info(f"🔹 **Mã hàng (CLV4) cảnh báo đỏ**: **{top_clv4['CLV4']}** đang dẫn đầu với mức chênh lệch {format_vn(top_clv4['Chênh lệch'])}.")
            display_df_with_download(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), "Top_5_CLV4")
        with col5:
            st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
            if not pivot_clv2.empty:
                top_clv2 = pivot_clv2.iloc[0]
                st.info(f"🔹 **Ngành hàng (CLV2) trọng điểm**: **{top_clv2['CLV2']}** chiếm số lượng chênh lệch cao nhất ({format_vn(top_clv2['Chênh lệch'])}).")
            display_df_with_download(pivot_clv2_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_clv2_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_CLV2")
    
        st.write("---")
        # Sort dates chronologically
        sorted_dates_dt = sorted(pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce').dropna().unique())
        sorted_dates = [d.strftime('%d/%m/%Y') for d in sorted_dates_dt if d.strftime('%d/%m/%Y') != 'Tổng']
        dates = ["Tất cả các ngày"] + sorted_dates
    
        # 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)
        st.subheader("🛒 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)")
        item_qty_sum = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        item_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST chênh lệch')
        item_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_item = item_qty_sum.join(item_qty_count).join(item_qty_nhap0).fillna(0).reset_index()
        pivot_qty_item.rename(columns={
            'CLV4': 'Mã hàng (CLV4)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_item['Tỷ lệ (%)'] = np.where(pivot_qty_item['Số lượng chuyển'] > 0, (pivot_qty_item['Chênh lệch'] / pivot_qty_item['Số lượng chuyển']) * 100, 0)
        pivot_qty_item['Abs_ChenhLech'] = pivot_qty_item['Chênh lệch'].abs()
        pivot_qty_item = pivot_qty_item.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_item['SL ST chênh lệch'] = pivot_qty_item['SL ST chênh lệch'].astype(int)
        pivot_qty_item['SL ST nhập=0'] = pivot_qty_item['SL ST nhập=0'].astype(int)
        pivot_qty_item.insert(2, 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', pivot_qty_item['SL ST nhập=0'].astype(str) + " / " + pivot_qty_item['SL ST chênh lệch'].astype(str))
        pivot_qty_item = pivot_qty_item[['Ngày_str', 'Mã hàng (CLV4)', 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        pivot_val_item = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_item.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'CLV4': 'Mã hàng (CLV4)'}, inplace=True)
    
        selected_date_item = st.selectbox("🔍 Lọc theo Ngày (Mã hàng):", dates)
        if selected_date_item != "Tất cả các ngày":
            filtered_qty_item = pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item]
            filtered_val_item = pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item]
        else:
            filtered_qty_item = pivot_qty_item
            filtered_val_item = pivot_val_item
    
        tong_qty_item = pd.DataFrame() if filtered_qty_item.empty else filtered_qty_item.sum(numeric_only=True).to_frame().T
        if not tong_qty_item.empty: tong_qty_item['Ngày_str'] = 'Tổng'
        filtered_qty_item_renamed = create_multiindex_headers(filtered_qty_item, tong_qty_item)
    
        tong_val_item = pd.DataFrame() if filtered_val_item.empty else filtered_val_item.sum(numeric_only=True).to_frame().T
        if not tong_val_item.empty: tong_val_item['Ngày_str'] = 'Tổng'
        filtered_val_item_renamed = create_multiindex_headers(filtered_val_item, tong_val_item)
    
        tab3, tab4 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (Mã Hàng)", "💰 Chi Tiết GIÁ TRỊ (Mã Hàng)"])
        with tab3:
            display_df_with_download(filtered_qty_item_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_item_renamed.columns if 'Chênh lệch' in c[1]]), "Chi_Tiet_SL_CLV4", height=600)
        with tab4:
            display_df_with_download(filtered_val_item_renamed.style.format(format_vn), "Chi_Tiet_GT_CLV4", height=600)
    
        # 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)
        st.write("---")
        st.subheader("🏷️ 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)")
        sku_qty_sum = df_active.groupby(['Ngày_str', 'SKU_Full'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        sku_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST chênh lệch')
        sku_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_sku = sku_qty_sum.join(sku_qty_count).join(sku_qty_nhap0).fillna(0).reset_index()
        pivot_qty_sku.rename(columns={
            'SKU_Full': 'Mã hàng (SKU)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_sku['Tỷ lệ (%)'] = np.where(pivot_qty_sku['Số lượng chuyển'] > 0, (pivot_qty_sku['Chênh lệch'] / pivot_qty_sku['Số lượng chuyển']) * 100, 0)
        pivot_qty_sku['Abs_ChenhLech'] = pivot_qty_sku['Chênh lệch'].abs()
        pivot_qty_sku = pivot_qty_sku.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_sku['SL ST chênh lệch'] = pivot_qty_sku['SL ST chênh lệch'].astype(int)
        pivot_qty_sku['SL ST nhập=0'] = pivot_qty_sku['SL ST nhập=0'].astype(int)
    with tab_daily:
        st.subheader(f"{icon} Đối Soát Chéo Dư - Thiếu {kho_name}")
        st.markdown("Hệ thống tự động kết nối StarRocks qua VPN để đối soát chéo lượng hàng thừa/thiếu hàng ngày.")
    
        import datetime
        # Date selection
        selected_date = st.date_input("Chọn ngày đối soát (Daily):", datetime.date(2026, 7, 22), key="meat_fish_date_picker")
        date_str = selected_date.strftime('%Y-%m-%d')
    
        if True: # Tự động chạy khi thay đổi ngày
            with st.spinner("Đang tải dữ liệu và tính toán đối soát chéo..."):
                try:
                    # 1. Fetch branch mapping
                    sql_branches = """
                    SELECT branch_id, branch_code, branch_name
                    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
                    WHERE branch_name IS NOT NULL AND branch_name != ''
                    GROUP BY branch_id, branch_code, branch_name
                    """
                    df_branches = fetch_data_to_df(sql_branches)
                    id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
    
                    # 2. Fetch shortages (MF01)
                    sql_mf01 = f"""
                    SELECT 
                        i.to_branch_id,
                        i.code as `Mã chuyển hàng`,
                        IFNULL(c.code, i.double_check_code) as `Mã thùng`,
                        l.barcode as `Mã hàng`,
                        l.name as `Tên hàng`,
                        l.unit__name as `ĐVT`,
                        CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                        CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
                    FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                    INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                    LEFT JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines c ON i._id = c._parent_id
                    WHERE {shortage_condition}
                      AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                      AND i.status = 5
                      AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                    """
                    df_mf01 = fetch_data_to_df(sql_mf01)
                    
                    if df_mf01.empty:
                        st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho {kho_code} ngày {selected_date.strftime('%d/%m/%Y')}.")
                    else:
                        df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
                        df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
                        
                        
                        df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
                        
                        # 3. Fetch surpluses (MF02)
                        sql_mf02 = f"""
                        SELECT 
                            i.to_branch_id,
                            i.code as `Mã chuyển hàng`,
                            i.double_check_code as `Mã thùng`,
                            i.note as `Ghi chú chuyển (phiếu)`,
                            i.created_by,
                            l.description,
                            l.reason,
                            l.barcode as `Mã hàng`,
                            l.name as `Tên hàng`,
                            l.unit__name as `ĐVT`,
                            CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`,
                            CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `SL_chuyen_du`
                        FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                        INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                        WHERE {surplus_condition}
                          AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                          AND i.status = 5
                          AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                        """
                        df_mf02 = fetch_data_to_df(sql_mf02)
                        df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
                        
                        if khu_vuc == "Rau Củ Quả":
                            import re
                            def extract_date(text):
                                if pd.isna(text): return None
                                match = re.search(r'(?<!\d)(\d{1,2})[\./-](\d{1,2})(?!\d)', str(text))
                                if match:
                                    try:
                                        d, m = int(match.group(1)), int(match.group(2))
                                        return f"{selected_date.year}-{m:02d}-{d:02d}"
                                    except:
                                        pass
                                return None
                            
                            df_mf02['Note_Date'] = df_mf02['Ghi chú chuyển (phiếu)'].apply(extract_date)
                            df_mf02['Desc_Date'] = df_mf02['description'].apply(extract_date)
                            df_mf02['Final_Date'] = df_mf02['Note_Date'].fillna(df_mf02['Desc_Date'])
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            
                            mask_exclude = mask_non_sys & (df_mf02['Final_Date'].notna()) & (df_mf02['Final_Date'] != date_str)
                            df_mf02 = df_mf02[~mask_exclude].copy()
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            df_mf02.loc[mask_non_sys, 'SL_du'] = df_mf02.loc[mask_non_sys, 'SL_chuyen_du']
                        
                        df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()
    
                        # 4. Clean surplus crate code
                        def extract_surplus_crate(row):
                            val = str(row.get('Ghi chú chuyển (phiếu)', '')).strip()
                            if not val or val == 'nan':
                                return str(row['Mã thùng']).strip()
                            prefix = str(row['Mã chuyển hàng']).strip()
                            if prefix and val.startswith(prefix):
                                res = val[len(prefix):].strip()
                                if res: return res
                            import re
                            m = re.search(r'của thùng\s+([A-Z0-9_-]+)', val, flags=re.IGNORECASE)
                            if m: return m.group(1).strip()
                            m = re.search(r'(TRB[A-Z0-9_-]+|PT[A-Z0-9_-]+)', val)
                            if m: return m.group(1).strip()
                            return str(row['Mã thùng']).strip()
                            
                        if not df_surplus.empty:
                            df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
                        else:
                            df_surplus['Mã thùng'] = ""
    
                        # 5. Load layout
                        # file_layout already set based on khu_vuc
                        layout_df = pd.read_excel(file_layout, sheet_name=0)
                        
                        # Normalize columns
                        if 'Chi nhánh nhận' in layout_df.columns and 'STT' in layout_df.columns:
                            layout_df.rename(columns={'STT': 'Vị trí', 'Chi nhánh nhận': 'Siêu thị'}, inplace=True)
                        elif 'Siêu thị' not in layout_df.columns:
                            layout_df = pd.read_excel(file_layout, sheet_name=0, header=None)
                            if len(layout_df.columns) >= 3:
                                layout_df.rename(columns={0: 'Vị trí', 1: 'Mã', 2: 'Siêu thị'}, inplace=True)
                        
                        store_to_pos = {}
                        if 'Siêu thị' in layout_df.columns and 'Vị trí' in layout_df.columns:
                            for _, row in layout_df.iterrows():
                                try:
                                    st_name = str(row['Siêu thị']).strip().upper()
                                    pos_val = int(row['Vị trí'])
                                    store_to_pos[st_name] = pos_val
                                except (ValueError, TypeError):
                                    pass
    
                        # Clean barcodes and exclude 'CC' prefixes
                        df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
                        df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
                        df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
                        df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()
    
                        # 6. Group shortage & surplus
                        diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                            'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                            'Chênh lệch': 'sum',
                            'ĐVT': 'first',
                            'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                            'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                        }).reset_index()
                        diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu', 'Mã chuyển hàng': 'Mã chuyển hàng thiếu'}, inplace=True)
                        
                        
                        
                        if not df_surplus.empty:
                            du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                                'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                                'SL_du': 'sum',
                                'ĐVT': 'first',
                                'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                                'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                            }).reset_index()
                            du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
                        else:
                            du_grouped = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa'])
    
                        # Merge for internal matching
                        merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
                        merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
                        try:
                            ten_hang_col = [c for c in df_all.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
                            sku_mapping = dict(zip(df_all['Mã hàng'].astype(str).str.strip(), df_all[ten_hang_col]))
                            merged_internal['Tên hàng'] = merged_internal['Mã hàng'].astype(str).str.strip().map(sku_mapping).fillna(merged_internal['Tên hàng'])
                            merged_internal['Tên hàng'] = merged_internal['Tên hàng'].replace({'nan': '', 'None': ''})
                        except:
                            pass
                        merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
                        merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
                        merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('kg')
                        merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
                        merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()
    
                        # Step 1: Khớp nội bộ 100%
                        df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
                        
                        loi_text = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                        df_exact['Lỗi'] = loi_text
                        df_exact = df_exact[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
                        df_exact.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Lỗi']
                        df_exact['SL Thiếu'] = df_exact['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_exact['SL Thừa'] = df_exact['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Step 2: Khớp nội bộ một phần
                        df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
                        df_partial['Dif'] = df_partial['Chênh lệch'] - df_partial['SL_du']
                        df_partial['Lỗi'] = loi_text
                        df_partial = df_partial[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Dif', 'Lỗi']]
                        df_partial.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Chênh lệch thừa - thiếu', 'Lỗi']
                        df_partial['SL Thiếu'] = df_partial['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_partial['SL Thừa'] = df_partial['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Remainder calculation
                        merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
                        merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']
                        
                        rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 3: Khớp chéo liên siêu thị
                        cross_matches = []
                        skus_shortage = rem_shortages['Mã hàng'].unique()
                        skus_surplus = rem_surpluses['Mã hàng'].unique()
                        common_skus = set(skus_shortage).intersection(skus_surplus)
                        
                        matched_sho_keys = set()
                        matched_sur_keys = set()
                        
                        for sku in common_skus:
                            sku_shortages = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
                            sku_surpluses = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
                            
                            for idx_sur, row_sur in sku_surpluses.iterrows():
                                sur_qty = row_sur['Remaining_Surplus']
                                sur_store = row_sur['Chi nhánh nhận']
                                sur_crate = row_sur['Mã thùng thừa']
                                sur_transfer = row_sur['Mã chuyển hàng thừa']
                                sku_name = row_sur['Tên hàng']
                                dvt = row_sur['ĐVT']
                                pos_sur = store_to_pos.get(str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store, None)
                                
                                matching_shortages = []
                                for idx_sho, row_sho in sku_shortages.iterrows():
                                    sho_qty = row_sho['Remaining_Shortage']
                                    if abs(sur_qty - sho_qty) <= 0.01:
                                        matching_shortages.append(row_sho)
                                
                                if len(matching_shortages) > 0:
                                    best_match = None
                                    best_dist = 9999
                                    for sho_row in matching_shortages:
                                        sho_store = sho_row['Chi nhánh nhận']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        if pos_sur is not None and pos_sho is not None:
                                            dist = abs(pos_sur - pos_sho)
                                            if dist < best_dist:
                                                best_dist = dist
                                                best_match = sho_row
                                        else:
                                            if best_match is None:
                                                best_match = sho_row
                                    
                                    if best_match is not None:
                                        sho_store = best_match['Chi nhánh nhận']
                                        sho_qty = best_match['Remaining_Shortage']
                                        sho_crate = best_match['Mã thùng thiếu']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        
                                        prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                                        cross_matches.append({
                                            'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                                            'Vị trí Dư': pos_sur if pos_sur is not None else '-', 'Mã Thùng Thừa': sur_crate,
                                            'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                                            'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                                            'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                                            'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                                            'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                                        })
                                        matched_sur_keys.add((sur_store, sku))
                                        matched_sho_keys.add((sho_store, sku))
                                        
                        df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
                            'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 
                            'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 
                            'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
                        ])
                        
                        # Exclude matched from remainder
                        for index, row in rem_shortages.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
                                rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
                        for index, row in rem_surpluses.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
                                rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
                                
                        rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 4: Tổng Dư >= Tổng Thiếu
                        if not rem_shortages.empty or not rem_surpluses.empty:
                            sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
                            sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
                            sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Mã hàng', 'Tên hàng'], how='outer')
                            sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
                            sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
                            sku_totals['Dif'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
                            
                            df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
                            
                            sur_details, sho_details = [], []
                            for idx, row in df_total_gte.iterrows():
                                sku = row['Mã hàng']
                                sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
                                sur_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Surplus']:.3f} kg)" for _, r in sku_sur.iterrows()]))
                                sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
                                sho_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Shortage']:.3f} kg)" for _, r in sku_sho.iterrows()]) if len(sku_sho) > 0 else "Không có")
                            
                            if not df_total_gte.empty:
                                df_total_gte['Chi tiết ST nhận Dư'] = sur_details
                                df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
                                df_total_gte = df_total_gte[['Mã hàng', 'Tên hàng', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Dif']]
                                df_total_gte.columns = ['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)']
                            else:
                                df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
                        else:
                            df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
    
                        # Step 5: Chỉ có thiếu ròng
                        if not rem_shortages.empty:
                            df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
                            df_only_diff.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
                        else:
                            df_only_diff = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
                        
                        # Step 6: Chỉ có thừa ròng
                        if not rem_surpluses.empty:
                            df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Remaining_Surplus']].copy()
                            df_only_du.columns = ['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)']
                        else:
                            df_only_du = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)'])
    
                        # Display KPIs
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ff4b4b; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ 100%</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ff4b4b;">{len(df_exact)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ffaa00; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ MỘT PHẦN</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ffaa00;">{len(df_partial)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #00c0f2; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP CHÉO LIÊN ST 1-1</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #00c0f2;">{len(df_cross)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c4:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #2ebd59; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">THIẾU RÒNG / THỪA RÒNG</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #2ebd59;">{len(df_only_diff)} / {len(df_only_du)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
    
                        st.write("---")
                        # Export Excel to Memory for Download Button
                        output_excel = io.BytesIO()
                        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                            df_shortage.to_excel(writer, sheet_name='0. Dữ liệu Thiếu Raw', index=False)
                            df_surplus.to_excel(writer, sheet_name='0. Dữ liệu Thừa Raw', index=False)
                            df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
                            df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
                            df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
                            df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
                            df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
                            df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
                        
                        st.download_button(
                            label="📥 Tải Xuống Báo Cáo Đối Soát Chéo Excel",
                            data=output_excel.getvalue(),
                            file_name=f"Doi_Soat_Cheo_Thit_Ca_{date_str}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
    
                        # Tab presentation
                        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
                            "1. Khớp nội bộ 100%", 
                            "2. Khớp nội bộ một phần", 
                            "3. Khớp chéo liên ST 1-1", 
                            "4. Tổng Dư >= Tổng Thiếu", 
                            "5. Chỉ ghi nhận Thiếu ròng", 
                            "6. Chỉ ghi nhận Thừa ròng"
                        ])
                        
                        with sub_tab1:
                            loi_text_display = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                            st.subheader(f"1. Danh sách Khớp nội bộ 100% ({loi_text_display})")
                            st.dataframe(df_exact, use_container_width=True)
                        with sub_tab2:
                            st.subheader("2. Danh sách Khớp nội bộ một phần")
                            st.dataframe(df_partial, use_container_width=True)
                        with sub_tab3:
                            st.subheader("3. Danh sách Khớp chéo liên ST 1-1 (DC giao nhầm CH)")
                            st.dataframe(df_cross, use_container_width=True)
                        with sub_tab4:
                            st.subheader("4. Danh sách Tổng Dư >= Tổng Thiếu")
                            st.dataframe(df_total_gte, use_container_width=True)
                        with sub_tab5:
                            st.subheader("5. Danh sách Chỉ ghi nhận Thiếu ròng (Siêu thị nhận thiếu)")
                            st.dataframe(df_only_diff, use_container_width=True)
                        with sub_tab6:
                            st.subheader("6. Danh sách Chỉ ghi nhận Thừa ròng (Siêu thị nhận thừa)")
                            st.dataframe(df_only_du, use_container_width=True)
    
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi chạy đối soát: {e}")
                    st.exception(e)
    
    
    with tab_dc:
        st.header("👨‍🔧 Theo Dõi Tiến Độ Xử Lý & Phản Hồi Của DC")
        render_dc_feedback_progress_report(df_active, "Tab_3")
    


def render_dong_mat():

    data_url = "https://docs.google.com/spreadsheets/d/18LwNc2FTqSy9aKMtnqlBFmVQJPPn9E7ALnXajVXHhzI/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"
    shortage_condition = "i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name IN ('Chill - Miền Đông - SCF - Quá Cảnh', 'Frozen - Miền Đông - SCF - Quá Cảnh'))"
    surplus_condition = """
    (
        i.from_branch_id IN (SELECT branch_id FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard WHERE branch_name = 'Frozen - Miền Đông - SCF - Quá Cảnh')
        OR
        (i.from_branch_id = '6a34ed8d6607ba000703e235' AND i.created_by = '5f1152906c86b40006155d97')
    )
    """
    kho_name = "Kho Đông Mát"
    kho_code = "KDM"
    icon = "❄️"
    khu_vuc = "Đông Mát"

    def get_excel_bytes(df):
        output = io.BytesIO()
        df_to_export = df.copy()
        if isinstance(df_to_export.columns, pd.MultiIndex):
            df_to_export.columns = [' - '.join(str(c) for c in col if c).strip() for col in df_to_export.columns.values]
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_to_export.to_excel(writer, index=False)
        return output.getvalue()
    
    def display_df_with_download(styled_df, filename, height=None):
        if height:
            st.dataframe(styled_df, use_container_width=True, height=height)
        else:
            st.dataframe(styled_df, use_container_width=True)
        df_raw = styled_df.data if hasattr(styled_df, 'data') else styled_df
        try:
            excel_data = get_excel_bytes(df_raw)
            st.download_button(label="📥 Tải xuống Excel", data=excel_data, file_name=f"{filename}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=filename)
        except Exception as e:
            st.error(f"Lỗi xuất Excel: {e}")
    
    st.title(f"{icon} Báo Cáo Đối Soát {kho_name}")
    st.markdown("Dữ liệu tự động cập nhật từ Hệ thống Google Sheets")
    
    # Hàm làm sạch số lượng chênh lệch (Đơn vị nhỏ: cái, kg, hộp)
    def clean_qty(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Ở cột số lượng, dấu phẩy thường là phân cách thập phân (VD: 5,5 -> 5.5) hoặc dấu chấm cũng vậy (VD: -1.000 -> -1.0)
            # Không có số lượng hàng nghìn trên 1 dòng ở {kho_name.lower()}, nên ta quy về dạng chuẩn
            x = x.replace(',', '.')
            # Nếu có nhiều dấu chấm (lỗi định dạng), chỉ giữ lại dấu chấm cuối cùng
            if x.count('.') > 1:
                parts = x.split('.')
                x = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(x)
        except:
            return 0.0
    
    # Hàm làm sạch giá trị tiền tệ (Đơn vị lớn: VNĐ)
    def clean_val(x):
        if pd.isna(x) or x == '':
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x = x.strip()
            if x == '':
                return 0.0
            # Xử lý tiền tệ VNĐ (VD: -2.045.634 hoặc -2,045,634.00 hoặc -13.914.047,04)
            num_dots = x.count('.')
            num_commas = x.count(',')
            if num_dots > 0 and num_commas > 0:
                last_dot = x.rfind('.')
                last_comma = x.rfind(',')
                if last_comma > last_dot: # Định dạng VN: 1.234.567,89
                    x = x.replace('.', '').replace(',', '.')
                else: # Định dạng EN: 1,234,567.89
                    x = x.replace(',', '')
            elif num_dots > 1: # Nhiều dấu chấm: 1.234.567 -> bỏ chấm
                x = x.replace('.', '')
            elif num_commas > 1: # Nhiều dấu phẩy: 1,234,567 -> bỏ phẩy
                x = x.replace(',', '')
            elif num_dots == 1:
                # Nếu chỉ có 1 dấu chấm, xem nó là thập phân hay hàng nghìn (VD: -13914047.04 hay 16.000 VNĐ)
                parts = x.split('.')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace('.', '') # 16.000 -> 16000 VNĐ
                else:
                    pass # 12.5 -> 12.5
            elif num_commas == 1:
                parts = x.split(',')
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace(',', '') # 16,000 -> 16000 VNĐ
                else:
                    x = x.replace(',', '.') # 12,5 -> 12.5
        try:
            return float(x)
        except:
            return 0.0
    
    def clean_number(x):
        # Hàm dự phòng giữ nguyên tương thích ngược
        return clean_val(x)
    
    # HÀM XỬ LÝ SỐ AN TOÀN CHO BÁO CÁO
    def to_numeric(series):
        if series.dtype == 'object':
            return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return pd.to_numeric(series, errors='coerce').fillna(0)
    
    @st.cache_data(ttl=600)
    def load_data_rau_cu_v2(url):
        
        
        def read_csv_with_retry(url, max_retries=3):
            import time
            for i in range(max_retries):
                try:
                    response = requests.get(url, timeout=30, verify=False)
                    response.raise_for_status()
                    # Google Sheets CSV exports are UTF-8 encoded
                    content = response.content.decode('utf-8')
                                    # Dynamic header finding
                    lines = content.split('\n')
                    header_idx = 1
                    for idx, line in enumerate(lines[:10]):
                        if 'Số lượng chuyển' in line or 'Mã hàng' in line:
                            header_idx = idx
                            break
                    return pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
                except Exception as e:
                    if i == max_retries - 1:
                        raise e
                    time.sleep(2)
                    
        df = read_csv_with_retry(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Rename columns to standard ones if needed
        df.rename(columns={
            'ST': 'ID ST',
            'SL chênh lệch CXD': 'SL chênh lệch CXD'
        }, inplace=True)
        
        # Clean numeric columns
        qty_cols = ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Qty_N', 'Qty_O', 'Qty_P', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']
        
        # Clean money columns
        for col in ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', f'Tổng {kho_name.lower()}', 'Tổng chưa xác định']:
            matched_cols = [c for c in df.columns if col.lower() in c.lower()]
            for c in matched_cols:
                df[c] = df[c].apply(clean_val)
                
        df['Số lượng chuyển'] = df['Số lượng chuyển'].apply(clean_qty)
        df['Số lượng nhận'] = df['Số lượng nhận'].apply(clean_qty)
        df['Chênh lệch'] = df['Chênh lệch'].apply(clean_qty)
        
        if 'Chi nhánh nhận' in df.columns:
            df['Chi nhánh nhận'] = df['Chi nhánh nhận'].astype(str).str.replace(',', '.', regex=False)
                
        # Lọc lý do chênh lệch
        df['LyDo_HaoHut'] = df['Hao hụt'].astype(str).str.strip().str.lower()
        df['LyDo_SieuThi'] = df['Siêu thị'].astype(str).str.strip().str.lower()
        
        col_kho_list = [c for c in df.columns if f'{kho_name.upper()}' in c.upper() or 'KHO TH' in c.upper() or 'KHO RAU' in c.upper() or 'KRC' in c.upper()]
        col_kho = col_kho_list[0] if col_kho_list else None
        if col_kho:
            df['LyDo_Kho'] = df[col_kho].astype(str).str.strip().str.lower()
        else:
            df['LyDo_Kho'] = ''
        df['LyDo_Loi'] = df['Lỗi'].astype(str).str.strip().str.lower() if 'Lỗi' in df.columns else ''
        
        col_hao_hut_qty = 'Hạo hụt tự nhiê' if 'Hạo hụt tự nhiê' in df.columns else ('Hạo hụt tự nhiên' if 'Hạo hụt tự nhiên' in df.columns else None)
        df['Qty_N'] = df[col_hao_hut_qty].apply(clean_qty) if col_hao_hut_qty else df['Tổng hao hụt']
        df['Qty_O'] = df['SL trả tồn về ST'].apply(clean_qty) if 'SL trả tồn về ST' in df.columns else df['Tổng ST']
        df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_qty) if 'SL chênh lệch CXD' in df.columns else 0.0
        
        # Kết hợp các cột tổng chênh lệch
        col_total_kho_list = [c for c in df.columns if f'{kho_name}' in c or f'Tổng {kho_name.lower()}' in c or 'Tổng kho rau' in c.lower()]
        col_total_kho = col_total_kho_list[0] if col_total_kho_list else None
        col_total_cxd = [c for c in df.columns if 'Tổng chưa xác định' in c or 'chưa xác định' in c][0]
        
        df['Hao hụt'] = np.where(df['LyDo_HaoHut'].str.contains('hao hụt'), df['Qty_N'], 0)
        df['BS_ST'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị'), df['Qty_O'], 0)
        df['ST_NhapThieu'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        df['ST_SaiQT'] = np.where(df['LyDo_SieuThi'].str.contains('siêu thị') & ~df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
        
        import unicodedata
        lydo_kho_nfc = pd.Series([unicodedata.normalize('NFC', str(x)) if pd.notna(x) else '' for x in df['LyDo_Kho']], index=df.index)
        
        kho_lower_nfc = unicodedata.normalize('NFC', kho_name.lower())
        df['Kho_Rau'] = np.where(lydo_kho_nfc.str.contains(kho_lower_nfc) | lydo_kho_nfc.str.contains('kho rau') | lydo_kho_nfc.str.contains('krc'), df['Qty_P'], 0)
        df['CXD'] = np.where(lydo_kho_nfc.str.contains('chưa xác định'), df['Qty_P'], 0)
        
        if col_total_kho:
            df['Tổng kho rau'] = df[col_total_kho].apply(clean_val)
        else:
            df['Tổng kho rau'] = 0.0
        df['Tổng chưa xác định'] = df[col_total_cxd].apply(clean_val)
        
        # Parse dates strictly (Google Sheets sends dates in MM/DD/YYYY format)
        if 'Ngày' in df.columns:
            date_col = 'Ngày'
        elif 'Ngày chuyển hàng' in df.columns:
            date_col = 'Ngày chuyển hàng'
        elif 'Thời gian' in df.columns:
            date_col = 'Thời gian'
        elif 'Ngành' in df.columns:
            date_col = 'Ngành'
        else:
            date_col = 'Ngày'
        
        df['Ngày_parsed'] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
        df['Ngày_str'] = df['Ngày_parsed'].dt.strftime('%d/%m/%Y')
        df['Ngày'] = df['Ngày_parsed']
        df = df[df['Ngày_parsed'].notna()]
        
        # Categories & SKU
        clv2_col = 'CLV2' if 'CLV2' in df.columns else ('Loại hàng' if 'Loại hàng' in df.columns else 'Unnamed: 0')
        df['CLV2'] = df[clv2_col].fillna('Chưa phân loại')
        
        clv4_col = 'CLV4' if 'CLV4' in df.columns else 'CLV2'
        df['CLV4'] = df[clv4_col].fillna('Chưa phân loại')
        
        ten_hang_col = [c for c in df.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
        df['SKU_Full'] = df['Mã hàng'].fillna('').astype(str) + " - " + df[ten_hang_col].fillna('').astype(str)
        
        return df
    
    # HÀM TÍNH TOÁN NĂNG SUẤT DAILY MỚI
    def calculate_daily_metrics(data, group_by_col='CLV2'):
        if data.empty:
            return pd.DataFrame(columns=[
                group_by_col, 'SL chuyển', 'SL chênh lệch', 'GT chênh lệch', 
                'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 
                'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'Số lượng hao hụt', 
                'GT hao hụt', 'Tỷ lệ hao hụt', 'SL bs ST', 'GT bs ST', 
                'SL bs kho rau', 'GT bs kho rau', 'Đang xử lý', 'GT Đang xử lý', 
                'Chưa xử lý', 'GT Chưa xử lý', 'Không xử lý (WRITE OFF)', 'Giá trị WRITE OFF',
                'Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 'GT Lỗi ST (Nhập thiếu)', 'GT Lỗi ST (Sai QT)'
            ])
        
        df = data.copy()
        df['SL_chuyen_num'] = to_numeric(df['Số lượng chuyển'])
        df['CL_num'] = to_numeric(df['Chênh lệch'])
        df['GT_num'] = to_numeric(df['Tổng GT'])
        df['HH_qty'] = to_numeric(df['Hao hụt'])
        df['HH_val'] = to_numeric(df['Tổng hao hụt'])
        df['ST_qty'] = to_numeric(df['BS_ST'])
        df['ST_val'] = to_numeric(df['Tổng ST'])
        df['Kho_qty'] = to_numeric(df['Kho_Rau'])
        df['Kho_val'] = to_numeric(df['Tổng kho rau'])
        df['CXD_qty'] = to_numeric(df['CXD'])
        df['CXD_val'] = to_numeric(df['Tổng chưa xác định'])
        
        df['ST_NhapThieu_qty'] = to_numeric(df['ST_NhapThieu']) if 'ST_NhapThieu' in df.columns else 0.0
        df['ST_SaiQT_qty'] = to_numeric(df['ST_SaiQT']) if 'ST_SaiQT' in df.columns else 0.0
        
        price_col = 'Giá nhập \n( -VAT)' if 'Giá nhập \n( -VAT)' in df.columns else None
        if price_col:
            df['ST_NhapThieu_val'] = df['ST_NhapThieu_qty'] * to_numeric(df[price_col])
            df['ST_SaiQT_val'] = df['ST_SaiQT_qty'] * to_numeric(df[price_col])
        else:
            df['ST_NhapThieu_val'] = 0.0
            df['ST_SaiQT_val'] = 0.0
            
        df['Xuly_clean'] = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        
        groups = df.groupby(group_by_col, dropna=False)
        rows = []
        
        for g_name, g_df in groups:
            cl_df = g_df[g_df['CL_num'].abs() > 0]
            sl_chuyen = g_df['SL_chuyen_num'].sum()
            sl_cl = g_df['CL_num'].sum()
            gt_cl = g_df['GT_num'].sum()
            
            sl_st_cl = cl_df['ID ST'].nunique()
            sl_line_cl = len(cl_df)
            sl_line_hh = len(g_df[g_df['HH_qty'].abs() > 0])
            
            done_df = g_df[g_df['Xuly_clean'].str.contains('hoàn thành')]
            sl_line_done = len(done_df)
            tyle_line_done = f"{(sl_line_done / sl_line_cl * 100):.2f}%" if sl_line_cl > 0 else "0.00%"
            
            sl_hh = g_df['HH_qty'].sum()
            gt_hh = g_df['HH_val'].sum()
            tyle_hh = f"{(sl_hh / sl_chuyen * 100):.2f}%" if sl_chuyen > 0 else "0.00%"
            
            sl_bs_st = g_df['ST_qty'].sum()
            gt_bs_st = g_df['ST_val'].sum()
            sl_bs_kho = g_df['Kho_qty'].sum()
            gt_bs_kho = g_df['Kho_val'].sum()
            
            sl_st_nhap = g_df['ST_NhapThieu_qty'].sum()
            sl_st_sai = g_df['ST_SaiQT_qty'].sum()
            gt_st_nhap = g_df['ST_NhapThieu_val'].sum()
            gt_st_sai = g_df['ST_SaiQT_val'].sum()
            
            # Đang xử lý
            dang_xl_df = g_df[g_df['Xuly_clean'].str.contains('đang chuyển') | g_df['Xuly_clean'].str.contains('đang xử lý')]
            sl_dang_xl = dang_xl_df['CL_num'].sum()
            gt_dang_xl = dang_xl_df['GT_num'].sum()
            
            # Không xử lý (Write Off)
            write_off_df = g_df[g_df['Xuly_clean'].str.contains('không xử lý') | g_df['Xuly_clean'].str.contains('write of')]
            sl_write_off = write_off_df['CL_num'].sum()
            gt_write_off = write_off_df['GT_num'].sum()
            
            # Chưa xử lý
            chua_xl_df = g_df[~g_df['Xuly_clean'].str.contains('hoàn thành') & 
                              ~g_df['Xuly_clean'].str.contains('đang chuyển') & 
                              ~g_df['Xuly_clean'].str.contains('đang xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('không xử lý') & 
                              ~g_df['Xuly_clean'].str.contains('write of')]
            sl_chua_xl = chua_xl_df['CL_num'].sum()
            gt_chua_xl = chua_xl_df['GT_num'].sum()
            
            row = {
                group_by_col: g_name,
                'SL chuyển': sl_chuyen,
                'SL chênh lệch': sl_cl,
                'GT chênh lệch': gt_cl,
                'SL ST chênh lệch': sl_st_cl,
                'SL line chênh lệch': sl_line_cl,
                'SL line hao hụt': sl_line_hh,
                'SL line đã xử lý': sl_line_done,
                'Tỷ lệ line đã xử lý': tyle_line_done,
                'Số lượng hao hụt': sl_hh,
                'GT hao hụt': gt_hh,
                'Tỷ lệ hao hụt': tyle_hh,
                'SL bs ST': sl_bs_st,
                'GT bs ST': gt_bs_st,
                'SL bs kho rau': sl_bs_kho,
                'GT bs kho rau': gt_bs_kho,
                'Đang xử lý': sl_dang_xl,
                'GT Đang xử lý': gt_dang_xl,
                'Chưa xử lý': sl_chua_xl,
                'GT Chưa xử lý': gt_chua_xl,
                'Không xử lý (WRITE OFF)': sl_write_off,
                'Giá trị WRITE OFF': gt_write_off,
                'Lỗi ST (Nhập thiếu)': sl_st_nhap,
                'Lỗi ST (Sai QT)': sl_st_sai,
                'GT Lỗi ST (Nhập thiếu)': gt_st_nhap,
                'GT Lỗi ST (Sai QT)': gt_st_sai
            }
            rows.append(row)
            
        return pd.DataFrame(rows)
    
    # HÀM HIỂN THỊ BẢNG DAILY
    def display_daily_table(df, cols, title_prefix, group_by_col='CLV2'):
        if df.empty:
            st.info("Không có dữ liệu.")
            return
        df_to_show = df.copy()
        for col in cols:
            if col not in df_to_show.columns:
                df_to_show[col] = 0.0
        df_to_show = df_to_show[cols]
        format_custom_table_with_total(df_to_show, group_by_col, title_prefix)
    
    # HÀM TÍNH TỔNG QUAN DAILY DẠNG TEXT
    def compute_daily_summary(df, date_str):
        if df.empty:
            return None
        
        cl_qty = to_numeric(df['Chênh lệch'])
        gt_val = to_numeric(df['Tổng GT'])
        
        total_items = cl_qty.abs().sum()
        total_value = gt_val.abs().sum()
        
        xuly_clean = df['Xử lý'].fillna('').astype(str).str.strip().str.lower()
        df_done = df[xuly_clean.str.contains('hoàn thành')]
        
        ret_qty = to_numeric(df_done['Kho_Rau']).abs().sum()
        bs_qty = to_numeric(df_done['BS_ST']).abs().sum()
        lost_qty = to_numeric(df_done['Hao hụt']).abs().sum()
        
        processed_qty = ret_qty + bs_qty + lost_qty
        remaining_qty = total_items - processed_qty
        if remaining_qty < 0:
            remaining_qty = 0.0
            
        return {
            'date': date_str,
            'total_items': int(total_items),
            'total_value': total_value,
            'processed': int(processed_qty),
            'return': int(ret_qty),
            'bs': int(bs_qty),
            'lost': int(lost_qty),
            'remaining': int(remaining_qty)
        }
    
    # Insight Generators y hệt bên Kho Rau
    def generate_insights(df_raw, table_type, df_grouped=None, df_metrics=None, date_str=None):
        if df_raw.empty and (df_grouped is None or df_grouped.empty):
            return "Không có dữ liệu trong kỳ báo cáo này."
        
        def get_hh_insight():
            if df_metrics is not None and not df_metrics.empty and 'Số lượng chuyển' in df_metrics.columns and 'Số lượng hao hụt' in df_metrics.columns:
                tong_chuyen = df_metrics['Số lượng chuyển'].sum()
                tong_hh = df_metrics['Số lượng hao hụt'].sum()
                if tong_chuyen > 0:
                    return f"\n- Tỷ lệ hao hụt ghi nhận: {round((tong_hh / tong_chuyen) * 100, 2)}%."
            return ""
        
        try:
            if table_type == "Bảng 1":
                df_raw_tmp = df_raw.copy()
                df_raw_tmp['Chênh_lệch_num'] = to_numeric(df_raw_tmp['Chênh lệch'])
                df_raw_tmp['Kho_Rau_num'] = to_numeric(df_raw_tmp['Kho_Rau'])
                df_raw_tmp['BS_ST_num'] = to_numeric(df_raw_tmp['BS_ST'])
                
                total_lines = len(df_raw_tmp)
                total_chenh_lech = df_raw_tmp['Chênh_lệch_num'].sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                msg = f"Trong kỳ có tổng cộng {total_lines} dòng phát sinh chênh lệch (Tổng chênh lệch: {fmt(total_chenh_lech)}).\n"
                msg += "\n- Phân tích 3 nhóm ngành hàng (CLV4) phát sinh chênh lệch cao nhất:\n"
                
                clv4_lines = df_raw_tmp['CLV4'].value_counts()
                top3_clv4 = clv4_lines.head(3)
                
                for clv4, lines in top3_clv4.items():
                    sub_df = df_raw_tmp[df_raw_tmp['CLV4'] == clv4]
                    sub_cl = sub_df['Chênh_lệch_num'].sum()
                    sub_kr = sub_df['Kho_Rau_num'].sum()
                    msg += f"  + [{clv4}]: {lines} dòng (Tổng chênh lệch: {fmt(sub_cl)} | Trả về {kho_name.lower()}: {fmt(sub_kr)})\n"
                    
                msg += "\n- Phân bổ trả về Siêu Thị (ST):\n"
                st_by_clv4 = df_raw_tmp.groupby('CLV4')['BS_ST_num'].sum().sort_values(ascending=False)
                st_by_clv4 = st_by_clv4[st_by_clv4 > 0]
                
                if not st_by_clv4.empty:
                    top_st_clv4 = st_by_clv4.index[0]
                    top_st_val = st_by_clv4.iloc[0]
                    total_st = st_by_clv4.sum()
                    if top_st_val > (total_st * 0.3) and len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST tập trung nhiều nhất ở nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                    elif len(st_by_clv4) > 1:
                        msg += f"  Số lượng trả về ST nằm rải rác lẻ tẻ (cao nhất là [{top_st_clv4}] với {fmt(top_st_val)}).\n"
                    else:
                        msg += f"  Số lượng trả về ST thuộc về nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                else:
                    msg += "  Không phát sinh số lượng chênh lệch trả về ST trong kỳ.\n"
                    
                msg += "  -> Nguyên nhân: Do ST thao tác sai nên phải tạo lại thôi."
                msg += get_hh_insight()
                return msg
                
            elif table_type == "Bảng 1.1":
                if df_grouped is not None and not df_grouped.empty:
                    top_nguon = df_grouped.iloc[0]['Nguồn xác nhận']
                    top_sl = df_grouped.iloc[0]['Tổng ({kho_name.lower()} + ST)'] if 'Tổng ({kho_name.lower()} + ST)' in df_grouped.columns else df_grouped.iloc[0]['Tổng (Kho Rau + ST)']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    if top_nguon == 'Check camera':
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Việc dựa phần lớn vào Check camera cho thấy tình trạng ST báo thiếu/dư hàng nhưng không cung cấp đủ hình ảnh xác thực đang khá cao. Cần nhắc nhở ST tuân thủ quy định chụp hình."
                    else:
                        return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là dựa vào [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Điều này phản ánh cơ sở dữ liệu chính yếu mà DC dùng để đối soát và phân bổ lượng hàng chênh lệch trong kỳ."
                
            elif table_type == "Bảng 2.1_New":
                if df_metrics is not None and not df_metrics.empty:
                    t_cl = df_metrics['SL chênh lệch'].sum()
                    if t_cl > 0:
                        l_st_nhap = df_metrics.get('Lỗi ST (Nhập thiếu)', pd.Series([0])).sum()
                        l_st_sai = df_metrics.get('Lỗi ST (Sai QT)', pd.Series([0])).sum()
                        l_st_tong = l_st_nhap + l_st_sai
                        pct_st = (l_st_tong / t_cl) * 100
                        pct_nhap = (l_st_nhap / t_cl) * 100
                        pct_sai = (l_st_sai / t_cl) * 100
                        
                        giao_thieu_5 = df_metrics.get('<= 5%', pd.Series([0])).sum()
                        giao_thieu_10 = df_metrics.get('5-10%', pd.Series([0])).sum()
                        giao_thieu_15 = df_metrics.get('10-15%', pd.Series([0])).sum()
                        giao_thieu_15_plus = df_metrics.get('> 15%', pd.Series([0])).sum()
                        
                        pct_5 = (giao_thieu_5 / t_cl) * 100
                        pct_10 = (giao_thieu_10 / t_cl) * 100
                        pct_15 = (giao_thieu_15 / t_cl) * 100
                        pct_15_plus = (giao_thieu_15_plus / t_cl) * 100
                        
                        d_str = "kỳ báo cáo"
                        if date_str and date_str != "Tất cả các ngày":
                            try:
                                d_str = "ngày " + date_str.split('/')[0] + "." + date_str.split('/')[1]
                            except:
                                d_str = "ngày " + str(date_str)
                                
                        def get_top_clv4(col):
                            if col in df_metrics.columns and df_metrics[col].max() > 0:
                                top_row = df_metrics.loc[df_metrics[col].idxmax()]
                                return f"[{top_row['CLV4']}] - {int(top_row[col])} item"
                            return ""
                            
                        top_5_clv4 = get_top_clv4('<= 5%')
                        top_10_clv4 = get_top_clv4('5-10%')
                        top_15_clv4 = get_top_clv4('10-15%')
                        top_15_plus_clv4 = get_top_clv4('> 15%')
                                
                        msg = f"Hàng KG có số lượng nhập nhưng phát sinh chênh lệch ghi nhận {d_str}\n"
                        msg += f"- Lỗi ST chiếm {pct_st:.1f}%: trong đó nhập sót {pct_nhap:.1f}% và sai QT chiếm {pct_sai:.1f}%\n"
                        if l_st_sai > 0:
                            msg += f"  + SL ST sai QT: {int(l_st_sai)}\n"
                        msg += f"- Giao thiếu:\n"
                        msg += f"  + Nhóm <= 5%: {pct_5:.1f}%\n"
                        if top_5_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_5_clv4}\n"
                        msg += f"  + Nhóm 5 - 10%: {pct_10:.1f}%\n"
                        if top_10_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_10_clv4}\n"
                        msg += f"  + Nhóm 10 - 15%: {pct_15:.1f}%\n"
                        if top_15_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_15_clv4}\n"
                        msg += f"  + Nhóm > 15%: {pct_15_plus:.1f}%"
                        if top_15_plus_clv4: msg += f"\n    -> Nhóm lệch nhiều nhất: {top_15_plus_clv4}"
                        return msg
                return "Chưa có đủ dữ liệu để đánh giá."
                
            elif table_type == "Bảng 2.1":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                return f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh." + get_hh_insight()
                
            elif table_type == "Bảng 3":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                base_msg = f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh."
                
                df_kr = df_raw.copy()
                df_kr['Kho_Rau_num'] = to_numeric(df_kr['Kho_Rau'])
                kr_by_clv4 = df_kr.groupby('CLV4')['Kho_Rau_num'].sum().sort_values(ascending=False)
                kr_by_clv4 = kr_by_clv4[kr_by_clv4 > 0]
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                if not kr_by_clv4.empty:
                    top3 = kr_by_clv4.head(3)
                    top3_msg = "\n- Top nhóm ngành hàng (CLV4) đang có lượng chênh lệch trả về {kho_name.lower()} cao nhất:\n"
                    for i, (clv4, val) in enumerate(top3.items(), 1):
                        top3_msg += f"  {i}. {clv4}: {fmt(val)}\n"
                else:
                    top3_msg = "\n- Không ghi nhận hàng Pack nào có chênh lệch trả về {kho_name.lower()} trong kỳ."
                    
                return base_msg + top3_msg.rstrip() + get_hh_insight()
                
            elif table_type == "Bảng 2.2":
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                sku_counts = df_raw['SKU_Full'].value_counts()
                top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
                top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
                
                sum_kr = to_numeric(df_raw['Kho_Rau']).sum()
                sum_st = to_numeric(df_raw['BS_ST']).sum()
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                    
                return (f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n"
                        f"- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh.\n"
                        f"- Vấn đề chênh lệch này được phân bổ xử lý như sau:\n"
                        f"  + Trả về ST (Số lượng: {fmt(sum_st)}): Lý do là DC giao bù do ban đầu giao sai điểm.\n"
                        f"  + Trả {kho_name.lower()} (Số lượng: {fmt(sum_kr)}): Do có ST khác nhận dư số này và có ST nhận thiếu."
                        f"{get_hh_insight()}")
                
            elif table_type == "Bảng 4":
                if df_grouped is not None and not df_grouped.empty:
                    top_sku = df_grouped.iloc[0]['Mã & Tên hàng']
                    top_hh = df_grouped.iloc[0]['Tổng số lượng hao hụt']
                    
                    clv4_counts = df_raw['CLV4'].value_counts()
                    top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                    
                    return f"- Top 3 ngành hàng (CLV4) phát sinh hao hụt nhiều nhất: {top3_clv4_str}.\n- Mã hàng có sản lượng hao hụt nghiêm trọng nhất là [{top_sku}] (Hao hụt: {top_hh} KG).\n- Khuyến nghị: Cần ưu tiên kiểm tra chất lượng thực tế và quy trình đóng gói đối với mã hàng này."
    
            elif table_type == "Bảng 6":
                if df_grouped is not None and not df_grouped.empty:
                    top_dc = df_grouped.iloc[0]['DC xác nhận']
                    top_loi = df_grouped.iloc[0]['Lỗi'] if 'Lỗi' in df_grouped.columns else ('Nhom_Loi' if 'Nhom_Loi' in df_grouped.columns else 'Không phân loại')
                    top_sl = df_grouped.iloc[0]['Tổng số lượng']
                    
                    def fmt(val):
                        try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except: return str(val)
                    
                    return f"- Dựa trên xác nhận của DC, lỗi [{top_loi}] được ghi nhận nhiều nhất từ [{top_dc}] với tổng số lượng trả về {kho_name.lower()} là {fmt(top_sl)}.\n- Khuyến nghị: DC cần kiểm tra lại quy trình xuất hàng và kiểm đếm để giảm thiểu tình trạng này."
    
        except Exception as e:
            return "Chưa đủ dữ liệu để tạo nhận xét tự động."
            
        return ""
    
    def render_dc_feedback_progress_report(df, tab_id=""):
        st.write("---")
        
        if df.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi.")
            return
            
        # Tính toán daily summary (Toàn hệ thống)
        df['GT_chuyen_temp'] = to_numeric(df.get('Số lượng chuyển', pd.Series(0, index=df.index))) * to_numeric(df.get('Giá trị ĐV', pd.Series(0, index=df.index)))
        daily_summary = df.groupby('Ngày_str').agg(
            SL_chuyen=('Số lượng chuyển', lambda x: to_numeric(x).sum()),
            SL_chenh_lech=('Chênh lệch', lambda x: to_numeric(x).sum()),
            GT_chuyen=('GT_chuyen_temp', 'sum'),
            GT_chenh_lech=('Tổng GT', lambda x: to_numeric(x).sum())
        ).reset_index()
    
        df_dc = df[to_numeric(df.get('Kho_Rau', pd.Series(0, index=df.index))) > 0].copy()
        df_dc['SL_CXD'] = to_numeric(df_dc.get('Kho_Rau', pd.Series(0, index=df_dc.index)))
        df_dc['GT_CXD'] = to_numeric(df_dc.get('Tổng kho rau', pd.Series(0, index=df_dc.index)))
            
        if df_dc.empty:
            st.info("Không có dữ liệu tiến độ DC phản hồi trong kỳ báo cáo này.")
            return
            
        df_dc['DC_Xac_Nhan'] = df_dc['DC xác nhận'].fillna('Chưa xác nhận')
        df_dc['DC_Xac_Nhan'] = df_dc['DC_Xac_Nhan'].apply(lambda x: 'Chưa xác nhận' if str(x).strip() == '' else x)
        loi_col = 'Lỗi' if 'Lỗi' in df_dc.columns else ('LyDo_Loi' if 'LyDo_Loi' in df_dc.columns else None)
        if loi_col:
            df_dc['Nhom_Loi'] = df_dc[loi_col].fillna('Không phân loại').replace('', 'Không phân loại')
        else:
            df_dc['Nhom_Loi'] = 'Không phân loại'
        df_dc['Chi_Tiet_Loi'] = 'Không ghi chú'
        
        df_chua_xn = df_dc[df_dc['DC_Xac_Nhan'] == 'Chưa xác nhận']
        tong_chua_xn = df_chua_xn['SL_CXD'].sum()
        tong_gt_chua_xn = df_chua_xn['GT_CXD'].sum()
        
        top_loi_name = "Không có"
        if not df_chua_xn.empty:
            loi_sum = df_chua_xn.groupby('Nhom_Loi')['SL_CXD'].sum()
            if not loi_sum.empty and loi_sum.max() > 0:
                top_loi_name = f"{loi_sum.idxmax()} ({int(loi_sum.max())} item)"
                
        # Hiển thị Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🔴 Tổng chờ DC xác nhận", value=f"{int(tong_chua_xn)} item", delta=f"{format_vn(tong_gt_chua_xn)} VNĐ", delta_color="off")
        with col2:
            st.metric(label="🔥 Top 1 Lỗi chờ phản hồi", value=top_loi_name)
        
        st.write("### 📌 Bảng chi tiết (Tiến độ DC)")
        tab_ngay, tab_loi = st.tabs(["📅 Góc nhìn 1: Theo Ngày", "⚠️ Góc nhìn 2: Theo Nhóm Lỗi"])
        
        # Góc nhìn 1
        with tab_ngay:
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_ngay = pd.pivot_table(df_dc, values='SL_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            dc_cols = [c for c in pivot_ngay.columns if c != 'Ngày_str']
            pivot_ngay['SL {kho_name.upper()}'] = pivot_ngay[dc_cols].sum(axis=1)
            
            final_ngay = pd.merge(daily_summary[['Ngày_str', 'SL_chuyen', 'SL_chenh_lech']], pivot_ngay, on='Ngày_str', how='right')
            sorted_dc_cols = [c for c in dc_cols if c != 'Chưa xác nhận']
            sorted_dc_cols.sort()
            if 'Chưa xác nhận' in dc_cols:
                sorted_dc_cols = ['Chưa xác nhận'] + sorted_dc_cols
                
            col_order = ['Ngày_str', 'SL_chuyen', 'SL_chenh_lech', 'SL {kho_name.upper()}'] + sorted_dc_cols
            final_ngay = final_ngay[[c for c in col_order if c in final_ngay.columns]]
            
            final_ngay['% Chưa xác nhận'] = final_ngay.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay['% Tiến độ phản hồi'] = final_ngay.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'SL_chuyen': 'SL chuyển',
                'SL_chenh_lech': 'SL chênh lệch'
            }, inplace=True)
            format_custom_table_with_total(final_ngay, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_ngay_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_ngay_gt['GT {kho_name.upper()}'] = pivot_ngay_gt[dc_cols].sum(axis=1)
            final_ngay_gt = pd.merge(daily_summary[['Ngày_str', 'GT_chuyen', 'GT_chenh_lech']], pivot_ngay_gt, on='Ngày_str', how='right')
            
            col_order_gt = ['Ngày_str', 'GT_chuyen', 'GT_chenh_lech', 'GT {kho_name.upper()}'] + sorted_dc_cols
            final_ngay_gt = final_ngay_gt[[c for c in col_order_gt if c in final_ngay_gt.columns]]
            
            final_ngay_gt['% Chưa xác nhận'] = final_ngay_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            final_ngay_gt['% Tiến độ phản hồi'] = final_ngay_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            final_ngay_gt.rename(columns={
                'Ngày_str': 'Ngày chuyển hàng',
                'GT_chuyen': 'GT chuyển (VNĐ)',
                'GT_chenh_lech': 'GT chênh lệch (VNĐ)'
            }, inplace=True)
            format_custom_table_with_total(final_ngay_gt, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_GT_{tab_id}")
            
        # Góc nhìn 2
        with tab_loi:
            df_dc['Nhóm Lỗi & Chi tiết'] = df_dc['Nhom_Loi'] + " | " + df_dc['Chi_Tiet_Loi']
            
            st.markdown("**1. Bảng Số Lượng (Item)**")
            pivot_loi = pd.pivot_table(df_dc, values='SL_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi['SL {kho_name.upper()}'] = pivot_loi[dc_cols].sum(axis=1)
            col_order_loi = ['Nhóm Lỗi & Chi tiết', 'SL {kho_name.upper()}'] + sorted_dc_cols
            pivot_loi = pivot_loi[[c for c in col_order_loi if c in pivot_loi.columns]]
            
            pivot_loi['% Chưa xác nhận'] = pivot_loi.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi['% Tiến độ phản hồi'] = pivot_loi.apply(
                lambda r: f"{((r['SL {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['SL {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('SL {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_SL_{tab_id}")
            
            st.markdown("**2. Bảng Giá Trị (VNĐ)**")
            pivot_loi_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
            pivot_loi_gt['GT {kho_name.upper()}'] = pivot_loi_gt[dc_cols].sum(axis=1)
            pivot_loi_gt = pivot_loi_gt[[c for c in col_order_loi if c in pivot_loi_gt.columns]]
            pivot_loi_gt.rename(columns={'SL {kho_name.upper()}': 'GT {kho_name.upper()}'}, inplace=True)
            
            pivot_loi_gt['% Chưa xác nhận'] = pivot_loi_gt.apply(
                lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "0,00%", axis=1
            )
            pivot_loi_gt['% Tiến độ phản hồi'] = pivot_loi_gt.apply(
                lambda r: f"{((r['GT {kho_name.upper()}'] - r.get('Chưa xác nhận', 0)) / r['GT {kho_name.upper()}'] * 100):.2f}%".replace('.', ',') if r.get('GT {kho_name.upper()}', 0) > 0 else "100,00%", axis=1
            )
            
            format_custom_table_with_total(pivot_loi_gt, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_GT_{tab_id}")
    
    # Format màu đỏ cho số chênh lệch
    def color_red_for_chenhlech(val):
        color = 'red' if isinstance(val, (int, float)) and val > 0 else ''
        return f'color: {color}'
    
    # Format số theo chuẩn Việt Nam (1.000.000,00)
    def format_vn(val):
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float, np.integer, np.floating)):
            if val == int(val):
                return f"{int(val):,}".replace(',', '.')
            else:
                formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                if formatted.endswith(',00'):
                    return formatted[:-3]
                return formatted
        return val
    
    def format_money(val):
        if val >= 1000000:
            return f"{val/1000000:.1f} triệu".replace('.', ',')
        elif val >= 1000:
            return f"{val/1000:.1f} ngàn".replace('.', ',')
        return format_vn(val)
    
    def format_custom_table_with_total(df, name_col, title_prefix):
        if df.empty: return
        
        tong_df = pd.DataFrame(index=[0])
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                tong_df[col] = df[col].sum()
            else:
                tong_df[col] = ''
                
        tuples = []
        for col in df.columns:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    total_str = f"🟡 {format_vn(val)}"
                else:
                    total_str = f"🟡 {str(val)}"
            else:
                total_str = '⭐ TỔNG' if col == name_col else ''
                
            tuples.append((total_str, col))
            
        df_renamed = df.copy()
        df_renamed.columns = pd.MultiIndex.from_tuples(tuples)
        styler = df_renamed.style.format(format_vn).hide(axis="index")
        display_df_with_download(styler, f"Daily_{title_prefix}")
    
    # ==========================================
    # GIAO DIỆN CHIA TAB
    # ==========================================
    
    
    try:
        df_all = load_data_rau_cu_v2(data_url)
        st.sidebar.success(f"Tải dữ liệu từ Google Sheets thành công!")
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu Google Sheets: {e}")
        st.stop()
    
    tab_main, tab_daily, tab_dc = st.tabs(["📊 Báo Cáo Tổng Quan", "📈 Báo Cáo Năng Suất Daily", "👨‍🔧 Tiến Độ DC Phản Hồi"])
    
    # ==========================================
    # TRANG 1: BÁO CÁO TỔNG QUAN
    # ==========================================
    with tab_main:
        # Nút Cập nhật dữ liệu mới nhất
        if st.button('🔄 Cập nhật dữ liệu mới nhất'):
            st.cache_data.clear()
            st.rerun()
            
        df_active = df_all.copy()
    
        # Process Dataframes
        pivot_ngay_sum = df_active.groupby('Ngày_str')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_ngay = pivot_ngay_sum.fillna(0).reset_index()
        
        pivot_ngay['Ngày_dt'] = pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay = pivot_ngay.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        # Tính phần trăm đã phân bổ / chênh lệch cho từng ngày
        sum_dist = pivot_ngay['Hao hụt'] + pivot_ngay['BS_ST'] + pivot_ngay['Kho_Rau'] + pivot_ngay['CXD']
        pct_vals = np.where(pivot_ngay['Chênh lệch'].abs() > 0, (sum_dist / pivot_ngay['Chênh lệch'].abs()) * 100, 0.0)
        pivot_ngay['% Cột Tổng'] = [f"{v:.2f}%".replace('.', ',') for v in pct_vals]
    
        tong_row_ngay = pivot_ngay.sum(numeric_only=True).to_frame().T
        tong_row_ngay['Ngày_str'] = 'Tổng'
        
        # Tính phần trăm đã phân bổ / chênh lệch cho hàng Tổng
        total_sum_dist = tong_row_ngay['Hao hụt'].iloc[0] + tong_row_ngay['BS_ST'].iloc[0] + tong_row_ngay['Kho_Rau'].iloc[0] + tong_row_ngay['CXD'].iloc[0]
        total_cl = abs(tong_row_ngay['Chênh lệch'].iloc[0])
        total_pct = (total_sum_dist / total_cl) * 100 if total_cl > 0 else 0.0
        tong_row_ngay['% Cột Tổng'] = f"{total_pct:.2f}%".replace('.', ',')
    
        pivot_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        tong_row_ngay.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
    
        # Theo ngày (Giá trị)
        pivot_ngay_val = df_active.groupby('Ngày_str')[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_ngay_val['Ngày_dt'] = pd.to_datetime(pivot_ngay_val['Ngày_str'], format='%d/%m/%Y', errors='coerce')
        pivot_ngay_val = pivot_ngay_val.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
    
        tong_row_ngay_val = pivot_ngay_val.sum(numeric_only=True).to_frame().T
        if not tong_row_ngay_val.empty: tong_row_ngay_val['Ngày_str'] = 'Tổng'
    
        pivot_ngay_val.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
            'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
            'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
        }, inplace=True)
        if not tong_row_ngay_val.empty:
            tong_row_ngay_val.rename(columns={
                'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
                'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
                'Tổng kho rau': 'Giá trị đã trả {kho_name} (VNĐ)',
                'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
            }, inplace=True)
    
        # Theo CLV2
        pivot_clv2_sum = df_active.groupby('CLV2', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
        pivot_clv2_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('CLV2', dropna=False).size().rename('Số lượng line')
        pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
        pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
        pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False)
        
        tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
        tong_row_clv2['CLV2'] = 'Tổng'
    
        # Top 5 CLV4
        clv4_sum = df_active.groupby('CLV4', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
        clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
        pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)
    
        # Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
        pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line chênh lệch')
        pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line nhập=0')
    
        pivot_qty = pivot_qty_sum.join(pivot_qty_count).join(pivot_qty_nhap0).fillna(0).reset_index()
        pivot_qty.rename(columns={
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty['Tỷ lệ (%)'] = np.where(pivot_qty['Số lượng chuyển'] > 0, (pivot_qty['Chênh lệch'] / pivot_qty['Số lượng chuyển']) * 100, 0)
        pivot_qty['Abs_ChenhLech'] = pivot_qty['Chênh lệch'].abs()
        pivot_qty = pivot_qty.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty['SL line chênh lệch'] = pivot_qty['SL line chênh lệch'].astype(int)
        pivot_qty['SL line nhập=0'] = pivot_qty['SL line nhập=0'].astype(int)
        pivot_qty.insert(3, 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', pivot_qty['SL line nhập=0'].astype(str) + " / " + pivot_qty['SL line chênh lệch'].astype(str))
        pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        # Bảng GIÁ TRỊ Chi tiết Từng Ngày - Siêu Thị
        pivot_val_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)
    
        # Thẻ thông tin (Metrics)
        st.write("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng số lượng chuyển", format_vn(df_active['Số lượng chuyển'].sum()))
        with col2:
            st.metric("Tổng số lượng nhận", format_vn(df_active['Số lượng nhận'].sum()))
        with col3:
            st.metric("TỔNG CHÊNH LỆCH", format_vn(df_active['Chênh lệch'].sum()))
    
        def create_multiindex_headers(df, tong_df):
            if df.empty or tong_df.empty: return df
            tuples = []
            for i, col in enumerate(df.columns):
                if col in tong_df.columns:
                    val = tong_df.iloc[0][col]
                    if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                        if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                            tuples.append((f"🟡 {format_vn(val)}", col))
                        else:
                            tuples.append((f"🟡 {str(val)}", col))
                    else:
                        tuples.append(('⭐ TỔNG' if i == 0 else '', col))
                else:
                    tuples.append(('⭐ TỔNG' if i == 0 else '', col))
            df_new = df.copy()
            df_new.columns = pd.MultiIndex.from_tuples(tuples)
            return df_new
    
        pivot_ngay_renamed = create_multiindex_headers(pivot_ngay, tong_row_ngay)
        pivot_ngay_val_renamed = create_multiindex_headers(pivot_ngay_val, tong_row_ngay_val)
        pivot_clv2_renamed = create_multiindex_headers(pivot_clv2, tong_row_clv2)
    
        # Layout các bảng
        st.write("---")
        st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
        
        if not pivot_ngay.empty:
            top_day = pivot_ngay.sort_values(by='Chênh lệch', ascending=False).iloc[0]
            st.info(f"🔹 **Ngày biến động nhất**: **{top_day['Ngày_str']}** ghi nhận mức chênh lệch cao nhất ({format_vn(top_day['Chênh lệch'])} item).")
    
        tab_ngay_qty, tab_ngay_val = st.tabs(["📊 Số lượng (Từng Ngày)", "💰 Giá trị (Từng Ngày)"])
    
        with tab_ngay_qty:
            display_df_with_download(pivot_ngay_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_ngay_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_Theo_Ngay_So_Luong")
    
        with tab_ngay_val:
            display_df_with_download(pivot_ngay_val_renamed.style.format(format_vn), "Tong_Hop_Theo_Ngay_Gia_Tri")
    
        st.write("---")
        col4, col5 = st.columns(2)
        with col4:
            st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
            if not pivot_clv4.empty:
                top_clv4 = pivot_clv4.iloc[0]
                st.info(f"🔹 **Mã hàng (CLV4) cảnh báo đỏ**: **{top_clv4['CLV4']}** đang dẫn đầu với mức chênh lệch {format_vn(top_clv4['Chênh lệch'])}.")
            display_df_with_download(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), "Top_5_CLV4")
        with col5:
            st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
            if not pivot_clv2.empty:
                top_clv2 = pivot_clv2.iloc[0]
                st.info(f"🔹 **Ngành hàng (CLV2) trọng điểm**: **{top_clv2['CLV2']}** chiếm số lượng chênh lệch cao nhất ({format_vn(top_clv2['Chênh lệch'])}).")
            display_df_with_download(pivot_clv2_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_clv2_renamed.columns if 'Chênh lệch' in c[1]]), "Tong_Hop_CLV2")
    
        st.write("---")
        # Sort dates chronologically
        sorted_dates_dt = sorted(pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce').dropna().unique())
        sorted_dates = [d.strftime('%d/%m/%Y') for d in sorted_dates_dt if d.strftime('%d/%m/%Y') != 'Tổng']
        dates = ["Tất cả các ngày"] + sorted_dates
    
        # 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)
        st.subheader("🛒 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)")
        item_qty_sum = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        item_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST chênh lệch')
        item_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_item = item_qty_sum.join(item_qty_count).join(item_qty_nhap0).fillna(0).reset_index()
        pivot_qty_item.rename(columns={
            'CLV4': 'Mã hàng (CLV4)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_item['Tỷ lệ (%)'] = np.where(pivot_qty_item['Số lượng chuyển'] > 0, (pivot_qty_item['Chênh lệch'] / pivot_qty_item['Số lượng chuyển']) * 100, 0)
        pivot_qty_item['Abs_ChenhLech'] = pivot_qty_item['Chênh lệch'].abs()
        pivot_qty_item = pivot_qty_item.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_item['SL ST chênh lệch'] = pivot_qty_item['SL ST chênh lệch'].astype(int)
        pivot_qty_item['SL ST nhập=0'] = pivot_qty_item['SL ST nhập=0'].astype(int)
        pivot_qty_item.insert(2, 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', pivot_qty_item['SL ST nhập=0'].astype(str) + " / " + pivot_qty_item['SL ST chênh lệch'].astype(str))
        pivot_qty_item = pivot_qty_item[['Ngày_str', 'Mã hàng (CLV4)', 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', f'SL đã xác nhận được trả {kho_name.lower()}', 'Số lượng hao hụt', 'Số lượng chưa xác định']]
    
        pivot_val_item = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng chưa xác định']].sum().reset_index()
        pivot_val_item.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'CLV4': 'Mã hàng (CLV4)'}, inplace=True)
    
        selected_date_item = st.selectbox("🔍 Lọc theo Ngày (Mã hàng):", dates)
        if selected_date_item != "Tất cả các ngày":
            filtered_qty_item = pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item]
            filtered_val_item = pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item]
        else:
            filtered_qty_item = pivot_qty_item
            filtered_val_item = pivot_val_item
    
        tong_qty_item = pd.DataFrame() if filtered_qty_item.empty else filtered_qty_item.sum(numeric_only=True).to_frame().T
        if not tong_qty_item.empty: tong_qty_item['Ngày_str'] = 'Tổng'
        filtered_qty_item_renamed = create_multiindex_headers(filtered_qty_item, tong_qty_item)
    
        tong_val_item = pd.DataFrame() if filtered_val_item.empty else filtered_val_item.sum(numeric_only=True).to_frame().T
        if not tong_val_item.empty: tong_val_item['Ngày_str'] = 'Tổng'
        filtered_val_item_renamed = create_multiindex_headers(filtered_val_item, tong_val_item)
    
        tab3, tab4 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (Mã Hàng)", "💰 Chi Tiết GIÁ TRỊ (Mã Hàng)"])
        with tab3:
            display_df_with_download(filtered_qty_item_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_item_renamed.columns if 'Chênh lệch' in c[1]]), "Chi_Tiet_SL_CLV4", height=600)
        with tab4:
            display_df_with_download(filtered_val_item_renamed.style.format(format_vn), "Chi_Tiet_GT_CLV4", height=600)
    
        # 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)
        st.write("---")
        st.subheader("🏷️ 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)")
        sku_qty_sum = df_active.groupby(['Ngày_str', 'SKU_Full'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
        sku_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST chênh lệch')
        sku_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST nhập=0')
    
        pivot_qty_sku = sku_qty_sum.join(sku_qty_count).join(sku_qty_nhap0).fillna(0).reset_index()
        pivot_qty_sku.rename(columns={
            'SKU_Full': 'Mã hàng (SKU)',
            'BS_ST': 'SL đã tạo bs cho ST',
            'Kho_Rau': f'SL đã xác nhận được trả {kho_name.lower()}',
            'Hao hụt': 'Số lượng hao hụt',
            'CXD': 'Số lượng chưa xác định'
        }, inplace=True)
        pivot_qty_sku['Tỷ lệ (%)'] = np.where(pivot_qty_sku['Số lượng chuyển'] > 0, (pivot_qty_sku['Chênh lệch'] / pivot_qty_sku['Số lượng chuyển']) * 100, 0)
        pivot_qty_sku['Abs_ChenhLech'] = pivot_qty_sku['Chênh lệch'].abs()
        pivot_qty_sku = pivot_qty_sku.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
    
        pivot_qty_sku['SL ST chênh lệch'] = pivot_qty_sku['SL ST chênh lệch'].astype(int)
        pivot_qty_sku['SL ST nhập=0'] = pivot_qty_sku['SL ST nhập=0'].astype(int)
    with tab_daily:
        st.subheader(f"{icon} Đối Soát Chéo Dư - Thiếu {kho_name}")
        st.markdown("Hệ thống tự động kết nối StarRocks qua VPN để đối soát chéo lượng hàng thừa/thiếu hàng ngày.")
    
        import datetime
        # Date selection
        selected_date = st.date_input("Chọn ngày đối soát (Daily):", datetime.date(2026, 7, 22), key="meat_fish_date_picker")
        date_str = selected_date.strftime('%Y-%m-%d')
    
        if True: # Tự động chạy khi thay đổi ngày
            with st.spinner("Đang tải dữ liệu và tính toán đối soát chéo..."):
                try:
                    # 1. Fetch branch mapping
                    sql_branches = """
                    SELECT branch_id, branch_code, branch_name
                    FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
                    WHERE branch_name IS NOT NULL AND branch_name != ''
                    GROUP BY branch_id, branch_code, branch_name
                    """
                    df_branches = fetch_data_to_df(sql_branches)
                    id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
    
                    # 2. Fetch shortages (MF01)
                    sql_mf01 = f"""
                    SELECT 
                        i.from_branch_id,
                        i.to_branch_id,
                        i.code as `Mã chuyển hàng`,
                        IFNULL(c.code, i.double_check_code) as `Mã thùng`,
                        l.barcode as `Mã hàng`,
                        l.name as `Tên hàng`,
                        l.unit__name as `ĐVT`,
                        CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                        CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
                    FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                    INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                    LEFT JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines c ON i._id = c._parent_id
                    WHERE {shortage_condition}
                      AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                      AND i.status = 5
                      AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                    """
                    df_mf01 = fetch_data_to_df(sql_mf01)
                    
                    if not df_mf01.empty:
                        df_mf01['Kho xuất'] = df_mf01['from_branch_id'].map(id_to_name)
                        df_mf01['Phân loại'] = df_mf01['Kho xuất'].apply(lambda x: 'Đông' if 'Frozen' in str(x) else 'Mát')
                        
                        # Fix missing Tên hàng
                        mapping_ten_hang = dict(zip(df_all['Mã hàng'], df_all.get('Tên Hàng', df_all.get('Tên hàng', pd.Series())).fillna('')))
                        df_mf01['Tên hàng'] = df_mf01['Tên hàng'].replace('', None).fillna(df_mf01['Mã hàng'].map(mapping_ten_hang))
                    
                    if df_mf01.empty:
                        st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ kho {kho_code} ngày {selected_date.strftime('%d/%m/%Y')}.")
                    else:
                        df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
                        df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
                        
                        
                        df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
                        
                        # 3. Fetch surpluses (MF02)
                        sql_mf02 = f"""
                        SELECT 
                            i.from_branch_id,
                            i.to_branch_id,
                            i.code as `Mã chuyển hàng`,
                            i.double_check_code as `Mã thùng`,
                            i.note as `Ghi chú chuyển (phiếu)`,
                            i.created_by,
                            l.description,
                            l.reason,
                            l.barcode as `Mã hàng`,
                            l.name as `Tên hàng`,
                            l.unit__name as `ĐVT`,
                            CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`,
                            CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `SL_chuyen_du`
                        FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                        INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                        WHERE {surplus_condition}
                          AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                          AND i.status = 5
                          AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                        """
                        df_mf02 = fetch_data_to_df(sql_mf02)
                        
                        if not df_mf02.empty:
                            df_mf02['Kho xuất'] = df_mf02['from_branch_id'].map(id_to_name).replace('', 'Chill - Miền Đông - SCF - Lệch Chuyển Hàng')
                            df_mf02['Phân loại'] = df_mf02['Kho xuất'].apply(lambda x: 'Đông' if 'Frozen' in str(x) else 'Mát')
                            df_mf02['Tên hàng'] = df_mf02['Tên hàng'].replace('', None).fillna(df_mf02['Mã hàng'].map(mapping_ten_hang))
                        df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
                        
                        if khu_vuc == "Rau Củ Quả":
                            import re
                            def extract_date(text):
                                if pd.isna(text): return None
                                match = re.search(r'(?<!\d)(\d{1,2})[\./-](\d{1,2})(?!\d)', str(text))
                                if match:
                                    try:
                                        d, m = int(match.group(1)), int(match.group(2))
                                        return f"{selected_date.year}-{m:02d}-{d:02d}"
                                    except:
                                        pass
                                return None
                            
                            df_mf02['Note_Date'] = df_mf02['Ghi chú chuyển (phiếu)'].apply(extract_date)
                            df_mf02['Desc_Date'] = df_mf02['description'].apply(extract_date)
                            df_mf02['Final_Date'] = df_mf02['Note_Date'].fillna(df_mf02['Desc_Date'])
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            
                            mask_exclude = mask_non_sys & (df_mf02['Final_Date'].notna()) & (df_mf02['Final_Date'] != date_str)
                            df_mf02 = df_mf02[~mask_exclude].copy()
                            
                            mask_non_sys = df_mf02['created_by'] != '5f1152906c86b40006155d97'
                            df_mf02.loc[mask_non_sys, 'SL_du'] = df_mf02.loc[mask_non_sys, 'SL_chuyen_du']
                        
                        df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()
    
                        # 4. Clean surplus crate code
                        def extract_surplus_crate(row):
                            val = str(row.get('Ghi chú chuyển (phiếu)', '')).strip()
                            if not val or val == 'nan':
                                return str(row['Mã thùng']).strip()
                            prefix = str(row['Mã chuyển hàng']).strip()
                            if prefix and val.startswith(prefix):
                                res = val[len(prefix):].strip()
                                if res: return res
                            import re
                            m = re.search(r'của thùng\s+([A-Z0-9_-]+)', val, flags=re.IGNORECASE)
                            if m: return m.group(1).strip()
                            m = re.search(r'(TRB[A-Z0-9_-]+|PT[A-Z0-9_-]+)', val)
                            if m: return m.group(1).strip()
                            return str(row['Mã thùng']).strip()
                            
                        if not df_surplus.empty:
                            df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
                        else:
                            df_surplus['Mã thùng'] = ""
    
                        # 5. Load layout
                        # file_layout already set based on khu_vuc
                        layout_df = pd.read_excel(file_layout, sheet_name=0)
                        
                        # Normalize columns
                        if 'Chi nhánh nhận' in layout_df.columns and 'STT' in layout_df.columns:
                            layout_df.rename(columns={'STT': 'Vị trí', 'Chi nhánh nhận': 'Siêu thị'}, inplace=True)
                        elif 'Siêu thị' not in layout_df.columns:
                            layout_df = pd.read_excel(file_layout, sheet_name=0, header=None)
                            if len(layout_df.columns) >= 3:
                                layout_df.rename(columns={0: 'Vị trí', 1: 'Mã', 2: 'Siêu thị'}, inplace=True)
                        
                        store_to_pos = {}
                        if 'Siêu thị' in layout_df.columns and 'Vị trí' in layout_df.columns:
                            for _, row in layout_df.iterrows():
                                try:
                                    st_name = str(row['Siêu thị']).strip().upper()
                                    pos_val = int(row['Vị trí'])
                                    store_to_pos[st_name] = pos_val
                                except (ValueError, TypeError):
                                    pass
    
                        # Clean barcodes and exclude 'CC' prefixes
                        df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
                        df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
                        df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
                        df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()
    
                        # 6. Group shortage & surplus
                        diff_grouped = df_shortage.groupby(['Phân loại', 'Chi nhánh nhận', 'Mã hàng']).agg({
                            'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                            'Chênh lệch': 'sum',
                            'ĐVT': 'first',
                            'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                            'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                        }).reset_index()
                        diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu', 'Mã chuyển hàng': 'Mã chuyển hàng thiếu'}, inplace=True)
                        
                        
                        
                        if not df_surplus.empty:
                            du_grouped = df_surplus.groupby(['Phân loại', 'Chi nhánh nhận', 'Mã hàng']).agg({
                                'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                                'SL_du': 'sum',
                                'ĐVT': 'first',
                                'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                                'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                            }).reset_index()
                            du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
                        else:
                            du_grouped = pd.DataFrame(columns=['Phân loại', 'Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa'])
    
                        # Merge for internal matching
                        merged_internal = pd.merge(diff_grouped, du_grouped, on=['Phân loại', 'Chi nhánh nhận', 'Mã hàng'], how='outer')
                        merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
                        try:
                            ten_hang_col = [c for c in df_all.columns if 'Tên hàng' in c or 'Tên Hàng' in c][0]
                            sku_mapping = dict(zip(df_all['Mã hàng'].astype(str).str.strip(), df_all[ten_hang_col]))
                            merged_internal['Tên hàng'] = merged_internal['Mã hàng'].astype(str).str.strip().map(sku_mapping).fillna(merged_internal['Tên hàng'])
                            merged_internal['Tên hàng'] = merged_internal['Tên hàng'].replace({'nan': '', 'None': ''})
                        except:
                            pass
                        merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
                        merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
                        merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('kg')
                        merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
                        merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()
    
                        # Step 1: Khớp nội bộ 100%
                        df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
                        
                        loi_text = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                        df_exact['Lỗi'] = loi_text
                        df_exact = df_exact[['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
                        df_exact.columns = ['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Lỗi']
                        df_exact['SL Thiếu'] = df_exact['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_exact['SL Thừa'] = df_exact['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Step 2: Khớp nội bộ một phần
                        df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
                        df_partial['Dif'] = df_partial['Chênh lệch'] - df_partial['SL_du']
                        df_partial['Lỗi'] = loi_text
                        df_partial = df_partial[['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Chênh lệch', 'SL_du', 'Dif', 'Lỗi']]
                        df_partial.columns = ['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'SL Thiếu', 'SL Thừa', 'Chênh lệch thừa - thiếu', 'Lỗi']
                        df_partial['SL Thiếu'] = df_partial['SL Thiếu'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
                        df_partial['SL Thừa'] = df_partial['SL Thừa'].apply(lambda x: f"{x:g}" if pd.notna(x) else "")
    
                        # Remainder calculation
                        merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
                        merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']
                        
                        rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 3: Khớp chéo liên siêu thị
                        cross_matches = []
                        skus_shortage = rem_shortages['Mã hàng'].unique()
                        skus_surplus = rem_surpluses['Mã hàng'].unique()
                        common_skus = set(skus_shortage).intersection(skus_surplus)
                        
                        matched_sho_keys = set()
                        matched_sur_keys = set()
                        
                        for sku in common_skus:
                            sku_shortages = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
                            sku_surpluses = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
                            
                            for idx_sur, row_sur in sku_surpluses.iterrows():
                                sur_qty = row_sur['Remaining_Surplus']
                                sur_store = row_sur['Chi nhánh nhận']
                                sur_crate = row_sur['Mã thùng thừa']
                                sur_transfer = row_sur['Mã chuyển hàng thừa']
                                sku_name = row_sur['Tên hàng']
                                dvt = row_sur['ĐVT']
                                pos_sur = store_to_pos.get(str(sur_store).strip().upper() if pd.notna(sur_store) else sur_store, None)
                                
                                matching_shortages = []
                                for idx_sho, row_sho in sku_shortages.iterrows():
                                    sho_qty = row_sho['Remaining_Shortage']
                                    if abs(sur_qty - sho_qty) <= 0.01:
                                        matching_shortages.append(row_sho)
                                
                                if len(matching_shortages) > 0:
                                    best_match = None
                                    best_dist = 9999
                                    for sho_row in matching_shortages:
                                        sho_store = sho_row['Chi nhánh nhận']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        if pos_sur is not None and pos_sho is not None:
                                            dist = abs(pos_sur - pos_sho)
                                            if dist < best_dist:
                                                best_dist = dist
                                                best_match = sho_row
                                        else:
                                            if best_match is None:
                                                best_match = sho_row
                                    
                                    if best_match is not None:
                                        sho_store = best_match['Chi nhánh nhận']
                                        sho_qty = best_match['Remaining_Shortage']
                                        sho_crate = best_match['Mã thùng thiếu']
                                        pos_sho = store_to_pos.get(str(sho_store).strip().upper() if pd.notna(sho_store) else sho_store, None)
                                        
                                        prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                                        cross_matches.append({
                                            'Phân loại': row_sur.get('Phân loại', row_sho.get('Phân loại', 'Mát')), 'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                                            'Vị trí Dư': pos_sur if pos_sur is not None else '-', 'Mã Thùng Thừa': sur_crate,
                                            'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                                            'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                                            'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                                            'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                                            'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                                        })
                                        matched_sur_keys.add((sur_store, sku))
                                        matched_sho_keys.add((sho_store, sku))
                                        
                        df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
                            'Phân loại', 'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 
                            'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 
                            'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
                        ])
                        
                        # Exclude matched from remainder
                        for index, row in rem_shortages.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
                                rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
                        for index, row in rem_surpluses.iterrows():
                            if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
                                rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
                                
                        rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
                        rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()
    
                        # Step 4: Tổng Dư >= Tổng Thiếu
                        if not rem_shortages.empty or not rem_surpluses.empty:
                            sku_shortage_totals = rem_shortages.groupby(['Phân loại', 'Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Phân loại', 'Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
                            sku_surplus_totals = rem_surpluses.groupby(['Phân loại', 'Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Phân loại', 'Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
                            sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Phân loại', 'Mã hàng', 'Tên hàng'], how='outer')
                            sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
                            sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
                            sku_totals['Dif'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
                            
                            df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
                            
                            sur_details, sho_details = [], []
                            for idx, row in df_total_gte.iterrows():
                                sku = row['Mã hàng']
                                sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
                                sur_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Surplus']:.3f} kg)" for _, r in sku_sur.iterrows()]))
                                sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
                                sho_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).strip().upper() if pd.notna(r['Chi nhánh nhận']) else r['Chi nhánh nhận'], '-')}) ({r['Remaining_Shortage']:.3f} kg)" for _, r in sku_sho.iterrows()]) if len(sku_sho) > 0 else "Không có")
                            
                            if not df_total_gte.empty:
                                df_total_gte['Chi tiết ST nhận Dư'] = sur_details
                                df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
                                df_total_gte = df_total_gte[['Phân loại', 'Mã hàng', 'Tên hàng', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Dif']]
                                df_total_gte.columns = ['Phân loại', 'Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)']
                            else:
                                df_total_gte = pd.DataFrame(columns=['Phân loại', 'Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
                        else:
                            df_total_gte = pd.DataFrame(columns=['Phân loại', 'Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
    
                        # Step 5: Chỉ có thiếu ròng
                        if not rem_shortages.empty:
                            df_only_diff = rem_shortages[['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
                            df_only_diff.columns = ['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
                        else:
                            df_only_diff = pd.DataFrame(columns=['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thiếu', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
                        
                        # Step 6: Chỉ có thừa ròng
                        if not rem_surpluses.empty:
                            df_only_du = rem_surpluses[['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Remaining_Surplus']].copy()
                            df_only_du.columns = ['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)']
                        else:
                            df_only_du = pd.DataFrame(columns=['Phân loại', 'Chi nhánh nhận', 'Mã chuyển hàng thừa', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'SL Thừa (kg)'])
    
                        # Display KPIs
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ff4b4b; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ 100%</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ff4b4b;">{len(df_exact)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #ffaa00; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ MỘT PHẦN</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #ffaa00;">{len(df_partial)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #00c0f2; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">KHỚP CHÉO LIÊN ST 1-1</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #00c0f2;">{len(df_cross)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c4:
                            st.markdown(f"""
                                <div class="metric-card" style="border-left-color: #2ebd59; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                    <div style="font-size: 12px; color: #a3a8b4;">THIẾU RÒNG / THỪA RÒNG</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #2ebd59;">{len(df_only_diff)} / {len(df_only_du)} dòng</div>
                                </div>
                            """, unsafe_allow_html=True)
    
                        st.write("---")
                        # Export Excel to Memory for Download Button
                        output_excel = io.BytesIO()
                        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                            df_shortage.to_excel(writer, sheet_name='0. Dữ liệu Thiếu Raw', index=False)
                            df_surplus.to_excel(writer, sheet_name='0. Dữ liệu Thừa Raw', index=False)
                            df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
                            df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
                            df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
                            df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
                            df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
                            df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
                        
                        st.download_button(
                            label="📥 Tải Xuống Báo Cáo Đối Soát Chéo Excel",
                            data=output_excel.getvalue(),
                            file_name=f"Doi_Soat_Cheo_Thit_Ca_{date_str}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
    
                        # Tab presentation
                        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
                            "1. Khớp nội bộ 100%", 
                            "2. Khớp nội bộ một phần", 
                            "3. Khớp chéo liên ST 1-1", 
                            "4. Tổng Dư >= Tổng Thiếu", 
                            "5. Chỉ ghi nhận Thiếu ròng", 
                            "6. Chỉ ghi nhận Thừa ròng"
                        ])
                        
                        with sub_tab1:
                            loi_text_display = 'ST nhập thiếu' if khu_vuc == "Rau Củ Quả" else 'DC thao tác sai'
                            st.subheader(f"1. Danh sách Khớp nội bộ 100% ({loi_text_display})")
                            st.dataframe(df_exact, use_container_width=True)
                        with sub_tab2:
                            st.subheader("2. Danh sách Khớp nội bộ một phần")
                            st.dataframe(df_partial, use_container_width=True)
                        with sub_tab3:
                            st.subheader("3. Danh sách Khớp chéo liên ST 1-1 (DC giao nhầm CH)")
                            st.dataframe(df_cross, use_container_width=True)
                        with sub_tab4:
                            st.subheader("4. Danh sách Tổng Dư >= Tổng Thiếu")
                            st.dataframe(df_total_gte, use_container_width=True)
                        with sub_tab5:
                            st.subheader("5. Danh sách Chỉ ghi nhận Thiếu ròng (Siêu thị nhận thiếu)")
                            st.dataframe(df_only_diff, use_container_width=True)
                        with sub_tab6:
                            st.subheader("6. Danh sách Chỉ ghi nhận Thừa ròng (Siêu thị nhận thừa)")
                            st.dataframe(df_only_du, use_container_width=True)
    
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi chạy đối soát: {e}")
                    st.exception(e)
    
    
    with tab_dc:
        st.header("👨‍🔧 Theo Dõi Tiến Độ Xử Lý & Phản Hồi Của DC")
        render_dc_feedback_progress_report(df_active, "Tab_3")
    



if khu_vuc_selected == "Thịt Cá":
    render_thit_ca()
elif khu_vuc_selected == "Rau Củ Quả":
    render_rau_cu()
else:
    render_dong_mat()
