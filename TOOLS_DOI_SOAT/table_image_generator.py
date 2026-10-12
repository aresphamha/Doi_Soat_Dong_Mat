import os
import sys
from PIL import Image, ImageDraw, ImageFont

def render_pastel_gradient_table(headers, rows, output_path, col_widths=None):
    """
    Render bảng dữ liệu ra file ảnh với:
    - Header: Gradient Xanh lá pastel (#B7E4C7) sang Cam đào pastel (#FED7AA)
    - Data: Nền trắng (#FFFFFF), viền lưới (#E2E8F0)
    - Tự động căn chỉnh và hỗ trợ DPI sắc nét
    """
    # 1. Khởi tạo Font
    font_size_header = 14
    font_size_data = 13
    font_title_size = 16

    font_path_bold = "C:\\Windows\\Fonts\\segoeuib.ttf"
    font_path_regular = "C:\\Windows\\Fonts\\segoeui.ttf"
    if not os.path.exists(font_path_bold):
        font_path_bold = "C:\\Windows\\Fonts\\arialbd.ttf"
        font_path_regular = "C:\\Windows\\Fonts\\arial.ttf"

    try:
        font_header = ImageFont.truetype(font_path_bold, font_size_header)
        font_data = ImageFont.truetype(font_path_regular, font_size_data)
        font_data_bold = ImageFont.truetype(font_path_bold, font_size_data)
    except Exception:
        font_header = ImageFont.load_default()
        font_data = ImageFont.load_default()
        font_data_bold = ImageFont.load_default()

    # 2. Tính toán độ rộng từng cột
    padding_x = 16
    padding_y = 10
    row_height = 36
    header_height = 42

    num_cols = len(headers)
    if not col_widths:
        col_widths = []
        for c in range(num_cols):
            # Lấy text dài nhất
            texts = [str(headers[c])] + [str(r[c]) for r in rows if c < len(r)]
            max_w = 0
            for t in texts:
                try:
                    w = font_header.getlength(t)
                except AttributeError:
                    w = len(t) * 9
                if w > max_w:
                    max_w = w
            col_widths.append(int(max_w + padding_x * 2))

    total_width = sum(col_widths)
    total_height = header_height + (len(rows) * row_height)

    # Thêm margin viền ngoài
    margin = 12
    img_w = total_width + margin * 2
    img_h = total_height + margin * 2

    img = Image.new("RGB", (img_w, img_h), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 3. Vẽ Header với Gradient từ Xanh lá pastel (#B7E4C7) sang Cam đào pastel (#FED7AA)
    # RGB(#B7E4C7) = (183, 228, 199)
    # RGB(#FED7AA) = (254, 215, 170)
    start_r, start_g, start_b = 183, 228, 199
    end_r, end_g, end_b = 254, 215, 170

    header_x0 = margin
    header_y0 = margin
    header_x1 = margin + total_width
    header_y1 = margin + header_height

    # Vẽ từng dải màu gradient theo chiều ngang
    for x in range(header_x0, header_x1):
        ratio = (x - header_x0) / max(total_width - 1, 1)
        r = int(start_r + (end_r - start_r) * ratio)
        g = int(start_g + (end_g - start_g) * ratio)
        b = int(start_b + (end_b - start_b) * ratio)
        draw.line([(x, header_y0), (x, header_y1)], fill=(r, g, b))

    # Vẽ chữ Header
    cur_x = margin
    header_text_color = "#0F172A"
    for c, h_text in enumerate(headers):
        w = col_widths[c]
        try:
            tw = font_header.getlength(h_text)
        except AttributeError:
            tw = len(h_text) * 8
        tx = cur_x + (w - tw) / 2
        ty = header_y0 + (header_height - font_size_header) / 2 - 2
        draw.text((tx, ty), h_text, fill=header_text_color, font=font_header)
        cur_x += w

    # 4. Vẽ các dòng dữ liệu
    border_color = "#E2E8F0"
    for r_idx, row in enumerate(rows):
        row_y0 = header_y1 + r_idx * row_height
        row_y1 = row_y0 + row_height
        row_bg = "#FFFFFF" if r_idx % 2 == 0 else "#F8FAFC"
        draw.rectangle([(margin, row_y0), (margin + total_width, row_y1)], fill=row_bg)

        cur_x = margin
        for c, cell_val in enumerate(row):
            w = col_widths[c]
            val_str = str(cell_val)
            # Cột 0 (mã), cột 1 (ngày), cột trạng thái (cuối) -> căn giữa hoặc in đậm
            is_center = c in [0, 1, num_cols - 1, num_cols - 2] if num_cols > 3 else False
            is_bold = (c == 0) or ("Đang chuyển" in val_str) or ("Cần hậu kiểm" in val_str)
            f = font_data_bold if is_bold else font_data

            try:
                tw = f.getlength(val_str)
            except AttributeError:
                tw = len(val_str) * 8

            if is_center:
                tx = cur_x + (w - tw) / 2
            else:
                tx = cur_x + 14  # padding left
            ty = row_y0 + (row_height - font_size_data) / 2 - 2

            # Màu chữ
            if "Cần hậu kiểm" in val_str:
                text_col = "#DC2626"  # Đỏ cảnh báo
            elif "Đang chuyển" in val_str:
                text_col = "#D97706"  # Cam cảnh báo
            else:
                text_col = "#1E293B"

            draw.text((tx, ty), val_str, fill=text_col, font=f)
            cur_x += w

    # 5. Vẽ viền lưới toàn bộ bảng
    # Viền ngoài
    draw.rectangle([(margin, margin), (margin + total_width, margin + total_height)], outline="#CBD5E1", width=1)
    # Đường kẻ ngang
    for r_idx in range(len(rows) + 1):
        y = margin + header_height + r_idx * row_height
        draw.line([(margin, y), (margin + total_width, y)], fill=border_color, width=1)
    # Đường kẻ dọc
    cur_x = margin
    for w in col_widths:
        cur_x += w
        draw.line([(cur_x, margin), (cur_x, margin + total_height)], fill=border_color, width=1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, quality=95)
    return output_path

if __name__ == '__main__':
    headers_demo = ["Mã phiếu chuyển", "Ngày chuyển", "Nơi chuyển", "Nơi nhận", "Trạng thái"]
    rows_demo = [
        ["PT1942307", "07/10/2026", "FGA10101 _ Bình Thắng _ Lưu Hàng", "KFM_BDU_TAN - 275 D33 KDC Viet Sing", "Đang chuyển"]
    ]
    render_pastel_gradient_table(headers_demo, rows_demo, "scratch/demo_table_chi_tiet.png")
    print("Demo rendered!")
