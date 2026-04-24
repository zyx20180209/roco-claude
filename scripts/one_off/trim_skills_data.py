"""
精简 skills.json：
- 去除 beizhu / detail_url / learner_count / tujian_reward_sources / tujian_reward_source_count
- learners 只保留 pokemon.json 中存在的最终进化形态
- learners 每条只保留 key 和 name
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "data" / "raw" / "pokemon.json") as f:
    valid_keys = {p["pokemon_key"] for p in json.load(f)}

with open(ROOT / "data" / "raw" / "skills.json") as f:
    content = f.read()
skills = json.loads(content[content.find("["):])

trimmed = []
for s in skills:
    learners = [
        {"key": l["key"], "name": l["name"]}
        for l in s.get("learners", [])
        if l["key"] in valid_keys
    ]
    trimmed.append({
        "id": s["id"],
        "name": s["name"],
        "energy_consumption": s["energy_consumption"],
        "category": s["category"],
        "attribute": s["attribute"],
        "power": s["power"],
        "description": s["description"],
        "learners": learners,
    })

with open(ROOT / "data" / "raw" / "skills.json", "w") as f:
    json.dump(trimmed, f, ensure_ascii=False, indent=2)

print(f"Done. {len(trimmed)} 技能，learner 条目: {sum(len(s['learners']) for s in trimmed)}")
