"""replay CLI 入口。

用法:
  python3 -m replay.cli new <id> --my P1 P2 ... --enemy P1 P2 ...
  python3 -m replay.cli list
  python3 -m replay.cli turn <id> --my-action ATK --my-skill ... [其他]
  python3 -m replay.cli show <id>
  python3 -m replay.cli delete <id>

加 --json 用 JSON 输出。
"""

import argparse
import json
import sys

from . import storage


ACTION_ZH = {
    "attack": "攻击", "defend": "防御", "status": "状态",
    "switch": "换人", "charge": "聚能", "unknown": "未知",
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="replay", description="洛克王国对战回放记录")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建回放")
    p_new.add_argument("replay_id")
    p_new.add_argument("--my", nargs="+", dest="my_team", required=True, help="我方队伍精灵名")
    p_new.add_argument("--enemy", nargs="+", dest="enemy_team", required=True, help="敌方队伍精灵名")

    sub.add_parser("list", help="列出所有回放")

    p_t = sub.add_parser("turn", help="记录一个回合")
    p_t.add_argument("replay_id")
    p_t.add_argument("--my-action", required=True,
                     choices=["attack", "defend", "status", "switch", "charge"], dest="my_action")
    p_t.add_argument("--my-skill", dest="my_skill")
    p_t.add_argument("--my-damage", type=int, dest="my_damage")
    p_t.add_argument("--my-switch", dest="my_switch", help="换入精灵名")
    p_t.add_argument("--enemy-action",
                     choices=["attack", "defend", "status", "switch", "charge", "unknown"],
                     dest="enemy_action", default="unknown")
    p_t.add_argument("--enemy-skill", dest="enemy_skill")
    p_t.add_argument("--enemy-damage", type=int, dest="enemy_damage")
    p_t.add_argument("--enemy-switch", dest="enemy_switch", help="换入精灵名")
    p_t.add_argument("--note", help="备注")

    p_show = sub.add_parser("show", help="显示回放内容")
    p_show.add_argument("replay_id")

    p_del = sub.add_parser("delete", help="删除回放")
    p_del.add_argument("replay_id")

    args = parser.parse_args(argv)
    return _dispatch(args)


def _dispatch(args) -> int:
    try:
        result, formatter = _route(args)
    except (ValueError, KeyError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(formatter(result))
    return 0


def _route(args):
    cmd = args.cmd
    if cmd == "new":
        return storage.create(args.replay_id, args.my_team, args.enemy_team), _fmt_generic
    if cmd == "list":
        return storage.list_replays(), _fmt_list
    if cmd == "turn":
        r = storage.load(args.replay_id)
        entry = storage.add_turn(
            r, args.my_action, args.my_skill, args.my_damage, args.my_switch,
            args.enemy_action, args.enemy_skill, args.enemy_damage, args.enemy_switch,
            args.note,
        )
        storage.save(r)
        return entry, _fmt_turn
    if cmd == "show":
        return storage.load(args.replay_id), _fmt_replay
    if cmd == "delete":
        storage.delete(args.replay_id)
        return {"deleted": args.replay_id}, _fmt_generic
    raise ValueError(f"未知命令: {cmd}")


def _fmt_generic(result) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def _fmt_list(result) -> str:
    if not result:
        return "（无回放）"
    return "回放列表:\n  " + "\n  ".join(result)


def _fmt_turn(entry: dict) -> str:
    my, en = entry["my"], entry["enemy"]
    return f"已记录第{entry['turn']}回合\n  我方: {_fmt_action(my)}\n  敌方: {_fmt_action(en)}"


def _fmt_action(side: dict) -> str:
    a = ACTION_ZH.get(side.get("action", ""), side.get("action", ""))
    parts = [a]
    if side.get("skill"):
        parts.append(side["skill"])
    if side.get("switch_to"):
        parts.append(f"→{side['switch_to']}")
    if side.get("damage") is not None:
        parts.append(f"{side['damage']}伤")
    return " ".join(parts)


def _fmt_replay(result: dict) -> str:
    lines = [
        f"回放: {result['id']}  ({result.get('created_at','')})",
        f"我方: {' / '.join(result['my_team'])}",
        f"敌方: {' / '.join(result['enemy_team'])}",
        f"共 {len(result['turns'])} 回合",
        "",
    ]
    for t in result["turns"]:
        line = f"  第{t['turn']:>2}回合  我方: {_fmt_action(t['my']):20s}  敌方: {_fmt_action(t['enemy'])}"
        if t.get("note"):
            line += f"  [{t['note']}]"
        lines.append(line)
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
