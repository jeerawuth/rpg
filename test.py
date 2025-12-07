import pygame
import math

pygame.init()
SIZE = WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode(SIZE)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LINE_COLOR = (0, 255, 255)

# -----------------------------------
# ฟังก์ชันแปลงพิกัด 2D -> isometric
# -----------------------------------
ANGLE_DEG = 25
ANGLE_RAD = math.radians(ANGLE_DEG)
ISO_K = math.sin(ANGLE_RAD)  # factor เอียง

def iso_transform(x: float, y: float, cx: int, cy: int) -> tuple[int, int]:
    sx = x - y
    sy = (x + y) * ISO_K
    return int(cx + sx), int(cy + sy)

# -----------------------------------
# เตรียมจุดของสี่เหลี่ยม + วงกลม ใน 2D ปกติ
# -----------------------------------
L = 200          # ความยาวด้านของสี่เหลี่ยม
R = L / 2        # รัศมีของวงกลม (วงกลมครอบในสี่เหลี่ยม)
cx_screen = WIDTH // 2
cy_screen = HEIGHT // 2 + 50   # ขยับลงนิดให้ดูบาลานซ์

# สี่เหลี่ยมจัตุรัส (ก่อนแปลง)
square_2d = [
    (-L/2, -L/2),
    ( L/2, -L/2),
    ( L/2,  L/2),
    (-L/2,  L/2),
]

# สร้าง polyline ของวงกลมด้วยหลาย ๆ จุด
circle_2d = []
segments = 64
for i in range(segments):
    t = 2 * math.pi * i / segments
    x = R * math.cos(t)
    y = R * math.sin(t)
    circle_2d.append((x, y))

# แปลงพิกัดทั้งหมดเป็น isometric
square_iso = [iso_transform(x, y, cx_screen, cy_screen) for (x, y) in square_2d]
circle_iso = [iso_transform(x, y, cx_screen, cy_screen) for (x, y) in circle_2d]

# ปิด polygon ของสี่เหลี่ยมให้ครบ 4 ด้าน
square_iso.append(square_iso[0])

running = True
clock = pygame.time.Clock()

while running:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)

    # วาดเส้นสี่เหลี่ยม
    pygame.draw.lines(screen, LINE_COLOR, False, square_iso, 2)

    # วาดวงกลม (ด้วย polyline)
    pygame.draw.lines(screen, LINE_COLOR, True, circle_iso, 2)

    pygame.display.flip()

pygame.quit()
