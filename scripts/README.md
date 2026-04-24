# scripts/

按职责分三类：

```
scripts/
├── generates/    # 从 raw/ 生成 processed/ 报告，可反复运行
├── tools/        # 交互式/可复用工具
└── one_off/      # 一次性数据迁移脚本，通常跑完就归档
```

所有脚本使用基于 `Path(__file__)` 的绝对路径，可从任何目录运行。

---

## generates/ — 刷新 processed/

| 脚本 | 输出 |
|------|------|
| `generate_rankings.py` | `processed/total_stats_ranking.{json,md}` + `effective_stats_ranking.{json,md}` |
| `generate_speed_tiers.py` | `processed/pvp_speed_tiers.json`（加速/中性性格，满个体） |
| `generate_batch_analysis.py` | `processed/batch_analysis.json` |

**刷新流程**：更新 `data/raw/` 后，依次运行三个脚本即可。

---

## tools/ — 工具

| 脚本 | 用途 |
|------|------|
| `damage_calculator.py` | 伤害计算器，可 import 也可直接运行看示例 |
| `kill_threshold.py` | 秒杀阈值分析：反推所需攻击值和威力，配套文档 `data/mechanics/kill_threshold.md` |
| `query.py` | 命令行查询（按系别/种族值/技能） |

---

## one_off/ — 一次性

当前：

- `trim_pokemon_data.py` — 从 `archive/` 精简生成 `raw/pokemon.json`
- `trim_skills_data.py` — 从 `archive/` 精简生成 `raw/skills.json`

这些脚本记录数据加工历史，不用于日常刷新。
