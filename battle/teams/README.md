# 队伍配置文件

把你常用的对战队伍存成 JSON 文件，battle CLI 用 `load-myteam` 一键加载。

## 文件位置

`battle/teams/<team_name>.json`

文件名（不含 `.json`）就是 team_name，用于 CLI 引用。

## Schema

每个文件是一个**列表**，每项是一只精灵：

```json
[
  {
    "pokemon": "黑猫巫师",
    "nature": {
      "boost": "无",
      "reduce": "无"
    },
    "ivs": {
      "hp": 10,
      "special_defense": 10,
      "speed": 10
    },
    "skills": ["精神扰乱", "嗜痛", "无畏之心", "晒太阳"],
    "bloodline": "普通"
  },
  {
    "pokemon": "翠顶夫人",
    "nature": {
      "boost": "速度",
      "reduce": "物攻"
    },
    "ivs": {
      "hp": 10,
      "special_defense": 10,
      "speed": 10
    },
    "skills": ["风墙", "蓄水", "水炮", "先发制人"],
    "bloodline": "水"
  }
]
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pokemon` | string | ✅ | 精灵 display_name，需与 `data/raw/pokemon.json` 完全一致 |
| `nature.boost` | string | ✅ | 性格加成项（见下方取值表） |
| `nature.reduce` | string | ✅ | 性格减成项（见下方取值表） |
| `ivs` | object | ✅ | 个体值，最多 3 项填 10，其余省略（默认 0） |
| `skills` | array | ✅ | 4 个技能名，允许 `null` 或省略尾部 |
| `bloodline` | string | — | 血脉属性（见下方取值表），`null` 表示默认本系血脉 |

---

### `nature.boost` / `nature.reduce` 取值

| 值 | 含义 |
|----|------|
| `"无"` | 无加成/减成（两项都填"无"则无性格） |
| `"HP"` | 生命值 |
| `"物攻"` | 物理攻击 |
| `"魔攻"` | 魔法攻击（特殊攻击） |
| `"物防"` | 物理防御 |
| `"魔防"` | 魔法防御（特殊防御） |
| `"速度"` | 速度 |

**示例**：加速减物攻 → `{"boost": "速度", "reduce": "物攻"}`

---

### `ivs` 字段名

| 字段名 | 含义 |
|--------|------|
| `hp` | 生命值个体 |
| `attack` | 物攻个体 |
| `special_attack` | 魔攻个体 |
| `defense` | 物防个体 |
| `special_defense` | 魔防个体 |
| `speed` | 速度个体 |

每项取值 `0`（无个体）或 `10`（满个体）。**每只精灵最多 3 项填 10**，其余省略即为 0。

---

### `bloodline` 取值

18 个系别名 + 首领：

| 值 | 说明 |
|----|------|
| `"普通"` | 普通系血脉 |
| `"草"` | 草系血脉 |
| `"火"` | 火系血脉 |
| `"水"` | 水系血脉 |
| `"光"` | 光系血脉 |
| `"地"` | 地系血脉 |
| `"冰"` | 冰系血脉 |
| `"龙"` | 龙系血脉 |
| `"电"` | 电系血脉 |
| `"毒"` | 毒系血脉 |
| `"虫"` | 虫系血脉 |
| `"武"` | 武系血脉 |
| `"翼"` | 翼系血脉 |
| `"萌"` | 萌系血脉 |
| `"幽"` | 幽系血脉 |
| `"恶"` | 恶系血脉 |
| `"机械"` | 机械系血脉 |
| `"幻"` | 幻系血脉 |
| `"首领"` | 首领血脉（不能使用愿力冲击，可首领化） |
| `null` | 默认本系血脉（不填此字段） |

## CLI 用法

```bash
# 列出所有队伍配置
ls battle/teams/

# 把 battle/teams/team_a.json 加载到 session pvp001 中
python3 -m battle.cli load-myteam pvp001 team_a
```

加载后等价于：依次执行 `set-myteam` + 每只精灵的 `set-myskills` + 个体值/性格/血脉填入。
