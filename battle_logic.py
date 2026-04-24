"""对战逻辑推断：速度层、耐久、出手权、核心潜力评估"""

from typing import Any


UTILITY_KEYWORDS = {
    "healing": ["回复", "恢复", "治疗", "回血", "吸取", "吸血", "再生", "续航"],
    "speed_control": ["速度", "减速", "加速", "先手", "后手"],
    "status": ["中毒", "睡眠", "麻醉", "灼烧", "烧伤", "冰冻", "寄生", "恐惧", "混乱"],
    "setup": ["提升", "强化", "上升", "增加", "印记", "蓄力"],
    "energy": ["能量", "回能", "获得1能量", "获得2能量", "回复1能量", "回复2能量", "能耗-"],
    "disruption": ["删除", "消除", "驱散", "禁止", "封印", "沉默", "净化"],
    "pivot": ["强制换人", "吓退", "驱逐", "逼退", "换下", "撤退", "场下精灵"],
}


def categorize_speed(speed: int) -> str:
    if speed >= 120: return "很快"
    if speed >= 105: return "高速"
    if speed >= 85:  return "中速"
    if speed >= 60:  return "偏慢"
    return "很慢"


def categorize_bulk(hp: int, defense: int, special_defense: int) -> str:
    bulk = hp + defense + special_defense
    if bulk >= 340: return "很厚"
    if bulk >= 320: return "较厚"
    if bulk >= 290: return "中等"
    return "偏脆"


def _parse_cost(raw) -> int:
    try:
        v = int(str(raw))
        return v if v > 0 else 0
    except (TypeError, ValueError):
        return 0


def _raw_text(skill_details: list[dict], ability_text: str) -> str:
    parts = [ability_text]
    for s in skill_details:
        parts.append(" ".join(filter(None, [s.get("name"), s.get("description"), s.get("beizhu")])))
    return "\n".join(parts)


def collect_keyword_counts(skill_details: list[dict], ability_text: str) -> dict[str, int]:
    text = _raw_text(skill_details, ability_text)
    return {label: sum(1 for kw in kws if kw in text) for label, kws in UTILITY_KEYWORDS.items()}


def find_low_cost_scaling_attacks(skill_details: list[dict]) -> list[str]:
    hints = ["每次使用后，本技能威力", "威力永久", "连击数永久", "连击数+"]
    result = []
    for s in skill_details:
        if s.get("category") not in ("物攻", "魔攻"):
            continue
        if _parse_cost(s.get("energy_consumption")) > 2:
            continue
        desc = " ".join(filter(None, [s.get("name"), s.get("description"), s.get("beizhu")]))
        if any(h in desc for h in hints):
            result.append(s["name"])
    return result


def assess_action_rights(stats: dict, skill_details: list[dict], ability_text: str, kw: dict) -> dict:
    text = _raw_text(skill_details, ability_text)
    bulk = stats["hp"] + stats["defense"] + stats["special_defense"]
    speed = stats["speed"]
    offense = max(stats["attack"], stats["special_attack"])
    modes, score = [], 0

    if bulk >= 320:
        modes.append("高耐久赖场"); score += 2
    elif bulk >= 290 and kw["healing"] >= 1:
        modes.append("耐久续航赖场"); score += 2
    elif bulk >= 280:
        score += 1

    if speed >= 105 and offense >= 95:
        modes.append("高速先手压制"); score += 2
    elif speed >= 95:
        score += 1

    if kw["speed_control"] >= 2:
        score += 1
    if "吸血" in text or "吸取" in text:
        score += 1

    return {"modes": list(dict.fromkeys(modes)), "score": score}


def assess_sustained_damage(stats: dict, skill_details: list[dict], ability_text: str, kw: dict) -> dict:
    text = _raw_text(skill_details, ability_text)
    offense = max(stats["attack"], stats["special_attack"])
    score, reasons = 0, []

    if offense >= 115:
        score += 2; reasons.append("高输出面板")
    elif offense >= 95:
        score += 1; reasons.append("输出达到合格线")

    if kw["setup"] >= 2:
        score += 1; reasons.append("具备强化能力")
    if kw["healing"] >= 1 or kw["energy"] >= 2:
        score += 1; reasons.append("具备续航或资源循环")

    scaling = find_low_cost_scaling_attacks(skill_details)
    if scaling:
        score += 1; reasons.append(f"低费成长主炮({'、'.join(scaling[:2])})")
    if "奉献" in text:
        score += 1; reasons.append("可利用奉献提高持续收益")

    return {"score": score, "reasons": reasons}


