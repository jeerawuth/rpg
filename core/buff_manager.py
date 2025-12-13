# core/buff_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict


# ============================================================
# Generic Buff / Effect System (ขยายง่าย)
# - ใช้กับบัฟแบบมีเวลา (duration-based)
# - รองรับการจัดกลุ่ม (group) เพื่อให้ “บัฟชนิดเดียวกัน” ไม่ซ้อนกัน
# - รองรับนโยบาย refresh (reset/extend/ignore)
# ============================================================

@dataclass(frozen=True)
class EffectSpec:
    id: str
    duration: float
    group: Optional[str] = None
    refresh: str = "reset"  # "reset" | "extend" | "ignore"


class Effect:
    """เอฟเฟกต์พื้นฐาน (บัฟ/ดีบัฟ) ที่มีเวลา"""

    def __init__(self, spec: EffectSpec) -> None:
        self.spec = spec
        self.remaining: float = float(spec.duration)

    def on_apply(self, player) -> None:
        """เรียกครั้งเดียวตอนเริ่มบัฟ"""
        return

    def on_remove(self, player) -> None:
        """เรียกครั้งเดียวตอนบัฟหมด/ถูกแทนที่"""
        return

    def update(self, player, dt: float) -> bool:
        """อัปเดตทุกเฟรม: คืนค่า True เมื่อควรถูกลบออก"""
        self.remaining -= dt
        return self.remaining <= 0.0


class WeaponOverrideEffect(Effect):
    """บัฟเปลี่ยนอาวุธหลักชั่วคราว (main_hand)"""

    def __init__(self, spec: EffectSpec, weapon_id: str) -> None:
        super().__init__(spec)
        self.weapon_id = weapon_id
        self._prev_main_hand: Optional[str] = None

    def on_apply(self, player) -> None:
        eq = getattr(player, "equipment", None)
        if eq is None:
            return

        self._prev_main_hand = eq.main_hand
        eq.main_hand = self.weapon_id

        # ถ้า PlayerNode มีเมธอดนี้ ให้คำนวณ stats ใหม่
        if hasattr(player, "_recalc_stats_from_equipment"):
            player._recalc_stats_from_equipment()

    def update(self, player, dt: float) -> bool:
        # ถ้าระหว่างทางผู้เล่นเปลี่ยนอาวุธเอง -> ให้บัฟนี้หมดทันที
        eq = getattr(player, "equipment", None)
        if eq is not None and eq.main_hand != self.weapon_id:
            self.remaining = 0.0
            return True

        return super().update(player, dt)

    def on_remove(self, player) -> None:
        eq = getattr(player, "equipment", None)
        if eq is None:
            return

        # revert เฉพาะกรณีที่ยังถืออาวุธบัฟนี้อยู่ (กัน revert ทับของใหม่)
        if eq.main_hand == self.weapon_id:
            eq.main_hand = self._prev_main_hand

            if hasattr(player, "_recalc_stats_from_equipment"):
                player._recalc_stats_from_equipment()


class BuffManager:
    """ตัวจัดการบัฟแบบขยายง่าย"""

    def __init__(self) -> None:
        self._effects: List[Effect] = []

    @property
    def effects(self) -> List[Effect]:
        # expose แบบ read-only-ish (อย่าแก้ list ตรง ๆ)
        return list(self._effects)

    def clear_group(self, player, group: str) -> None:
        to_remove = [e for e in self._effects if e.spec.group == group]
        for e in to_remove:
            e.on_remove(player)
            self._effects.remove(e)

    def add(self, player, effect: Effect) -> None:
        # Handle group policy
        group = effect.spec.group
        if group:
            existing = next((e for e in self._effects if e.spec.group == group), None)
            if existing:
                policy = effect.spec.refresh
                if policy == "ignore":
                    return
                if policy == "extend":
                    existing.remaining += effect.spec.duration
                    return
                # reset (default): remove existing then apply new
                existing.on_remove(player)
                self._effects.remove(existing)

        effect.on_apply(player)
        self._effects.append(effect)

    def update(self, player, dt: float) -> None:
        # update copy to allow removal during iteration
        expired: List[Effect] = []
        for e in self._effects:
            if e.update(player, dt):
                expired.append(e)

        for e in expired:
            e.on_remove(player)
            if e in self._effects:
                self._effects.remove(e)

    # ---------- convenience APIs ----------
    def apply_weapon_override(
        self,
        player,
        weapon_id: str,
        duration: float,
        *,
        group: str = "weapon_override",
        refresh: str = "reset",
    ) -> None:
        spec = EffectSpec(
            id=f"weapon_override:{weapon_id}",
            duration=duration,
            group=group,
            refresh=refresh,
        )
        self.add(player, WeaponOverrideEffect(spec, weapon_id=weapon_id))
