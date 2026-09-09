with open('extracted_script.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[:120]):
    print(f"{i+1:3d}: {line.rstrip()}")
