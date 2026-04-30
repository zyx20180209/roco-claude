"""
analysis/state_builder.py

从回放 JSON 重建每回合结束后的完整精灵状态快照。

用法:
    from analysis.state_builder import build_states
    states = build_states(replay)  # replay 是已解析的 dict
    # states[0] = 初始状态
    # states[n] = 第n回合结束后的状态
"""

import copy
import json
import math
from pathlib import Path


def build_states(replay: dict) -> list[dict]:
    """
    返回长度为 len(turns)+1 的列表。
    states[0] = 初始状态（所有精灵满血满能量）
    states[n] = 第n回合结束后的状态

    每个状态结构:
    {
      "my":     {pokemon_name: PokemonState},
      "enemy":  {pokemon_name: PokemonState},
      "field":  {"my": {"marks": []}, "enemy": {"marks": []}}
    }

    PokemonState:
    {
      "hp_pct": float,       # 当前血量百分比
      "hp_cur": int|None,    # 当前血量（仅我方有精确值）
      "hp_max": int|None,    # 血量上限（仅我方有精确值）
      "energy": int,         # 当前能量 0-10
      "active": bool,        # 是否在场
      "fainted": bool,       # 是否战死
      "boss": bool,          # 是否已首领化
      "buffs": dict,         # 临时 buff 层数
      "dots": dict,          # DoT 层数 {poison, burn, freeze}
      "passive_effects": dict  # 永久效果
    }
    """
    state = _init_state(replay)
    states = [copy.deepcopy(state)]

    for turn in replay.get("turns", []):
        for change in turn.get("changes", []):
            _apply_change(state, change)
        _end_of_turn(state, turn)
        states.append(copy.deepcopy(state))

    return states


def _init_state(replay: dict) -> dict:
    state = {"my": {}, "enemy": {}, "field": {"my": {"marks": []}, "enemy": {"marks": []}}}
    starting = replay.get("starting_active", {})
    for side in ("my", "enemy"):
        team = replay.get(f"{side}_team", [])
        starter = starting.get(side) or (team[0] if team else None)
        for name in team:
            state[side][name] = {
                "hp_pct": 100.0, "hp_cur": None, "hp_max": None,
                "energy": 10, "active": name == starter, "fainted": False, "boss": False,
                "buffs": {"attack": 0, "special_attack": 0, "defense": 0,
                          "special_defense": 0, "speed": 0, "hit_count": 0, "power": 0},
                "dots": {"poison": 0, "burn": 0, "freeze": 0},
                "passive_effects": {"attack_pct": 0, "special_attack_pct": 0,
                                    "defense_pct": 0, "special_defense_pct": 0,
                                    "speed_flat": 0, "power_flat": 0,
                                    "hit_count": 0, "moe": 0},
            }
    return state


def _apply_change(state: dict, c: dict):
    side = c["side"]
    name = c["pokemon"]
    s = state[side].get(name)
    if s is None:
        return

    if c.get("hp_pct") is not None:
        s["hp_pct"] = c["hp_pct"]
    if c.get("hp_cur") is not None:
        s["hp_cur"] = c["hp_cur"]
    if c.get("hp_max") is not None:
        s["hp_max"] = c["hp_max"]
    if c.get("energy_delta") is not None:
        s["energy"] = max(0, min(10, s["energy"] + c["energy_delta"]))
    if c.get("boss"):
        s["boss"] = True
    if c.get("fainted"):
        s["fainted"] = True
        s["hp_pct"] = 0
        s["active"] = False
    if c.get("entered"):
        for pk in state[side].values():
            pk["active"] = False
        s["active"] = True
    if c.get("exited"):
        s["active"] = False
        for k in s["buffs"]:
            s["buffs"][k] = 0
        s["dots"]["poison"] = 0
        s["dots"]["burn"] = 0
    if c.get("buffs"):
        for k, v in c["buffs"].items():
            s["buffs"][k] = s["buffs"].get(k, 0) + v
    if c.get("dots"):
        for k, v in c["dots"].items():
            s["dots"][k] = max(0, s["dots"].get(k, 0) + v)
    if c.get("passive_effects"):
        for k, v in c["passive_effects"].items():
            s["passive_effects"][k] = s["passive_effects"].get(k, 0) + v
    if c.get("marks_added"):
        state["field"][side]["marks"].extend(c["marks_added"])
    if c.get("marks_removed"):
        state["field"][side]["marks"] = [
            m for m in state["field"][side]["marks"] if m not in c["marks_removed"]
        ]


def _end_of_turn(state: dict, turn: dict):
    """回合末结算：留场精灵灼烧减半。"""
    exited = {
        f"{c['side']}_{c['pokemon']}"
        for c in turn.get("changes", [])
        if c.get("exited") or c.get("fainted")
    }
    for side in ("my", "enemy"):
        for name, s in state[side].items():
            if s["active"] and f"{side}_{name}" not in exited:
                if s["dots"]["burn"] > 0:
                    s["dots"]["burn"] = math.floor(s["dots"]["burn"] / 2)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "analysis/replays/250430-03.json"
    with open(path, encoding="utf-8") as f:
        replay = json.load(f)
    states = build_states(replay)
    print(f"共 {len(states)} 个状态快照（含初始）")
    for i, st in enumerate(states):
        label = "初始" if i == 0 else f"第{i}回合后"
        active_my = next((n for n, s in st["my"].items() if s["active"]), "无")
        active_en = next((n for n, s in st["enemy"].items() if s["active"]), "无")
        print(f"  {label}: 我方在场={active_my}, 敌方在场={active_en}")
