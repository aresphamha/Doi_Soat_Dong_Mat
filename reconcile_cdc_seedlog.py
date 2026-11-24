import os
import glob
import pandas as pd
import requests
from io import StringIO

# Configuration
DOWNLOADS_DIR = r"C:/Users/Thu Ha/Downloads"
SEEDLOG_URL = "https://docs.google.com/spreadsheets/d/1IM-3V5PRmnv191JQUx7yPQAMYFVtQRfgCU4ANLGnRBQ/export?format=csv&gid=0"

def find_latest_transfer_file():
    pattern = os.path.join(DOWNLOADS_DIR, "transfer_*.xlsx")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No transfer_*.xlsx files found in {DOWNLOADS_DIR}")
    latest = max(files, key=os.path.getmtime)
    return latest

def load_cdc_data(filepath):
    # Try reading all sheets, pick the one that contains 'SL chuyển' or similar columns
    xl = pd.ExcelFile(filepath)
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name)
        # Look for expected columns by index if names are missing
        if df.shape[1] >= 12:  # need at least 12 columns (K is 11 zero-index)
            return df
    # fallback to first sheet
    return xl.parse(xl.sheet_names[0])

def compute_cdc_totals(df):
    # Assume column A is date, column K (index 10) is SL chuyển, column L (index 11) is SL nhận
    # If column names present, use them, else fallback to positional indexes
    # Get date column name (first column)
    date_col = df.columns[0]
    # Ensure date column is string for merging
    df[date_col] = df[date_col].astype(str).str.strip()
    transfer_col = None
    receive_col = None
    # Try to locate columns by header names containing keywords
    for col in df.columns:
        if isinstance(col, str) and ('chuyển' in col.lower() or 'transfer' in col.lower()):
            transfer_col = col
        if isinstance(col, str) and ('nhận' in col.lower() or 'receive' in col.lower()):
            receive_col = col
    # Fallback to positions if not found
    if transfer_col is None:
        transfer_col = df.columns[10]  # K
    if receive_col is None:
        receive_col = df.columns[11]  # L
    # Clean data: ensure numeric
    df[transfer_col] = pd.to_numeric(df[transfer_col], errors='coerce').fillna(0)
    df[receive_col] = pd.to_numeric(df[receive_col], errors='coerce').fillna(0)
    # Compute capped receive per row
    df['capped_receive'] = df[[transfer_col, receive_col]].min(axis=1)
    # Group by date
    grouped = df.groupby(date_col).agg(
        total_transfer=pd.NamedAgg(column=transfer_col, aggfunc='sum'),
        total_capped_receive=pd.NamedAgg(column='capped_receive', aggfunc='sum')
    ).reset_index()
    grouped['diff'] = grouped['total_capped_receive'] - grouped['total_transfer']
    # Rename date column to a common name for merging
    grouped = grouped.rename(columns={date_col: 'date'})
    return grouped
    # Assume column A is date, column K (index 10) is SL chuyển, column L (index 11) is SL nhận
    # If column names present, use them, else fallback to positional indexes
    # Get date column name (first column)
    date_col = df.columns[0]
    transfer_col = None
    receive_col = None
    # Try to locate columns by header names containing keywords
    for col in df.columns:
        if isinstance(col, str) and ('chuyển' in col.lower() or 'transfer' in col.lower()):
            transfer_col = col
        if isinstance(col, str) and ('nhận' in col.lower() or 'receive' in col.lower()):
            receive_col = col
    # Fallback to positions if not found
    if transfer_col is None:
        transfer_col = df.columns[10]  # K
    if receive_col is None:
        receive_col = df.columns[11]  # L
    # Clean data: ensure numeric
    df[transfer_col] = pd.to_numeric(df[transfer_col], errors='coerce').fillna(0)
    df[receive_col] = pd.to_numeric(df[receive_col], errors='coerce').fillna(0)
    # Compute capped receive per row
    df['capped_receive'] = df[[transfer_col, receive_col]].min(axis=1)
    # Group by date
    grouped = df.groupby(date_col).agg(
        total_transfer=pd.NamedAgg(column=transfer_col, aggfunc='sum'),
        total_capped_receive=pd.NamedAgg(column='capped_receive', aggfunc='sum')
    ).reset_index()
    grouped['diff'] = grouped['total_capped_receive'] - grouped['total_transfer']
    return grouped

def load_seedlog():
    resp = requests.get(SEEDLOG_URL)
    resp.raise_for_status()
    txt = resp.text
    df = pd.read_csv(StringIO(txt))
    return df

