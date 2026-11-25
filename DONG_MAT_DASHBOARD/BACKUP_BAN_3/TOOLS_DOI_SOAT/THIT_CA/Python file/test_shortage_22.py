import sys
import os
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath('C:\\Users\\PC\\Desktop\\AI\\Đối soát\\THỊT CÁ'))
from app_thit_ca import load_data

# Simulate what app_thit_ca does for 22/07
df_mf01, df_mf02 = load_data('2026-07-22', '65430263f3ffc80007137f8f', 'KHO RAU')

df_shortage = df_mf01[(df_mf01['Chênh lệch'].round(5) > 0.0)]
valid_shortage = df_shortage[['to_branch_id', 'Mã hàng', 'Chênh lệch']].copy()
valid_shortage.rename(columns={'Chênh lệch': 'Số lượng thiếu'}, inplace=True)
valid_shortage = valid_shortage.groupby(['to_branch_id', 'Mã hàng'])['Số lượng thiếu'].sum().reset_index()

valid_surplus = df_mf02
print("Valid surplus:")
print(valid_surplus[valid_surplus['to_branch_id'] == '69bcfc8e8abcc600073e596d'][['Mã chuyển hàng', 'Mã hàng', 'Số lượng']])

merged = pd.merge(valid_shortage, valid_surplus, on=['to_branch_id', 'Mã hàng'], how='inner')
print("Merged for 69bcfc8e8abcc600073e596d:")
print(merged[merged['to_branch_id'] == '69bcfc8e8abcc600073e596d'])
