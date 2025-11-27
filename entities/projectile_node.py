# entities/projectile_node.py
from __future__ import annotations

import math
import pygame

from .animated_node import AnimatedNode
from combat.damage_system import DamagePacket


class ProjectileNode(AnimatedNode):
    """
    กระสุนแบบ 'ลูกธนู' ที่มีแอนิเมชัน และหมุนตามทิศทาง (8 ทิศ)

    - owner          : ใครเป็นคนยิง (ต้องมี .game และ .stats)
    - damage_packet  : ใช้ตอนคำนวณดาเมจใน on_projectile_hit
    """

    def __init__(
        self,
        owner,
        pos: tuple[int, int],
        direction: pygame.Vector2,
        speed: float,
        damage_packet: DamagePacket,
        lifetime: float = 1.5,
        *groups,
    ) -> None:
        # ---------- เก็บข้อมูลพื้นฐาน ----------
        self.owner = owner
        self.damage_packet = damage_packet

        self.speed = speed
        self.lifetime = lifetime
        self.age = 0.0

        self.position = pygame.Vector2(pos)

        # กันทิศทาง (0, 0)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.direction = direction.normalize()

        # คำนวณมุมจากทิศทาง และ snap เป็น 8 ทิศ (step ละ 45°)
        dx, dy = self.direction.x, self.direction.y
        raw_angle = math.degrees(math.atan2(dy, dx))  # (1,0)=0°, (0,1)=90°, (0,-1)=-90°
        snapped_angle = round(raw_angle / 45.0) * 45.0
        self._angle = snapped_angle

        # ---------- โหลดเฟรม (จะถูกหมุนแล้ว) ----------
        frames = self._load_frames()

        # ความเร็วแอนิเมชัน
        frame_duration = 0.06  # วินาทีต่อเฟรม (ปรับได้)
        loop = True

        # เรียก AnimatedNode.__init__
        super().__init__(frames, frame_duration, loop, *groups)

        # ตั้งตำแหน่งเริ่มต้น
        self.rect.center = self.position

    # ------------------------------------------------------------------
    # โหลดเฟรมจาก ResourceManager แล้วหมุนให้ตรงมุม
    # ------------------------------------------------------------------
    def _load_frames(self) -> list[pygame.Surface]:
        """
        พยายามโหลดเฟรมจาก:
            assets/graphics/images/projectiles/arrow/arrow_01.png
            assets/graphics/images/projectiles/arrow/arrow_02.png
            ...

        *ResourceManager จะจัด scale ให้แล้ว ผ่าน projectile_scale*
        ถ้าไม่มีไฟล์เลย จะใช้ placeholder เป็นแท่งสีเหลือง 1 เฟรม
        """
        frames: list[pygame.Surface] = []
        resources = self.owner.game.resources

        index = 1
        while True:
            rel_path = f"projectiles/arrow/arrow_{index:02d}.png"
            try:
                base_frame = resources.load_image(rel_path)
            except Exception:
                break
            else:
                # หมุนเฟรมตามมุมที่ snap แล้ว
                rotated = pygame.transform.rotate(base_frame, -self._angle)
                frames.append(rotated)
                index += 1

        if frames:
            return frames

        # --- ถ้าไม่มีไฟล์รูปจริงเลย: ใช้ placeholder ---
        w, h = 24, 6
        base_frame = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(base_frame, (250, 230, 80), base_frame.get_rect())

        rotated = pygame.transform.rotate(base_frame, -self._angle)
        frames.append(rotated)
        return frames

    # ------------------------------------------------------------------
    # Update: อายุ + เคลื่อนที่ + แอนิเมชัน
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        # อายุ
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return

        # เคลื่อนที่เป็นเส้นตรงตามทิศ
        self.position += self.direction * self.speed * dt
        self.rect.center = (int(self.position.x), int(self.position.y))

        # ให้ AnimatedNode จัดการเปลี่ยนเฟรม
        super().update(dt)
