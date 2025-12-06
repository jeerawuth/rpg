import json

INPUT = "./output/layers.json"      # ไฟล์ JSON ตัวเดิม
OUTPUT = "./output/layers_pretty.json"  # ไฟล์ JSON ที่จัดรูปแบบใหม่

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

def write_2d_array(f, key, arr, indent="  "):
    f.write(f'{indent}"{key}": [\n')
    for i, row in enumerate(arr):
        row_str = ", ".join(str(v) for v in row)
        f.write(f'{indent}  [{row_str}]')
        if i < len(arr) - 1:
            f.write(',')      # ใส่ , คั่นระหว่างแถว
        f.write('\n')
    f.write(f'{indent}]')

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write('{\n')
    write_2d_array(f, "ground", data["ground"])
    f.write(',\n')
    write_2d_array(f, "details", data["details"])
    f.write(',\n')
    write_2d_array(f, "collision", data["collision"])
    f.write('\n}\n')

print("saved", OUTPUT)
