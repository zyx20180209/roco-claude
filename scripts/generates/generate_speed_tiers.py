"""
从 data/raw/pokemon.json 生成 data/processed/pvp_speed_tiers.json。

计算每只精灵在"满个体 + 加速/中性性格"下的速度值，按速度值降序分档。
公式（来自洛克计算器 2.0）：速度 = ROUND(1.1 × (种族+30) + 10) × 性格 + 50
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NATURE_MAP = {"加速性格": 1.2, "中性性格": 1.0}


def calc_speed(base: int, nature_mult: float) -> int:
    inner = round(1.1 * (base + 30)) + 10
    return round(inner * nature_mult) + 50


def main():
    with open(ROOT / "data" / "raw" / "pokemon.json") as f:
        pokemon = json.load(f)

    tiers = defaultdict(list)
    for p in pokemon:
        base = int(p["stats"]["speed"])
        pid = p["pokemon_key"].split(":", 1)[0]
        form_label = p.get("form_name") or "原始形态"
        for nature_name, mult in NATURE_MAP.items():
            speed = calc_speed(base, mult)
            tiers[speed].append({
                "key": p["pokemon_key"],
                "id": pid,
                "name": p["display_name"],
                "form": form_label,
                "nature": nature_name,
            })

    result = [
        {"speed": s, "pokemon": tiers[s]}
        for s in sorted(tiers.keys(), reverse=True)
    ]

    with open(ROOT / "data" / "processed" / "pvp_speed_tiers.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(result)} 个速度档位，共 {sum(len(t['pokemon']) for t in result)} 条记录")


if __name__ == "__main__":
    main()
