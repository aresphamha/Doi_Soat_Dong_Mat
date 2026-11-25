import os, glob, pandas as pd, requests, io

# Configuration
DOWNLOADS_DIR = r"C:/Users/Thu Ha/Downloads"
SEEDLOG_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&gid=0"

def list_all_transfer_files():
    pattern = os.path.join(DOWNLOADS_DIR, "transfer_*.xlsx")
    return sorted(glob.glob(pattern))

def load_cdc_data(files):
    dfs = []
    for f in files:
        xl = pd.ExcelFile(f)
        sheet = 'transfer' if 'transfer' in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet)
        dfs.append(df)
    if not dfs:
        raise FileNotFoundError('No CDC transfer files found')
    return pd.concat(dfs, ignore_index=True)

def compute_cdc_totals(df):
    # Identify columns
    date_col = df.columns[0]
    transfer_col = df.columns[10] if len(df.columns) > 10 else None
    receive_col = df.columns[11] if len(df.columns) > 11 else None
    df[date_col] = df[date_col].astype(str).str.strip()
    df[transfer_col] = pd.to_numeric(df[transfer_col], errors='coerce').fillna(0)
    df[receive_col] = pd.to_numeric(df[receive_col], errors='coerce').fillna(0)
    df['capped_receive'] = df[[transfer_col, receive_col]].min(axis=1)
    grouped = df.groupby(date_col).agg(
        total_transfer=pd.NamedAgg(column=transfer_col, aggfunc='sum'),
        total_capped_receive=pd.NamedAgg(column='capped_receive', aggfunc='sum')
    ).reset_index()
    grouped['diff'] = grouped['total_capped_receive'] - grouped['total_transfer']
    grouped = grouped.rename(columns={date_col: 'date'})
    return grouped

def load_seedlog():
    txt = requests.get(SEEDLOG_URL).text
    df = pd.read_csv(io.StringIO(txt))
    # Identify year, month, day columns
    year_col = next((c for c in df.columns if 'column 1' in str(c).lower() or 'year' in str(c).lower()), df.columns[0])
    month_col = next((c for c in df.columns if 'tháng' in str(c).lower() or 'month' in str(c).lower()), df.columns[1] if len(df.columns)>1 else None)
    day_col = next((c for c in df.columns if 'ngày' in str(c).lower() or 'day' in str(c).lower()), df.columns[2] if len(df.columns)>2 else None)
    # Diff column
    diff_col = next((c for c in df.columns if isinstance(c,str) and ('chênh lệch' in c.lower() or 'difference' in c.lower())), df.columns[11] if len(df.columns)>11 else None)
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce').fillna(0)
    # Build date string
    def build_date(row):
        y = str(row[year_col]).strip()
        m = str(row[month_col]).strip() if month_col is not None else ''
        d = str(row[day_col]).strip() if day_col is not None else ''
        if m.isdigit(): m = m.zfill(2)
        if d.isdigit(): d = d.zfill(2)
        return f"{d}/{m}/{y}" if d and m else y
    df['date'] = df.apply(build_date, axis=1)
    grouped = df.groupby('date').agg(seedlog_diff=pd.NamedAgg(column=diff_col, aggfunc='sum')).reset_index()
    return grouped

def filter_from_nov2026(df):
    def to_dt(s):
        try:
            return pd.to_datetime(s, dayfirst=True)
        except Exception:
            return pd.NaT
    df['dt'] = df['date'].apply(to_dt)
    df = df[df['dt'] >= pd.Timestamp('2026-11-01')]
    return df.drop(columns=['dt'])

def main():
    try:
        files = list_all_transfer_files()
        print('CDC files found:', files)
        cdc_df = load_cdc_data(files)
        cdc_totals = compute_cdc_totals(cdc_df)
        seedlog_totals = load_seedlog()
        cdc_totals = filter_from_nov2026(cdc_totals)
        seedlog_totals = filter_from_nov2026(seedlog_totals)
        merged = pd.merge(cdc_totals, seedlog_totals, on='date', how='outer', suffixes=(' _cdc',' _seed'))
        merged = merged.fillna(0)
        merged['match'] = (merged['diff'].round(6) == merged['seedlog_diff'].round(6))
        report_path = r"g:/My Drive/Đối soát SCM/reconciliation_full.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('# CDC vs Seedlog Full Reconciliation\n\n')
            f.write('| Ngày | SL Chuyển (CDC) | SL Nhận (capped) | SL chênh lệch (CDC) | SL chênh lệch (Seedlog) | Match |\n')
            f.write('|------|-----------------|-------------------|----------------------|--------------------------|-------|\n')
            for _, r in merged.iterrows():
                f.write(f"| {r['date']} | {int(r['total_transfer'])} | {int(r['total_capped_receive'])} | {int(r['diff'])} | {int(r['seedlog_diff'])} | {'✅' if r['match'] else '❌'} |\n")
        print('Report written to', report_path)
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    main()
