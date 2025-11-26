# scenes/game_scene.py
from __future__ import annotations

import pygame

from .base_scene import BaseScene
from entities.player_node import PlayerNode
from entities.enemy_node import EnemyNode
from combat.collision_system import handle_group_vs_group


class GameScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = pygame.font.Font(None, 32)

        # --- Sprite groups ---
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()

        # expose ให้ player ใช้ใน shoot()
        self.game.all_sprites = self.all_sprites
        self.game.enemies = self.enemies
        self.game.projectiles = self.projectiles

        # --- Player & Enemy ตัวอย่าง ---
        self.player = PlayerNode(
            self.game,          # game
            (400, 300),         # pos
            self.projectiles,   # projectile_group
            self.all_sprites,   # *groups
        )

        # สร้าง enemy สัก 2 ตัว
        EnemyNode(self.game, (700, 260), self.all_sprites, self.enemies)
        EnemyNode(self.game, (700, 340), self.all_sprites, self.enemies)

    # ---------- EVENTS ----------
    def handle_events(self, events) -> None:
        from .pause_scene import PauseScene
        from .inventory_scene import InventoryScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.scene_manager.push_scene(PauseScene(self.game))
                elif event.key == pygame.K_i:
                    # ✅ ส่ง player เข้า InventoryScene ด้วย
                    self.game.scene_manager.push_scene(InventoryScene(self.game, self.player))
                elif event.key == pygame.K_SPACE:
                    # ยิง
                    self.player.shoot()


    # ---------- UPDATE ----------
    def update(self, dt: float) -> None:
        self.all_sprites.update(dt)

        # ตรวจชน projectile vs enemies
        from combat.damage_system import DamagePacket  # ใช้แค่เป็น type hint

        def on_projectile_hit(projectile, enemy):
            if not hasattr(enemy, "take_hit"):
                return
            packet: DamagePacket = projectile.damage_packet
            enemy.take_hit(projectile.owner.stats, packet)

        handle_group_vs_group(
            attackers=self.projectiles,
            targets=self.enemies,
            on_hit=on_projectile_hit,
            kill_attack_on_hit=True,
        )

    # ---------- DRAW ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 100, 50))
        self.all_sprites.draw(surface)

        # HUD เล็กน้อย
        lines = [
            "Game Scene (Combat Demo)",
            "WASD - Move | SPACE - Shoot",
            f"Player HP: {int(self.player.stats.hp)}/{int(self.player.stats.max_hp)}",
            f"Enemies: {len(self.enemies.sprites())}",
        ]
        for i, t in enumerate(lines):
            t_surf = self.font.render(t, True, (10, 10, 10))
            surface.blit(t_surf, (20, 20 + i * 24))
