import codecs
import re

content = codecs.open('app_thit_ca.py', 'r', 'utf-8').read()

def replacer_shortage(match):
    return '''                        df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
                        df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
                        
                        def get_ma_thung_from_sheets(row_mf01):
                            store = str(row_mf01['Chi nhánh nhận']).strip()
                            sku = str(row_mf01['Mã hàng']).strip()
                            # Match using substring for store name because Google Sheets has a prefix
                            mask = (df['Chi nhánh nhận'].str.contains(store, na=False, regex=False)) & (df['Mã hàng'].astype(str).str.strip() == sku)
                            match = df[mask]
                            if not match.empty:
                                return str(match.iloc[0]['Mã thùng']).strip()
                            return str(row_mf01['Mã thùng']).strip()
                            
                        df_mf01['Mã thùng'] = df_mf01.apply(get_ma_thung_from_sheets, axis=1)
                        df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()'''

content = re.sub(
    r'                        df_mf01\[\'Chi nhánh nhận\'\] = df_mf01\[\'to_branch_id\'\]\.map\(id_to_name\).*?df_shortage = df_mf01\[df_mf01\[\'Chênh lệch\'\]\.round\(5\) > 0\.0\]\.copy\(\)',
    replacer_shortage,
    content,
    flags=re.DOTALL
)

codecs.open('app_thit_ca.py', 'w', 'utf-8').write(content)
print('Done!')
