import re

file_path = "C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ\\app_thit_ca.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = 'tab_main, tab_daily, tab_dc = st.tabs(["📊 Báo Cáo Tổng Quan", "📈 Báo Cáo Năng Suất Daily", "👨‍🔧 Tiến Độ DC Phản Hồi"])'

insertion = """
st.sidebar.title("Cài đặt chung")
khu_vuc = st.sidebar.radio("Khu vực đối soát:", ["Thịt Cá", "Rau Củ Quả"])

if khu_vuc == "Thịt Cá":
    data_url = "https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1116669931"
    file_layout = "LayoutImportThitCa.xlsx"
else:
    data_url = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv&gid=1422896115"
    file_layout = "Layout Rau.xlsx"

try:
    df_all = load_data(data_url)
    st.sidebar.success(f"Tải dữ liệu từ Google Sheets thành công!")
except Exception as e:
    st.error(f"Lỗi tải dữ liệu Google Sheets: {e}")
    st.stop()

"""

if target in content:
    content = content.replace(target, insertion + target)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed successfully!")
else:
    print("Could not find the target line.")
