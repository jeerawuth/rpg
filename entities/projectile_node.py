# entities/projectile_node.py
from __future__ import annotations

import math
import pygame

from .node_base import NodeBase
from combat.damage_system import DamagePacket


class ProjectileNode(NodeBase):
    """
    กระสุนแบบ 'ลูกธนู' รองรับการหมุน 8 ทิศ (N, NE, E, SE, S, SW, W, NW)

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
        super().__init__(*groups)

        self.owner = owner
        self.damage_packet = damage_packet

        self.speed = speed
        self.lifetime = lifetime
        self.age = 0.0

        self.position = pygame.Vector2(pos)

        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.direction = direction.normalize()

        self._load_graphics()

    # ---------------- Graphics ----------------
    def _load_graphics(self) -> None:
        """
        พยายามโหลดรูปธนูจาก:
            assets/graphics/images/projectiles/arrow_01.png

        ถ้าไม่มีไฟล์ => ใช้วงกลมเหลืองเล็ก ๆ เป็น placeholder

        จากนั้นจะหมุน sprite ตามทิศ self.direction โดยสแนปเป็นมุม 8 ทิศ
        (แต่ละทิศห่างกัน 45°)
        """
        # 1) โหลด base image
        try:
            base_image = self.owner.game.resources.load_image(
                "projectiles/arrow_01.png"
            )
        except Exception:
            # placeholder: วงกลมเล็กสีเหลือง
            radius = 6
            base_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                base_image,
                (255, 230, 90),
                (radius, radius),
                radius,
            )

        self._base_image = base_image

        # 2) คำนวณมุมจากเวกเตอร์ทิศทาง
        dx, dy = self.direction.x, self.direction.y

        # ใช้พิกัดจอ (y ลงล่าง) -> atan2(dy, dx)
        raw_angle = math.degrees(math.atan2(dy, dx))
        # raw_angle:
        #   (1, 0)   -> 0   (ขวา)
        #   (0, 1)   -> 90  (ลง)
        #   (-1, 0)  -> 180 (ซ้าย)
        #   (0, -1)  -> -90 (ขึ้น)

        # 3) สแนปมุมให้เป็น step ละ 45° (8 ทิศ)
        snapped_angle = round(raw_angle / 45.0) * 45.0

        # 4) หมุน sprite
        # pygame.transform.rotate: มุมบวก = หมุนทวนเข็มนาฬิกา
        # base arrow หันขวา -> ใช้ -snapped_angle เพื่อให้ทิศตรงกับเวกเตอร์บนจอ
        rotated = pygame.transform.rotate(base_image, -snapped_angle)

        self.image = rotated
        self.rect = self.image.get_rect(center=self.position)

        # เก็บมุมไว้เผื่อ debug
        self._snapped_angle = snapped_angle

    # ---------------- Update ----------------
    def update(self, dt: float) -> None:
        # อายุ
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return

        # เคลื่อนที่
        self.position += self.direction * self.speed * dt
        self.rect.center = (int(self.position.x), int(self.position.y))
