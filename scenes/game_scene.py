# scenes/game_scene.py
from __future__ import annotations

import pygame

from .base_scene import BaseScene
from entities.player_node import PlayerNode
from entities.enemy_node import EnemyNode
from combat.collision_system import handle_group_vs_group
from world.level_data import load_level
from world.tilemap import TileMap
from core.camera import Camera
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from entities.item_node import ItemNode

from .pause_scene import PauseScene
from .inventory_scene import InventoryScene

# Projectile vs Enemies
from combat.damage_system import DamagePacket  # แค่ type hint


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
        self.items = pygame.sprite.Group()          # สำหรับไอเท็มที่วางในฉาก

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

        # ---------- ITEMS (ตัวอย่าง: ไอเท็มเพิ่มพลังธนู) ----------
        # สมมติ item_id ในฐานข้อมูลคือ "bow_power_1"
        ItemNode(
            self.game,
            (self.player.rect.centerx + 64, self.player.rect.centery),
            "bow_power_1",        # item_id ต้องมีอยู่ใน ITEM_DB
            1,                    # จำนวน
            self.all_sprites,
            self.items,
        )

        # ---------- CAMERA ----------
        self.camera = Camera(
            world_width=self.tilemap.pixel_width,
            world_height=self.tilemap.pixel_height,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
            follow_speed=8.0,                   # ใช้ตัวนี้แทน smooth_factor
            deadzone_width=SCREEN_WIDTH // 2,   # กึ่งกลางจอ
            deadzone_height=SCREEN_HEIGHT // 2,
        )

    # ---------- EVENTS ----------
    def handle_events(self, events) -> None:
        

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
        # ถ้าคุณใช้ collisionRect จาก tilemap
        self.player.set_collision_rects(self.tilemap.collision_rects)

        self.all_sprites.update(dt)

        # อัปเดตกล้องให้ตาม player
        self.camera.update(self.player.rect, dt)

        

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
        
        # Player vs Items (pickup)
        hits = pygame.sprite.spritecollide(self.player, self.items, dokill=True)

        for item_node in hits:
            inv = getattr(self.player, "inventory", None)
            if inv is None:
                # ถ้า player ยังไม่มีระบบ inventory ก็แค่ลบ item ออกไปเฉย ๆ
                continue

            leftover = inv.add_item(item_node.item_id, item_node.amount)

            if leftover > 0:
                # ถ้าเก็บไม่หมด (กระเป๋าเต็ม) จะทำยังไงต่อ อยู่ที่ดีไซน์คุณ
                # ตัวอย่าง: spawn item กลับลงพื้นใหม่
                print("Inventory full! ไอเท็มบางส่วนเก็บไม่เข้า")
                # ถ้าอยาก drop กลับลงพื้นจริง ๆ:
                # ItemNode(self.game, item_node.rect.center, item_node.item_id, leftover,
                #          self.all_sprites, self.items)


    # ---------- DRAW ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        offset = self.camera.offset

        # วาด tilemap ตาม offset
        self.tilemap.draw(surface, camera_offset=offset)

        # วาด sprite โดยเลื่อนตาม offset (แทนการใช้ self.all_sprites.draw(surface) ตรง ๆ)
        for sprite in self.all_sprites:
            draw_x = sprite.rect.x - int(offset.x)
            draw_y = sprite.rect.y - int(offset.y)
            surface.blit(sprite.image, (draw_x, draw_y))

        # HUD (วาดแบบ fixed screen, ไม่ต้องใช้ offset)
        lines = [
            "Game Scene (Camera + Tilemap + Combat)",
            "WASD - Move | SPACE - Shoot | I - Inventory",
            f"Player HP: {int(self.player.stats.hp)}/{int(self.player.stats.max_hp)}",
            f"Enemies: {len(self.enemies.sprites())}",
        ]
        for i, t in enumerate(lines):
            t_surf = self.font.render(t, True, (10, 10, 10))
            surface.blit(t_surf, (20, 20 + i * 24))
