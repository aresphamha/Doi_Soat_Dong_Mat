import pandas as pd, glob, os

# Configuration
SEEDLOG_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&id=1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ&gid=0"
TARGET_DATES = ["2026-11-03", "2026-11-05", "2026-11-07"]
OUTPUT_PATH = os.path.abspath('SO_SANH_FMCG_03_05_07.xlsx')

def load_seedlog():
    df = pd.read_csv(SEEDLOG_URL, dtype=str)
    # Find date and diff columns
    date_col = next((c for c in df.columns if isinstance(c, str) and 'ngày' in c.lower()), None)
    diff_col = next((c for c in df.columns if str(c).strip().lower() in ['difference', 'chênh lệch', 'diff']), None)
    if not date_col or not diff_col:
        raise ValueError('Date or difference column not found')
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce')
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df[df[diff_col] < 0]
    df['date_str'] = df[date_col].dt.strftime('%Y-%m-%d')
    df = df[df['date_str'].isin(TARGET_DATES)]
    return df[['date_str', diff_col]].rename(columns={diff_col: 'seedlog_diff'})

def load_cdc():
    download_dir = os.path.expanduser('~/Downloads')
    files = glob.glob(os.path.join(download_dir, 'transfer_*.xlsx'))
    rows = []
    for f in files:
        # read only needed columns: assume A=Date, K=SL chuyển, L=SL nhận
        try:
            df = pd.read_excel(f, usecols='A,K,L', engine='openpyxl')
        except Exception:
            df = pd.read_excel(f, engine='openpyxl')  # fallback
            # try to locate columns by name if present
        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]
        # Identify columns
        date_col = df.columns[0]
        col_k = df.columns[1] if len(df.columns) > 1 else None
        col_l = df.columns[2] if len(df.columns) > 2 else None
        if col_k is None or col_l is None:
            continue
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        df[col_k] = pd.to_numeric(df[col_k], errors='coerce').fillna(0)
        df[col_l] = pd.to_numeric(df[col_l], errors='coerce').fillna(0)
        df['capped_receive'] = df.apply(lambda r: min(r[col_l], r[col_k]), axis=1)
        df['cdc_diff'] = df['capped_receive'] - df[col_k]
        df['date_str'] = df[date_col].dt.strftime('%Y-%m-%d')
        df = df[df['date_str'].isin(TARGET_DATES) & (df['cdc_diff'] < 0)]
        rows.append(df[['date_str', 'cdc_diff']])
    if not rows:
        return pd.DataFrame(columns=['date_str', 'cdc_diff'])
    all_cdc = pd.concat(rows)
    summary = all_cdc.groupby('date_str')['cdc_diff'].sum().reset_index()
    return summary

def build_excel():
    seed = load_seedlog()
    cdc = load_cdc()
    merged = pd.merge(seed, cdc, on='date_str', how='outer')
    merged['seedlog_diff'] = merged['seedlog_diff'].fillna(0).astype(int)
    merged['cdc_diff'] = merged['cdc_diff'].fillna(0).astype(int)
    merged['match'] = merged['seedlog_diff'] == merged['cdc_diff']
    # Write Excel
    with pd.ExcelWriter(OUTPUT_PATH, engine='openpyxl') as writer:
        # Summary sheet
        summary = merged[['date_str', 'cdc_diff', 'seedlog_diff', 'match']].copy()
        summary['match'] = summary['match'].apply(lambda x: '✅' if x else '❌')
        summary.to_excel(writer, sheet_name='Summary', index=False)
        # Raw Seedlog sheet (export all columns for transparency)
        raw_seed = load_seedlog().merge(pd.read_csv(SEEDLOG_URL, dtype=str), left_on='date_str', right_on=lambda row: pd.to_datetime(row['ngày'], dayfirst=True).strftime('%Y-%m-%d'), how='left')
        raw_seed.to_excel(writer, sheet_name='Seedlog_Raw', index=False)
    print('Excel file created at', OUTPUT_PATH)

if __name__ == '__main__':
    build_excel()
