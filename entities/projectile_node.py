# entities/projectile_node.py
from __future__ import annotations

import pygame

from .node_base import NodeBase
from combat.damage_system import DamagePacket


class ProjectileNode(NodeBase):
    def __init__(
        self,
        owner,
        pos: tuple[int, int],
        direction: pygame.Vector2,
        speed: float,
        damage_packet: DamagePacket,
        lifetime: float = 1.0,
        *groups,
    ) -> None:
        """
        - owner: ใครเป็นคนยิง (Player หรือ Enemy)
        - pos: จุดกำเนิดกระสุน
        - direction: Vector2 ทิศทาง (จะ normalize ให้)
        - speed: ความเร็วพิกเซล/วินาที
        - damage_packet: ข้อมูลดาเมจ
        - lifetime: เวลาก่อนกระสุนหาย (วินาที)
        """
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

        # กราฟิกกระสุนง่าย ๆ: วงกลมเล็กสีเหลือง
        radius = 6
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 230, 90), (radius, radius), radius)
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return

        self.position += self.direction * self.speed * dt
        self.rect.center = (int(self.position.x), int(self.position.y))
