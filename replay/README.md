# replay — 对战回放记录工具

记录高分局视频/直播中的对战流程，每场对战保存为独立 JSON 文件，用于后续决策分析。

---

## 设计目标

- **数据采集**：边看视频边按命令记录每回合双方动作
- **结构化存储**：每场对战独立 JSON 文件，便于检索/分析
- **与 battle 工具解耦**：battle 是即时对战助手（我方已知/敌方推测），replay 是离线观察记录（双方都是观察）

文件位置：`~/.roco-battle/replays/<id>.json`

---

## 快速上手

### 1. 新建回放

指定双方 6 只精灵：

```bash
python3 -m replay.cli new r001 \
  --my 寂灭骨龙 声波缇塔 圣羽翼王 岚鸟冬天的样子 绒光优优 尖嘴狐仙 \
  --enemy 黑猫巫师 音速犬 花衣蝶 铠甲虫 陨星虫 帕帕斯卡
```

### 2. 逐回合记录

每回合一条命令，记录双方动作：

```bash
# 攻击 + 防御
python3 -m replay.cli turn r001 \
  --my-action attack --my-skill 闪击 --my-damage 472 \
  --enemy-action defend --enemy-skill 风墙

# 我方换人 + 敌方攻击
python3 -m replay.cli turn r001 \
  --my-action switch --my-switch 声波缇塔 \
  --enemy-action attack --enemy-skill 暗影球 --enemy-damage 320

# 状态 + 聚能
python3 -m replay.cli turn r001 \
  --my-action status --my-skill 力量增效 \
  --enemy-action charge
```

### 3. 查看与管理

```bash
python3 -m replay.cli show r001     # 显示完整回放
python3 -m replay.cli list          # 列出所有回放
python3 -m replay.cli delete r001   # 删除
```

加 `--json` 切换为 JSON 输出，便于脚本处理：

```bash
python3 -m replay.cli show r001 --json
```

---

## action 类型

| 值 | 含义 |
|---|---|
| `attack` | 攻击技能 |
| `defend` | 防御技能 |
| `status` | 状态技能（含 buff/debuff/印记/天气/DoT） |
| `switch` | 换人 |
| `charge` | 聚能（恢复5能量） |
| `unknown` | 未知（视频看不清时使用） |

---

## 字段说明

每个回合的字段：

| 字段 | 适用 action | 说明 |
|------|-----------|------|
| `--my-skill` / `--enemy-skill` | attack/defend/status | 技能名 |
| `--my-damage` / `--enemy-damage` | 任意 | 实际造成的伤害（从画面读取） |
| `--my-switch` / `--enemy-switch` | switch | 换入的精灵名 |
| `--note` | 任意 | 本回合备注（如"对方应对成功"） |

---

## 数据格式

每场对战是一个 JSON 文件：

```json
{
  "id": "r001",
  "created_at": "2026-04-28T18:00:57",
  "my_team": ["寂灭骨龙", "声波缇塔", ...],
  "enemy_team": ["黑猫巫师", "音速犬", ...],
  "turns": [
    {
      "turn": 1,
      "my": {"action": "attack", "skill": "闪击", "damage": 472},
      "enemy": {"action": "defend", "skill": "风墙"}
    }
  ]
}
```

---

## 后续规划

收集到一定数量的回放后，可基于这些数据做：

- 常见决策模式提取（哪些精灵在什么局面下使用什么技能）
- 高分局战术统计（队伍构成 / 关键技能使用频率）
- 决策框架校准（验证 `data/mechanics/decision_value.md` 中的规则）

---

## 相关工具

- [`battle/`](../battle/README.md) — 即时对战助手（我方已知，敌方推测）
- [`data/mechanics/decision_value.md`](../data/mechanics/decision_value.md) — 决策收益框架
