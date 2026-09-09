import pymysql
import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

host = "103.147.122.103"
port = 9030
user = "kfm_scm_tho_nguyen"
password = "oh1dtJwR4ihLGrX4E7bs"
database = "kfm_scm"

print(f"Connecting to StarRocks {host}:{port}/{database}...")
try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        connect_timeout=10
    )
    print("✅ Kết nối StarRocks thành công!\n")

    cursor = conn.cursor()
    
    # 1. SHOW DATABASES
    cursor.execute("SHOW DATABASES;")
    databases = [row[0] for row in cursor.fetchall()]
    print("📁 Danh sách các Database có quyền truy cập:")
    for db in databases:
        print(f" - {db}")
    print()

    # 2. SHOW TABLES in kfm_scm
    cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📊 Danh sách tất cả các bảng trong DB '{database}' (Tổng {len(tables)} bảng):")
    for t in tables:
        print(f" - {t}")
    print()

    # 3. Tìm các bảng liên quan đến CDC hoặc Đối Soát
    cdc_tables = [t for t in tables if any(k in t.lower() for k in ['cdc', 'doi_soat', 'doisoat', 'scm', 'chuyen', 'nhan', 'meat', 'fish', 'dong', 'mat'])]
    print(f"🔍 Các bảng liên quan đến CDC / Đối Soát ({len(cdc_tables)} bảng):")
    for t in cdc_tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{t}`;")
        cnt = cursor.fetchone()[0]
        print(f"\n==========================================")
        print(f"📌 BẢNG: {t} (Số dòng: {cnt:,})")
        print(f"==========================================")
        
        # Cấu trúc bảng
        cursor.execute(f"DESCRIBE `{t}`;")
        desc = cursor.fetchall()
        print("  Cấu trúc cột:")
        for col in desc:
            print(f"    - {col[0]} ({col[1]})")
            
        # Xem 3 dòng mẫu
        if cnt > 0:
            df_sample = pd.read_sql(f"SELECT * FROM `{t}` LIMIT 3;", conn)
            print("\n  Dữ liệu mẫu (3 dòng đầu):")
            print(df_sample.to_string(index=False))

    conn.close()

except Exception as e:
    print(f"❌ Lỗi kết nối hoặc truy vấn StarRocks: {e}")
