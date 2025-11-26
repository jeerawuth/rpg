# combat/collision_system.py
from __future__ import annotations

import pygame
from typing import Callable

Sprite = pygame.sprite.Sprite
Group = pygame.sprite.Group


def handle_group_vs_group(
    attackers: Group,
    targets: Group,
    on_hit: Callable[[Sprite, Sprite], None],
    kill_attack_on_hit: bool = False,
) -> None:
    """
    ตรวจชนระหว่าง attackers vs targets
    - on_hit(attack_sprite, target_sprite) จะถูกเรียกทุกคู่ที่ชนกัน
    - kill_attack_on_hit=True จะ kill projectile/weapon ที่ตีโดนแล้ว (เหมาะกับ projectile ทั่วไป)
    """
    for attacker in attackers.sprites():
        collided = pygame.sprite.spritecollide(attacker, targets, False)
        if not collided:
            continue

        for target in collided:
            on_hit(attacker, target)

        if kill_attack_on_hit:
            attacker.kill()
