# combat/damage_system.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Callable
import random

DamageType = str  # เช่น "physical", "fire", "ice", "poison"


# ---- Stats พื้นฐานของตัวละคร/มอน ----
@dataclass
class Stats:
    max_hp: float
    hp: float

    attack: float = 0.0       # พลังโจมตีปกติ
    magic: float = 0.0        # พลังเวท
    armor: float = 0.0        # เกราะ (กัน physical)
    resistances: Dict[DamageType, float] = field(default_factory=dict)
    # resistances: {"fire": 0.25} = ลดดาเมจไฟ 25%

    crit_chance: float = 0.05     # 0.05 = 5%
    crit_multiplier: float = 1.5  # ดาเมจ * 1.5 เมื่อคริ

    def is_dead(self) -> bool:
        return self.hp <= 0

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)


# ---- ตัวแพ็กเกจข้อมูลการโจมตี ----
@dataclass
class DamagePacket:
    base: float                    # ดาเมจฐานจากอาวุธ/เวท
    damage_type: DamageType = "physical"

    scaling_attack: float = 0.0    # คูณกับ attacker.attack
    scaling_magic: float = 0.0     # คูณกับ attacker.magic

    flat_bonus: float = 0.0        # บวกเพิ่มแบบตรง ๆ จาก buff ฯลฯ
    armor_pen: float = 0.0         # ทะลุเกราะ

    attacker_multiplier: float = 1.0  # ตัวคูณรวมจาก buff/damage up ต่าง ๆ


@dataclass
class DamageResult:
    raw_damage: float
    after_armor: float
    after_resist: float
    final_damage: int

    is_crit: bool
    killed: bool
    damage_type: DamageType


def compute_damage(
    attacker: Stats,
    defender: Stats,
    packet: DamagePacket,
    rng: Callable[[], float] = random.random,
) -> DamageResult:
    """
    คำนวนดาเมจและปรับ hp ของ defender ให้เรียบร้อย
    แล้ว return DamageResult กลับมา
    """

    # 1) base + scaling
    raw = packet.base
    raw += attacker.attack * packet.scaling_attack
    raw += attacker.magic * packet.scaling_magic
    raw += packet.flat_bonus
    raw *= packet.attacker_multiplier

    if raw < 0:
        raw = 0.0

    # 2) armor (ใช้กับ physical เป็นหลัก แต่ถ้าอยากใช้กับทุก type ก็เปลี่ยนได้)
    effective_armor = max(defender.armor - packet.armor_pen, 0.0)
    if effective_armor <= 0:
        after_armor = raw
    else:
        # สูตรลดดาเมจจากเกราะแบบ soft
        after_armor = raw * (100.0 / (100.0 + effective_armor))

    # 3) resist ตาม type
    resist = defender.resistances.get(packet.damage_type, 0.0)
    # clamp ให้อยู่ประมาณ 0–0.9 (กันเกิน 90% จะโหดไป)
    resist = max(0.0, min(resist, 0.9))
    after_resist = after_armor * (1.0 - resist)

    # 4) critical hit
    is_crit = False
    final = after_resist
    if final > 0:
        if rng() < attacker.crit_chance:
            is_crit = True
            final *= attacker.crit_multiplier

    final_int = int(round(final))
    if final_int < 0:
        final_int = 0

    # 5) apply damage to defender
    defender.hp = max(0.0, defender.hp - final_int)
    killed = defender.hp <= 0

    return DamageResult(
        raw_damage=raw,
        after_armor=after_armor,
        after_resist=after_resist,
        final_damage=final_int,
        is_crit=is_crit,
        killed=killed,
        damage_type=packet.damage_type,
    )
