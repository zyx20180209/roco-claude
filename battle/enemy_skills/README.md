# 热门精灵配招库

存放对战环境中常见精灵的**先验知识**——精灵常用的技能列表。

## 定位

- **先验知识库**，不是对战中实时维护的敌方技能
- 用于 `set-enemy` 时给出"对手可能携带的技能"推测
- 对战中观察到敌方实际技能后，由 session 状态记录"已观察 vs 推测"

## 文件位置

`battle/enemy_skills/<精灵名>.json`

文件名 = 精灵 `display_name`（与 `data/raw/pokemon.json` 一致）。

## Schema

```json
{
  "hot_skills": ["火云车", "跌落", "当头棒喝", "热身"]
}
```

只有一个字段：`hot_skills` 是该精灵在 PVP 中常见的技能名列表。可以包含多套配招中的所有技能（去重）。

## `all_skills`（运行时）

每只精灵能学会的所有技能，由代码运行时从 `data/raw/pokemon.json` 动态拉取，**不写进 JSON 文件**——避免数据冗余。

通过 `core.get_movesets(name)` 获取统一结构：

```python
{
  "hot_skills": [...],   # 来自本目录的 JSON
  "all_skills": [...],   # 运行时合并 moves + jinengshi + xuemai
}
```

## 命名约定

- 文件名直接用精灵 display_name（如 `音速犬.json`）
- 形态精灵用完整名（如 `岚鸟冬天的样子.json`）

## 与其他目录的关系

- `battle/teams/` — 我方队伍的具体配置（自己当前用的）
- `battle/enemy_skills/` — 环境精灵的先验知识（社区常见配招）
