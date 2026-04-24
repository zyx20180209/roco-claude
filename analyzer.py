"""对战分析入口：读取程序层数据和AI报告"""

import json
import sys
from pathlib import Path
from typing import Optional

from data_repo import DataRepo
from battle_logic import build_battle_logic

DATA_DIR = Path(__file__).parent / "data"
ROLE_CORPUS_PATH = DATA_DIR / "meta" / "role_corpus.json"
AI_REPORTS_PATH = DATA_DIR / "meta" / "ai_reports.json"


def load_corpus() -> dict:
    if not ROLE_CORPUS_PATH.exists():
        return {}
    with open(ROLE_CORPUS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {e["pokemon"]: e for e in data.get("entries", [])}


def load_ai_reports() -> dict:
    if not AI_REPORTS_PATH.exists():
        return {}
    with open(AI_REPORTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _collect_skill_details(pokemon: dict, repo: DataRepo) -> list[dict]:
    """收集技能池，按来源分类标注。"""
    source_map = {
        "moves": "自身学会",
        "jinengshi": "技能石",
        "xuemai": "血脉技能",
    }
    results = []
    seen = set()
    for key, source_label in source_map.items():
        for name in pokemon.get("skills", {}).get(key, []):
            if name in seen or name not in repo.skill_by_name:
                continue
            seen.add(name)
            skill = dict(repo.skill_by_name[name])
            skill["source"] = source_label
            results.append(skill)
    return results


def build_facts(pokemon: dict, repo: DataRepo, corpus: dict) -> dict:
    skill_details = _collect_skill_details(pokemon, repo)
    defending_types = pokemon.get("attributes_list", [])
    defense_profile = repo.compute_defense_profile(defending_types)

    facts: dict = {
        "identity": {
            "name": pokemon["display_name"],
            "key": pokemon["pokemon_key"],
            "attributes": defending_types,
            "ability": pokemon.get("ability", ""),
        },
        "stats_comparison": repo.build_stat_comparison(pokemon["stats"]),
        "defense_profile": defense_profile,
        "skill_pool": [
            {
                "name": s["name"],
                "source": s.get("source"),
                "category": s.get("category"),
                "attribute": s.get("attribute"),
                "power": s.get("power"),
                "energy_cost": s.get("energy_consumption"),
                "description": s.get("description", ""),
            }
            for s in skill_details
        ],
        "battle_logic": build_battle_logic(pokemon, skill_details, defense_profile),
        "battle_constraints": {
            "team_size": 6,
            "mana_per_battle": 4,
            "skill_slots": 4,
            "energy_per_pokemon": 10,
            "note": "每只精灵初始10点能量，技能消耗能量；精灵力竭消耗全队1点魔力，4点魔力耗尽判负。聚能（回复5能量）不占技能栏，技能栏实际为4+1。",
        },
    }

    entry = corpus.get(pokemon["display_name"]) or corpus.get(pokemon["base_name"])
    if entry:
        facts["community_consensus"] = {
            "role": entry["community_role"],
            "typical_moveset": entry.get("typical_moveset", []),
            "role_logic": entry.get("role_logic", ""),
        }

    return facts


def get_report(name: str, repo: DataRepo) -> Optional[str]:
    """从已有AI报告中读取分析结果"""
    pokemon = repo.find(name)
    if not pokemon:
        # 模糊搜索提示
        matches = [p["display_name"] for p in repo.pokemon
                   if any(c in p["display_name"] for c in name)]
        print(f"未找到精灵: {name}")
        if matches:
            print(f"你是否在找: {', '.join(matches[:5])}")
        return None

    reports = load_ai_reports()
    key = pokemon["pokemon_key"]
    if key in reports:
        return reports[key]["report"]
    return None


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "迪莫"
    repo = DataRepo()
    report = get_report(query, repo)
    if report:
        print(f"=== {query} ===")
        print(report)
