import pygame
import os
import sys

sys.path.append(os.getcwd())

from core.resource_manager import ResourceManager
from entities.enemy_node import EnemyNode
from config.enemy_config import ENEMY_CONFIG
from combat.damage_system import Stats

class MockGame:
    def __init__(self):
        self.resources = ResourceManager(base_path="assets", sprite_scale=0.25)
        self.all_sprites = pygame.sprite.Group()

try:
    pygame.init()
    pygame.display.set_mode((100, 100))
    
    game = MockGame()
    
    print(" Instantiating EnemyNode(spider)...")
    enemy = EnemyNode(game, (0, 0), enemy_id="spider")
    
    print(f"Enemy sprite_id: {enemy.sprite_id}")
    print(f"Animations keys: {list(enemy.animations.keys())}")
    
    if not enemy.animations:
        print("ERROR: No animations loaded!")
    else:
        print(f"Success! Loaded {len(enemy.animations)} sequences.")
        if ("idle", "down") in enemy.animations:
            print("idle_down loaded.")
            print(f"Frame size: {enemy.animations[('idle', 'down')][0].get_size()}")
        else:
            print("idle_down NOT loaded.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
