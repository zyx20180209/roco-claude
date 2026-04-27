<!--
 * @Author: zyx20180209 zyx20180209@users.noreply.github.com
 * @Date: 2026-04-26 22:28:31
 * @LastEditors: zyx20180209 zyx20180209@users.noreply.github.com
 * @LastEditTime: 2026-04-27
 * @FilePath: /roco-claude/battle/README.md
 * @Description: 即时对战助手
-->
# battle — 洛克王国即时对战助手

为 PVP 对战提供**数值层面的快速决策辅助**的 CLI 工具。

> 设计上为后续接入视觉识别模型预留接口：每条命令可独立调用，所有命令支持 `--json` 输出。

---

## 设计哲学

### 边界

**工具只做"数值决策辅助"，不做"对战流程模拟"。**

如果追求完美会陷入复刻整个游戏引擎的陷阱（模拟印记结算、特性触发顺序、应对判定路径……），投入产出比极低。游戏 UI 已经能展示这些信息，工具不重复展示。

### 核心问题

工具围绕一个核心问题：**"这一回合该怎么决策？"**

具体回答三个子问题：

1. **我能秒杀对面吗？** — 综合我方技能伤害 + 对方剩余血量
2. **对面会秒杀我吗？** — 综合对方所有可能技能 + 我的剩余血量 + 速度
3. **现在换人合理吗？** — 基于场下威胁矩阵 + 队友的克制关系

### 价值排序（玩家越难自己算 → 工具价值越高）

| 等级 | 功能 | 玩家心算能力 |
|------|------|-----------|
| ⭐⭐⭐ | 跨回合斩杀推演（含 DoT/冻结） | ❌ |
| ⭐⭐⭐ | 6v6 换人决策矩阵 | ❌ |
| ⭐⭐⭐ | 多次伤害反推对手配置 | ❌ |
| ⭐⭐ | 当前回合伤害预估 | ⚠️ |
| ⭐⭐ | 速度比较 | ⚠️ |
| ⭐ | 记录已观察技能 | ✅ |

### 不做的事

- ❌ 模拟回合结算（印记/buff/debuff 触发顺序）
- ❌ 模拟应对成功率（取决于双方决策，无法预测）
- ❌ 模拟首领化时机
- ❌ 复刻游戏 UI 已经展示的信息

---

## 当前功能

### Session 管理

```bash
battle list                       # 列出所有 session
battle new <id>                   # 新建对战
battle status <id>                # 显示完整状态
battle end <id> [--save]          # 结束对战（默认删除）
battle delete <id>                # 强制删除
```

### 我方设置

```bash
battle list-teams                                   # 列出预设队伍
battle load-myteam <id> <team_name>                 # 加载预设队伍
battle set-myteam <id> <p1> <p2> ...                # 手动设置队伍
battle set-myskills <id> <pokemon> <s1> ...         # 设置技能
```

### 敌方设置

```bash
# 盲选模式（用 ? 占位）
battle set-enemy <id> <slot> ?

# 已知构成模式
battle set-enemy <id> <slot> <pokemon>
battle set-enemy-team <id> <p1> <p2> ... | ?       # 一次性设置

# 实测/观察
battle observe <id> enemy <pokemon> <skill>        # 观察到的技能
battle update-enemy <id> <pokemon> --hp 65 --energy 3  # 更新血量/能量
battle infer-atk <id> <skill> <damage>             # 实测反推对方攻击值
```

### 在场设置

```bash
battle active <id> my <index>
battle active <id> enemy <index>
```

### 计算（核心）

```bash
battle speed <id>                # 速度比较
battle my-damages <id>           # 我方 4 技能对敌方在场精灵伤害
battle enemy-damages <id>        # 敌方所有技能对我方伤害（三档估算）
battle bench-threats <id>        # 敌方场下精灵的威胁评估
```

---

## 开发路线图

> 按价值密度优先开发，每完成一项更新本节进度。

### 已完成

- ✅ Session 管理 + 我方/敌方设置
- ✅ 速度比较（含极速/中位/最低三档）
- ✅ 当前回合伤害预估（已知配置单值 / 未知三档）
- ✅ 实测反推（infer-atk → confirmed_stats 自动存储）
- ✅ 场下威胁评估（bench-threats）
- ✅ 热门配招库（enemy_skills/）
- ✅ 队伍配置文件（teams/）

### 进行中

- 🔥 **跨回合斩杀推演** — 综合多回合伤害 + DoT + 冻结，给出"X 回合内能秒杀对方"

### 待规划

- ⏳ **完整换人决策矩阵** — 计算 36 种"我方任意 × 敌方任意"伤害组合，推荐最优换入
- ⏳ **多次推断累积锁定配置** — 多次 infer-atk 结果交集，逐步收窄敌方真实配置
- ⏳ **buff/特性触发的速度反超预警** — 对方触发顺风/预警等加速效果后的实时速度对比

### 不开发

- ❌ 印记叠层结算模拟
- ❌ 应对成功路径模拟
- ❌ 视觉识别（独立模块，但工具应保持 CLI 接口可被外部调用）

---

## 模块架构

```
battle/
├── core.py              数据加载 + 能力值/克制/显示威力/伤害公式
├── session.py           Session 状态读写（~/.roco-battle/sessions/）
├── commands.py          业务逻辑层 cmd_* 函数（被 CLI / 未来 REPL / API 共享）
├── formatters.py        输出格式化（文本和 JSON）
├── cli.py               argparse 入口
├── teams/               预设我方队伍配置
└── enemy_skills/        敌方精灵热门配招（先验知识库）
```

### 设计原则

- **业务逻辑函数只返回数据**，不直接 `print`（方便复用到 REPL/API）
- **错误抛 `ValueError`**，CLI 层统一捕获显示
- **session 文件存到用户目录** `~/.roco-battle/sessions/<id>.json`，不污染项目
- **所有命令支持 `--json` 输出**，方便外部工具集成
- **`core.damage()` 等核心函数单一来源**，公式更新只改一处

---

## 数据来源

- **精灵/技能/属性克制**：`data/raw/`（项目共享）
- **预设我方队伍**：`battle/teams/<team_name>.json`
- **敌方热门配招**：`battle/enemy_skills/<精灵名>.json`
- **对战会话**：`~/.roco-battle/sessions/<session_id>.json`

各文件 schema 详见对应目录的 README。

---

## 公式来源

伤害公式来自 `伤害计算器-洛克王国世界` 的世界版（`INT(ROUND(攻击 × 连击 × 威力 × 减伤 × 37/41) / 防御)`）。

详见 `data/mechanics/damage_formula.md`。
