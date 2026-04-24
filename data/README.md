# Data 目录说明

本目录存放项目所有数据，按生产阶段分为四个子目录。

---

## 目录结构

```
data/
├── raw/          # 原始数据（人工维护，数据源头）
├── processed/    # 脚本处理产物
├── analysis/     # AI 生成的单体精灵分析报告
├── meta/         # AI 生成的跨精灵综合分析
├── mechanics/    # 手动维护的对战机制词条
└── archive/      # 已归档的完整原始数据（git 忽略）
```

---

## raw/ — 原始数据

人工整理、直接维护的结构化数据，是整个数据流的源头。

| 文件 | 内容 |
|------|------|
| `pokemon.json` | 精灵战斗数据：名称/形态/属性/种族值/属性弱点/特性/技能（moves/jinengshi/xuemai） |
| `skills.json` | 技能库：基础数值、描述、学习者定位信息 |
| `type_chart.json` | 属性克制矩阵 |

**维护约定：**
- 图片信息不进入此数据
- `shiny` 不视为独立形态
- 形态命名以"标准名 + 当前形态说明"为准

---

## processed/ — 脚本处理产物

由 Python 脚本从 `raw/` 计算或整理生成，不应手动修改。

| 文件 | 生成脚本 | 内容 |
|------|----------|------|
| `total_stats_ranking.{json,md}` | `scripts/generates/generate_rankings.py` | 总种族值排名（239只） |
| `effective_stats_ranking.{json,md}` | `scripts/generates/generate_rankings.py` | 有效种族值排名（去除物攻/特攻较低项） |
| `pvp_speed_tiers.json` | `scripts/generates/generate_speed_tiers.py` | PVP 速度档位（加速/中性性格） |
| `batch_analysis.json` | `scripts/generates/generate_batch_analysis.py` | 批量分析结果：定位、种族百分位、打击面等 |

**刷新流程**：更新 `raw/` 后依次运行 `scripts/generates/` 下的三个脚本。

---

## analysis/ — 单体精灵 AI 分析报告

每只精灵一个 `.md` 文件，由 AI 生成，包含：

- 四维协同定位（种族值 / 特性 / 技能池 / 属性）
- 战术角色与技能池评价
- PVP 潜力与评分
- 擅长应对的情况、棘手对手、自身弱点

当前共约 150 只精灵的报告。文件名即精灵名，如 `白金独角兽.md`。

---

## meta/ — 跨精灵综合分析

AI 生成的环境级、跨精灵分析产物。

| 文件/目录 | 内容 |
|-----------|------|
| `ai_reports.json` | AI 报告汇总索引 |
| `counter_relationships.json` | 精灵间克制关系图谱 |
| `counter_research/` | 特定精灵的克制专项研究（`.md` 格式） |
| `deep_analysis.zip` | 深度分析归档 |
| `effective_stats_ranking.md` | 实战种族值排行（已被 `processed/effective_stats_ranking.json` 取代，保留作历史参考） |
| `meta_counter_guide.md` | 当前环境克制指南 |
| `role_corpus.json` | 定位语料库，用于 AI 分析的参考语料 |
| `hot_pokemon.json` | 当前环境热门精灵列表 |
| `status_mechanics.md` | 状态机制说明文档 |

---

## mechanics/ — 对战机制词条

手动维护的底层机制参考，不属于数据流水线产物。

| 文件 | 内容 |
|------|------|
| `battle_terms.md` | 对战词条库：基础机制 / 资源 / 天气 / debuff / 印记 / 玩家技能 / 血脉 |
| `turn_flow.md` | 回合瀑布算法：从指令输入到回合末结算的完整流程 |
| `damage_formula.md` | 能力值与伤害计算公式（人类阅读版），来源：洛克计算器 2.0 |
| `damage_formula.json` | 上述公式的结构化定义（代码可读版） |

**维护约定：**
- 机制按"词条"维护，不按系别文件拆分
- 词条描述应写清触发条件、结算方式、离场是否保留、是否免疫

---

## 数据流向

```
raw/ ──脚本──▶ processed/
raw/ ──AI──▶ analysis/  ──AI汇总──▶ meta/
mechanics/  （独立维护，供 AI 分析参考）
```
