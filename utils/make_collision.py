from PIL import Image
import numpy as np
import json
import math

IMG = "./input/overworld_level_11_bone.png"

# ขนาด cell สำหรับ collision (ไม่จำเป็นต้องเท่ากับ tile art)
COLL_TILE   = 4       # 8x8 px
ALPHA_THR   = 32      # pixel ที่ alpha >= 32 ถือว่า "ทึบ"
COVER_THR   = 0.40    # มี pixel ทึบ >= 40% ⇒ cell นี้ชนได้

img   = Image.open(IMG).convert("RGBA")
w, h  = img.size

# เอาเฉพาะ alpha channel มาใช้
alpha = np.array(img.split()[-1], dtype=np.uint8)   # shape: (h, w)

tiles_x = math.ceil(w / COLL_TILE)
tiles_y = math.ceil(h / COLL_TILE)

# collision[y][x] = 0 or 1
collision = np.zeros((tiles_y, tiles_x), dtype=np.uint8)

for ty in range(tiles_y):
    y0 = ty * COLL_TILE
    y1 = min(y0 + COLL_TILE, h)
    for tx in range(tiles_x):
        x0 = tx * COLL_TILE
        x1 = min(x0 + COLL_TILE, w)

        # พื้นที่ย่อยของ alpha ใน cell นี้
        sub = alpha[y0:y1, x0:x1]
        if sub.size == 0:
            continue

        solid = (sub >= ALPHA_THR)       # bool array
        coverage = solid.mean()          # ค่า 0.0 - 1.0

        if coverage >= COVER_THR:
            collision[ty, tx] = 1

layers = {
    "collision": collision.tolist()
}

with open("./output/collision.json", "w", encoding="utf-8") as f:
    json.dump(layers, f, ensure_ascii=False, indent=2)

print("saved collision.json")
