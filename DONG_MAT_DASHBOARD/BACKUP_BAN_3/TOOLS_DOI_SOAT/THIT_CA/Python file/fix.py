import codecs
import re

content = codecs.open('app_thit_ca.py', 'r', 'utf-8').read()

def replacer(match):
    return '''                    def extract_crate(row):
                        val = str(row.get('Ghi chú chuyển (phiếu)', '')).strip()
                        if not val or val == 'nan':
                            return str(row['Mã thùng']).strip()
                        prefix = str(row['Mã chuyển hàng']).strip()
                        if prefix and val.startswith(prefix):
                            res = val[len(prefix):].strip()
                            if res: return res
                        import re
                        m = re.search(r'của thùng\\s+([A-Z0-9_-]+)', val, flags=re.IGNORECASE)
                        if m: return m.group(1).strip()
                        m = re.search(r'(TRB[A-Z0-9_-]+|PT[A-Z0-9_-]+)', val)
                        if m: return m.group(1).strip()
                        return str(row['Mã thùng']).strip()'''

content = re.sub(
    r'def extract_crate\(row\):.*?return str\(row\[\'Mã thùng\'\]\)\.strip\(\)',
    replacer,
    content,
    flags=re.DOTALL
)

def replacer_surplus(match):
    return replacer(match).replace('def extract_crate', 'def extract_surplus_crate')

content = re.sub(
    r'def extract_surplus_crate\(row\):.*?return str\(row\[\'Mã thùng\'\]\)\.strip\(\)',
    replacer_surplus,
    content,
    flags=re.DOTALL
)

codecs.open('app_thit_ca.py', 'w', 'utf-8').write(content)
print('Done!')
