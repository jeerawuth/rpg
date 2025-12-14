# core/audio_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame
from .resource_manager import ResourceManager


@dataclass(frozen=True)
class MusicCue:
    """
    ระบุเพลงของฉาก/สถานะ
    - intro: เล่นครั้งเดียว (optional)
    - loop: เล่นวน (required ถ้าต้องการ bgm)
    """
    loop: str
    intro: Optional[str] = None
    volume: float = 0.7
    fade_ms: int = 250          # fade in ตอนเริ่มเพลงใหม่
    fadeout_ms: int = 200       # fade out เพลงเดิมก่อนสลับ


class AudioManager:
    # เลือก offset ให้ห่างจาก event อื่น ๆ ในเกม
    EVT_MUSIC_END = pygame.USEREVENT + 40
    EVT_MUSIC_START_PENDING = pygame.USEREVENT + 41

    def __init__(self, resources: ResourceManager) -> None:
        self.resources = resources

        # --- volumes ---
        self.master_volume = 1.0
        self.music_volume = 1.0
        self.sfx_volume = 1.0

        # --- music state ---
        self._current_cue: Optional[MusicCue] = None
        self._pending_start: Optional[tuple[str, int, float, int]] = None  # (file, loops, vol, fade_ms)
        self._pending_loop_after_intro: Optional[tuple[str, float, int]] = None  # (loop_file, vol, fade_ms)

        # ให้ mixer.music ส่ง event ตอนเพลงจบ (ไว้ทำ intro->loop)
        pygame.mixer.music.set_endevent(self.EVT_MUSIC_END)

        # --- sfx channels ---
        pygame.mixer.set_num_channels(16)
        self._ch_ui = pygame.mixer.Channel(0)      # UI click/confirm
        self._ch_impact = pygame.mixer.Channel(1)  # hit/explosion สำคัญ
        self._sfx_channels = [pygame.mixer.Channel(i) for i in range(2, 16)]

        # cooldown กันเสียงเดิมยิงรัวเกินไป
        self._cooldown_ms: dict[str, int] = {}
        self._last_play_ms: dict[str, int] = {}

    # ---------------------------
    # Utilities
    # ---------------------------
    def _music_path(self, music_file: str) -> str:
        # assets/sounds/music/<file>
        return self.resources._resolve("sounds", "music", music_file)

    def _apply_vol(self, base: float, kind: str) -> float:
        if kind == "music":
            return max(0.0, min(1.0, base * self.master_volume * self.music_volume))
        return max(0.0, min(1.0, base * self.master_volume * self.sfx_volume))

    # ---------------------------
    # Public: update/event hook
    # ---------------------------
    def handle_events(self, events) -> None:
        """
        เรียกจาก GameApp ทุกเฟรม เพื่อให้:
        - intro จบแล้วเข้าสู่ loop
        - fadeout แล้วเริ่มเพลงใหม่ตามคิว
        """
        for e in events:
            if e.type == self.EVT_MUSIC_START_PENDING and self._pending_start:
                pygame.time.set_timer(self.EVT_MUSIC_START_PENDING, 0)  # stop timer
                music_file, loops, vol, fade_ms = self._pending_start
                self._pending_start = None
                self._start_music_immediately(music_file, loops=loops, volume=vol, fade_ms=fade_ms)

            elif e.type == self.EVT_MUSIC_END and self._pending_loop_after_intro:
                loop_file, vol, fade_ms = self._pending_loop_after_intro
                self._pending_loop_after_intro = None
                self._start_music_immediately(loop_file, loops=-1, volume=vol, fade_ms=fade_ms)

    # ---------------------------
    # Music controls
    # ---------------------------
    def apply_music(self, cue: Optional[MusicCue]) -> None:
        """
        ให้ SceneManager เรียกใช้
        - cue=None => หยุดเพลง
        - cue=MusicCue(...) => เล่นตาม cue (รองรับ intro+loop)
        """
        if cue is None:
            self.stop_music()
            self._current_cue = None
            return

        # ถ้าเป็น cue เดิม (กันโหลดซ้ำ)
        if self._current_cue == cue:
            return

        self._current_cue = cue

        vol = self._apply_vol(cue.volume, "music")

        # ถ้ามี intro -> เล่น intro ครั้งเดียว แล้วค่อย start loop
        if cue.intro:
            self._start_music_with_fade(cue.intro, loops=0, volume=vol, fade_ms=cue.fade_ms, fadeout_ms=cue.fadeout_ms)
            self._pending_loop_after_intro = (cue.loop, vol, cue.fade_ms)
        else:
            self._start_music_with_fade(cue.loop, loops=-1, volume=vol, fade_ms=cue.fade_ms, fadeout_ms=cue.fadeout_ms)

    def stop_music(self, fadeout_ms: int = 150) -> None:
        self._pending_loop_after_intro = None
        self._pending_start = None
        pygame.time.set_timer(self.EVT_MUSIC_START_PENDING, 0)
        if fadeout_ms > 0:
            pygame.mixer.music.fadeout(fadeout_ms)
        else:
            pygame.mixer.music.stop()

    def _start_music_with_fade(self, music_file: str, loops: int, volume: float, fade_ms: int, fadeout_ms: int) -> None:
        """
        เริ่มเพลงใหม่แบบ “มืออาชีพ”:
        - fadeout เพลงเก่า
        - ตั้ง pending ให้เริ่มเพลงใหม่หลัง fadeout จบ
        """
        # ถ้าไม่ได้เล่นอะไรอยู่ ก็เริ่มทันที
        if not pygame.mixer.music.get_busy() or fadeout_ms <= 0:
            self._start_music_immediately(music_file, loops=loops, volume=volume, fade_ms=fade_ms)
            return

        pygame.mixer.music.fadeout(fadeout_ms)
        self._pending_start = (music_file, loops, volume, fade_ms)
        pygame.time.set_timer(self.EVT_MUSIC_START_PENDING, fadeout_ms, loops=1)

    def _start_music_immediately(self, music_file: str, loops: int, volume: float, fade_ms: int) -> None:
        full_path = self._music_path(music_file)
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)

    # ---------------------------
    # SFX controls
    # ---------------------------
    def set_sfx_cooldown(self, sfx_file: str, cooldown_ms: int) -> None:
        self._cooldown_ms[sfx_file] = cooldown_ms

    def play_sfx(
        self,
        sfx_file: str,
        volume: float = 1.0,
        *,
        channel: str = "auto",   # "ui" | "impact" | "auto"
        pan: Optional[float] = None,  # -1.0 (L) ... 0 ... +1.0 (R)
        cooldown_ms: Optional[int] = None,
    ) -> None:
        now = pygame.time.get_ticks()

        cd = cooldown_ms if cooldown_ms is not None else self._cooldown_ms.get(sfx_file, 0)
        last = self._last_play_ms.get(sfx_file, -10_000_000)
        if cd > 0 and (now - last) < cd:
            return
        self._last_play_ms[sfx_file] = now

        sound = self.resources.load_sound(sfx_file)
        vol = self._apply_vol(volume, "sfx")

        if channel == "ui":
            ch = self._ch_ui
        elif channel == "impact":
            ch = self._ch_impact
        else:
            ch = next((c for c in self._sfx_channels if not c.get_busy()), None) or pygame.mixer.find_channel(True)

        # pan แบบง่าย (stereo)
        if pan is None:
            sound.set_volume(vol)
            ch.play(sound)
        else:
            pan = max(-1.0, min(1.0, pan))
            left = math.sqrt((1.0 - pan) * 0.5) * vol
            right = math.sqrt((1.0 + pan) * 0.5) * vol
            ch.set_volume(left, right)
            ch.play(sound)

    def preload_sfx(self, files: list[str]) -> None:
        # โหลดเข้าค cache ของ ResourceManager กันกระตุกตอนเล่นครั้งแรก
        for f in files:
            self.resources.load_sound(f)

import math
