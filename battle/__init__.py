"""即时对战助手 — 子命令链路的核心逻辑。

模块结构：
- core.py        数据加载与基础计算
- session.py     对战 session 的状态读写
- commands.py    业务逻辑（被 CLI / REPL / API 共享）
- formatters.py  输出格式化
- cli.py         argparse 入口
"""
