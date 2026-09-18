import pandas as pd
df = pd.read_csv('https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/export?format=csv&gid=1422896115', skiprows=1)
with open('cols.txt', 'w', encoding='utf-8') as f:
    for i, c in enumerate(df.columns):
        f.write(f'{i}: {c}\n')
