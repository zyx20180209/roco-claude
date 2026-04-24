# roco-claude

洛克王国 PVP 数据分析与战斗计算工具集。

> 🤖 **本项目全部由 AI 完成编写、设计与整理，没有一点人类操作。**
> 人类仅提供需求描述、测试反馈和游戏数据验证。

## 项目简介

本项目基于洛克王国 Wiki 和《洛克计算器 2.0》的公式，提供：

- **精灵数据库**：239 只精灵的种族值、属性、特性、技能池、属性弱点
- **战斗计算工具**：伤害计算、速度档位、种族值排行
- **网页小工具**：可直接在浏览器使用的计算器（支持 GitHub Pages 部署）
- **对战机制文档**：回合流程、印记/debuff 系统、伤害公式、秒杀阈值分析

## 目录结构

```
roco-claude/
├── apps/                    # 网页小工具（可部署到 GitHub Pages）
│   ├── swarm_calculator/    # 虫群斩杀计算器
│   └── damage_calculator/   # 伤害计算器
├── data/
│   ├── raw/                 # 原始数据（精灵、技能、属性克制）
│   ├── processed/           # 脚本生成的排行榜和分析数据
│   ├── analysis/            # 单体精灵 AI 分析报告（~150只）
│   ├── meta/                # 跨精灵综合分析（环境、克制关系）
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
- `https://zyx20180209.github.io/roco-claude/apps/swarm_calculator/`
- `https://zyx20180209.github.io/roco-claude/apps/damage_calculator/`

### 本地运行

```bash
./apps/serve.sh          # 默认 8000 端口
./apps/serve.sh 8080     # 自定义端口
```

然后打开 `http://localhost:8000/apps/`

### 虫群斩杀计算器

- 选择释放虫群的精灵（花衣蝶 / 陨星虫 / 花魁蜂后 / 女王蜂）
- 输入奉献层数（威力+20 / 连击+1 / 中毒+2）
- 输入防御方精灵名称（自动获取种族值和属性克制）
- 自动判断当场秒杀 / 回合末毒死 / 无法斩杀

### 伤害计算器

- **按显示威力**：直接输入游戏内看到的威力数字（已含本系/克制/攻击buff）
- **按技能名称**：输入技能名自动计算本系、克制、属性差（闪击/鸣沙陷阱阶梯）
- 支持隐藏乘区：顺风 / 破空 / 风起印记
- 攻防双方支持精灵名称自动填入种族值

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
