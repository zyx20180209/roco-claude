"""
伤害计算器 — 参考洛克计算器 2.0 的思路

用户只需输入：
  - 攻击方攻击种族值/个体值/性格修正
  - 防御方防御种族值/个体值/性格修正
  - 防御方血量种族值/个体值/性格修正
  - 修正后威力（用户预先合并：基础威力 × 本系 × 克制 × 特性/应对 × 天气 等）
  - 减伤系数
  - 连击次数

性格修正取值："加" / "无" / "减"，分别对应 1.2 / 1.0 / 0.9。

公式来源：data/mechanics/damage_formula.md
"""

import math

NATURE_MAP = {"加": 1.2, "无": 1.0, "减": 0.9}


def calc_hp(base: int, iv: int, nature: str = "无") -> int:
    """生命值：ROUND(1.7×(种族+3×个体)+70) × 性格 + 100"""
    inner = round(1.7 * (base + 3 * iv)) + 70
    return round(inner * NATURE_MAP[nature]) + 100


def calc_stat(base: int, iv: int, nature: str = "无") -> int:
    """其他五项：ROUND(1.1×(种族+3×个体)+10) × 性格 + 50"""
    inner = round(1.1 * (base + 3 * iv)) + 10
    return round(inner * NATURE_MAP[nature]) + 50


def stat_diff_power(diff: int) -> int:
    """闪击/鸣沙陷阱等阶梯威力表（属性差 → 基础威力）。"""
    if diff < 0: return 60
    if diff <= 14: return 100
    if diff <= 29: return 130
    table = [140, 150, 160, 170, 180, 190, 200]
    return table[min((diff - 30) // 15, len(table) - 1)]


def calc_damage(
    atk_base: int, atk_iv: int, atk_nature: str,
    def_base: int, def_iv: int, def_nature: str,
    hp_base: int, hp_iv: int, hp_nature: str,
    effective_power: float,
    mitigation: float = 1.0,
    hit_count: int = 1,
) -> dict:
    """
    计算伤害。

    参数
    ----
    atk_base / atk_iv / atk_nature : 攻击方攻击种族值 / 个体值 / 性格修正
    def_base / def_iv / def_nature : 防御方防御种族值 / 个体值 / 性格修正
    hp_base  / hp_iv  / hp_nature  : 防御方血量种族值 / 个体值 / 性格修正
    effective_power                : 修正后威力（已合并本系/克制/特性/应对/天气等）
    mitigation                     : 减伤系数（防御技能、减伤特性），默认 1.0
    hit_count                      : 连击次数，默认 1

    性格修正取值："加"(1.2) / "无"(1.0) / "减"(0.9)

    返回
    ----
    dict: damage / atk / def / hp / percent / kill_count
    """
    atk = calc_stat(atk_base, atk_iv, atk_nature)
    defense = calc_stat(def_base, def_iv, def_nature)
    hp = calc_hp(hp_base, hp_iv, hp_nature)

    damage = int(round(atk * hit_count * effective_power * mitigation * 37 / 41) / defense)

    return {
        "damage": damage,
        "atk": atk,
        "def": defense,
        "hp": hp,
        "percent": round(100 * damage / hp, 1),
        "kill_count": math.ceil(hp / damage),
    }


if __name__ == "__main__":
    # 示例：岚鸟冬天（物攻128/加速性格/满个体）闪击 → 黑猫巫师（物防67/0个体/无性格）
    # 闪击基础威力 170（速度差84），本系 1.25，顺风特性 1.5
    # 修正后威力 = 170 × 1.25 × 1.5 = 318.75
    result = calc_damage(
        atk_base=128, atk_iv=10, atk_nature="无",   # 岚鸟物攻（加速性格对物攻不加成）
        def_base=67,  def_iv=0,  def_nature="无",   # 黑猫物防
        hp_base=152,  hp_iv=10,  hp_nature="无",    # 黑猫血量
        effective_power=318.75,
        mitigation=1.0,
        hit_count=1,
    )
    print(result)
    # {'damage': 501, 'atk': 234, 'def': 134, 'hp': 479, 'percent': 104.6, 'kill_count': 1}
