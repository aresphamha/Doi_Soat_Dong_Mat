with open('DONG_MAT_DASHBOARD/BACKUP_BAN_1/generate_web_report.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def\s+compute|def\s+generate|BUNDLES', text)]
print(f"Total matches in BACKUP_BAN_1: {len(matches)}")
for m in matches[:15]:
    snippet = text[max(0, m-20):min(len(text), m+80)].replace('\n', ' ')
    print(f"Match at {m}: {snippet}")
