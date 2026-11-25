import pandas as pd, glob, os

# Configuration
SEEDLOG_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&id=1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ&gid=0"
TARGET_DATES = ["2026-11-03", "2026-11-05", "2026-11-07"]
OUTPUT_PATH = os.path.abspath('SO_SANH_FMCG_03_05_07.xlsx')

def load_seedlog_raw():
    df = pd.read_csv(SEEDLOG_URL, dtype=str)
    # Find date column
    date_col = next((c for c in df.columns if isinstance(c, str) and 'ngày' in c.lower()), None)
    diff_col = next((c for c in df.columns if str(c).strip().lower() in ['difference', 'chênh lệch', 'diff']), None)
    if not date_col or not diff_col:
        raise ValueError('Required columns not found')
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce')
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df[df[diff_col] < 0]
    # Rename columns for consistency
    df = df.rename(columns={date_col: 'date', diff_col: 'seedlog_diff'})
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    df = df[df['date_str'].isin(TARGET_DATES)]
    return df

def load_cdc_data():
    download_dir = os.path.expanduser('~/Downloads')
    pattern = os.path.join(download_dir, 'transfer_*.xlsx')
    files = glob.glob(pattern)
    all_rows = []
    for f in files:
        xl = pd.ExcelFile(f)
        sheet = 'transfer' if 'transfer' in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet)
        # Identify columns
        date_col = df.columns[0]
        df['date'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        # Find SL chuyển (K) and SL nhận (L)
        col_k = next((c for c in df.columns if isinstance(c, str) and ('chuyển' in c.lower() or c.lower() in ['sl chuyển','sl chuyen'])), None)
        col_l = next((c for c in df.columns if isinstance(c, str) and ('nhận' in c.lower() or c.lower() in ['sl nhận','sl nhan'])), None)
        if col_k is None: col_k = df.columns[10]
        if col_l is None: col_l = df.columns[11]
        df[col_k] = pd.to_numeric(df[col_k], errors='coerce').fillna(0)
        df[col_l] = pd.to_numeric(df[col_l], errors='coerce').fillna(0)
        # Apply capping
        df['capped_receive'] = df.apply(lambda r: min(r[col_l], r[col_k]), axis=1)
        df['cdc_diff'] = df['capped_receive'] - df[col_k]
        # Keep only negative diff rows (shortage)
        df = df[df['cdc_diff'] < 0]
        # Keep only target dates
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
        df = df[df['date_str'].isin(TARGET_DATES)]
        all_rows.append(df[['date','cdc_diff']])
    if not all_rows:
        return pd.DataFrame(columns=['date','cdc_diff'])
    all_df = pd.concat(all_rows)
    summary = all_df.groupby('date')['cdc_diff'].sum().reset_index()
    return summary

def build_excel():
    seed_raw = load_seedlog_raw()
    # Summary per date for Seedlog (sum of diff)
    seed_summary = seed_raw.groupby('date_str')['seedlog_diff'].sum().reset_index()
    # CDC summary
    cdc_summary = load_cdc_data()
    cdc_summary['date_str'] = cdc_summary['date'].dt.strftime('%Y-%m-%d')
    # Merge summaries
    merged = pd.merge(seed_summary, cdc_summary, on='date_str', how='outer')
    merged = merged.rename(columns={'seedlog_diff':'seedlog_diff','cdc_diff':'cdc_diff'})
    merged['seedlog_diff'] = merged['seedlog_diff'].fillna(0).astype(int)
    merged['cdc_diff'] = merged['cdc_diff'].fillna(0).astype(int)
    merged['match'] = merged['seedlog_diff'] == merged['cdc_diff']
    # Write to Excel with two sheets
    with pd.ExcelWriter(OUTPUT_PATH, engine='openpyxl') as writer:
        # Sheet 1: summary
        summary_sheet = merged[['date_str','cdc_diff','seedlog_diff','match']]
        summary_sheet['match'] = summary_sheet['match'].apply(lambda x: '✅' if x else '❌')
        summary_sheet.to_excel(writer, sheet_name='Summary', index=False)
        # Sheet 2: raw Seedlog rows (export all columns available)
        raw_sheet = seed_raw.copy()
        raw_sheet.to_excel(writer, sheet_name='Seedlog_Raw', index=False)
    print('Excel report written to', OUTPUT_PATH)

if __name__ == '__main__':
    build_excel()
