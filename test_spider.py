import pygame
import os
import sys

# Ensure we can import from current directory
sys.path.append(os.getcwd())

from core.resource_manager import ResourceManager

try:
    pygame.init()
    pygame.display.set_mode((100, 100))
    
    # Mock settings
    rm = ResourceManager(
        base_path="assets",
        sprite_scale=0.25
    )
    
    path = "enemy/spider/idle/idle_down_01.png"
    print(f"Testing ResourceManager load: {path}")
    
    # Test loading with default scale (None passed)
    img = rm.load_image(path, scale_override=None)
    print(f"Load success! Size: {img.get_size()}")
    
    # Test loading with explicit scale fallback check
    print("Testing cache key logic...")
    img2 = rm.load_image(path, scale_override=None)
    print(f"Load 2 success! Size: {img2.get_size()}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
