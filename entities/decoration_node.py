# entities/decoration_node.py
from __future__ import annotations

from typing import Literal, Tuple
import pygame

from .node_base import NodeBase
from core.resource_manager import ResourceManager

AnchorType = Literal["topleft", "center", "midbottom"]


class DecorationNode(NodeBase):
    """
    Node สำหรับของตกแต่งฉาก เช่น ต้นไม้ ก้อนหิน ฯลฯ
    - ไม่เคลื่อนที่
    - ไม่ชนอะไร (ใช้แค่สำหรับวาด)
    """
    def __init__(
        self,
        rm: ResourceManager,
        pos: Tuple[int, int],
        image_path: str,
        anchor: AnchorType = "topleft",
        scale: float = 1.0,
        *groups,
    ) -> None:
        super().__init__(*groups)

        # โหลดรูป
        self.image = rm.load_image(image_path)

        # scale ตามที่อ่านจาก JSON (เพิ่มจาก sprite_scale เดิม)
        if scale != 1.0:
            w, h = self.image.get_size()
            new_size = (int(w * scale), int(h * scale))
            if new_size[0] > 0 and new_size[1] > 0:
                self.image = pygame.transform.smoothscale(self.image, new_size)

        # ตั้ง rect ตาม anchor
        self._set_rect_by_anchor(pos, anchor)

    def _set_rect_by_anchor(self, pos: Tuple[int, int], anchor: AnchorType) -> None:
        self.rect = self.image.get_rect()

        if anchor == "center":
            self.rect.center = pos
        elif anchor == "midbottom":
            self.rect.midbottom = pos
        else:
            self.rect.topleft = pos
