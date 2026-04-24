import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

with open(RAW / "pokemon.json") as f:
    data = json.load(f)

def get_stats(p):
    s = p["stats"]
    atk = int(s["attack"])
    spa = int(s["special_attack"])
    total = int(s["total"])
    weak_atk = min(atk, spa)
    strong_atk = max(atk, spa)
    removed = "特攻" if spa <= atk else "物攻"
    effective = total - weak_atk
    return total, effective, removed, strong_atk

def rank(entries, key):
    entries.sort(key=lambda x: x[key], reverse=True)
    rank = 1
    for i, e in enumerate(entries):
        if i > 0 and e[key] == entries[i-1][key]:
            e["rank"] = entries[i-1]["rank"]
        else:
            e["rank"] = rank
        rank = i + 2
    return entries

total_list = []
effective_list = []

for p in data:
    total, effective, removed, _ = get_stats(p)
    base = {"name": p["display_name"], "attributes": "/".join(p["attributes_list"])}
    total_list.append({**base, "total": total})
    effective_list.append({**base, "total": total, "effective": effective, "removed": removed, "diff": total - effective})

rank(total_list, "total")
rank(effective_list, "effective")

with open(OUT / "total_stats_ranking.json", "w") as f:
    json.dump(total_list, f, ensure_ascii=False, indent=2)

with open(OUT / "effective_stats_ranking.json", "w") as f:
    json.dump(effective_list, f, ensure_ascii=False, indent=2)

today = date.today().strftime("%Y-%m-%d")

lines = [f"# 总种族值排行榜\n", f"数据总数：{len(total_list)} 只精灵　　数据日期：{today}\n",
         "\n| 排名 | 精灵 | 属性 | 总种族值 |\n|------|------|------|---------|"]
for p in total_list:
    lines.append(f"| {p['rank']} | {p['name']} | {p['attributes']} | **{p['total']}** |")
with open(OUT / "total_stats_ranking.md", "w") as f:
    f.write("\n".join(lines) + "\n")

lines = [f"# 有效种族值排行榜\n",
         "**有效种族值定义**：去除物攻/特攻中较低项后的5条种族值之和\n",
         f"数据总数：{len(effective_list)} 只精灵　　数据日期：{today}\n",
         "\n| 排名 | 精灵 | 属性 | 有效种族 | 总种族 | 差值 | 去除项 |\n|------|------|------|---------|-------|------|-------|"]
for p in effective_list:
    lines.append(f"| {p['rank']} | {p['name']} | {p['attributes']} | **{p['effective']}** | {p['total']} | -{p['diff']} | {p['removed']} |")
with open(OUT / "effective_stats_ranking.md", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Done. {len(total_list)} pokemon ranked.")
