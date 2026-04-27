"""Session 状态管理：保存对战进度到本地文件，支持读写。"""

import json
from datetime import datetime
from pathlib import Path

# 默认状态目录：~/.roco-battle/sessions/
DEFAULT_DIR = Path.home() / ".roco-battle" / "sessions"


def _session_dir() -> Path:
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DIR


def _path(session_id: str) -> Path:
    return _session_dir() / f"{session_id}.json"


def list_sessions() -> list:
    return sorted(p.stem for p in _session_dir().glob("*.json"))


def exists(session_id: str) -> bool:
    return _path(session_id).exists()


def create(session_id: str) -> dict:
    """创建一个新 session。已存在则报错。"""
    if exists(session_id):
        raise ValueError(f"session '{session_id}' 已存在")
    session = {
        "id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "my_team": [],          # [{pokemon, ivs, natures, skills, buff_layers}]
        "enemy_team": [],       # [{pokemon, observed_skills, guessed_skills}]
        "active": {"my_index": None, "enemy_index": None},
        "log": [],
    }
    save(session)
    return session


def load(session_id: str) -> dict:
    if not exists(session_id):
        raise ValueError(f"session '{session_id}' 不存在")
    with open(_path(session_id)) as f:
        return json.load(f)


def save(session: dict):
    with open(_path(session["id"]), "w") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)


def delete(session_id: str):
    p = _path(session_id)
    if p.exists():
        p.unlink()


# --- 队伍/精灵操作 ---

def make_my_pokemon(name: str, ivs: dict = None, natures: dict = None,
                    skills: list = None, buff_layers: dict = None,
                    bloodline: str = None) -> dict:
    """创建一只我方精灵的 session 条目。"""
    return {
        "pokemon": name,
        "ivs": ivs or {"hp": 10, "attack": 10, "special_attack": 10,
                       "defense": 0, "special_defense": 0, "speed": 10},
        "natures": natures or {"attack": "无", "speed": "无", "hp": "无", "defense": "无"},
        "skills": skills or [],  # 4 个技能名
        "buff_layers": buff_layers or {"attack": 0, "defense": 0, "special_defense": 0, "speed": 0},
        "bloodline": bloodline,  # 系别名 / "首领" / None
    }


def make_enemy_pokemon(name: str) -> dict:
    return {
        "pokemon": name,
        "observed_skills": [],
        "guessed_skills": [],
        "buff_layers": {"attack": 0, "defense": 0, "special_defense": 0, "speed": 0},
        "confirmed_stats": {},
        "hp_pct": 100,    # 剩余血量百分比（0-100）
        "energy": 10,     # 剩余能量（0-10）
    }


def log_event(session: dict, msg: str):
    session.setdefault("log", []).append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "msg": msg,
    })


# --- 队伍配置文件 ---

TEAMS_DIR = Path(__file__).resolve().parent / "teams"

# team 文件中的字段名 → session 内部字段名
_NATURE_TO_INTERNAL = {
    "HP": "hp",
    "物攻": "attack",
    "魔攻": "special_attack",
    "物防": "defense",
    "魔防": "special_defense",
    "速度": "speed",
}


def list_teams() -> list:
    if not TEAMS_DIR.exists():
        return []
    return sorted(p.stem for p in TEAMS_DIR.glob("*.json"))


def load_team_file(team_name: str) -> list:
    path = TEAMS_DIR / f"{team_name}.json"
    if not path.exists():
        raise ValueError(f"队伍配置文件不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def team_entry_to_my_pokemon(entry: dict) -> dict:
    """把 team 文件中的一条精灵记录转为 session 中的 my_pokemon 结构。"""
    name = entry["pokemon"]

    # 个体值：默认全 0，team 中显式填的项设为对应值
    ivs = {"hp": 0, "attack": 0, "special_attack": 0,
           "defense": 0, "special_defense": 0, "speed": 0}
    for k, v in (entry.get("ivs") or {}).items():
        # 兼容 team 中用中文 key 的情况
        internal_k = _NATURE_TO_INTERNAL.get(k, k)
        if internal_k in ivs:
            ivs[internal_k] = int(v)

    # 性格：team 中是 {"boost": "速度", "reduce": "物攻"} 形式
    natures = {"attack": "无", "special_attack": "无", "defense": "无",
               "special_defense": "无", "speed": "无", "hp": "无"}
    nature = entry.get("nature") or {}
    boost_field = _NATURE_TO_INTERNAL.get(nature.get("boost"))
    reduce_field = _NATURE_TO_INTERNAL.get(nature.get("reduce"))
    if boost_field and boost_field in natures:
        natures[boost_field] = "加"
    if reduce_field and reduce_field in natures:
        natures[reduce_field] = "减"

    # 技能：过滤掉 None
    skills = [s for s in (entry.get("skills") or []) if s]

    return make_my_pokemon(
        name=name,
        ivs=ivs,
        natures=natures,
        skills=skills,
        bloodline=entry.get("bloodline"),
    )