def compute_seedlog_totals(df):
    # Seedlog CSV has columns: Column 1 (year), Tháng (month), Ngày (day), ... and a diff column (e.g., 'Difference' or contains 'chênh lệch')
    # Build a proper date string "dd/MM/yyyy" for merging.
    # Identify year, month, day columns (fallback to positional indexes if names differ).
    year_col = None
    month_col = None
    day_col = None
    for col in df.columns:
        name = str(col).lower()
        if 'column 1' in name or 'year' in name:
            year_col = col
        if 'tháng' in name or 'month' in name:
            month_col = col
        if 'ngày' in name or 'day' in name:
            day_col = col
    # Fallback to first three columns if not found
    if year_col is None:
        year_col = df.columns[0]
    if month_col is None:
        month_col = df.columns[1] if len(df.columns) > 1 else None
    if day_col is None:
        day_col = df.columns[2] if len(df.columns) > 2 else None
    # Identify diff column (contains 'chênh lệch' or 'difference')
    diff_col = None
    for col in df.columns:
        if isinstance(col, str) and ('chênh lệch' in col.lower() or 'difference' in col.lower()):
            diff_col = col
            break
    if diff_col is None:
        # try column M (index 11) as fallback
        diff_col = df.columns[11] if len(df.columns) > 11 else None
    if diff_col is None:
        raise ValueError('Cannot locate diff column in Seedlog')
    # Clean numeric diff
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce').fillna(0)
    # Build date string
    def build_date(row):
        y = str(row[year_col]).strip()
        m = str(row[month_col]).strip() if month_col is not None else ''
        d = str(row[day_col]).strip() if day_col is not None else ''
        # Ensure month and day are two‑digit
        if m.isdigit():
            m = m.zfill(2)
        if d.isdigit():
            d = d.zfill(2)
        return f"{d}/{m}/{y}" if d and m else f"{y}"  # fallback to year only
    df['date'] = df.apply(build_date, axis=1)
    # Group by constructed date
    grouped = df.groupby('date').agg(seedlog_diff=pd.NamedAgg(column=diff_col, aggfunc='sum')).reset_index()
    return grouped
    # Assume there is a date column and a diff column (cột M?)
    # Identify date column (first column) and diff column (column containing 'chênh lệch' or 'M')
    date_col = df.columns[0]
    # Ensure date column is string for merging
    df[date_col] = df[date_col].astype(str).str.strip()
    diff_col = None
    for col in df.columns:
        if isinstance(col, str) and ('chênh lệch' in col.lower() or col.strip().upper() == 'M'):
            diff_col = col
            break
    if diff_col is None:
        # try column M by position (12th column index 11)
        if len(df.columns) > 11:
            diff_col = df.columns[11]
        else:
            raise ValueError('Cannot locate diff column in Seedlog')
    # Clean numeric
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce').fillna(0)
    # Group by date
    grouped = df.groupby(date_col).agg(seedlog_diff=pd.NamedAgg(column=diff_col, aggfunc='sum')).reset_index()
    # Rename date column to common name
    grouped = grouped.rename(columns={date_col: 'date'})
    return grouped
    # Assume there is a date column and a diff column (cột M?)
    # Identify date column (first column) and diff column (column containing 'chênh lệch' or 'M')
    date_col = df.columns[0]
    diff_col = None
    for col in df.columns:
        if isinstance(col, str) and ('chênh lệch' in col.lower() or col.strip().upper() == 'M'):
            diff_col = col
            break
    if diff_col is None:
        # try column M by position (12th column index 11)
        if len(df.columns) > 11:
            diff_col = df.columns[11]
        else:
            raise ValueError('Cannot locate diff column in Seedlog')
    # Clean numeric
    df[diff_col] = pd.to_numeric(df[diff_col], errors='coerce').fillna(0)
    # Group by date
    grouped = df.groupby(date_col).agg(seedlog_diff=pd.NamedAgg(column=diff_col, aggfunc='sum')).reset_index()
    return grouped

def main():
    try:
        cdc_file = find_latest_transfer_file()
        print(f"Using CDC file: {cdc_file}")
        cdc_df = load_cdc_data(cdc_file)
        cdc_totals = compute_cdc_totals(cdc_df)
        seedlog_df = load_seedlog()
        seedlog_totals = compute_seedlog_totals(seedlog_df)
            # Filter dates from November 2026 onward
        def parse_date(s):
            try:
                return pd.to_datetime(s, dayfirst=True)
            except Exception:
                return pd.NaT
        cdc_totals['date_dt'] = cdc_totals['date'].apply(parse_date)
        seedlog_totals['date_dt'] = seedlog_totals['date'].apply(parse_date)
        mask_cdc = cdc_totals['date_dt'] >= pd.Timestamp('2026-11-01')
        mask_seed = seedlog_totals['date_dt'] >= pd.Timestamp('2026-11-01')
        cdc_totals = cdc_totals[mask_cdc].drop(columns=['date_dt'])
        seedlog_totals = seedlog_totals[mask_seed].drop(columns=['date_dt'])

    def parse_date(s):
        try:
            return pd.to_datetime(s, dayfirst=True)
        except Exception:
            return pd.NaT
    cdc_totals['date_dt'] = cdc_totals['date'].apply(parse_date)
    seedlog_totals['date_dt'] = seedlog_totals['date'].apply(parse_date)
    # Keep only dates >= 2026-11-01
    mask_cdc = cdc_totals['date_dt'] >= pd.Timestamp('2026-11-01')
    mask_seed = seedlog_totals['date_dt'] >= pd.Timestamp('2026-11-01')
    cdc_totals = cdc_totals[mask_cdc]
    seedlog_totals = seedlog_totals[mask_seed]
    # Drop auxiliary column before merge
    cdc_totals = cdc_totals.drop(columns=['date_dt'])
    seedlog_totals = seedlog_totals.drop(columns=['date_dt'])

        merged = pd.merge(cdc_totals, seedlog_totals, on='date', how='outer', suffixes=('_cdc','_seed'))
        merged = merged.fillna(0)
        merged['match'] = (merged['diff'].round(6) == merged['seedlog_diff'].round(6))
        # Output report
        report_path = r"g:/My Drive/Đối soát SCM/reconciliation_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# CDC vs Seedlog Reconciliation Report\n\n")
            f.write("| Ngày | SL Chuyển (CDC) | SL Nhận (capped) | SL chênh lệch (CDC) | SL chênh lệch (Seedlog) | Match |\n")
            f.write("|------|-----------------|-------------------|----------------------|--------------------------|-------|\n")
            for _, row in merged.iterrows():
                f.write(f"| {row[0]} | {int(row['total_transfer'])} | {int(row['total_capped_receive'])} | {int(row['diff'])} | {int(row['seedlog_diff'])} | {'✅' if row['match'] else '❌'} |\n")
        print(f"Report written to {report_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
