# 数据来源

## 精灵与技能数据

- **洛克王国 Wiki** — https://wiki.lcx.cab/lk/
  - 精灵基础数据（种族值、属性、特性、技能列表）：`data/raw/pokemon.json`
  - 技能库（威力、能耗、描述）：`data/raw/skills.json`
  - 属性克制矩阵：`data/raw/type_chart.json`

## 计算公式

- **洛克计算器 2.0**（bilibili 爱心尾巴）— `洛克计算器2.0.xlsx`
  - 能力值计算公式（生命/物攻/魔攻/物防/魔防/速度）
  - 伤害计算公式
  - 速度线数据
  - 属性克制表（已与 Wiki 数据交叉验证，完全一致）
  - 整理后存放于：`data/mechanics/damage_formula.md` / `damage_formula.json`

- **用户补充（2026-04-24）**
  - 闪击/鸣沙陷阱等属性差阶梯威力表
  - 天气影响（雨天增强水系）与减伤系数机制说明
  - 完整伤害公式：`单次伤害 = (攻击/防御) × 0.9 × 有效威力 × 能力等级 × 本系加成 × 克制 × 天气 × 减伤系数`

## AI 分析数据

- **AI 生成**（基于上述原始数据）
  - 单体精灵分析报告：`data/analysis/`
  - 跨精灵综合分析：`data/meta/`
  - 排行榜：`data/processed/total_stats_ranking.*` / `effective_stats_ranking.*`
