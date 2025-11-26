# combat/status_effect_system.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List


@dataclass
class StatusEffect:
    """
    effect 1 ตัว เช่น 'burn', 'haste'
    - modifiers: เก็บ multiplier หรือโบนัสต่าง ๆ เช่น {"attack": 1.2, "speed": 0.5}
    """
    id: str
    duration: float  # วินาที; <= 0 หมายถึงไม่มีวันหมด
    modifiers: Dict[str, float] = field(default_factory=dict)

    tick_interval: Optional[float] = None  # วินาที; ถ้า != None จะเรียก on_tick เป็นครั้งคราว
    elapsed: float = 0.0
    _tick_accumulator: float = 0.0

    # callback: รับ owner (เช่น Player/Enemy node)
    on_apply: Optional[Callable[[Any], None]] = None
    on_remove: Optional[Callable[[Any], None]] = None
    on_tick: Optional[Callable[[Any], None]] = None


class StatusEffectManager:
    """เอาไว้ติดกับ entity แต่ละตัว"""

    def __init__(self, owner: Any):
        self.owner = owner
        self._effects: Dict[str, StatusEffect] = {}

    # ---------- การจัดการ effect ----------
    def add(self, effect: StatusEffect, refresh: bool = True) -> None:
        """
        ใส่ effect ใหม่
        ถ้า id ซ้ำและ refresh=True -> รีเซ็ตเวลา
        """
        existing = self._effects.get(effect.id)
        if existing and refresh:
            existing.elapsed = 0.0
            existing._tick_accumulator = 0.0
        else:
            self._effects[effect.id] = effect
            if effect.on_apply:
                effect.on_apply(self.owner)

    def remove(self, effect_id: str) -> None:
        eff = self._effects.pop(effect_id, None)
        if eff and eff.on_remove:
            eff.on_remove(self.owner)

    def clear(self) -> None:
        for eff in list(self._effects.values()):
            if eff.on_remove:
                eff.on_remove(self.owner)
        self._effects.clear()

    # ---------- update ทุกเฟรม ----------
    def update(self, dt: float) -> None:
        to_remove: List[str] = []
        for eff_id, eff in self._effects.items():
            eff.elapsed += dt

            # tick (เช่น poison โดนทุก 0.5 วินาที)
            if eff.tick_interval is not None and eff.tick_interval > 0:
                eff._tick_accumulator += dt
                while eff._tick_accumulator >= eff.tick_interval:
                    eff._tick_accumulator -= eff.tick_interval
                    if eff.on_tick:
                        eff.on_tick(self.owner)

            # เช็คหมดเวลา
            if eff.duration > 0 and eff.elapsed >= eff.duration:
                to_remove.append(eff_id)

        for eff_id in to_remove:
            self.remove(eff_id)

    # ---------- ดึงค่าไปใช้ตอนคำนวน stat ----------
    def get_multiplier(self, key: str) -> float:
        """
        รวม multiplier จากทุก effect สำหรับ key นั้น เช่น:
        - 'attack' สำหรับคูณพลังโจมตี
        - 'damage_taken' สำหรับคูณดาเมจที่โดน
        """
        mult = 1.0
        for eff in self._effects.values():
            if key in eff.modifiers:
                mult *= eff.modifiers[key]
        return mult

    def get_additive(self, key: str) -> float:
        """
        รวม bonus แบบบวกจากทุก effect
        convention: ใช้ชื่อ key + '_add'
        เช่น: {'attack_add': 5}
        """
        total = 0.0
        add_key = f"{key}_add"
        for eff in self._effects.values():
            if add_key in eff.modifiers:
                total += eff.modifiers[add_key]
        return total
