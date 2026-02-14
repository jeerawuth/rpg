import pygame
from .node_base import NodeBase
from config.settings import UI_SCORE_PATH, UI_FONT_HUD_PATH

class DamageNumberNode(NodeBase):
    def __init__(
        self,
        game,
        pos: tuple[float, float],
        value: int | str,
        *groups,
        color: tuple[int, int, int] = (255, 255, 255),
        is_crit: bool = False
    ) -> None:
        super().__init__(*groups)
        self.game = game
        self.pos = pygame.math.Vector2(pos)
        
        # ตั้งค่าฟอนต์
        # ถ้าติด Critical หรือเป็นข้อความพิเศษ (str) อาจจะทำตัวใหญ่ขึ้น
        if isinstance(value, str):
            font_size = 23  # (28 - 5) ลดขนาดฟอนต์ข้อความลงตามที่ user ขอ
        elif is_crit:
            font_size = 28
        else:
            font_size = 20
        
        # เลือกฟอนต์: ถ้าเป็นข้อความ (เช่น ภาษาไทย) ให้ใช้ UI_FONT_HUD_PATH
        # ถ้าเป็นตัวเลข (Damage) ให้ใช้ UI_SCORE_PATH ตามเดิม
        font_path = UI_FONT_HUD_PATH if isinstance(value, str) else UI_SCORE_PATH
        font = self.game.resources.load_font(font_path, font_size)
        
        if isinstance(value, str):
            text = value
        else:
            text = str(value)
            # ถ้าติดลบ (เช่น ลดเลือด) ให้ใส่ - นำหน้า หรือจะใส่แค่ตัวเลขก็ได้ตามดีไซน์
            # โจทย์บอก "เช่น -20"
            if value > 0:
                 text = f"-{value}"
        
        # Render text
        final_color = (255, 50, 50) if is_crit else color
        self.image = font.render(text, True, final_color)
        
        # ใส่ขอบดำเพื่อให้มองเห็นชัดขึ้น (Optional)
        # วิธีง่ายๆ คือ render สีดำทับแล้วแปะสีจริงทับแบบ shift เล็กน้อย หรือใช้ outline
        # ในที่นี้ใช้แบบง่าย: สร้าง surface ใหม่ ใหญ่กว่าเดิมนิดหน่อย
        text_surf = self.image
        w, h = text_surf.get_size()
        
        # สร้าง surface ที่มี outline
        outline_surf = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        # วาดเงาดำ 4 ทิศ
        black_surf = font.render(text, True, (0, 0, 0))
        outline_surf.blit(black_surf, (0, 1))
        outline_surf.blit(black_surf, (2, 1))
        outline_surf.blit(black_surf, (1, 0))
        outline_surf.blit(black_surf, (1, 2))
        # วาดตัวจริงทับตรงกลาง
        outline_surf.blit(text_surf, (1, 1))
        
        self.image = outline_surf
        self.rect = self.image.get_rect(center=pos)
        
        # Physics
        # เด้งขึ้นเล็กน้อย
        self.velocity = pygame.math.Vector2(0, -50)  # ขึ้นด้วยความเร็ว 50 px/s
        self.lifetime = 0.8  # อยู่ได้ 0.8 วินาที
        self.alpha = 255.0
        
        # Z-index สูงๆ จะได้อยู่ทับตัวละคร
        self.z = 20

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
            
        # เคลื่อนที่
        self.pos += self.velocity * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        
        # Fade out ในช่วงครึ่งหลัง
        if self.lifetime < 0.4:
            # 0.4 -> 0.0 แปลงเป็น alpha 255 -> 0
            ratio = self.lifetime / 0.4
            self.alpha = 255 * ratio
            self.image.set_alpha(int(self.alpha))
