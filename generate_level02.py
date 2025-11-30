# build_level02.py
import json

TILE_SIZE = 32
WIDTH = 64   # > 40 ของ level01
HEIGHT = 40  # > 22 ของ level01


def build_level02() -> None:
    W, H = WIDTH, HEIGHT

    # ---------- ground layer ----------
    # ข้างในเป็น 1 ขอบนอกเป็น 0 (เหมือน level01)
    ground: list[list[int]] = []
    for r in range(H):
        row: list[int] = []
        for c in range(W):
            if r == 0 or r == H - 1 or c == 0 or c == W - 1:
                row.append(0)
            else:
                row.append(1)
        ground.append(row)

    # ---------- collision layer ----------
    # เริ่มจากกำแพงเต็ม (1 ทั้งแผนที่)
    collision: list[list[int]] = [[1] * W for _ in range(H)]

    # กำหนดรูปตัว U:
    # - แขนซ้าย: คอลัมน์ 4–6
    # - แขนขวา: คอลัมน์ 57–59
    # - ความหนาทางเดิน = 3 tile
    # - ช่วงแขนแนวตั้ง: แถว 2 ถึง (H-8) - 1
    # - ฐานตัว U: สูง 3 แถว เริ่มที่แถว (H-8)
    t = 3
    left_c = 4
    right_c = W - 1 - 4 - t + 1  # = 57 เมื่อ W=64

    top_arm_start_row = 2
    bottom_base_row_start = H - 8  # = 32 เมื่อ H=40
    base_height = 3

    # แขน U ด้านซ้าย–ขวา (แนวตั้ง)
    for r in range(top_arm_start_row, bottom_base_row_start):
        for c in range(left_c, left_c + t):
            collision[r][c] = 0
        for c in range(right_c, right_c + t):
            collision[r][c] = 0

    # ฐานตัว U (แนวนอน)
    for r in range(bottom_base_row_start, bottom_base_row_start + base_height):
        for c in range(left_c, right_c + t):
            collision[r][c] = 0

    # ขอบนอกยังเป็น 1 อยู่แล้ว (กันไม่ให้ออกนอกแผนที่)

    # ---------- ข้อมูลระดับสูง ----------
    level_data = {
        "id": "level02",
        "tileset": "overworld_tiles.png",  # ใช้ tileset เดียวกับ level01
        "tile_size": TILE_SIZE,
        "width": W,
        "height": H,
        "layers": {
            "ground": ground,
            "collision": collision,
        },
        # จุดเกิด player กลางฐานตัว U (ประมาณ tile 32,32)
        "player_spawn": [32 * TILE_SIZE, 32 * TILE_SIZE],

        # ศัตรูวางตามแขนซ้าย–ขวา และฐานตัว U
        "enemy_spawns": [
            {"type": "goblin", "pos": [5 * TILE_SIZE, 5 * TILE_SIZE]},
            {"type": "goblin", "pos": [58 * TILE_SIZE, 6 * TILE_SIZE]},
            {"type": "goblin", "pos": [5 * TILE_SIZE, 25 * TILE_SIZE]},
            {"type": "slime_green", "pos": [58 * TILE_SIZE, 24 * TILE_SIZE]},
            {"type": "slime_green", "pos": [15 * TILE_SIZE, 32 * TILE_SIZE]},
            {"type": "slime_green", "pos": [48 * TILE_SIZE, 32 * TILE_SIZE]},
        ],

        # ไอเท็ม: ตรงฐานตัว U และด้านบนของแขนทั้งสองข้าง
        "item_spawns": [
            {
                "item_id": "bow_power_1",
                "pos": [32 * TILE_SIZE, 33 * TILE_SIZE],
                "amount": 1,
            },
            {
                "item_id": "shield",
                "pos": [5 * TILE_SIZE, 10 * TILE_SIZE],
                "amount": 1,
            },
            {
                "item_id": "shield",
                "pos": [58 * TILE_SIZE, 10 * TILE_SIZE],
                "amount": 1,
            },
        ],
    }

    # ---------- เซฟไฟล์ JSON ----------
    out_path = "assets/data/level02.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(level_data, f, indent=2)

    print(f"Saved {out_path}")


if __name__ == "__main__":
    build_level02()
