# scenes/game_scene.py
from __future__ import annotations

import pygame

from .base_scene import BaseScene
from entities.player_node import PlayerNode
from entities.enemy_node import EnemyNode
from combat.collision_system import handle_group_vs_group
from world.level_data import load_level
from world.tilemap import TileMap


class GameScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = pygame.font.Font(None, 32)

        # ---------- LEVEL / TILEMAP ----------
        self.level_data = load_level("level01")
        self.tilemap = TileMap(self.level_data, self.game.resources)

        # ---------- SPRITE GROUPS ----------
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()

        # ให้ object อื่นอ้างถึงได้ (ProjectileNode ฯลฯ)
        self.game.all_sprites = self.all_sprites
        self.game.enemies = self.enemies
        self.game.projectiles = self.projectiles

        # ---------- PLAYER ----------
        player_spawn = self.level_data.player_spawn
        self.player = PlayerNode(
            self.game,
            player_spawn,
            self.projectiles,
            self.all_sprites,
        )

        # ---------- ENEMIES ----------
        for pos in self.level_data.enemy_spawns:
            EnemyNode(self.game, pos, self.all_sprites, self.enemies)

    # ---------- EVENTS ----------
    def handle_events(self, events) -> None:
        from .pause_scene import PauseScene
        from .inventory_scene import InventoryScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.scene_manager.push_scene(PauseScene(self.game))
                elif event.key == pygame.K_i:
                    self.game.scene_manager.push_scene(
                        InventoryScene(self.game, self.player)
                    )
                elif event.key == pygame.K_SPACE:
                    self.player.shoot()

    # ---------- UPDATE ----------
    def update(self, dt: float) -> None:
        # ส่งกำแพงจาก tilemap ให้ player ใช้ชน
        self.player.set_collision_rects(self.tilemap.collision_rects)

        self.all_sprites.update(dt)

        # Projectile vs Enemies
        from combat.damage_system import DamagePacket  # แค่ type hint

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
        surface.fill((0, 0, 0))

        # วาด tilemap
        self.tilemap.draw(surface)

        # วาด entity
        self.all_sprites.draw(surface)

        # HUD
        lines = [
            "Game Scene (Tilemap + Combat + Collision)",
            "WASD - Move | SPACE - Shoot | I - Inventory",
            f"Player HP: {int(self.player.stats.hp)}/{int(self.player.stats.max_hp)}",
            f"Enemies: {len(self.enemies.sprites())}",
        ]
        for i, t in enumerate(lines):
            t_surf = self.font.render(t, True, (10, 10, 10))
            surface.blit(t_surf, (20, 20 + i * 24))