def infer_archetypes(stats: dict, skill_details: list[dict], ability_text: str, role_tags: list[str]) -> list[str]:
    text = _raw_text(skill_details, ability_text)
    bulk_band = categorize_bulk(stats["hp"], stats["defense"], stats["special_defense"])
    speed_band = categorize_speed(stats["speed"])
    offense = max(stats["attack"], stats["special_attack"])
    candidates = []

    if bulk_band in ("较厚", "很厚") and any(t in role_tags for t in ["续航", "防守", "控速", "干扰"]):
        candidates.append("平衡队")
    if (speed_band in ("很快", "高速") or bulk_band in ("较厚", "很厚")) and offense >= 100:
        candidates.append("核心队")
    if "每有1只其他的虫系精灵" in ability_text:
        candidates.append("六虫队")
    if "奉献" in text or "虫群" in text:
        candidates.append("奉献体系")
    if text.count("印记") >= 2:
        candidates.append("印记体系")
    if text.count("天气") >= 2 or "暴风雪" in text:
        candidates.append("天气体系")
    if text.count("中毒") + text.count("毒伤") >= 2:
        candidates.append("毒队")
    if text.count("星陨") >= 2:
        candidates.append("星陨队")

    return list(dict.fromkeys(candidates))


def count_resists(defense_profile: dict) -> int:
    return len(defense_profile.get("resists_half", [])) + len(defense_profile.get("resists_third", [])) * 2


def evaluate_core_potential(stats: dict, skill_details: list[dict], ability_text: str, kw: dict,
                             defense_profile: dict | None = None) -> dict:
    text = _raw_text(skill_details, ability_text)
    offense = max(stats["attack"], stats["special_attack"])
    bulk = stats["hp"] + stats["defense"] + stats["special_defense"]
    ar = assess_action_rights(stats, skill_details, ability_text, kw)
    sd = assess_sustained_damage(stats, skill_details, ability_text, kw)
    a, s = ar["score"], sd["score"]
    resist_count = count_resists(defense_profile) if defense_profile else 0

    # 联防手：高抗性数量 + 速度偏慢 + 有换人/控场技
    if resist_count >= 6 and stats["speed"] <= 75 and kw.get("pivot", 0) >= 1:
        return {"potential": "中", "role": "联防手", "anchor": "非核心",
                "reason": f"拥有{resist_count}条抗性，速度偏慢走后手接招路线，携带换人技可打断对面节奏。"}
    # 高抗性但无换人技，仍可作轮转
    if resist_count >= 6 and stats["speed"] <= 75 and bulk >= 280:
        return {"potential": "低", "role": "轮转联防位", "anchor": "非核心",
                "reason": f"抗性覆盖广（{resist_count}条），适合用抗性换血，但缺乏主动换人手段。"}

    if "每有1只其他的虫系精灵" in ability_text and a >= 3 and s >= 3:
        return {"potential": "条件性", "role": "六虫队核心候选", "anchor": "精灵核心",
                "reason": "裸面板不足，但六虫队中攻速修正后可升格为精灵核心。"}
    if ("虫群" in text or text.count("奉献") >= 2) and a >= 3 and s >= 3:
        return {"potential": "条件性", "role": "奉献体系核心候选", "anchor": "机制核心",
                "reason": "依赖奉献层数建立持续推进，核心价值绑定机制本身。"}
    if a >= 3 and s >= 3 and (offense >= 115 or bulk >= 320):
        return {"potential": "高", "role": "大核心候选", "anchor": "精灵核心",
                "reason": "出手权强，能稳定维持高伤，满足大核心三要素。"}
    if offense >= 115 and (stats["speed"] >= 105 or bulk >= 320):
        return {"potential": "高", "role": "大核心候选", "anchor": "精灵核心",
                "reason": "高输出配合高速或高耐久，满足大核心基本面板要求。"}
    if a >= 2 and s >= 2 and (offense >= 95 or bulk >= 300):
        return {"potential": "中", "role": "副核心或功能核心", "anchor": "精灵核心",
                "reason": "有一定出手权，可通过强化或续航维持输出。"}
    if stats["total"] >= 560 and bulk >= 310:
        return {"potential": "低", "role": "平衡队轮转位", "anchor": "非核心",
                "reason": "面板适合轮转联防，不适合单独吃资源当核心。"}
    return {"potential": "低", "role": "辅助或体系拼图", "anchor": "非核心",
            "reason": "自身面板不足，依赖队伍体系放大价值。"}


