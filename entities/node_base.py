# entities/node_base.py
import pygame


class NodeBase(pygame.sprite.Sprite):
    """
    base class ของทุก entity ในเกม
    - มี image + rect พื้นฐาน
    - รองรับการอัปเดตด้วย dt
    """

    def __init__(self, *groups) -> None:
        super().__init__(*groups)
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self.image.fill((255, 0, 255))  # debug magenta
        self.rect = self.image.get_rect()

    def update(self, dt: float) -> None:
        """override ใน subclass ตามต้องการ"""
        pass
