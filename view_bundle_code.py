with open('extracted_compute_group_bundle.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("First 80 lines:")
for i, line in enumerate(lines[:80]):
    print(f"{i+1:3d}: {line.rstrip()}")

print("\nLast 50 lines:")
for i, line in enumerate(lines[-50:]):
    print(f"{len(lines)-50+i+1:3d}: {line.rstrip()}")
