"""即时对战助手 CLI 入口。

用法:
  python3 -m battle.cli new <session_id>
  python3 -m battle.cli list
  python3 -m battle.cli status <session_id>
  python3 -m battle.cli set-myteam <session_id> <p1> <p2> ...
  python3 -m battle.cli set-myskills <session_id> <pokemon> <s1> <s2> <s3> <s4>
  python3 -m battle.cli set-enemy <session_id> <slot> <pokemon>
  python3 -m battle.cli observe <session_id> my|enemy <pokemon> <skill>
  python3 -m battle.cli active <session_id> my|enemy <index>
  python3 -m battle.cli my-damages <session_id>
  python3 -m battle.cli enemy-damages <session_id>
  python3 -m battle.cli speed <session_id>
  python3 -m battle.cli delete <session_id>

加 --json 用 JSON 输出。
"""

import argparse
import sys

from . import commands, formatters


def main(argv=None):
    parser = argparse.ArgumentParser(prog="battle", description="洛克王国即时对战助手")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出所有 session")

    p_new = sub.add_parser("new", help="新建 session")
    p_new.add_argument("session_id")

    p_status = sub.add_parser("status", help="显示 session 状态")
    p_status.add_argument("session_id")

    p_del = sub.add_parser("delete", help="强制删除 session（不提示）")
    p_del.add_argument("session_id")

    p_end = sub.add_parser("end", help="结束对战（默认删除，加 --save 保留）")
    p_end.add_argument("session_id")
    p_end.add_argument("--save", action="store_true", help="保留 session 文件")

    p_team = sub.add_parser("set-myteam", help="设置我方 6 只精灵")
    p_team.add_argument("session_id")
    p_team.add_argument("pokemons", nargs="+")

    sub.add_parser("list-teams", help="列出 battle/teams/ 下所有队伍配置")

    p_load = sub.add_parser("load-myteam", help="从队伍配置文件加载我方队伍")
    p_load.add_argument("session_id")
    p_load.add_argument("team_name", help="文件名（不含 .json）")

    p_skills = sub.add_parser("set-myskills", help="设置我方某只精灵的 4 个技能")
    p_skills.add_argument("session_id")
    p_skills.add_argument("pokemon")
    p_skills.add_argument("skills", nargs="+")

    p_enemy = sub.add_parser("set-enemy", help="设置敌方第 N 位精灵（用 ? 表示未知占位）")
    p_enemy.add_argument("session_id")
    p_enemy.add_argument("slot", type=int)
    p_enemy.add_argument("pokemon", help="精灵名，或 ? 表示盲选占位")

    p_eteam = sub.add_parser("set-enemy-team", help="一次性设置敌方队伍（已知构成模式，可用 ? 占位）")
    p_eteam.add_argument("session_id")
    p_eteam.add_argument("pokemons", nargs="+", help="精灵名列表，? 表示未知")

    p_obs = sub.add_parser("observe", help="记录观察到的技能")
    p_obs.add_argument("session_id")
    p_obs.add_argument("side", choices=["my", "enemy"])
    p_obs.add_argument("pokemon")
    p_obs.add_argument("skill")

    p_upd = sub.add_parser("update-enemy", help="更新敌方精灵的状态（血量/能量/DoT层数）")
    p_upd.add_argument("session_id")
    p_upd.add_argument("pokemon")
    p_upd.add_argument("--hp", type=int, dest="hp_pct", help="剩余血量百分比 0-100")
    p_upd.add_argument("--energy", type=int, help="剩余能量 0-10")
    p_upd.add_argument("--poison", type=int, help="中毒总层数")
    p_upd.add_argument("--burn", type=int, help="灼烧总层数")
    p_upd.add_argument("--freeze", type=int, help="冻结总层数")

    p_act = sub.add_parser("active", help="设置在场精灵索引")
    p_act.add_argument("session_id")
    p_act.add_argument("side", choices=["my", "enemy"])
    p_act.add_argument("index", type=int)

    p_md = sub.add_parser("my-damages", help="计算我方技能对敌方伤害")
    p_md.add_argument("session_id")

    p_bt = sub.add_parser("bench-threats", help="计算敌方场下精灵对我方在场精灵的威胁")
    p_bt.add_argument("session_id")

    p_kc = sub.add_parser("kill-chain", help="斩杀推演：我方技能能否本回合斩杀对方（含DoT/冻结/对方防御）")
    p_kc.add_argument("session_id")

    p_csk = sub.add_parser("set-custom-skill", help="设置自定义技能（用游戏显示威力，绕过基础威力推算）")
    p_csk.add_argument("session_id")
    p_csk.add_argument("side", choices=["my", "enemy"])
    p_csk.add_argument("slot", type=int, help="技能位 0~3")
    p_csk.add_argument("name", help="技能名（用于显示）")
    p_csk.add_argument("shown_power", type=float, help="游戏内显示威力")
    p_csk.add_argument("--hits", type=int, default=1, dest="hit_count")
    p_csk.add_argument("--extra", type=float, default=1.0, dest="extra_mult", help="隐藏乘区（顺风1.5等）")

    p_ed = sub.add_parser("enemy-damages", help="计算敌方所有可能技能对我方伤害")
    p_ed.add_argument("session_id")
    p_ed.add_argument("--no-guess", action="store_true", help="只看已观察技能，不含推测")

    p_sp = sub.add_parser("speed", help="速度比较")
    p_sp.add_argument("session_id")

    p_infer = sub.add_parser("infer-atk", help="根据实际伤害反推对方攻击配置")
    p_infer.add_argument("session_id")
    p_infer.add_argument("skill", help="对方使用的技能名")
    p_infer.add_argument("damage", type=int, help="实际造成的伤害数值")

    args = parser.parse_args(argv)
    return _dispatch(args)


