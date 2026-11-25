import streamlit as st
import os
import glob

st.set_page_config(page_title="Hệ Thống Tài Liệu & Logic", page_icon="📚", layout="wide")

st.sidebar.title("📚 Danh Mục Tài Liệu")
st.sidebar.write("Chọn tài liệu bạn muốn đọc:")

# Tìm kiếm đệ quy tất cả các file markdown trong thư mục AI và thư mục Đối soát
base_dir = r"C:\Users\PC\Desktop\AI"
md_files = []

for root, dirs, files in os.walk(base_dir):
    # Bỏ qua các thư mục không cần thiết
    if '__pycache__' in root or '.git' in root or '.gemini' in root:
        continue
    for file in files:
        if file.endswith(".md") or ("logic" in file.lower() and file.endswith(".txt")):
            md_files.append(os.path.join(root, file))

if not md_files:
    st.sidebar.info("Chưa có tài liệu nào trong hệ thống.")
    st.title("Hệ Thống Tài Liệu & Logic AI")
    st.write("Chào mừng bạn đến với Cổng tài liệu nội bộ. Các tài liệu logic do AI xuất ra sẽ tự động xuất hiện ở đây.")
else:
    # Create a nice mapping of filenames to display names
    doc_options = {}
    for f in md_files:
        filename = os.path.basename(f)
        display_name = filename.replace(".md", "").replace("_", " ").title()
        doc_options[display_name] = f
        
    selected_doc_name = st.sidebar.radio("Danh sách:", list(doc_options.keys()))
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Mẹo:** Mỗi khi AI xuất thêm tài liệu mới, bạn chỉ cần F5 lại trang web này là tài liệu sẽ xuất hiện trong danh sách.")
    
    # Read and display the selected document
    selected_file_path = doc_options[selected_doc_name]
    with open(selected_file_path, "r", encoding="utf-8") as file:
        content = file.read()
        
    st.markdown(content)
