"""
从 data/archive/final_pokemon_verified.json 精简生成 data/raw/pokemon.json
只保留战斗相关字段：
  - pokemon_key (id:形态)
  - base_name / form_name
  - display_name
  - attributes_list (属性)
  - stats (种族值)
  - defense_profile (属性弱点)
  - ability (特性文本)
  - skills: moves / jinengshi / xuemai (去除 tujian)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "data" / "archive" / "final_pokemon_verified.json") as f:
    data = json.load(f)

trimmed = []
for p in data:
    item = {
        "pokemon_key": p["pokemon_key"],
        "base_name": p["base_name"],
        "form_name": p.get("form_name"),
        "display_name": p["display_name"],
        "attributes_list": p["attributes_list"],
        "stats": p["stats"],
        "defense_profile": p["defense_profile"],
        "ability": p["abilities_text"],
        "skills": {
            "moves": p["skill_lists"].get("moves", []),
            "jinengshi": p["skill_lists"].get("jinengshi", []),
            "xuemai": p["skill_lists"].get("xuemai", []),
        },
    }
    trimmed.append(item)

with open(ROOT / "data" / "raw" / "pokemon.json", "w") as f:
    json.dump(trimmed, f, ensure_ascii=False, indent=2)

print(f"Done. {len(trimmed)} 精灵已精简输出到 data/raw/pokemon.json")
