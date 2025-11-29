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
        
        # ให้ enemy / ระบบอื่น ๆ อ้างถึง player ได้ผ่าน self.game
        self.game.player = self.player

        # ---------- ENEMIES ----------
        for spawn in self.level_data.enemy_spawns:
            enemy_type = spawn["type"]          # "goblin" หรือ "slime_green"
            pos = tuple(spawn["pos"])           # [x, y] -> (x, y)

            EnemyNode(
                self.game,
                pos,
                self.all_sprites,
                self.enemies,
                enemy_id=enemy_type,            # ให้ไป lookup ใน enemy_config.py
            )


        # ---------- ITEMS (ตาม level ที่่โหลดเข้ามา) ----------
        for spawn in self.level_data.item_spawns:
            pos = tuple(spawn["pos"])          # [x, y] -> (x, y)
            item_id = spawn["item_id"]
            amount = spawn.get("amount", 1)

            ItemNode(
                self.game,
                pos,
                item_id,
                amount,
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

    
    # ---------- Helper: เลือกสีแท่ง HP ตามสัดส่วน ----------
    def _get_hp_color(self, ratio: float) -> tuple[int, int, int]:
        """
        ratio: 0.0 (ตาย/ไม่มีเลือด) -> 1.0 (เต็มหลอด)
        ไล่สี: เขียว (1.0) -> เหลือง (0.5) -> แดง (0.0)
        """
        ratio = max(0.0, min(1.0, ratio))

        if ratio > 0.5:
            # โซนบน: เขียว (0,255,0) -> เหลือง (255,255,0)
            # ratio=1.0 => t=1 => (0,255,0)
            # ratio=0.5 => t=0 => (255,255,0)
            t = (ratio - 0.5) / 0.5  # 0 ที่ 0.5, 1 ที่ 1.0
            r = int(255 * (1.0 - t))  # 255 -> 0
            g = 255
        else:
            # โซนล่าง: เหลือง (255,255,0) -> แดง (255,0,0)
            # ratio=0.5 => t=1 => (255,255,0)
            # ratio=0.0 => t=0 => (255,0,0)
            t = ratio / 0.5  # 0 ที่ 0.0, 1 ที่ 0.5
            r = 255
            g = int(255 * t)  # 0 -> 255
        b = 0
        return (r, g, b)


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
                continue

            leftover = inv.add_item(item_node.item_id, item_node.amount)

            # 🔊 เล่นเสียงเก็บไอเท็ม (ใช้ slash.wav ร่วมกัน)
            if hasattr(self.player, "sfx_item_pickup"):
                self.player.sfx_item_pickup.play()
            else:
                # กันเหนียว ถ้าไม่มี ให้ลองใช้สกิลฟันแทน
                if hasattr(self.player, "sfx_slash"):
                    self.player.sfx_slash.play()

            if leftover > 0:
                print("Inventory full! ไอเท็มบางส่วนเก็บไม่เข้า")


    # ---------- DRAW ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        offset = self.camera.offset

        # วาด tilemap ตาม offset
        self.tilemap.draw(surface, camera_offset=offset)

        # วาด sprite โดยเลื่อนตาม offset
        for sprite in self.all_sprites:
            draw_x = sprite.rect.x - int(offset.x)
            draw_y = sprite.rect.y - int(offset.y)
            surface.blit(sprite.image, (draw_x, draw_y))

            # ---------- วาดแถบ HP ของศัตรู ----------
            if isinstance(sprite, EnemyNode) and not sprite.is_dead:
                ratio = sprite.hp_ratio   # ใช้ property ที่เราเพิ่มเมื่อกี้

                # ขนาดแท่ง HP (สั้นกว่าตัว 50%)
                full_width = sprite.rect.width
                bar_width = int(full_width * 0.5)
                bar_height = 3

                # ตำแหน่งวาด: เหนือหัวศัตรูนิดหน่อย + จัดให้อยู่กลางหัว
                bar_x = draw_x + (full_width - bar_width) // 2
                bar_y = draw_y - 4  # ปรับขึ้น/ลงตามที่ชอบ

                # พื้นหลังแท่ง (เทาเข้ม)
                bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
                pygame.draw.rect(surface, (40, 40, 40), bg_rect)

                # ความยาวตาม % HP
                hp_width = int(bar_width * ratio)
                hp_color = self._get_hp_color(ratio)

                hp_rect = pygame.Rect(bar_x, bar_y, hp_width, bar_height)
                pygame.draw.rect(surface, hp_color, hp_rect)


        # HUD (วาดแบบ fixed screen)
        lines = [
            "Game Scene (Camera + Tilemap + Combat)",
            "WASD - Move | SPACE - Attack | I - Inventory",
            f"Player HP: {int(self.player.stats.hp)}/{int(self.player.stats.max_hp)}",
            f"Enemies: {len(self.enemies.sprites())}",
        ]
        for i, t in enumerate(lines):
            t_surf = self.font.render(t, True, (10, 10, 10))
            surface.blit(t_surf, (20, 20 + i * 24))

