# scenes/preload_scene.py
# หน้าโหลด (Pre Loading Scene) เพื่อป้องกัน user คิดว่าเกมค้างตอนโหลดทรัพยากรครั้งแรก

from __future__ import annotations

import pygame
from typing import Callable, Optional

from .base_scene import BaseScene
from world.level_data import load_level
from world.tilemap import TileMap
from entities.enemy_node import EnemyNode
from entities.born_effect_node import BornEffectNode
from entities.slash_effect_node import SlashEffectNode
from entities.sword_slash_arc_node import SwordSlashArcNode


class PreloadScene(BaseScene):
    """
    โหลดทรัพยากรทีละนิดในแต่ละเฟรม (ไม่ block main loop)
    - ใช้เพื่อ warm up cache ของ ResourceManager (images/sounds/fonts) รอบแรกบน macOS
    - พอโหลดเสร็จแล้วค่อยเปลี่ยนไป scene ถัดไป (เช่น GameScene)
    """

    OVERRIDE_MUSIC = False  # ไม่อยากให้ _sync_music ไปโหลดเพลงหนัก ๆ ระหว่างโหลด

    def __init__(
        self,
        game,
        *,
        level_id: str = "level01",
        next_scene_factory: Callable[[], BaseScene],
        items_per_frame: int = 2,
        title: str = "Loading...",
        note: str = "กำลังโหลดทรัพยากรครั้งแรก อาจใช้เวลาสักครู่บน macOS",
    ) -> None:
        super().__init__(game)
        self.level_id = level_id
        self.next_scene_factory = next_scene_factory
        self.items_per_frame = max(1, int(items_per_frame))

        self.title = title
        self.note = note

        self._runner = None
        self._done = 0
        self._total: Optional[int] = None
        self._status = "Preparing..."

        # ใช้ฟอนต์ระบบ (ไม่ไปโหลดไฟล์ font เพิ่มในช่วง preload)
        self._title_font = pygame.font.Font(None, 42)
        self._font = pygame.font.Font(None, 22)

        # กัน user คิดว่าค้าง: หมุนสัญลักษณ์เล็ก ๆ
        self._spin_t = 0.0

    def enter(self) -> None:
        # สร้าง generator ตอนเข้า scene เพื่อเลี่ยงงานหนักใน __init__
        self._runner = self._preload_runner()

    def handle_events(self, events) -> None:
        for e in events:
            if e.type == pygame.QUIT:
                self.game.quit()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                # อนุญาตให้ยกเลิกได้
                self.game.quit()

    def update(self, dt: float) -> None:
        self._spin_t += dt

        if not self._runner:
            return

        # โหลดทีละนิดต่อเฟรม
        for _ in range(self.items_per_frame):
            try:
                next(self._runner)
                self._done += 1
            except StopIteration:
                # เสร็จแล้วไป scene ถัดไป
                self.game.scene_manager.set_scene(self.next_scene_factory())
                return
            except Exception as ex:
                # ถ้า preload ล้มเหลว อย่าให้เกมตายทั้งเกม: ไป scene ถัดไปแต่พิมพ์เตือน
                print("[WARN] preload failed:", ex)
                self.game.scene_manager.set_scene(self.next_scene_factory())
                return

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()

        # กล่องกลางจอ
        panel = pygame.Rect(0, 0, min(560, w - 40), 220)
        panel.center = (w // 2, h // 2)
        self.draw_panel(surface, panel, alpha=170)

        # Title
        title_surf = self._title_font.render(self.title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(centerx=panel.centerx, y=panel.top + 18)
        surface.blit(title_surf, title_rect)

        # Status
        status = self._status
        status_surf = self._font.render(status, True, (220, 220, 220))
        status_rect = status_surf.get_rect(centerx=panel.centerx, y=title_rect.bottom + 14)
        surface.blit(status_surf, status_rect)

        # Progress bar (ถ้ารู้ total แล้ว)
        bar_w = panel.width - 60
        bar_h = 18
        bar_x = panel.left + 30
        bar_y = status_rect.bottom + 18
        pygame.draw.rect(surface, (70, 70, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=8)

        if self._total and self._total > 0:
            pct = max(0.0, min(1.0, self._done / float(self._total)))
            fill_w = int(bar_w * pct)
            pygame.draw.rect(surface, (120, 220, 140), (bar_x, bar_y, fill_w, bar_h), border_radius=8)
            pct_text = f"{int(pct * 100)}%"
        else:
            # total ยังไม่รู้ → ทำแถบวิ่ง
            t = (pygame.time.get_ticks() % 1000) / 1000.0
            fill_w = max(40, int(bar_w * 0.25))
            x = int(bar_x + (bar_w - fill_w) * t)
            pygame.draw.rect(surface, (120, 220, 140), (x, bar_y, fill_w, bar_h), border_radius=8)
            pct_text = "..."

        pct_surf = self._font.render(pct_text, True, (255, 255, 255))
        pct_rect = pct_surf.get_rect(centerx=panel.centerx, y=bar_y + bar_h + 10)
        surface.blit(pct_surf, pct_rect)

        # Note
        note_surf = self._font.render(self.note, True, (180, 180, 180))
        note_rect = note_surf.get_rect(centerx=panel.centerx, y=pct_rect.bottom + 12)
        surface.blit(note_surf, note_rect)

        # Spinner (เล็ก ๆ)
        phase = int((self._spin_t * 4) % 4)
        dots = "." * phase
        sp = self._font.render(dots, True, (200, 200, 200))
        sp_rect = sp.get_rect(centerx=panel.centerx, y=note_rect.bottom + 10)
        surface.blit(sp, sp_rect)

    # ----------------- internal -----------------

    def _preload_runner(self):
        # 1) โหลดข้อมูลเลเวล
        self._status = f"Loading level data: {self.level_id}"
        level_data = load_level(self.level_id)
        yield

        # รวบรวม enemy types ที่จะใช้ในด่านนี้
        enemy_spawns = getattr(level_data, "enemy_spawns", []) or []
        enemy_ids = sorted({s.get("type") for s in enemy_spawns if s.get("type")})

        # effect ที่อยาก warm up (เพิ่มได้)
        effect_ids = ["born"]  # BornEffectNode ใช้ effect_id

        # ทิศที่ต้อง warm up สำหรับเอฟเฟ็กต์ฟัน (8 ทิศ)
        slash_dirs = ["up", "up_right", "right", "down_right", "down", "down_left", "left", "up_left"]


        # ตั้ง total หลังรู้จำนวนงาน
        # - 1: load level
        # - 1: build tilemap (tileset image)
        # - N: enemy types
        # - M: effects
        self._total = 2 + len(enemy_ids) + len(effect_ids) + len(slash_dirs) + len(slash_dirs)  # +slash +sword_arc

        # 2) สร้าง TileMap (จะโหลด tileset)
        self._status = "Building tilemap (tileset image)"
        _ = TileMap(level_data, self.game.resources)
        yield

        # 3) preload enemy assets: สร้าง dummy EnemyNode นอกจอเพื่อบังคับโหลด sprite/sound
        temp_group = pygame.sprite.Group()
        for enemy_id in enemy_ids:
            self._status = f"Preloading enemy: {enemy_id}"
            dummy = EnemyNode(self.game, (-9999, -9999), temp_group, enemy_id=enemy_id)
            dummy.kill()
            yield

        # 4) preload effects
        for effect_id in effect_ids:
            self._status = f"Preloading effect: {effect_id}"
            dummy = BornEffectNode(
                self.game,
                (-9999, -9999),
                *[temp_group],
                effect_id=effect_id,
                lifetime=0.01,
                scale=0.5,
            )
            dummy.kill()
            yield

                # 4) Warm up SlashEffectNode (สร้างเฟรมไว้ใน cache เพื่อลดกระตุกตอนฟัน)
        #
        # NOTE สำคัญ:
        # SlashEffectNode คำนวณ "radius" จากระยะห่างระหว่าง player_center กับ attack_rect.center
        # ถ้า game.player ไม่มีอยู่ (เช่นตอนอยู่ใน PreloadScene) radius จะถูก fallback เป็น 64 เสมอ
        # ทำให้ cache ที่ warm up ไว้ไม่ตรงกับของจริงตอนเล่น (โดยเฉพาะ sword_all_direction_2 ที่ offset ใหญ่)
        # ผลคือ “ฟันครั้งแรก” ต้องสร้างเฟรมใหม่หนัก ๆ => dt กระโดด => เอฟเฟ็กต์ดูต่างจากครั้งถัดไป
        #
        # วิธีแก้: สร้าง dummy player ชั่วคราว + warm up หลาย radius ที่ครอบคลุมของจริง
        class _DummyPlayer:
            def __init__(self, center: tuple[int, int]):
                self.rect = pygame.Rect(0, 0, 1, 1)
                self.rect.center = center

        old_player = getattr(self.game, "player", None)
        self.game.player = _DummyPlayer((0, 0))

        # radius จริงของเกมถูก clamp ที่ 48..220 ใน SlashEffectNode
        warm_radii = [64.0, 128.0, 176.0, 220.0]

        try:
            for d in slash_dirs:
                dir_vec = SlashEffectNode._direction_to_vector(d)
                for r in warm_radii:
                    self._status = f"Preloading slash effect frames: {d} (r={int(r)})"
                    dummy_attack = pygame.Rect(0, 0, 64, 64)
                    dummy_attack.center = (int(dir_vec.x * r), int(dir_vec.y * r))
                    dummy = SlashEffectNode(self.game, dummy_attack, d, temp_group)
                    dummy.kill()
                    yield
        finally:
            self.game.player = old_player

# 5) Warm up SwordSlashArcNode (โหลดรูปดาบ + เตรียมโครง)
        try:
            sword_img = self.game.resources.load_image("effects/sword_slash.png")
        except Exception:
            sword_img = None

        if sword_img is not None:
            for d in slash_dirs:
                self._status = f"Preloading sword arc: {d}"
                dummy = SwordSlashArcNode(self.game, (-9999, -9999), d, sword_img, 120.0, 0.01, temp_group)
                dummy.kill()
                yield

        self._status = "Done"
        return
