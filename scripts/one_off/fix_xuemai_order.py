"""
将 data/raw/pokemon.json 中 xuemai 字段从 list 改为 dict。

旧格式（list）：xuemai 是 18 长度数组，但顺序错位（机械系在位置 5）
新格式（dict）：xuemai 是 {"系别名": "技能名"} 字典，避免顺序问题

通过技能名反查实际属性，重建为字典。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "data" / "raw" / "pokemon.json") as f:
    pokemon = json.load(f)

with open(ROOT / "data" / "raw" / "skills.json") as f:
    skills = {s["name"]: s for s in json.load(f)}

ALL_TYPES = {'普通', '草', '火', '水', '光', '地', '冰', '龙', '电',
             '毒', '虫', '武', '翼', '萌', '幽', '恶', '机械', '幻'}

fixed = 0
warnings = []

for p in pokemon:
    xm = p.get("skills", {}).get("xuemai")
    if not isinstance(xm, list):
        continue  # 已经是 dict 或不存在

    new_xm = {}
    for sk_name in xm:
        sk = skills.get(sk_name)
        if not sk:
            warnings.append(f"{p['display_name']}: 未知技能 {sk_name}")
            continue
        attr = sk.get("attribute")
        if attr not in ALL_TYPES:
            warnings.append(f"{p['display_name']}: {sk_name} 属性={attr} 非标准")
            continue
        if attr in new_xm:
            warnings.append(f"{p['display_name']}: {attr}系重复（{new_xm[attr]} vs {sk_name}）")
        new_xm[attr] = sk_name

    p["skills"]["xuemai"] = new_xm
    fixed += 1

with open(ROOT / "data" / "raw" / "pokemon.json", "w", encoding="utf-8") as f:
    json.dump(pokemon, f, ensure_ascii=False, indent=2)

print(f"✓ 转换 {fixed} 只精灵的 xuemai 从 list 改为 dict")
if warnings:
    print(f"\n⚠️ {len(warnings)} 条警告:")
    for w in warnings[:20]:
        print(f"  {w}")
