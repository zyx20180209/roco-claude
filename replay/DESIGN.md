# 对战回放记录系统设计文档

## 一、目标

记录高分局视频/直播中的对战流程，以精灵为单位追踪每回合的状态变化，用于事后分析并最终服务于实时辅助决策。

---

## 二、回合数据模型

每个回合由一组 `changes` 组成，每条 change 对应一只精灵在本回合的所有变化。

```json
{
  "turn": 1,
  "changes": [
    {
      "side": "my",
      "pokemon": "寂灭骨龙",
      "entered": false,
      "exited": false,
      "fainted": false,
      "skill": "闪击",
      "hp_pct": 85,
      "energy_delta": -5,
      "damage_dealt": {"value": 472, "pct": 40.0},
      "buffs": {
        "attack": 0,
        "special_attack": 0,
        "defense": 0,
        "special_defense": 0,
        "speed": 0,
        "hit_count": 0,
        "power": 0
      },
      "dots": {"poison": 0, "burn": 0, "freeze": 0},
      "marks_added": [],
      "marks_removed": []
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `side` | `"my"` / `"enemy"` | 所属方 |
| `pokemon` | string | 精灵名 |
| `entered` | bool | 本回合换入上场 |
| `exited` | bool | 本回合换出下场 |
| `fainted` | bool | 本回合战死 |
| `skill` | string / null | 本回合使用的技能名 |
| `hp_pct` | float / null | 回合结束时血量百分比（0=战死，null=未变化） |
| `energy_delta` | int / null | 能量变化（负=消耗，正=回复，null=未变化） |
| `damage_dealt` | `{value, pct}` / null | 对对方造成的伤害（数值和百分比可互相纠正） |
| `buffs` | object | 各项 buff 层数变化（0=无变化，正=增加，负=减少） |
| `dots` | object | DoT 层数变化（毒/灼烧/冻结） |
| `marks_added` | string[] | 本回合新增的印记 |
| `marks_removed` | string[] | 本回合移除的印记 |

### buff 字段

| key | 含义 |
|-----|------|
| `attack` | 物攻层数变化 |
| `special_attack` | 魔攻层数变化 |
| `defense` | 物防层数变化 |
| `special_defense` | 魔防层数变化 |
| `speed` | 速度层数变化 |
| `hit_count` | 连击层数变化 |
| `power` | 威力层数变化 |

### 设计原则

- 只填有变化的字段，未变化的字段为 null 或 0
- 一回合可以有多条 change（双方都有变化时）
- `entered`/`exited` 同时为 true 表示换人（下场+上场是两条 change）
- `damage_dealt.value` 和 `damage_dealt.pct` 可以只填其中一个，UI 根据精灵生命值互相推算

---

## 三、完整回放文件结构

```json
{
  "id": "r001",
  "created_at": "2026-04-28T18:00:00",
  "my_team": ["精灵1", "精灵2", "精灵3", "精灵4", "精灵5", "精灵6"],
  "enemy_team": ["精灵1", "精灵2", "精灵3", "精灵4", "精灵5", "精灵6"],
  "turns": [
    {
      "turn": 1,
      "changes": [...]
    }
  ]
}
```

---

## 四、UI 设计

### 布局（网页 app）

```
┌─────────────────────────────────────────────────────────┐
│  我方队伍状态（6只精灵，显示血量/能量/DoT/buff）           │
├─────────────────────────────────────────────────────────┤
│  敌方队伍状态（同上）                                     │
├─────────────────────────────────────────────────────────┤
│  本回合输入面板                                           │
│  [添加变化] 选择精灵 → 填写变化字段 → 确认               │
├─────────────────────────────────────────────────────────┤
│  回合历史（可折叠，点击展开详情）                          │
├─────────────────────────────────────────────────────────┤
│  [上一回合] [提交本回合] [导出 JSON]                      │
└─────────────────────────────────────────────────────────┘
```

### 操作流程

1. 页面加载时输入双方队伍（6只精灵名）
2. 每回合：
   - 点击"添加变化"，选择精灵，填写本回合变化
   - 可以添加多条变化（双方各自的精灵）
   - 点击"提交本回合"，状态面板自动更新
3. 全程自动保存到 localStorage
4. 结束后点击"导出 JSON"，与 `replay/storage.py` 格式兼容

---

## 五、文件位置

| 文件 | 说明 |
|------|------|
| `apps/replay_recorder/index.html` | 网页 UI |
| `replay/storage.py` | Python 数据层（CLI 工具共用） |
| `replay/cli.py` | 命令行入口 |

---

## 六、后续分析方向

收集到足够回放后，可基于数据做：

- 常见换人时机分析（什么局面下换人）
- 技能使用频率与胜率关联
- DoT/印记的实际收益统计
- 决策框架校准（验证 `data/mechanics/decision_value.md`）
