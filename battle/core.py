"""数据加载与基础计算。"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NATURE_MULT = {"加": 1.2, "无": 1.0, "减": 0.9}

# --- 数据文件路径（变量化，便于测试和定制） ---

POKEMON_PATH = ROOT / "data" / "raw" / "pokemon.json"
SKILLS_PATH = ROOT / "data" / "raw" / "skills.json"
TYPE_CHART_PATH = ROOT / "data" / "raw" / "type_chart.json"
ENEMY_SKILLS_DIR = Path(__file__).resolve().parent / "enemy_skills"


def _load_pokemon():
    with open(POKEMON_PATH) as f:
        data = json.load(f)
    return {p["display_name"]: p for p in data}


def _load_skills():
    with open(SKILLS_PATH) as f:
        return {s["name"]: s for s in json.load(f)}


def _load_type_chart():
    with open(TYPE_CHART_PATH) as f:
        content = f.read()
        tc = json.loads(content[content.find("{"):])
    return tc.get("multiplier_matrix", {})


def _load_hot_skills():
    """从 battle/enemy_skills/<精灵名>.json 加载先验配招知识。

    返回 { pokemon_name: [skill_names...] }
    """
    result = {}
    if not ENEMY_SKILLS_DIR.exists():
        return result
    for path in ENEMY_SKILLS_DIR.glob("*.json"):
        name = path.stem
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        hot = data.get("hot_skills", [])
        # 兼容旧 schema：如果是字典列表，提取 skills
        if hot and isinstance(hot[0], dict):
            flat = []
            for entry in hot:
                for s in entry.get("skills", []):
                    if s and s not in flat:
                        flat.append(s)
            hot = flat
        result[name] = hot
    return result


POKEMON = _load_pokemon()
SKILLS = _load_skills()
TYPE_CHART = _load_type_chart()
HOT_SKILLS = _load_hot_skills()


def all_skills_of(pokemon_name: str) -> list:
    """精灵能学会的所有技能（moves + jinengshi + xuemai 的并集）。"""
    p = POKEMON.get(pokemon_name)
    if not p:
        return []
    sk = p.get("skills", {})
    result = list(sk.get("moves", []))
    result.extend(sk.get("jinengshi", []))
    xm = sk.get("xuemai", {})
    if isinstance(xm, dict):
        result.extend(xm.values())
    elif isinstance(xm, list):
        result.extend(xm)
    return list(dict.fromkeys(result))  # 去重保序


def get_movesets(pokemon_name: str) -> dict:
    """统一返回 {hot_skills, all_skills} 结构。"""
    return {
        "hot_skills": HOT_SKILLS.get(pokemon_name, []),
        "all_skills": all_skills_of(pokemon_name),
    }


# --- 能力值公式 ---

def calc_stat(base: int, iv: int = 10, nature: str = "无") -> int:
    inner = round(1.1 * (base + 3 * iv)) + 10
    return round(inner * NATURE_MULT[nature]) + 50


def calc_hp(base: int, iv: int = 10, nature: str = "无") -> int:
    inner = round(1.7 * (base + 3 * iv)) + 70
    return round(inner * NATURE_MULT[nature]) + 100


# --- 属性克制 ---

def type_effectiveness(atk_type: str, def_attrs: list) -> float:
    """PVP 双属性加法规则。"""
    mults = [TYPE_CHART.get(atk_type, {}).get(a, 1.0) for a in def_attrs]
    if any(m == 0 for m in mults):
        return 0.0
    if len(mults) == 1:
        return mults[0]
    eff = sum(1 for m in mults if m > 1)
    res = sum(1 for m in mults if m < 1)
    if eff == 2: return 3.0
    if res == 2: return 0.25
    if eff == 1 and res == 1: return 1.0
    if eff == 1: return 2.0
    if res == 1: return 0.5
    return 1.0


# --- 阶梯威力（属性差技能） ---

STAT_DIFF_SKILLS = {
    "闪击": "speed",
    "鸣沙陷阱": "defense",
}


def stat_diff_power(diff: int) -> int:
    if diff < 0: return 60
    if diff <= 14: return 100
    if diff <= 29: return 130
    table = [140, 150, 160, 170, 180, 190, 200]
    return table[min((diff - 30) // 15, len(table) - 1)]


# --- 显示威力 ---

def shown_power(skill_name: str, atk_pokemon: dict, def_pokemon: dict,
                atk_buff_layers: int = 0,
                def_buff_layers: int = 0) -> dict:
    """
    计算技能的显示威力（已含本系/克制/攻击buff/属性差）。

    返回：{ shown, base, stab, type_mult, category, attribute, hits_unknown, hit_count, energy }
    hit_count 从描述中尝试提取，失败则 hits_unknown=True
    """
    skill = SKILLS.get(skill_name)
    if not skill:
        return None

    base_power = int(skill["power"]) if skill["power"] and skill["power"].isdigit() else 0
    atk_attr = skill["attribute"]
    category = skill["category"]

    # 属性差技能
    diff_field = STAT_DIFF_SKILLS.get(skill_name)
    if diff_field and atk_pokemon and def_pokemon:
        atk_val = calc_stat(int(atk_pokemon["stats"][diff_field]), 10,
                            "加" if diff_field == "speed" else "无")
        def_val = calc_stat(int(def_pokemon["stats"][diff_field]), 10, "无")
        base_power = stat_diff_power(atk_val - def_val)

    # 本系
    stab = 1.25 if atk_pokemon and atk_attr in atk_pokemon.get("attributes_list", []) else 1.0

    # 克制
    type_mult = type_effectiveness(atk_attr, def_pokemon["attributes_list"]) if def_pokemon else 1.0

    # 攻击 buff（每层 +10%）
    atk_buff = 1 + atk_buff_layers * 0.1

    shown = base_power * stab * type_mult * atk_buff

    # 连击数提取
    hit_count, hits_unknown = _extract_hit_count(skill["description"])

    return {
        "skill_name": skill_name,
        "shown": shown,
        "base": base_power,
        "stab": stab,
        "type_mult": type_mult,
        "category": category,
        "attribute": atk_attr,
        "hit_count": hit_count,
        "hits_unknown": hits_unknown,
        "energy": int(skill["energy_consumption"]) if skill["energy_consumption"] else 0,
    }


import re


def _extract_hit_count(desc: str) -> tuple:
    """从技能描述提取连击数。返回 (hit_count, is_unknown)。"""
    if not desc:
        return 1, False
    # "N连击" / "N段" / "N次"
    m = re.search(r"(\d+)\s*[连段次]\s*击?", desc)
    if m:
        return int(m.group(1)), False
    return 1, False


# --- 伤害计算 ---

def damage(atk_stat: int, def_stat: int, eff_power: float,
           hit_count: int = 1, mitigation: float = 1.0) -> int:
    """伤害公式：INT(ROUND(攻击 × 连击 × 有效威力 × 减伤 × 37/41) / 防御)

    来源：洛克王国世界版伤害计算器（系数 37/41 ≈ 0.9024，先 ROUND 再整除）
    """
    return int(round(atk_stat * hit_count * eff_power * mitigation * 37 / 41) / def_stat)
