"""
秒杀阈值分析器

核心原理：
    伤害 = CEIL(0.9 × 攻击 × 有效威力 / 防御)
    秒杀条件：伤害 ≥ HP
    → 阈值 T = HP × 防御 / 0.9
    → 只要 攻击 × 有效威力 ≥ T 即可秒杀

"有效威力" = 基础威力 × 本系加成(1.25) × 属性克制(2/3x) × 特性加成 × 连击数 × ...
阈值 T 越大，秒杀越难。

使用示例见 __main__ 块。
"""

import math
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
from damage_calculator import calc_stat, calc_hp

NATURE = {"加": 1.2, "无": 1.0, "减": 0.9}


def defender_stats(hp_base, hp_iv, hp_nature,
                   def_base, def_iv, def_nature):
    """计算防御方 HP 和 防御值"""
    hp = calc_hp(hp_base, hp_iv, hp_nature)
    df = calc_stat(def_base, def_iv, def_nature)
    return hp, df


def kill_threshold(hp, defense):
    """秒杀阈值 T = HP × 防御 / 0.9 （攻击 × 有效威力 需 ≥ T）"""
    return hp * defense / 0.9


def required_atk(threshold, effective_power):
    """给定有效威力，反推所需攻击能力值。保证 CEIL(0.9 × atk × eff / def) ≥ hp"""
    return math.ceil(threshold / effective_power)


def required_power(threshold, atk):
    """给定攻击能力值，反推所需有效威力"""
    return math.ceil(threshold / atk * 10) / 10


def atk_to_base(need_atk, nature="加", iv=10):
    """反推需要的种族值（给定性格+个体）"""
    for base in range(20, 400):
        if calc_stat(base, iv, nature) >= need_atk:
            return base
    return None


def analyze_defender(name, hp_base, hp_iv, hp_nature,
                     def_base, def_iv, def_nature, def_label="物防"):
    """分析一只防御方，列出秒杀所需的攻击值 × 有效威力组合"""
    hp, df = defender_stats(hp_base, hp_iv, hp_nature,
                            def_base, def_iv, def_nature)
    T = kill_threshold(hp, df)
    print(f"=== {name} ===")
    print(f"HP = {hp}  {def_label} = {df}")
    print(f"秒杀阈值 T = HP × {def_label} / 0.9 = {T:.1f}")
    print(f"→ 只要 攻击 × 有效威力 ≥ {T:.1f} 即可秒杀\n")
    return hp, df, T


def scenario_table(threshold, scenarios, reverse_to_base=True):
    """给一组"场景→有效威力"对应关系，输出所需攻击能力值和种族值"""
    print(f"{'场景':<30} {'有效威力':<10} {'需要攻击':<10} {'加攻+满个体10 种族':<20}")
    print("-" * 75)
    for name, eff in scenarios:
        need_atk = required_atk(threshold, eff)
        base = atk_to_base(need_atk, "加", 10) if reverse_to_base else "-"
        base_str = f"≥{base}" if base else "❌ 不可能"
        print(f"{name:<30} {eff:<10.1f} {need_atk:<10} {base_str}")


def power_grid(threshold, atk_values):
    """给一组攻击能力值，输出所需有效威力"""
    print(f"{'攻击能力值':<12} {'所需有效威力':<15}")
    print("-" * 30)
    for atk in atk_values:
        need = required_power(threshold, atk)
        print(f"{atk:<12} {need:<15}")


if __name__ == "__main__":
    # 示例1：满血加HP翠顶夫人（魔防方向）
    hp, df, T = analyze_defender(
        "翠顶夫人（HP/物防/魔防+HP性格） 魔防方向",
        hp_base=125, hp_iv=10, hp_nature="加",
        def_base=97, def_iv=10, def_nature="无",
        def_label="魔防",
    )
    # 愿力冲击应对成功 = 80×1.5 = 120 基础威力
    scenarios = [
        ("愿力冲击 无本系 1x",       120 * 1.0 * 1.0),
        ("愿力冲击 有本系 1x",       120 * 1.25 * 1.0),
        ("愿力冲击 有本系 2x",       120 * 1.25 * 2.0),
        ("愿力冲击 有本系 3x",       120 * 1.25 * 3.0),
        ("本系威力150技能 3x克制",   150 * 1.25 * 3.0),
        ("追打3连+特性×1.25 1x",    75 * 3 * 1.25 * 1.25),
    ]
    scenario_table(T, scenarios)

    # 示例2：反向看——给定攻击值，要多少有效威力
    print("\n如果攻击能力值已知，反推所需有效威力：")
    power_grid(T, [200, 250, 300, 350, 400])
