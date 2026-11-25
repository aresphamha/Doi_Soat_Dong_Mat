with open('app_thit_ca.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = "for col in ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', f'{kho_name}', 'Tổng chưa xác định']:"
repl = "for col in ['Tổng GT', 'Tổng hao hụt', 'Tổng ST', f'Tổng {kho_name.lower()}', 'Tổng chưa xác định']:"

if target in content:
    content = content.replace(target, repl)
    with open('app_thit_ca.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced')
else:
    print('Not found')
