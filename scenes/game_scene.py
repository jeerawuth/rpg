# scenes/game_scene.py
from __future__ import annotations

import pygame
import pygame
from pygame import gfxdraw
import math

from .base_scene import BaseScene
from core.audio_manager import MusicCue
from entities.player_node import PlayerNode
from entities.enemy_node import EnemyNode
from entities.born_effect_node import BornEffectNode

from combat.collision_system import handle_group_vs_group
from world.level_data import load_level
from world.tilemap import TileMap
from entities.decoration_node import DecorationNode

from world.spawn_manager import SpawnManager
from core.camera import Camera
from core.message_log import MessageLog
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, UI_FONT_HUD_PATH
from entities.item_node import ItemNode

from .pause_scene import PauseScene
from .game_over_scene import GameOverScene
from .inventory_scene import InventoryScene
from items.item_database import ITEM_DB

# Projectile vs Enemies
from combat.damage_system import DamagePacket  # แค่ type hint


class GameScene(BaseScene):
    # ---------- BGM (basic) ----------
    # intro 1 ครั้ง -> เข้าเพลงลูป
    # (ไฟล์ต้องอยู่ใน assets/sounds/music/)
    MUSIC = MusicCue(intro="battle_intro_5s.wav", loop="battle_loop_30s.wav", volume=0.3, fade_ms=120, fadeout_ms=120)

    def __init__(
        self,
        game,
        level_id: str = "level01",
        inventory_data: list | None = None,
        equipment_data: dict | None = None,
        player_type: str | None = None,
    ) -> None:
        super().__init__(game)
        self.font = self.game.resources.load_font(UI_FONT_HUD_PATH, 22)


        # สถานะเกมโอเวอร์
        self.game_over_triggered = False

        # เก็บชื่อเลเวลปัจจุบัน (เอาไว้ใช้เปลี่ยนด่าน)
        self.level_id = level_id

        # สถานะเคลียร์ด่าน (ใช้สำหรับแสดงข้อความ Stage Clear ชั่วคราว)
        self.stage_clear = False
        self.stage_clear_timer = 0.0
        self.stage_clear_duration = 2.0  # ระยะเวลาที่โชว์ข้อความ Stage Clear (วินาที)

        # ---------- LEVEL / TILEMAP ----------
        self.level_data = load_level(level_id)
        self.tilemap = TileMap(self.level_data, self.game.resources)

        # ---------- SPRITE GROUPS ----------
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.items = pygame.sprite.Group()          # สำหรับไอเท็มที่วางในฉาก
        self.decorations = pygame.sprite.Group()    # ของตกแต่งฉาก (ต้นไม้ ก้อนหิน ฯลฯ)

        # ให้ object อื่นอ้างถึงได้ (ProjectileNode ฯลฯ)
        self.game.all_sprites = self.all_sprites
        self.game.enemies = self.enemies
        self.game.projectiles = self.projectiles
        self.game.decorations = self.decorations


        # ---------- PLAYER ----------
        # ถ้าไม่ได้ระบุ player_type มา ให้ใช้จาก Global State (GameApp)
        # ถ้าไม่มี Global State ให้ใช้ "knight" เป็น default
        actual_player_type = player_type
        if actual_player_type is None:
             actual_player_type = getattr(self.game, "selected_player_type", "knight")

        player_spawn = self.level_data.player_spawn
        self.player = PlayerNode(
            self.game,
            player_spawn,
            self.projectiles,
            self.all_sprites,
            inventory_data=inventory_data,
            equipment_data=equipment_data,
            player_type=actual_player_type,
        )

        # ให้ enemy / ระบบอื่น ๆ อ้างถึง player ได้ผ่าน self.game
        self.game.player = self.player

        # ---------- ENEMIES (ใช้ SpawnManager แทนการ spawn ตรง ๆ) ----------
        # SpawnManager จะอ่าน enemy_spawns จาก LevelData แล้วคอยสร้าง EnemyNode ตามเวลา
        self.spawn_manager = SpawnManager(
            self.game,
            self.level_data,
            self.enemies,
            self.all_sprites,
        )
        # โหลด asset ของศัตรูทุกชนิดในด่านนี้ล่วงหน้า
        self._preload_enemy_assets()

        # โหลด asset ของ effect ต่าง ๆ (เช่น born_effect) ล่วงหน้า
        self._preload_effect_assets()

        # ---------- ITEMS (ตาม level ที่โหลดเข้ามา) ----------
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
            

        # ---------- DECORATIONS (ของตกแต่งฉาก) ----------
        for spawn in getattr(self.level_data, "decor_spawns", []):
            pos    = tuple(spawn["pos"])
            image  = spawn["image"]
            anchor = spawn.get("anchor", "topleft")
            scale  = spawn.get("scale", 1.0)
            layer  = spawn.get("layer", "front")   # "front" | "back"

            deco = DecorationNode(
                self.game.resources,   # rm
                pos,
                image,
                anchor,
                scale,
                self.all_sprites,
                self.decorations,
            )

            # กำหนด z-index ตาม layer
            # ค่าตัวเลขนี่แล้วแต่จะดีไซน์ ผมให้ back = -10, front = +10
            if layer == "back":
                deco.z = -10
            elif layer == "front":
                deco.z = 10
            else:
                deco.z = 0

            # เก็บ layer แบบตัวหนังสือไว้ใช้เช็คต่อก็ได้
            deco.draw_layer = layer



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

        # Message Log for HUD
        self.message_log = MessageLog(max_messages=10, default_lifetime=5.0)

        # ---------- PLAYER CONTACT vs ENEMY ----------
        # ใช้ควบคุมจังหวะโดนชนไม่ให้โดนทุกเฟรม
        self.player_contact_cooldown = 0.5  # วินาทีที่กันชนซ้ำ
        self.player_contact_timer = 0.0

        # ---------- HUD INDICATORS STATE ----------
        self.latest_consumable_id: str | None = None
        self.consumable_display_timer: float = 0.0
        self.consumable_display_duration: float = 2.0  # โชว์ 2 วินาทีแล้วหายไป

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

    # ---------- Helper: preload enemy assets ----------
    def _preload_enemy_assets(self) -> None:
        """
        โหลด sprite / animation / sound ของศัตรูทุกชนิดที่ใช้ในด่านนี้ล่วงหน้า
        เพื่อลดอาการกระตุกตอนศัตรู spawn ครั้งแรกกลางเกม
        """
        # ถ้า level_data ไม่มี enemy_spawns ก็ไม่ต้องทำอะไร
        enemy_spawns = getattr(self.level_data, "enemy_spawns", None)
        if not enemy_spawns:
            return

        # รวบรวมชนิดศัตรู (enemy_id) ที่จะใช้ในด่านนี้จาก field "type"
        enemy_ids: set[str] = set()
        for spawn in enemy_spawns:
            enemy_type = spawn.get("type")
            if enemy_type:
                enemy_ids.add(enemy_type)

        if not enemy_ids:
            return

        # ใช้ group ชั่วคราว เพื่อไม่ให้ dummy enemy ไปโผล่ใน all_sprites จริง
        temp_group = pygame.sprite.Group()

        # สร้าง enemy แต่ละชนิดนอกจอหนึ่งครั้ง เพื่อให้มันโหลด asset เข้าคลัง
        for enemy_id in enemy_ids:
            try:
                dummy = EnemyNode(
                    self.game,
                    (-9999, -9999),   # spawn นอกจอ
                    temp_group,       # ใส่แค่ใน temp_group
                    enemy_id=enemy_id,
                )
                # ไม่ต้องอยู่ต่อในเกม แค่ให้ __init__ ทำงานพอ
                dummy.kill()
            except Exception as e:
                # กันพลาด ถ้า enemy_id ไหน config มีปัญหา จะไม่ทำให้เกมพังทั้งด่าน
                print(f"[WARN] preload enemy assets failed for '{enemy_id}': {e}")

    # ---------- Helper: preload effect assets ----------
    def _preload_effect_assets(self) -> None:
        """
        โหลด asset ของ BornEffectNode ล่วงหน้า
        เพื่อลดการหน่วงตอนเล่นเอฟเฟกต์เกิดศัตรูกลางเกม
        """
        # ถ้าในด่านนี้ไม่มี spawn เป็นเวลา อาจจะไม่จำเป็น
        # แต่โหลดไว้ครั้งเดียวก็ไม่เสียหายอะไร
        temp_group = pygame.sprite.Group()

        # ถ้าในโปรเจกต์คุณใช้ effect_id อื่น ให้เพิ่มในลิสต์นี้ได้เลย
        effect_ids = ["born"]

        for effect_id in effect_ids:
            try:
                # สร้าง effect นอกจอหนึ่งครั้ง เพื่อให้มันโหลดเฟรมเข้าคลัง
                dummy = BornEffectNode(
                    self.game,
                    (-9999, -9999),
                    *[temp_group],
                    effect_id=effect_id,
                    lifetime=0.01,   # สั้น ๆ ก็พอ เพราะเราจะ kill เอง
                    scale=0.5,       # ให้ตรงกับที่คุณใช้ตอน spawn จริง
                )
                dummy.kill()
            except Exception as e:
                print(f"[WARN] preload effect assets failed for '{effect_id}': {e}")
    

    # ---------- EVENTS ----------
    def handle_events(self, events) -> None:
        # ให้ AudioManager รับ event (เพื่อสลับ intro -> loop และจัดการ fade)
        self.game.audio.handle_events(events)

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


    # ============================================================
    # Collision Handling สำหรับศัตรูด้วยกันจะไม่อยู่ตำแหน่งเดียวกัน
    # ============================================================

    def _handle_enemy_separation(self) -> None:
        """
        จัดการการชนกันระหว่างศัตรู (Enemy vs Enemy) เพื่อไม่ให้เดินซ้อนกัน
        โดยใช้หลักการ Circle-to-Circle collision และผลักออกจากกัน
        """
        # ใช้ list() เพื่อสร้างสำเนาของ enemies.sprites() 
        # เพื่อหลีกเลี่ยงการแก้ไข list ระหว่างวนลูป
        enemies_list = list(self.enemies.sprites())
        
        # วนลูปตรวจสอบทุกคู่ (i, j) โดยที่ i != j และไม่ซ้ำคู่เดิม
        for i in range(len(enemies_list)):
            for j in range(i + 1, len(enemies_list)):
                enemy1: EnemyNode = enemies_list[i]
                enemy2: EnemyNode = enemies_list[j]

                # ไม่ต้องทำ separation ถ้าตัวใดตัวหนึ่งตายแล้ว
                if enemy1.is_dead or enemy2.is_dead:
                    continue

                # 1. เช็คระยะห่างระหว่างจุดศูนย์กลาง (pos)
                distance_vec = enemy1.pos - enemy2.pos
                distance_sq = distance_vec.length_squared()

                # 2. คำนวณรัศมีที่ควรห่างกัน (enemy1.radius + enemy2.radius)
                # สมมติว่าศัตรูทุกตัวใช้ radius = 20.0 (ตามที่ตั้งใน enemy_node.py)
                # ถ้าศัตรูมีขนาดไม่เท่ากัน ให้ใช้รัศมีของแต่ละตัว
                combined_radius = enemy1.radius + enemy2.radius
                combined_radius_sq = combined_radius * combined_radius

                # 3. ถ้าชนกัน (ระยะห่างน้อยกว่าผลรวมรัศมี)
                if distance_sq < combined_radius_sq and distance_sq > 0:
                    
                    # คำนวณระยะห่างจริงและระยะซ้อนทับ (overlap)
                    distance = distance_vec.length()
                    if distance == 0:
                         # ป้องกันหารด้วยศูนย์ ถ้าตำแหน่งซ้อนกันสนิท
                         # ขยับตัวใดตัวหนึ่งเล็กน้อยในทิศสุ่ม
                         distance_vec = pygame.Vector2(1, 0).rotate(pygame.time.get_ticks() % 360)
                         distance = distance_vec.length()

                    overlap = combined_radius - distance
                    
                    # 4. คำนวณทิศทางผลัก (Normalized Vector)
                    normal = distance_vec.normalize()

                    # 5. คำนวณ MTV (Minimal Translation Vector)
                    # แบ่งการผลักให้ศัตรูแต่ละตัวเท่าๆ กัน (half overlap)
                    mtv = normal * (overlap / 2.0)

                    # 6. ผลักศัตรูออกจากกัน
                    enemy1.pos += mtv
                    enemy2.pos -= mtv
                    
                    # 7. อัปเดต rect (ทำใน enemy update ก็ได้ แต่ทำซ้ำเพื่อความชัวร์)
                    enemy1.rect.center = (round(enemy1.pos.x), round(enemy1.pos.y))
                    enemy2.rect.center = (round(enemy2.pos.x), round(enemy2.pos.y))

    # ---------- UPDATE ----------
    def update(self, dt: float) -> None:
        
        # Update Consumable Display Timer
        if self.consumable_display_timer > 0:
            self.consumable_display_timer -= dt
            if self.consumable_display_timer < 0:
                self.consumable_display_timer = 0.0

        # เช็คเกมโอเวอร์
        if self.player.is_dead and not self.game_over_triggered:
            pygame.mixer.stop()
            self.game_over_triggered = True
            self.game.scene_manager.push_scene(GameOverScene(self.game, score=0))


        # ถ้าด่านถูกเคลียร์แล้ว ให้แสดงข้อความ Stage Clear ชั่วคราว
        if self.stage_clear:
            self.stage_clear_timer += dt

            # รอครบเวลาที่กำหนดแล้วค่อยเปลี่ยนไปด่านถัดไป / ฉากถัดไป
            if self.stage_clear_timer >= self.stage_clear_duration:
                # อ่าน next_level จาก level_data
                next_id = getattr(self.level_data, "next_level", "") or ""

                if next_id:
                    # มีด่านถัดไป -> โหลด GameScene ใหม่ด้วย level_id ที่ JSON บอก
                    
                    # ----------------------------------------------------
                    # [FIX] เคลียร์บัฟอาวุธชั่วคราว (เช่น sword_all_direction)
                    # เพื่อให้ equipment.main_hand กลับเป็นอาวุธหลักเดิม
                    # ----------------------------------------------------
                    if hasattr(self.player, "buff_manager") and self.player.buff_manager:
                        # clear_group จะเรียก on_remove ซึ่งจะ revert equipment ให้เอง
                        self.player.buff_manager.clear_group(self.player, "weapon_override")
                        self.player.buff_manager.clear_group(self.player, "armor_override")

                    # EXTRACT Inventory / Equipment
                    inventory_data = None
                    if hasattr(self.player, "inventory") and self.player.inventory:
                        inventory_data = self.player.inventory.slots
                    
                    equipment_data = None
                    if hasattr(self.player, "equipment") and self.player.equipment:
                        # สร้าง dict จาก Equipment dataclass หรือดึงค่าตรงๆ
                        equipment_data = {
                            "main_hand": self.player.equipment.main_hand,
                            "off_hand": self.player.equipment.off_hand,
                            "armor": self.player.equipment.armor,
                        }

                    from .game_scene import GameScene
                    self.game.scene_manager.set_scene(
                        GameScene(
                            self.game, 
                            level_id=next_id, 
                            inventory_data=inventory_data, 
                            equipment_data=equipment_data,
                            player_type=self.player.player_type
                        )
                    )
                else:
                    # ไม่มีด่านถัดไปแล้ว -> กลับ Lobby (หรือ Main Menu)
                    from .lobby_scene import LobbyScene
                    self.game.scene_manager.set_scene(LobbyScene(self.game))

            return


        # ให้ player ใช้ข้อมูลชนจาก tilemap
        self.player.set_collision_segments(self.tilemap.collision_segments)

        # <--- Tilemap Collision (Enemies) --->
        # ส่ง segment การชนให้ EnemyNode ทุกตัว
        if hasattr(self.tilemap, "collision_segments"):
            for enemy in self.enemies.sprites():
                # ตรวจสอบว่ามี method set_collision_segments ใน enemy หรือไม่
                if hasattr(enemy, "set_collision_segments"):
                    enemy.set_collision_segments(self.tilemap.collision_segments)
        
        # เก็บ rect ไว้ใช้กับอย่างอื่นด้วย
        self.player.set_collision_rects(self.tilemap.collision_rects)

        # อัปเดต sprite ทั้งหมด
        self.all_sprites.update(dt)

        # อัปเดตการ spawn ศัตรูตามเวลา / wave
        if hasattr(self, "spawn_manager"):
            self.spawn_manager.update(dt)

        # จัดการการชนระหว่างศัตรู ไม่ให้อยู่ตำแหน่งเดียวกัน
        self._handle_enemy_separation()

        # อัปเดตกล้องให้ตาม player
        self.camera.update(self.player.rect, dt)

        # Projectile vs Enemies
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
            # ให้ ItemNode ตัดสินใจก่อนว่าไอเท็มนี้ใช้ทันทีไหม
            used_instant = item_node.on_pickup(self.player)

            # ถ้ายังไม่ใช้ทันที -> เก็บเข้า inventory ตามปกติ
            if not used_instant:
                inv = getattr(self.player, "inventory", None)
                if inv is not None:
                    leftover = inv.add_item(item_node.item_id, item_node.amount)
                    if leftover < item_node.amount:
                         # เก็บได้อย่างน้อย 1 ชิ้น
                         picked_count = item_node.amount - leftover
                         # หาชื่อไอเท็ม
                         iname = getattr(item_node.item, "name", item_node.item_id)
                         self.game.add_log(f"ได้รับ {iname} x{picked_count}")

                    if leftover > 0:
                        self.game.add_log("กระเป๋าเต็ม! เก็บไอเท็มบางส่วนไม่ได้")


            # check consumable trigger
            # ถ้าเป็น consumable และถูกใช้ทันที (used_instant=True) หรือแม้แต่เก็บเข้ากระเป๋า
            # ตามโจทย์ "item_type='consumable' ให้แสดงแว็บเดียวแล้วหายไป"
            # เราจะเช็คว่าเป็น consumable หรือไม่
            if item_node.item and getattr(item_node.item, "item_type", "") == "consumable":
                 self.latest_consumable_id = item_node.item_id
                 self.consumable_display_timer = self.consumable_display_duration

            # 🔊 เล่นเสียงเก็บไอเท็ม
            if hasattr(self.player, "sfx_item_pickup"):
                self.player.sfx_item_pickup.play()
            else:
                if hasattr(self.player, "sfx_slash"):
                    self.player.sfx_slash.play()


        # ---------- Player vs Enemies (touch damage) ----------
        # ลด cooldown การโดนชน (กันไม่ให้โดนซ้ำทุกเฟรม)
        if self.player_contact_timer > 0:
            self.player_contact_timer -= dt
            if self.player_contact_timer < 0:
                self.player_contact_timer = 0.0

        # ใช้ rect collision แบบเดิม
        touch_hits = pygame.sprite.spritecollide(self.player, self.enemies, False)

        if touch_hits and self.player_contact_timer <= 0.0:
            for enemy in touch_hits:
                # กันพลาด: enemy ต้องมี stats ถึงจะใช้ระบบ damage ได้
                if not hasattr(enemy, "stats"):
                    continue

                # ให้ดาเมจคำนวณจากค่า stats.attack ของ enemy (แยกตามชนิดของ enemy)
                packet = DamagePacket(
                    base=0.0,
                    damage_type="physical",
                    scaling_attack=1.0,
                )

                # 1) player โดน damage จากศัตรูตัวนี้
                self.player.take_hit(enemy.stats, packet)

                # 2) enemy หยุดการเคลื่อนไหวชั่วคราว 0.5 วินาที
                if hasattr(enemy, "hurt_timer"):
                    # ใช้ hurt_timer ที่มีอยู่แล้วใน EnemyNode
                    enemy.hurt_timer = max(getattr(enemy, "hurt_timer", 0.0), 0.5)

                # ให้โดนจาก enemy ตัวเดียวพอในการชนครั้งนี้
                break

            # ตั้ง cooldown ไม่ให้โดนชนทุกเฟรม
            self.player_contact_timer = self.player_contact_cooldown


        # ---------- เช็คจบด่าน & เริ่มแสดง Stage Clear ----------
        # เงื่อนไข:
        # - SpawnManager spawn ศัตรูครบทุกตัวแล้ว (is_finished)
        # - ศัตรูที่ถูกสร้างออกมาทั้งหมดถูกกำจัดหมด (กลุ่ม enemies ว่าง)
        # - ยังไม่ได้อยู่ในสถานะ stage_clear
        if (
            hasattr(self, "spawn_manager")
            and getattr(self.spawn_manager, "is_finished", False)
            and len(self.enemies.sprites()) == 0
            and not self.stage_clear
        ):
            # เข้าสู่โหมดเคลียร์ด่าน: หยุดอัปเดตเกมปกติ แล้วให้บล็อกด้านบนจัดการตัวจับเวลา
            self.stage_clear = True
            self.stage_clear_timer = 0.0
            return


    # ---------- DRAW ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        offset = self.camera.offset

        # วาด tilemap ก่อน
        self.tilemap.draw(surface, camera_offset=offset)

        # วาด sprite ตาม z-index (default = 0 ถ้าไม่มี z)
        for sprite in sorted(self.all_sprites, key=lambda s: getattr(s, "z", 0)):
            draw_x = sprite.rect.x - int(offset.x)
            draw_y = sprite.rect.y - int(offset.y)
            surface.blit(sprite.image, (draw_x, draw_y))

            # ---------- วาดแถบ HP ของศัตรู ----------
            if isinstance(sprite, EnemyNode) or isinstance(sprite, PlayerNode) and not sprite.is_dead:
                ratio = sprite.hp_ratio   # ใช้ property hp_ratio ใน EnemyNode

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

        # วาดเลเยอร์ foreground (ถ้ามี) ให้อยู่หน้าตัวละคร แต่หลังพื้นหลัง
        if hasattr(self.tilemap, "draw_foreground"):
            self.tilemap.draw_foreground(surface, camera_offset=offset)


        # HUD (วาดแบบ fixed screen)
        # --- current equipment ---
        eq = getattr(self.player, "equipment", None)

        weapon_item = None
        weapon_id = None
        if eq is not None:
            if hasattr(eq, "get_item"):
                try:
                    weapon_item = eq.get_item("main_hand")
                except Exception:
                    weapon_item = None
            if weapon_item is None and hasattr(eq, "main_hand"):
                weapon_id = getattr(eq, "main_hand", None)
                if weapon_id:
                    weapon_item = ITEM_DB.try_get(str(weapon_id))

        armor_item = None
        armor_id = None
        if eq is not None:
            if hasattr(eq, "get_item"):
                try:
                    armor_item = eq.get_item("armor")
                except Exception:
                    armor_item = None
            if armor_item is None and hasattr(eq, "armor"):
                armor_id = getattr(eq, "armor", None)
                if armor_id:
                    armor_item = ITEM_DB.try_get(str(armor_id))

        weapon_name = getattr(weapon_item, "name", None) or (str(weapon_id) if weapon_id else "-")
        armor_name = getattr(armor_item, "name", None) or (str(armor_id) if armor_id else "-")

        # --- HUD แบ่ง 2 ฝั่ง ---
        
        # 1. มุมขวาบน (HP + Enemies)
        hp_val = int(self.player.stats.hp)
        max_hp_val = int(self.player.stats.max_hp)
        hp_text = f"ระดับพลังชีวิต: {hp_val}/{max_hp_val}"
        
        # ถ้า HP < 25 ให้ตัวหนังสือสีแดง
        if hp_val < 25:
            line_hp_entry = (hp_text, (255, 50, 50))
        else:
            line_hp_entry = hp_text

        lines_right = [
            line_hp_entry,
            f"จำนวนศัตรู: {len(self.enemies.sprites())}",
        ]
        
        # คำนวณความกว้างเพื่อจัดชิดขวา
        max_w = 0
        for line in lines_right:
            # support tuple
            txt = line[0] if isinstance(line, tuple) else line
            w = self.font.size(txt)[0]
            if w > max_w:
                max_w = w
        
        padding = 10
        panel_w = max_w + (padding * 2)
        top_right_x = SCREEN_WIDTH - panel_w - 16
        
        self.draw_text_block(
            surface,
            lines_right,
            (top_right_x, 16),
            self.font,
            padding=padding,
            line_gap=4,
            panel_alpha=self.HUD_BG_ALPHA,
            text_color=self.HUD_TEXT_COLOR,
            shadow=True,
        )

        # 2. มุมซ้ายบน (Weapon + Armor) - ซ่อนถ้าไม่มี
        lines_left = []
        if weapon_name and weapon_name != "-":
             lines_left.append(f"อาวุธ: {weapon_name}")
        if armor_name and armor_name != "-":
             lines_left.append(f"เกราะ: {armor_name}")
        
        if lines_left:
            self.draw_text_block(
                surface,
                lines_left,
                (16, 16),
                self.font,
                padding=padding,
                line_gap=4,
                panel_alpha=self.HUD_BG_ALPHA,
                text_color=self.HUD_TEXT_COLOR,
                shadow=True,
            )

        # ---------- Draw Message Log (Top Center) ----------
        log_msgs = self.message_log.get_messages()
        if log_msgs:
            # 1. คำนวณความกว้างข้อความที่ยาวที่สุด
            max_w = 0
            for msg in log_msgs:
                w = self.font.size(msg)[0]
                if w > max_w:
                    max_w = w
            
            # 2. คำนวณตำแหน่ง X ให้กึ่งกลาง
            padding = 10
            panel_w = max_w + padding * 2
            center_x = SCREEN_WIDTH // 2
            start_x = center_x - (panel_w // 2)

            self.draw_text_block(
                surface,
                log_msgs,
                (start_x, 10),  # y=10 (top)
                self.font,
                padding=padding,
                line_gap=4,
                panel_alpha=self.HUD_BG_ALPHA,  # หรือปรับให้เข้มขึ้นถ้าต้องการ
                text_color=self.HUD_TEXT_COLOR,
                shadow=True
            )


# ถ้าอยู่ในสถานะเคลียร์ด่าน ให้แสดงข้อความ Stage Clear กลางจอ
        if self.stage_clear:
            # ทำ overlay ทึบเล็กน้อย
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            surface.blit(overlay, (0, 0))

            text = "STAGE CLEAR"
            text_surf = self.font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(
                center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),
            )
            surface.blit(text_surf, text_rect)

        # ----------------------------------------------------
        # [NEW] Multi-Slot Active Item Indicators (Bottom Right)
        # ----------------------------------------------------
        self.draw_hud_indicators(surface)

    def _draw_circular_indicator(self, surface: pygame.Surface, 
                                 item_id: str, 
                                 center_x: int, center_y: int, 
                                 radius: int, 
                                 ratio: float = 1.0, 
                                 fade_alpha: int = 255) -> None:
        """
        Helper วาดวงกลม 1 วง (Weapon / Armor / Consumable)
        ratio: 0.0 - 1.0 (สำหรับ Cooldown Overlay), ถ้าเป็น Consumable อาจจะไม่ใช้ overlay ก็ส่ง 1.0
        fade_alpha: 0 - 255 (สำหรับ Consumable ที่จะค่อยๆ จาง)
        """
        # 1. Prepare Item Icon
        item = ITEM_DB.try_get(item_id)
        icon_surf = None
        if item and item.ui_icon_key:
            try:
                # scale_override=1.0 เพื่อให้ได้ขนาดตามไฟล์จริง
                icon_surf = self.game.resources.load_image(item.ui_icon_key, scale_override=1.0)
            except Exception:
                pass
        
        if icon_surf is None:
            return

        # สร้าง surface ชั่วคราวสำหรับวงกลมนี้ เพื่อรองรับ fade_alpha
        # ขนาดเผื่อขอบนิดหน่อย
        size = radius * 2
        temp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Local Coordinates on temp_surf
        lc_radius = radius
        lc_center = radius # (radius, radius)

        # A. Background Circle (ดำโปร่งแสง)
        gfxdraw.filled_circle(temp_surf, lc_center, lc_center, lc_radius, (0, 0, 0, 100))
        gfxdraw.aacircle(temp_surf, lc_center, lc_center, lc_radius, (0, 0, 0, 100))

        # B. Icon
        icon_size = int(lc_radius * 2 * 0.7)
        scaled_icon = pygame.transform.smoothscale(icon_surf, (icon_size, icon_size))
        icon_rect = scaled_icon.get_rect(center=(lc_center, lc_center))
        temp_surf.blit(scaled_icon, icon_rect)

        # C. Cooldown Overlay (Radial Wipe)
        # ถ้า ratio < 1.0 แสดงว่ามีการนับถอยหลัง
        if ratio < 1.0:
            filled_percent = 1.0 - ratio
            if filled_percent > 0:
                overlay_surf = pygame.Surface((size, size), pygame.SRCALPHA)
                
                start_angle = -90
                end_angle = start_angle + (filled_percent * 360)
                
                points = [(lc_center, lc_center)]
                step = 5
                i_start = int(start_angle)
                i_end = int(end_angle)
                
                for deg in range(i_start, i_end + step, step):
                    draw_deg = deg
                    if draw_deg > end_angle:
                        draw_deg = end_angle
                    
                    rad = math.radians(draw_deg)
                    px = lc_radius + lc_radius * math.cos(rad)
                    py = lc_radius + lc_radius * math.sin(rad)
                    points.append((px, py))
                
                if len(points) > 2:
                    pygame.draw.polygon(overlay_surf, (0, 0, 0, 100), points)
                
                temp_surf.blit(overlay_surf, (0, 0))

        # Apply Global Alpha (for Consumable fade out)
        if fade_alpha < 255:
            # ใช้ special_flags เพื่อลด alpha ทั้งผืน
            # แต่วิธีง่ายกว่าคือ set_alpha ทั้ง surface ก่อน blit ลงจอ
            temp_surf.set_alpha(fade_alpha)

        # Blit to Main Surface
        surface.blit(temp_surf, (center_x - radius, center_y - radius))

    def draw_hud_indicators(self, surface: pygame.Surface) -> None:
        """
        วาด Indicator แยก 3 วง:
        1. Weapon (ขวาสุด) - Persistent Buff
        2. Armor (ถัดมา) - Persistent Buff
        3. Consumable (ถัดมาอีก/ด้านบน) - Show briefly then vanish
        """
        bm = getattr(self.player, "buff_manager", None)
        
        # --- 1. Find Active Weapon & Armor Buffs ---
        weapon_buff = None
        armor_buff = None

        if bm is not None and hasattr(bm, "effects"):
            for eff in bm.effects:
                if eff.remaining <= 0:
                    continue
                
                spec = getattr(eff, "spec", None)
                eid = str(getattr(spec, "id", ""))
                group = str(getattr(spec, "group", ""))
                
                # Check Type
                item_id = None
                if ":" in eid:
                    _, item_id = eid.split(":", 1)
                else:
                    item_id = eid
                
                # เช็คจาก item_db ว่าเป็น weapon หรือ armor
                item = ITEM_DB.try_get(item_id)
                itype = getattr(item, "item_type", "unknown")
                
                # Assign to slots (Priority: Last applied usually found later in list, 
                # but logic loop depends on complexity. Here we just take first match for simplicity 
                # OR we can strictly look for group names if defined.)
                
                is_weapon = (itype == "weapon") or group == "weapon_override" or eid.startswith("weapon_override")
                is_armor = (itype == "armor") or group == "armor_override" or eid.startswith("armor_override")
                
                if is_weapon and weapon_buff is None: 
                    weapon_buff = eff
                elif is_armor and armor_buff is None:
                    armor_buff = eff
        
        # --- Config & Positions (Equidistant Arc) ---
        radius = 30
        arc_radius = 160  # Distance from bottom-right corner (Increased from 130 to fix overlap)
        
        # Center of the arc is the bottom-right corner of the screen
        base_x = SCREEN_WIDTH
        base_y = SCREEN_HEIGHT
        
        # Calculate positions using polar coordinates
        # Angles: -110 (Weapon), -135 (Armor), -160 (Consumable)
        # 0 deg = Right, -90 deg = Up
        
        def get_arc_pos(angle_deg: float) -> tuple[int, int]:
            rad = math.radians(angle_deg)
            px = base_x + arc_radius * math.cos(rad)
            py = base_y + arc_radius * math.sin(rad)
            return int(px), int(py)

        # Slot 1: Weapon (Middle)
        x_weapon, y_weapon = get_arc_pos(-135)
        
        # Slot 2: Armor (Right-most in the arc)
        x_armor, y_armor = get_arc_pos(-110)
        
        # Slot 3: Consumable (Bottom-most in the arc)
        x_consumable, y_consumable = get_arc_pos(-160)

        # --- Draw Weapon Slot ---
        if weapon_buff:
            remaining = weapon_buff.remaining
            total = float(getattr(weapon_buff.spec, "duration", 1.0))
            ratio = max(0.0, min(1.0, remaining / total)) if total > 0 else 0.0
            
            # Extract ID
            eid = str(getattr(weapon_buff.spec, "id", ""))
            real_id = eid.split(":", 1)[1] if ":" in eid else eid
            
            self._draw_circular_indicator(surface, real_id, x_weapon, y_weapon, radius, ratio=ratio)

        # --- Draw Armor Slot ---
        if armor_buff:
            remaining = armor_buff.remaining
            total = float(getattr(armor_buff.spec, "duration", 1.0))
            ratio = max(0.0, min(1.0, remaining / total)) if total > 0 else 0.0
            
            eid = str(getattr(armor_buff.spec, "id", ""))
            real_id = eid.split(":", 1)[1] if ":" in eid else eid
            
            self._draw_circular_indicator(surface, real_id, x_armor, y_armor, radius, ratio=ratio)

        # --- Draw Consumable Slot ---
        if self.consumable_display_timer > 0 and self.latest_consumable_id:
            alpha = 255
            fade_start = 0.5 # start fading when 0.5s left
            
            if self.consumable_display_timer < fade_start:
                alpha = int((self.consumable_display_timer / fade_start) * 255)
            
            self._draw_circular_indicator(surface, 
                                          self.latest_consumable_id, 
                                          x_consumable, y_consumable, 
                                          radius, 
                                          ratio=1.0, # No cooldown wipe for consumable
                                          fade_alpha=alpha)