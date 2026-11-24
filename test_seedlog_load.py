import pandas as pd

SEEDLOG_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&id=1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ&gid=0"
TARGET_DATES = ["2026-11-03", "2026-11-05", "2026-11-07"]

def main():
    df = pd.read_csv(SEEDLOG_URL, dtype=str)
    # Identify date column (contains 'ngày')
    date_col = next((c for c in df.columns if isinstance(c, str) and 'ngày' in c.lower()), None)
    diff_col = next((c for c in df.columns if str(c).strip().lower() in ['difference', 'chênh lệch', 'diff']), None)
    if date_col is None or diff_col is None:
        print('Columns not found')
        return
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce')
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df[df[diff_col] < 0]
    df['date_str'] = df[date_col].dt.strftime('%Y-%m-%d')
    df = df[df['date_str'].isin(TARGET_DATES)]
    print('Rows for target dates:', len(df))
    print(df[['date_str', diff_col]].head())

if __name__ == '__main__':
    main()
