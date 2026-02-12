# entities/animated_node.py
from __future__ import annotations

from typing import List
import pygame

from .node_base import NodeBase


class AnimatedNode(NodeBase):
    """
    NodeBase แบบที่รองรับแอนิเมชันจาก list ของเฟรม (Surface)
    - ใช้เวลา dt ในการอัปเดตเฟรม
    - รองรับ loop / non-loop
    """

    def __init__(
        self,
        frames: List[pygame.Surface],
        frame_duration: float = 0.1,
        loop: bool = True,
        *groups,
    ) -> None:
        super().__init__(*groups)

        if not frames:
            raise ValueError("AnimatedNode ต้องมี frames อย่างน้อย 1 รูป")

        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop

        self._time_accumulator = 0.0
        self._frame_index = 0
        self.finished = False  # ถ้าไม่ loop แล้วเล่นจบ จะเป็น True

        self.image = self.frames[0]
        self.rect = self.image.get_rect()

    # ---------- การเปลี่ยนเซ็ตเฟรม ----------
    def set_frames(
        self,
        frames: List[pygame.Surface],
        *,
        frame_duration: float | None = None,
        loop: bool | None = None,
        reset: bool = True,
    ) -> None:
        """
        ใช้เปลี่ยน animation ทั้งชุด เช่น จาก idle → walk

        reset = True    : รีเซ็ตกลับเฟรม 0 เสมอ
        reset = False   : พยายามรักษา index เดิม แต่ถ้าเกินความยาวใหม่
                         จะถูก clamp กลับมาให้อยู่ในช่วง
        """
        if not frames:
            raise ValueError("set_frames() ต้องการ frames อย่างน้อย 1 รูป")

        self.frames = frames

        if frame_duration is not None:
            self.frame_duration = frame_duration
        if loop is not None:
            self.loop = loop

        if reset:
            self._frame_index = 0
            self._time_accumulator = 0.0
            self.finished = False
        else:
            # ถ้า index เดิมเลยขนาดเฟรมใหม่ ให้ clamp กลับมา
            if self._frame_index >= len(self.frames):
                self._frame_index = len(self.frames) - 1
            if self._frame_index < 0:
                self._frame_index = 0

        # รักษาตำแหน่งเดิมของ rect ถ้ามีแล้ว
        try:
            center = self.rect.center
        except AttributeError:
            center = self.frames[0].get_rect().center

        self.image = self.frames[self._frame_index]
        self.rect = self.image.get_rect(center=center)

    # ---------- การอัปเดตเฟรม ----------
    def _update_animation(self, dt: float) -> None:
        if self.finished:
            return

        # Special Case: Single frame
        if len(self.frames) <= 1:
             self._time_accumulator += dt
             if self._time_accumulator >= self.frame_duration:
                 if not self.loop:
                     self.finished = True
                 else:
                     self._time_accumulator %= self.frame_duration
             return

        self._time_accumulator += dt

        # เลื่อนเฟรมตามเวลา (รองรับ dt ใหญ่กว่าหนึ่งเฟรม)
        while self._time_accumulator >= self.frame_duration:
            self._time_accumulator -= self.frame_duration
            self._frame_index += 1

            if self._frame_index >= len(self.frames):
                if self.loop:
                    self._frame_index = 0
                else:
                    self._frame_index = len(self.frames) - 1
                    self.finished = True
                    break

        try:
            center = self.rect.center
        except AttributeError:
            center = self.frames[0].get_rect().center

        self.image = self.frames[self._frame_index]
        self.rect = self.image.get_rect(center=center)

    # ---------- override update ----------
    def update(self, dt: float) -> None:
        """
        ถ้า subclass จะเขียน logic เพิ่ม แนะนำให้:
            def update(self, dt):
                # logic การเคลื่อนที่ ฯลฯ
                ...
                # เรียก super().update(dt) เพื่ออัปเดตเฟรม
                super().update(dt)
        """
        self._update_animation(dt)
