# entities/node_base.py
import pygame


class NodeBase(pygame.sprite.Sprite):
    def __init__(self, *groups) -> None:
        super().__init__(*groups)
        self.image = pygame.Surface((32, 32))
        self.image.fill((255, 0, 255))  # debug magenta
        self.rect = self.image.get_rect()
