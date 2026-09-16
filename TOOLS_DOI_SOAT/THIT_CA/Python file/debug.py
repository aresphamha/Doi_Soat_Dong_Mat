import pandas as pd
import numpy as np

def clean_qty(val):
    if pd.isna(val): return 0.0
    val_str = str(val).strip().replace(',', '')
    try:
        return float(val_str)
    except:
        return 0.0

df = pd.read_csv('https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115', skiprows=1)
df.columns = [str(c).strip() for c in df.columns]

kho_name='Thịt Cá'
col_kho_list = [c for c in df.columns if f'{kho_name.upper()}' in c.upper() or 'KHO TH' in c.upper() or 'KHO RAU' in c.upper() or 'KRC' in c.upper()]
col_kho = col_kho_list[0] if col_kho_list else None
print('col_kho:', col_kho)

df['LyDo_Kho'] = df[col_kho].astype(str).str.strip().str.lower() if col_kho else ''
df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_qty) if 'SL chênh lệch CXD' in df.columns else 0.0

df['Kho_Rau'] = np.where(df['LyDo_Kho'].str.contains(f'{kho_name.lower()}') | df['LyDo_Kho'].str.contains('kho rau') | df['LyDo_Kho'].str.contains('krc'), df['Qty_P'], 0)
df['CXD'] = np.where(df['LyDo_Kho'].str.contains('chưa xác định'), df['Qty_P'], 0)

print(df[['Qty_P', 'Kho_Rau', 'CXD']].sum())
