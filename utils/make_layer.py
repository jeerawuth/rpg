from PIL import Image
import json

IMG = "./output/overworld_level_02.png"
TILE = 32

img = Image.open(IMG).convert("RGBA")
w, h = img.size
tiles_x = w // TILE        # จำนวนคอลัมน์ของ tile
tiles_y = h // TILE        # จำนวนแถวของ tile

print("image size:", w, h, "=> tiles:", tiles_x, "x", tiles_y)

pixels = img.load()

# เตรียมอาร์เรย์เริ่มต้น
# details: -1 = ไม่มี tile
details = [[-1 for _ in range(tiles_x)] for _ in range(tiles_y)]
# collision: 0 = เดินผ่านได้, 1 = ชนได้
collision = [[0  for _ in range(tiles_x)] for _ in range(tiles_y)]

for ty in range(tiles_y):
    for tx in range(tiles_x):
        x0, y0 = tx * TILE, ty * TILE
        has_wall = False

        # ตรวจพิกเซลในกรอบ 32x32 ของ tile นี้
        for py in range(y0, y0 + TILE):
            for px in range(x0, x0 + TILE):
                r, g, b, a = pixels[px, py]
                if a > 0:  # ไม่โปร่งใส = ถือว่ามีกำแพง
                    has_wall = True
                    break
            if has_wall:
                break

        if has_wall:
            # คำนวณหมายเลขเฟรมใน tileset
            frame_index = ty * tiles_x + tx
            details[ty][tx] = frame_index   # ใช้เฟรมนี้ใน layer details
            collision[ty][tx] = 1           # ช่องนี้ชนได้
        else:
            # ไม่มีกำแพง → ปล่อย details เป็น -1 และ collision เป็น 0
            pass

layers = {
    "ground":   [[0] * tiles_x for _ in range(tiles_y)],  # ถ้าอยากใช้พื้น 0 ล้วน
    "details":  details,
    "collision": collision,
}

with open("./output/layers.json", "w", encoding="utf-8") as f:
    json.dump(layers, f, ensure_ascii=False, indent=2)

print("saved layers.json")
