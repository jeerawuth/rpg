import json
import os

# ----- ขนาดเลเวล -----
WIDTH = 40   # จำนวน tile แนวนอน
HEIGHT = 22  # จำนวน tile แนวตั้ง
TILE_SIZE = 32

# ground: 1 = พื้น (ม่วง), 0 = กำแพง (น้ำเงิน)
ground = [[1] * WIDTH for _ in range(HEIGHT)]
# collision: 1 = ชน, 0 = เดินได้
collision = [[0] * WIDTH for _ in range(HEIGHT)]

# ----- กำแพงรอบนอกทั้ง map -----
for x in range(WIDTH):
    ground[0][x] = 0
    collision[0][x] = 1

    ground[HEIGHT - 1][x] = 0
    collision[HEIGHT - 1][x] = 1

for y in range(HEIGHT):
    ground[y][0] = 0
    collision[y][0] = 1

    ground[y][WIDTH - 1] = 0
    collision[y][WIDTH - 1] = 1


def add_room(x1, y1, x2, y2):
    """
    วาดห้องสี่เหลี่ยมแบบมีผนังหนา 1 ช่องรอบ ๆ
    (x1,y1) ถึง (x2,y2) inclusive เป็นขอบนอกห้อง
    ภายในเป็นพื้นเดินได้
    """
    # ขอบบน + ล่าง
    for x in range(x1, x2 + 1):
        for y in (y1, y2):
            ground[y][x] = 0
            collision[y][x] = 1

    # ขอบซ้าย + ขวา
    for y in range(y1, y2 + 1):
        for x in (x1, x2):
            ground[y][x] = 0
            collision[y][x] = 1

    # ภายในห้อง = พื้น (เผื่อมีตรงไหนโดนทับไว้ก่อน)
    for y in range(y1 + 1, y2):
        for x in range(x1 + 1, x2):
            ground[y][x] = 1
            collision[y][x] = 0


def clear_floor_rect(x1, y1, x2, y2):
    """
    เคลียร์เป็นพื้นเดินได้ (กว้างหลายช่อง)
    ใช้ทำประตู/ทางเดินที่กว้าง 2 ช่อง
    """
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                ground[y][x] = 1
                collision[y][x] = 0


# ----- สร้างห้อง -----
# ห้องซ้ายบน
add_room(2, 2, 16, 9)
# ห้องขวาบน
add_room(23, 2, 37, 10)
# ห้องซ้ายล่าง
add_room(3, 13, 18, 20)
# ห้องขวาล่าง
add_room(22, 13, 36, 20)

# ----- ประตูห้อง (กว้าง 2 ช่อง) -----
# ซ้ายบน เปิดลงด้านล่าง
clear_floor_rect(8, 9, 9, 10)

# ขวาบน เปิดลงด้านล่าง
clear_floor_rect(29, 10, 30, 11)

# ซ้ายล่าง เปิดขึ้นด้านบน
clear_floor_rect(10, 12, 11, 13)

# ขวาล่าง เปิดขึ้นด้านบน
clear_floor_rect(26, 12, 27, 13)

# ----- ทางเดินหลัก (กว้าง 2 ช่อง) -----
# ทางเดินแนวนอนกลาง map
# แถว y = 11 และ 12
for x in range(6, 34):
    clear_floor_rect(x, 11, x, 12)

# ทางเดินแนวตั้งกลาง map (spine)
# คอลัมน์ x = 19 และ 20
for y in range(5, 19):
    clear_floor_rect(19, y, 20, y)

# ทางเชื่อมจากทางเดินหลักเข้าแต่ละห้อง (กว้าง 2 ช่อง)
# จาก spine เข้าโรงซ้ายบน
clear_floor_rect(14, 7, 18, 8)   # แนวนอน 2 แถว

# จาก spine เข้าโรงขวาบน
clear_floor_rect(21, 6, 26, 7)

# จาก spine เข้าโรงซ้ายล่าง
clear_floor_rect(14, 16, 18, 17)

# จาก spine เข้าโรงขวาล่าง
clear_floor_rect(21, 16, 25, 17)

# ตอนนี้ทุกทางเดินหลักจะกว้างอย่างน้อย 2 ช่องเสมอ


# ----- กำหนดตำแหน่ง spawn -----
# ให้ player เริ่มในห้องซ้ายบน
player_spawn = [5 * TILE_SIZE + TILE_SIZE // 2,
                5 * TILE_SIZE + TILE_SIZE // 2]   # ประมาณ tile (5,5)

enemy_spawns = [
    [20 * TILE_SIZE + 16, 11 * TILE_SIZE + 16],  # กลางทางเดินแนวนอน
    [30 * TILE_SIZE + 16, 18 * TILE_SIZE + 16],  # แถวห้องขวาล่าง
]

level_data = {
    "id": "level01",
    "tileset": "overworld_tiles.png",
    "tile_size": TILE_SIZE,
    "width": WIDTH,
    "height": HEIGHT,
    "layers": {
        "ground": ground,
        "collision": collision,
    },
    "player_spawn": player_spawn,
    "enemy_spawns": enemy_spawns,
}

os.makedirs("assets/data", exist_ok=True)
out_path = os.path.join("assets", "data", "level01.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(level_data, f, ensure_ascii=False, indent=2)

print("Saved:", out_path)
