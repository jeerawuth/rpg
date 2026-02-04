import pygame
import random
from .animated_node import AnimatedNode

class HitEffectNode(AnimatedNode):
    """
    เอฟเฟ็กต์ Hit Spark เวลาโดนโจมตี
    """
    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        scale: float = 1.0,
        rotation: bool = True
    ) -> None:
        self.game = game
        
        # โหลดรูป hit_01.png ... hit_03.png
        self.frames = []
        try:
            for i in range(1, 4):
                path = f"effects/hit_{i:02d}.png"
                img = self.game.resources.load_image(path)
                if scale != 1.0:
                     img = self.game.resources._scale_surface(img, scale)
                self.frames.append(img)
            
            # สุ่มหมุนเพื่อความไม่ซ้ำซาก (หมุนทั้งชุดด้วยมุมเดียวกัน)
            if rotation:
                angle = random.randint(0, 360)
                self.frames = [pygame.transform.rotate(f, angle) for f in self.frames]
                
        except Exception:
            # Fallback
            s = pygame.Surface((32, 32), pygame.SRCALPHA)
            s.fill((255, 255, 200)) # สีเหลืองอ่อน
            self.frames = [s]

        # AnimatedNode ต้องการ frames list
        # frame_duration ปรับให้เร็วขึ้นเพราะเป็น effect สั้นๆ
        super().__init__(self.frames, 0.05, False, *groups)
        
        self.rect.center = pos
        self.z = 15 
        
        # ไม่ต้องใช้ timer เองแล้ว เพราะ AnimatedNode จะจบเองเมื่อ loop=False และเล่นครบ
        # แต่ถ้าอยากให้มั่นใจก็ใส่ finished check ใน update
        self.alpha = 255.0

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.finished:
            self.kill()
