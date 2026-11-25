import pandas as pd, glob, os

SEEDLOG_CSV_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&id=1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ&gid=0"
TARGET_DATES = ["2026-11-03", "2026-11-05", "2026-11-07"]

def load_seedlog():
    df = pd.read_csv(SEEDLOG_CSV_URL, dtype=str)
    # Find date column
    date_col = None
    for c in df.columns:
        if isinstance(c, str) and "ngày" in c.lower():
            date_col = c
            break
    if not date_col:
        raise ValueError('Date column not found')
    # Find diff column
    diff_col = None
    for c in df.columns:
        name = str(c).strip().lower()
        if name in ['difference', 'chênh lệch', 'difference (seedlog)', 'diff']:
            diff_col = c
            break
    if not diff_col:
        diff_col = df.columns[10]
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce')
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df[df[diff_col] < 0]
    df = df[[date_col, diff_col]].copy()
    df.rename(columns={date_col: 'date', diff_col: 'seedlog_diff'}, inplace=True)
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    df = df[df['date_str'].isin(TARGET_DATES)]
    return df[['date','seedlog_diff']]

def process_cdc_file(filepath):
    xl = pd.ExcelFile(filepath)
    sheet = 'transfer' if 'transfer' in xl.sheet_names else xl.sheet_names[0]
    df = xl.parse(sheet)
    # Identify date column (first column)
    date_col = df.columns[0]
    df['date'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    # Identify SL chuyển and SL nhận columns
    col_k = None
    col_l = None
    for c in df.columns:
        if isinstance(c, str) and ('chuyển' in c.lower() or c.lower() in ['sl chuyển','sl chuyen']):
            col_k = c
        if isinstance(c, str) and ('nhận' in c.lower() or c.lower() in ['sl nhận','sl nhan']):
            col_l = c
    if col_k is None:
        col_k = df.columns[10]
    if col_l is None:
        col_l = df.columns[11]
    df[col_k] = pd.to_numeric(df[col_k], errors='coerce').fillna(0)
    df[col_l] = pd.to_numeric(df[col_l], errors='coerce').fillna(0)
    df['capped_receive'] = df.apply(lambda r: min(r[col_l], r[col_k]), axis=1)
    df['cdc_diff'] = df['capped_receive'] - df[col_k]
    df = df[df['cdc_diff'] < 0]
    df = df[['date','cdc_diff']]
    df = df.dropna(subset=['date'])
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    df = df[df['date_str'].isin(TARGET_DATES)]
    return df[['date','cdc_diff']]

def aggregate_cdc(files):
    parts = []
    for f in files:
        try:
            parts.append(process_cdc_file(f))
        except Exception as e:
            print(f"Error {f}: {e}")
    if not parts:
        return pd.DataFrame(columns=['date','cdc_diff'])
    all_df = pd.concat(parts)
    return all_df.groupby('date')['cdc_diff'].sum().reset_index()

def main():
    seed = load_seedlog()
    download_dir = os.path.expanduser('~/Downloads')
    files = glob.glob(os.path.join(download_dir, 'transfer_*.xlsx'))
    cdc = aggregate_cdc(files)
    merged = pd.merge(seed, cdc, on='date', how='outer')
    merged['seedlog_diff'] = merged['seedlog_diff'].fillna(0)
    merged['cdc_diff'] = merged['cdc_diff'].fillna(0)
    merged['match'] = merged['seedlog_diff'] == merged['cdc_diff']
    lines = ["# Reconciliation for 03,05,07 Nov 2026", "", "| Date | CDC diff | Seedlog diff | Match |", "|---|---|---|---|"]
    for _, r in merged.sort_values('date').iterrows():
        d = r['date'].strftime('%Y-%m-%d') if pd.notnull(r['date']) else 'N/A'
        lines.append(f"| {d} | {int(r['cdc_diff'])} | {int(r['seedlog_diff'])} | {'✅' if r['match'] else '❌'} |")
    out_path = os.path.abspath('reconciliation_three_dates.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('Report written to', out_path)

if __name__ == '__main__':
    main()
