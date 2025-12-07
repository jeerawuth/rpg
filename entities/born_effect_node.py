# entities/born_effect_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode


class BornEffectNode(AnimatedNode):
    """
    เอฟเฟกต์แจ้งเตือนตำแหน่งเกิดศัตรู
    โหลดรูปจาก assets/graphics/images/effects/born_01.png, born_02.png, ...
    แล้วเล่น loop ตาม lifetime
    """

    # cache เฟรมต่อ (effect_id, scale) เพื่อลดการ scale ซ้ำทุกครั้งที่มี spawn ใหม่
    _FRAME_CACHE: dict[tuple[str, float], list[pygame.Surface]] = {}

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        effect_id: str = "born",
        frame_duration: float = 0.08,
        lifetime: float = 2.0,
        scale: float = 0.5,     # ขยาย/ย่อจากขนาดที่ ResourceManager ให้มา
    ) -> None:
        self.game = game
        self.effect_id = effect_id
        self.lifetime = lifetime
        self._timer = lifetime
        self._extra_scale = scale

        # ดึงจาก cache ถ้ามีแล้ว (ลดงาน scale หนัก ๆ ตอนสร้าง effect ระหว่างเกม)
        cache_key = (self.effect_id, self._extra_scale)
        frames = self._FRAME_CACHE.get(cache_key)

        if frames is None:
            frames = self._load_frames()

            # fallback ถ้าโหลดไม่ได้เลย
            if not frames:
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((255, 255, 0))
                frames = [surf]

            self._FRAME_CACHE[cache_key] = frames

        # ส่ง frames ให้ AnimatedNode
        super().__init__(frames, frame_duration, True, *groups)

        # วางตำแหน่งกลาง effect ไว้ที่ pos ที่รับมา
        self.rect.center = pos

    # ------------------------------------------------------------
    # โหลดเฟรมจาก ResourceManager
    # ------------------------------------------------------------
    def _load_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1
        rm = self.game.resources

        while True:
            # ชื่อไฟล์รูป effect: assets/graphics/images/effects/<effect_id>_01.png ...
            rel_path = f"effects/{self.effect_id}_{index:02d}.png"
            try:
                # ได้รูปที่โดน sprite_scale จาก ResourceManager มาแล้ว
                surf = rm.load_image(rel_path)
            except Exception:
                break

            # ถ้าอยากให้ born_effect ใหญ่/เล็กกว่า sprite ปกติ
            if self._extra_scale != 1.0:
                # ใช้ helper เดิมของ ResourceManager ในการ scale
                surf = rm._scale_surface(surf, self._extra_scale)

            frames.append(surf)
            index += 1

        return frames

    # ------------------------------------------------------------
    # update
    # ------------------------------------------------------------
    def update(self, dt: float) -> None:
        # นับถอยหลัง lifetime ของ effect
        self._timer -= dt
        if self._timer <= 0.0:
            self.kill()
            return

        # ให้ AnimatedNode จัดการเปลี่ยนเฟรมตามปกติ
        super().update(dt)
