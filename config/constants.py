# config/constants.py
# ค่าคงที่/อีเวนต์ภายในเกม

import pygame

# Custom pygame events
EV_PLAYER_DIED = pygame.USEREVENT + 1
EV_ITEM_PICKED = pygame.USEREVENT + 2
EV_MATCH_STARTED = pygame.USEREVENT + 3
EV_MATCH_ENDED = pygame.USEREVENT + 4

EV_SCENE_CHANGE = pygame.USEREVENT + 10

# Key mapping พื้นฐาน (จะไปผูกกับ input manager ทีหลังก็ได้)
KEY_BINDINGS = {
    "up": pygame.K_w,
    "down": pygame.K_s,
    "left": pygame.K_a,
    "right": pygame.K_d,
    "attack": pygame.K_SPACE,
    "spell": pygame.K_q,
    "inventory": pygame.K_i,
    "pause": pygame.K_ESCAPE,
}
