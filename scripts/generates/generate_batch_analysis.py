"""批量分析所有精灵，生成程序层分析结果 → data/processed/batch_analysis.json"""

import json
import sys
from pathlib import Path

# 允许从项目根目录导入模块
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data_repo import DataRepo
from battle_logic import build_battle_logic
from queries import effective_total

OUTPUT = ROOT / "data" / "processed" / "batch_analysis.json"


def main():
    repo = DataRepo()
    results = {}

    for p in repo.pokemon:
        key = p["pokemon_key"]
        defending_types = p.get("attributes_list", [])
        defense_profile = repo.compute_defense_profile(defending_types)
        stat_comparison = repo.build_stat_comparison(p["stats"])

        all_names = []
        for k in ("moves", "jinengshi", "xuemai"):
            v = p.get("skills", {}).get(k, [])
            all_names.extend(list(v.values()) if isinstance(v, dict) else v)
        skill_details = [repo.skill_by_name[n] for n in all_names if n in repo.skill_by_name]

        logic = build_battle_logic(p, skill_details, defense_profile)
        eff = effective_total(p["stats"])

        results[key] = {
            "name": p["display_name"],
            "attributes": defending_types,
            "ability": p.get("ability", ""),
            "stats": dict(p["stats"]),
            "effective_total": eff["effective_total"],
            "effective_total_removed": eff["removed"],
            "stat_percentiles": {k: v["percentile"] for k, v in stat_comparison.items()},
            "defense_profile": defense_profile,
            "battle_role": logic["battle_role"],
            "core_potential": logic["core_potential"],
            "core_anchor": logic["core_anchor"],
            "role_reason": logic["role_reason"],
            "speed_band": logic["speed_band"],
            "bulk_band": logic["bulk_band"],
            "archetype_candidates": logic["archetype_candidates"],
            "offensive_power": logic["offensive_power"],
            "defensive_power": logic["defensive_power"],
        }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"total": len(results), "entries": results}, f, ensure_ascii=False, indent=2)

    print(f"完成：{len(results)} 只精灵 → {OUTPUT}")


if __name__ == "__main__":
    main()