def _dispatch(args) -> int:
    try:
        result, formatter = _route(args)
    except (ValueError, KeyError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(formatters.format_generic(result))
    else:
        print(formatter(result))
    return 0


def _route(args):
    """根据 args.cmd 调用对应的业务函数，返回 (result, formatter)。"""
    cmd = args.cmd
    if cmd == "list":
        return commands.cmd_list(), formatters.format_list
    if cmd == "new":
        return commands.cmd_new(args.session_id), formatters.format_generic
    if cmd == "status":
        return commands.cmd_status(args.session_id), formatters.format_status
    if cmd == "delete":
        return commands.cmd_delete(args.session_id), formatters.format_generic
    if cmd == "end":
        return commands.cmd_end(args.session_id, save=args.save), formatters.format_generic
    if cmd == "set-myteam":
        return commands.cmd_set_my_team(args.session_id, args.pokemons), formatters.format_generic
    if cmd == "list-teams":
        return commands.cmd_list_teams(), formatters.format_generic
    if cmd == "load-myteam":
        return commands.cmd_load_my_team(args.session_id, args.team_name), formatters.format_generic
    if cmd == "set-myskills":
        return commands.cmd_set_my_skills(args.session_id, args.pokemon, args.skills), formatters.format_generic
    if cmd == "set-enemy":
        return commands.cmd_set_enemy(args.session_id, args.slot, args.pokemon), formatters.format_generic
    if cmd == "set-enemy-team":
        return commands.cmd_set_enemy_team(args.session_id, args.pokemons), formatters.format_generic
    if cmd == "observe":
        return commands.cmd_observe(args.session_id, args.side, args.pokemon, args.skill), formatters.format_generic
    if cmd == "update-enemy":
        return commands.cmd_update_enemy(args.session_id, args.pokemon,
                                         args.hp_pct, args.energy,
                                         args.poison, args.burn, args.freeze), formatters.format_generic
    if cmd == "active":
        return commands.cmd_set_active(args.session_id, args.side, args.index), formatters.format_generic
    if cmd == "my-damages":
        return commands.cmd_my_damages(args.session_id), formatters.format_damages
    if cmd == "enemy-damages":
        return commands.cmd_enemy_damages(args.session_id, include_guessed=not args.no_guess), formatters.format_damages
    if cmd == "bench-threats":
        return commands.cmd_bench_threats(args.session_id), formatters.format_bench_threats
    if cmd == "kill-chain":
        return commands.cmd_kill_chain(args.session_id), formatters.format_kill_chain
    if cmd == "set-custom-skill":
        return commands.cmd_set_custom_skill(
            args.session_id, args.side, args.slot, args.name, args.shown_power,
            args.hit_count, args.extra_mult
        ), formatters.format_generic
    if cmd == "speed":
        return commands.cmd_speed(args.session_id), formatters.format_speed
    if cmd == "infer-atk":
        return commands.cmd_infer_atk(args.session_id, args.skill, args.damage), formatters.format_generic
    raise ValueError(f"未知命令: {cmd}")


if __name__ == "__main__":
    sys.exit(main())
