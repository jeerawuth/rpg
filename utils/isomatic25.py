import pygame
import math

pygame.init()
WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
CYAN  = (0, 255, 255)
WHITE = (255, 255, 255)

# -----------------------------
# 1) isometric transform 25°
# -----------------------------
ANGLE_DEG = 25
ANGLE_RAD = math.radians(ANGLE_DEG)
ISO_K = math.sin(ANGLE_RAD)  # factor บีบแกนตั้ง

def iso_transform(x: float, y: float, cx: int, cy: int) -> tuple[int, int]:
    """แปลงจุด (x, y) ในระนาบปกติ -> พิกัดจอแบบ isometric 25°"""
    sx = x - y
    sy = (x + y) * ISO_K
    return int(cx + sx), int(cy + sy)


# -----------------------------
# 2) สร้างจุดบนวงกลมใน world
# -----------------------------
def build_circle_points(radius: float, segments: int = 128):
    """คืน list จุดบนวงกลม (world space) รอบจุด (0,0)"""
    pts = []
    for i in range(segments):
        t = 2 * math.pi * i / segments
        x = radius * math.cos(t)
        y = radius * math.sin(t)
        pts.append((x, y))
    return pts


# -----------------------------
# 3) สร้างส่วนโค้งที่ใช้ทำเอฟเฟ็กต์
# -----------------------------
def build_arc_points(radius: float, start_deg: float, end_deg: float,
                     segments: int = 48):
    """คืน list จุดบน 'ส่วนโค้ง' ของวงกลม (world space)"""
    pts = []

    if end_deg < start_deg:
        end_deg += 360

    for i in range(segments + 1):
        a_deg = start_deg + (end_deg - start_deg) * i / segments
        a_rad = math.radians(a_deg)
        x = radius * math.cos(a_rad)
        y = radius * math.sin(a_rad)
        pts.append((x, y))

    return pts


# เตรียมข้อมูล
CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2 + 40
RADIUS   = 170

# วงกลมเต็มใน world
circle_world = build_circle_points(RADIUS, segments=128)

# ส่วนโค้งสำหรับเอฟเฟ็กต์ (ตัวอย่าง: ช่วงมุม 30° ถึง 120°)
arc_world = build_arc_points(RADIUS, start_deg=0, end_deg=45, segments=48)

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)

    # -----------------------------
    # วาดวงกลม (กลายเป็นวงรี isometric)
    # + จุดเล็ก ๆ แสดงแต่ละ point
    # -----------------------------
    circle_iso = [iso_transform(x, y, CENTER_X, CENTER_Y) for (x, y) in circle_world]

    # วาดเส้นโครงวงกลมจาง ๆ
    pygame.draw.lines(screen, CYAN, True, circle_iso, 1)

    # วาดจุดบนวงกลมทุกจุด (debug / สาธิต)
    for sx, sy in circle_iso:
        pygame.draw.circle(screen, WHITE, (sx, sy), 2)

    # -----------------------------
    # วาดเอฟเฟ็กต์เรืองแสงตาม "ส่วนโค้ง"
    # -----------------------------
    arc_iso = [iso_transform(x, y, CENTER_X, CENTER_Y) for (x, y) in arc_world]

    # ทำ surface โปร่งใสสำหรับ glow
    fx_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    # วาดเส้นหลายชั้น ให้ดูเป็นแสงฟุ้ง ๆ
    for i in range(5):
        width = 10 - i * 2         # เส้นชั้นในเล็ก ชั้นนอกใหญ่
        alpha = 40 + i * 40        # ชั้นในสว่างกว่า
        color = (0, 255, 255, alpha)
        pygame.draw.lines(fx_surface, color, False, arc_iso, width)

    # ทับลงหน้าจอ
    screen.blit(fx_surface, (0, 0))

    # จุดกึ่งกลาง (ตำแหน่งตัวละคร)
    pygame.draw.circle(screen, WHITE, (CENTER_X, CENTER_Y), 4)

    pygame.display.flip()

pygame.quit()
