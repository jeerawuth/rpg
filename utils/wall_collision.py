from PIL import Image
import json

IMG = "overworld_rock_tiles_no_grid.png"
TILE = 32

img = Image.open(IMG).convert("RGBA")
w, h = img.size
tiles_x = w // TILE   # 64
tiles_y = h // TILE   # 36

pixels = img.load()

details = [[-1 for _ in range(tiles_x)] for _ in range(tiles_y)]
collision = [[0  for _ in range(tiles_x)] for _ in range(tiles_y)]

for ty in range(tiles_y):
    for tx in range(tiles_x):
        x0, y0 = tx*TILE, ty*TILE
        has_wall = False

        for py in range(y0, y0+TILE):
            for px in range(x0, x0+TILE):
                r,g,b,a = pixels[px,py]
                if a > 0:            # ไม่โปร่งใส = มีกำแพง
                    has_wall = True
                    break
            if has_wall:
                break

        if has_wall:
            details[ty][tx] = 0   # หรือ index tile กำแพง (ถ้ามี tileset แยก)
            collision[ty][tx] = 1

layers = {
  "ground": [[0]*tiles_x for _ in range(tiles_y)],
  "details": details,
  "collision": collision
}

with open("layers.json","w",encoding="utf-8") as f:
    json.dump(layers, f, ensure_ascii=False, indent=2)
