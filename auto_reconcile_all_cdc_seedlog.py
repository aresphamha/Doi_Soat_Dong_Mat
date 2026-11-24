import pandas as pd, glob, os, datetime

SEEDLOG_CSV_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&id=1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ&gid=0"

def load_seedlog():
    # Load Seedlog raw data CSV from public URL
    df = pd.read_csv(SEEDLOG_CSV_URL)
    # Identify date column (contains 'ngày')
    date_col = None
    for col in df.columns:
        if isinstance(col, str) and 'ngày' in col.lower():
            date_col = col
            break
    if date_col is None:
        raise ValueError('Date column not found in Seedlog CSV')
    # Identify difference column (negative values represent shortage)
    diff_col = None
    for col in df.columns:
        name = str(col).strip().lower()
        if name in ['difference', 'chênh lệch', 'difference (seedlog)', 'diff']:
            diff_col = col
            break
    if diff_col is None:
        # fallback to column 11 (index based)
        diff_col = df.columns[10]
    # Parse dates (dayfirst=True because format is DD/MM/YYYY)
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col])
    # Keep only rows where difference is negative (shortage)
    df = df[df[diff_col] < 0]
    df = df[[date_col, diff_col]].copy()
    df.rename(columns={date_col: 'date', diff_col: 'seedlog_diff'}, inplace=True)
    return df

def process_cdc_file(filepath):
    # Load CDC transfer Excel file (expects sheet named 'transfer' or first sheet)
    xl = pd.ExcelFile(filepath)
    sheet_name = 'transfer' if 'transfer' in xl.sheet_names else xl.sheet_names[0]
    df = xl.parse(sheet_name)
    # Expected columns: Date in column A, SL chuyển in K (index 10), SL nhận in L (index 11)
    # Find date column (first column with datetime values)
    date_col = df.columns[0]
    df['date'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    # Identify SL chuyển and SL nhận columns by header name or position
    col_k = None
    col_l = None
    for col in df.columns:
        if isinstance(col, str) and ('chuyển' in col.lower() or col.lower() == 'sl chuyển' or col.lower() == 'sl chuyen'):
            col_k = col
        if isinstance(col, str) and ('nhận' in col.lower() or col.lower() == 'sl nhận' or col.lower() == 'sl nhan'):
            col_l = col
    # Fallback to column positions if not found
    if col_k is None:
        col_k = df.columns[10]  # column K (0-indexed)
    if col_l is None:
        col_l = df.columns[11]  # column L
    # Ensure numeric
    df[col_k] = pd.to_numeric(df[col_k], errors='coerce').fillna(0)
    df[col_l] = pd.to_numeric(df[col_l], errors='coerce').fillna(0)
    # Apply capping: if receive > transfer then receive = transfer
    df['capped_receive'] = df.apply(lambda row: min(row[col_l], row[col_k]), axis=1)
    # Compute difference (capped_receive - transfer)
    df['cdc_diff'] = df['capped_receive'] - df[col_k]
    # Keep only rows where difference is negative (shortage)
    df = df[df['cdc_diff'] < 0]
    # Group by date and sum differences
    summary = df.groupby('date')['cdc_diff'].sum().reset_index()
    summary.rename(columns={'cdc_diff': 'cdc_diff'}, inplace=True)
    return summary

def aggregate_cdc(files):
    results = []
    for f in files:
        try:
            summary = process_cdc_file(f)
            results.append(summary)
        except Exception as e:
            print(f"Error processing {f}: {e}")
    if not results:
        return pd.DataFrame(columns=['date', 'cdc_diff'])
    all_df = pd.concat(results)
    total = all_df.groupby('date')['cdc_diff'].sum().reset_index()
    return total

def main():
    # Load Seedlog data
    seedlog_df = load_seedlog()
    # Get all transfer_*.xlsx files in Downloads folder
    download_dir = os.path.expanduser('~/Downloads')
    pattern = os.path.join(download_dir, 'transfer_*.xlsx')
    files = glob.glob(pattern)
    if not files:
        print('No transfer_*.xlsx files found in Downloads.')
        return
    cdc_df = aggregate_cdc(files)
    # Merge on date
    merged = pd.merge(seedlog_df, cdc_df, on='date', how='outer')
    merged['seedlog_diff'] = merged['seedlog_diff'].fillna(0)
    merged['cdc_diff'] = merged['cdc_diff'].fillna(0)
    merged['match'] = merged['seedlog_diff'] == merged['cdc_diff']
    # Generate markdown report
    lines = ['# CDC vs Seedlog Reconciliation', '', '| Date | CDC Diff (units) | Seedlog Diff (units) | Match |', '|---|---|---|---|']
    for _, row in merged.sort_values('date').iterrows():
        date_str = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else 'N/A'
        cdc_val = int(row['cdc_diff'])
        seed_val = int(row['seedlog_diff'])
        match = '✅' if row['match'] else '❌'
        lines.append(f"| {date_str} | {cdc_val} | {seed_val} | {match} |")
    report_path = os.path.abspath('reconciliation_full_auto.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'Report written to {report_path}')

if __name__ == '__main__':
    main()
