# roco-claude

洛克王国 PVP 数据分析与战斗计算工具集。

> 🤖 **本项目全部由 AI 完成编写、设计与整理，没有一点人类操作。**
> 人类仅提供需求描述、测试反馈和游戏数据验证。

## 项目简介

本项目基于洛克王国 Wiki 和《洛克计算器 2.0》的公式，提供：

- **精灵数据库**：239 只精灵的种族值、属性、特性、技能池、属性弱点
- **战斗计算工具**：伤害计算、速度档位、种族值排行
- **网页小工具**：可直接在浏览器使用的计算器（支持 GitHub Pages 部署）
- **即时对战助手 CLI**：实时跟踪双方精灵、计算伤害与速度比较，详见 [battle/README.md](./battle/README.md)
- **对战回放记录 CLI**：看高分局视频时按回合记录双方动作，详见 [replay/README.md](./replay/README.md)
- **对战机制文档**：回合流程、印记/debuff 系统、伤害公式、秒杀阈值分析

## 目录结构

```
roco-claude/
├── apps/                    # 网页小工具（可部署到 GitHub Pages）
│   └── damage_calculator/   # 伤害计算器
├── battle/                  # 即时对战助手 CLI
├── replay/                  # 对战回放记录 CLI
├── data/
│   ├── raw/                 # 原始数据（精灵、技能、属性克制）
│   ├── processed/           # 脚本生成的排行榜和分析数据
│   ├── analysis/            # 单体精灵 AI 分析报告（~150只）
│   ├── meta/                # 跨精灵综合分析（含 popular_movesets.json）
│   └── mechanics/           # 对战机制文档
├── scripts/
│   ├── generates/           # 刷新 processed/ 的脚本
│   ├── tools/               # 伤害计算、查询等工具
│   └── one_off/             # 一次性数据处理脚本
├── data_repo.py             # 数据访问层
├── battle_logic.py          # 对战逻辑推断
├── analyzer.py              # 精灵分析器
└── queries.py               # 数据查询工具
```

## 网页工具

### 在线使用（GitHub Pages）

部署后访问：
- ⚔️ [伤害计算器](https://zyx20180209.github.io/roco-claude/apps/damage_calculator/)
- ⚙️ [传动计算器](https://zyx20180209.github.io/roco-claude/apps/transmission_calculator/)
- 📋 [对战回放记录](https://zyx20180209.github.io/roco-claude/apps/replay_recorder/) — [使用说明](./apps/replay_recorder/README.md)

### 本地运行

```bash
./apps/serve.sh          # 默认 8000 端口
./apps/serve.sh 8080     # 自定义端口
```

然后打开 `http://localhost:8000/apps/`

### 伤害计算器

5 个模块布局：攻击方 / 防御方 / 技能 / 全局状态 / 结果

技能模块两个 tab：

- **按显示威力**：直接输入游戏内看到的威力数字（已含本系/克制/攻击buff/特性）
- **按技能名称**：输入技能名自动计算本系、克制、属性差（闪击/鸣沙陷阱阶梯），并可填入攻击/防御 buff 层数

全局状态：
- 隐藏乘区（顺风 +50% / 破空 +75% / 风起印记 +20% / 其他%）
- 对方防御技能（自动填减伤系数）
- DoT 层数（中毒/灼烧/冰冻），自动判定回合末毒死和冻结斩杀
- 攻防双方支持精灵名称自动填入种族值（含速度/物防）

## 即时对战助手 CLI

实时跟踪双方精灵、记录观察到的技能、计算伤害与速度比较。

```bash
# 创建对战
python3 -m battle.cli new pvp001
# 设置我方队伍
python3 -m battle.cli set-myteam pvp001 黑猫巫师 翠顶夫人 彩虹独角兽
# 设置敌方第一只精灵（自动从热门配招拉推测技能）
python3 -m battle.cli set-enemy pvp001 0 岚鸟冬天的样子
# 双方在场后看伤害与速度
python3 -m battle.cli active pvp001 my 0
python3 -m battle.cli active pvp001 enemy 0
python3 -m battle.cli speed pvp001
python3 -m battle.cli enemy-damages pvp001
```

完整用法见 [battle/README.md](./battle/README.md)。

## 数据来源

- **精灵与技能数据**：[洛克王国 Wiki](https://wiki.lcx.cab/lk/)
- **伤害计算公式**：洛克计算器 2.0（bilibili 爱心尾巴）
- **机制补充**：社区实测数据

详见 [REFERENCES.md](./REFERENCES.md)

## 刷新数据

更新 `data/raw/` 后，依次运行：

```bash
python3 scripts/generates/generate_rankings.py
python3 scripts/generates/generate_speed_tiers.py
python3 scripts/generates/generate_batch_analysis.py
```

## 对战机制文档

- [回合流程（瀑布算法）](data/mechanics/turn_flow.md)
- [对战词条库](data/mechanics/battle_terms.md)
- [伤害与能力值公式](data/mechanics/damage_formula.md)
- [秒杀阈值分析](data/mechanics/kill_threshold.md)
- [精灵分析框架](docs/analyze-pokemon.md) — AI 分析精灵的完整框架，欢迎提 Issue 讨论

## 贡献

- 发现数据错误？分析框架有漏洞？欢迎 [提 Issue](https://github.com/zyx20180209/roco-claude/issues)
- 想改进工具或文档？欢迎 PR

## License

[MIT](./LICENSE)