def evaluate_offensive_power(stats: dict, skill_details: list[dict], ability_text: str,
                              kw: dict, defense_profile: dict | None = None) -> dict:
    """收集进攻相关客观因素，供 AI 综合判断"""
    offense = max(stats["attack"], stats["special_attack"])
    offense_type = "物攻" if stats["attack"] >= stats["special_attack"] else "特攻"
    attack_moves = [s for s in skill_details if s.get("category") in ("物攻", "魔攻")]
    type_coverage = sorted({s.get("attribute") for s in attack_moves if s.get("attribute")})

    low_cost_high_power = [
        s["name"] for s in attack_moves
        if str(s.get("energy_consumption", "")).lstrip("-").isdigit()
        and str(s.get("power", "")).lstrip("-").isdigit()
        and int(s["energy_consumption"]) <= 3 and int(s["power"]) >= 100
    ]

    high_power_moves = [
        {"name": s["name"], "power": s.get("power"), "cost": s.get("energy_consumption")}
        for s in attack_moves
        if str(s.get("power", "")).lstrip("-").isdigit() and int(s["power"]) >= 130
    ]

    return {
        "peak_offense_stat": offense,
        "offense_type": offense_type,
        "speed": stats["speed"],
        "speed_band": categorize_speed(stats["speed"]),
        "type_coverage": type_coverage,
        "type_coverage_count": len(type_coverage),
        "low_cost_high_power_moves": low_cost_high_power,
        "high_power_moves": high_power_moves[:5],
        "has_setup": kw["setup"] >= 2,
        "ability_offense_keywords": [kw for kw in ["攻击+", "魔攻+", "双攻+", "攻防速+", "克制"] if kw in ability_text],
    }


def evaluate_defensive_power(stats: dict, ability_text: str,
                              defense_profile: dict | None = None) -> dict:
    """收集防御相关客观因素，供 AI 综合判断"""
    dp = defense_profile or {}
    return {
        "hp": stats["hp"],
        "defense": stats["defense"],
        "special_defense": stats["special_defense"],
        "bulk_total": stats["hp"] + stats["defense"] + stats["special_defense"],
        "bulk_band": categorize_bulk(stats["hp"], stats["defense"], stats["special_defense"]),
        "resists": dp.get("resists_half", []),
        "resists_third": dp.get("resists_third", []),
        "immune_to": dp.get("immune_to", []),
        "weak_to_2x": dp.get("takes_2x_from", []),
        "weak_to_3x": dp.get("takes_3x_from", []),
        "resist_count": len(dp.get("resists_half", [])) + len(dp.get("resists_third", [])) * 2,
        "weakness_count": len(dp.get("takes_2x_from", [])) + len(dp.get("takes_3x_from", [])) * 2,
        "ability_defense_keywords": [kw for kw in ["减伤", "护盾", "免疫", "复活", "不朽", "回复", "恢复"] if kw in ability_text],
    }


def build_battle_logic(pokemon: dict, skill_details: list[dict], defense_profile: dict | None = None) -> dict:
    stats = {k: int(v) for k, v in pokemon["stats"].items() if k != "total"}
    stats["total"] = int(pokemon["stats"]["total"])
    ability_text = pokemon.get("ability") or ""
    kw = collect_keyword_counts(skill_details, ability_text)
    role_tags = []

    core = evaluate_core_potential(stats, skill_details, ability_text, kw, defense_profile)
    ar = assess_action_rights(stats, skill_details, ability_text, kw)
    sd = assess_sustained_damage(stats, skill_details, ability_text, kw)
    archetypes = infer_archetypes(stats, skill_details, ability_text, role_tags)

    return {
        "speed_band": categorize_speed(stats["speed"]),
        "bulk_band": categorize_bulk(stats["hp"], stats["defense"], stats["special_defense"]),
        "offensive_power": evaluate_offensive_power(stats, skill_details, ability_text, kw, defense_profile),
        "defensive_power": evaluate_defensive_power(stats, ability_text, defense_profile),
        "core_potential": core["potential"],
        "battle_role": core["role"],
        "core_anchor": core["anchor"],
        "role_reason": core["reason"],
        "action_rights": ar,
        "sustained_damage": sd,
        "archetype_candidates": archetypes,
        "keyword_counts": kw,
    }
