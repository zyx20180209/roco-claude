"""回放记录数据层：保存对战回放到 ~/.roco-battle/replays/<id>.json"""

import json
from datetime import datetime
from pathlib import Path

REPLAY_DIR = Path.home() / ".roco-battle" / "replays"


def _path(replay_id: str) -> Path:
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    return REPLAY_DIR / f"{replay_id}.json"


def list_replays() -> list:
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(p.stem for p in REPLAY_DIR.glob("*.json"))


def exists(replay_id: str) -> bool:
    return _path(replay_id).exists()


def create(replay_id: str, my_team: list, enemy_team: list) -> dict:
    if exists(replay_id):
        raise ValueError(f"replay '{replay_id}' 已存在")
    replay = {
        "id": replay_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "my_team": my_team,
        "enemy_team": enemy_team,
        "turns": [],
    }
    save(replay)
    return replay


def load(replay_id: str) -> dict:
    if not exists(replay_id):
        raise ValueError(f"replay '{replay_id}' 不存在")
    with open(_path(replay_id), encoding="utf-8") as f:
        return json.load(f)


def save(replay: dict):
    with open(_path(replay["id"]), "w", encoding="utf-8") as f:
        json.dump(replay, f, ensure_ascii=False, indent=2)


def delete(replay_id: str):
    p = _path(replay_id)
    if p.exists():
        p.unlink()


def add_turn(replay: dict,
             my_action: str, my_skill: str = None, my_damage: int = None,
             my_switch: str = None,
             enemy_action: str = None, enemy_skill: str = None,
             enemy_damage: int = None, enemy_switch: str = None,
             note: str = None) -> dict:
    """添加一个回合记录。action: attack/defend/status/switch/charge"""
    turn_num = len(replay["turns"]) + 1
    entry = {
        "turn": turn_num,
        "my": _action_entry(my_action, my_skill, my_damage, my_switch),
        "enemy": _action_entry(enemy_action, enemy_skill, enemy_damage, enemy_switch),
    }
    if note:
        entry["note"] = note
    replay["turns"].append(entry)
    return entry


def _action_entry(action, skill, damage, switch_to):
    e = {"action": action}
    if skill:
        e["skill"] = skill
    if damage is not None:
        e["damage"] = damage
    if switch_to:
        e["switch_to"] = switch_to
    return e
