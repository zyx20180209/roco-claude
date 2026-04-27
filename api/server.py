"""
洛克王国伤害计算 API
无外部依赖，使用 Python 标准库 http.server

端点：
  POST /damage   — 通用伤害计算
  POST /swarm    — 虫群斩杀计算
  GET  /health   — 健康检查

启动：python3 api/server.py [port]  (默认 8080)
"""

import json
import math
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.tools.damage_calculator import calc_stat, calc_hp, stat_diff_power

# 加载数据
with open(ROOT / "data" / "raw" / "pokemon.json") as f:
    _pm_raw = json.load(f)
POKEMON_MAP = {p["display_name"]: p for p in _pm_raw}

with open(ROOT / "data" / "raw" / "skills.json") as f:
    _sk_raw = json.load(f)
SKILL_MAP = {s["name"]: s for s in _sk_raw}
DEFENSE_SKILLS = {}
for s in _sk_raw:
    if s["category"] != "防御":
        continue
    m = re.search(r"减伤(\d+)%", s["description"])
    is_interrupt = bool(re.search(r"打断|中断", s["description"]))
    DEFENSE_SKILLS[s["name"]] = {
        "name": s["name"],
        "attribute": s["attribute"],
        "mitigation": int(m.group(1)) if m else (100 if is_interrupt else 0),
        "is_interrupt": is_interrupt,
        "description": s["description"],
    }

STAT_DIFF_SKILLS = {
    "闪击": "speed",
    "鸣沙陷阱": "defense",
}

TYPE_CHART = {}
with open(ROOT / "data" / "raw" / "type_chart.json") as f:
    content = f.read()
    tc = json.loads(content[content.find("{"):])
    TYPE_CHART = tc.get("multiplier_matrix", {})


def type_effectiveness(atk_type: str, def_attrs: list) -> float:
    mults = [TYPE_CHART.get(atk_type, {}).get(a, 1.0) for a in def_attrs]
    if any(m == 0 for m in mults):
        return 0.0
    if len(mults) == 1:
        return mults[0]
    eff = sum(1 for m in mults if m > 1)
    res = sum(1 for m in mults if m < 1)
    if eff == 2: return 3.0
    if res == 2: return 1/3
    if eff == 1 and res == 1: return 1.0
    if eff == 1: return 2.0
    if res == 1: return 0.5
    return 1.0


def calc_damage_full(body: dict) -> dict:
    """
    通用伤害计算。

    body 字段：
      atk_base, atk_iv, atk_nature          攻击方攻击种族/个体/性格
      def_base, def_iv, def_nature          防御方防御种族/个体/性格
      hp_base, hp_iv, hp_nature             防御方HP种族/个体/性格
      shown_power                           显示威力（已含本系/克制/buff）
      hit_count                             连击数（默认1）
      hidden_mult                           隐藏乘区（顺风1.5/破空1.75等，默认1.0）
      mitigation_pct                        减伤系数%（默认0）
      hp_remain_pct                         剩余血量%（默认100）
      skill_name                            技能名（可选，自动计算本系/克制/属性差）
      atk_pokemon                           攻击方精灵名（可选，用于本系判断）
      def_pokemon                           防御方精灵名（可选，用于克制判断）
    """
    # 技能名模式：自动计算显示威力
    skill_name = body.get("skill_name")
    if skill_name and skill_name in SKILL_MAP:
        skill = SKILL_MAP[skill_name]
        base_power = int(skill["power"]) if skill["power"] else 0
        category = skill["category"]
        atk_attr = skill["attribute"]

        # 属性差技能
        diff_field = STAT_DIFF_SKILLS.get(skill_name)
        if diff_field:
            atk_p = POKEMON_MAP.get(body.get("atk_pokemon", ""))
            def_p = POKEMON_MAP.get(body.get("def_pokemon", ""))
            if atk_p and def_p:
                atk_val = calc_stat(int(atk_p["stats"][diff_field]), 10, "加" if diff_field == "speed" else "无")
                def_val = calc_stat(int(def_p["stats"][diff_field]), 10, "无")
                base_power = stat_diff_power(atk_val - def_val)

        # 本系
        atk_p = POKEMON_MAP.get(body.get("atk_pokemon", ""))
        stab = 1.25 if atk_p and atk_attr in atk_p.get("attributes_list", []) else 1.0

        # 克制
        def_p = POKEMON_MAP.get(body.get("def_pokemon", ""))
        type_mult = type_effectiveness(atk_attr, def_p["attributes_list"]) if def_p else 1.0

        shown_power = base_power * stab * type_mult
    else:
        shown_power = float(body.get("shown_power", 100))
        category = body.get("category", "物攻")

    hidden_mult = float(body.get("hidden_mult", 1.0))
    hit_count = int(body.get("hit_count", 1))
    mitigation = 1 - float(body.get("mitigation_pct", 0)) / 100
    hp_remain = float(body.get("hp_remain_pct", 100)) / 100

    atk_stat = calc_stat(
        int(body["atk_base"]), int(body.get("atk_iv", 10)), body.get("atk_nature", "无")
    )
    def_stat = calc_stat(
        int(body["def_base"]), int(body.get("def_iv", 0)), body.get("def_nature", "无")
    )
    hp_max = calc_hp(
        int(body["hp_base"]), int(body.get("hp_iv", 10)), body.get("hp_nature", "无")
    )
    hp_cur = max(1, round(hp_max * hp_remain))

    eff_power = shown_power * hidden_mult
    damage = int(round(atk_stat * hit_count * eff_power * mitigation * 37 / 41) / def_stat)
    pct = round(100 * damage / hp_cur, 1)
    kill_turn = 1 if damage >= hp_cur else math.ceil(hp_cur / damage)

    return {
        "damage": damage,
        "hp_cur": hp_cur,
        "hp_max": hp_max,
        "pct": pct,
        "kill_turn": kill_turn,
        "one_shot": damage >= hp_cur,
        "atk_stat": atk_stat,
        "def_stat": def_stat,
        "eff_power": round(eff_power, 2),
    }


def calc_swarm(body: dict) -> dict:
    """
    虫群斩杀计算。

    body 字段：
      attacker          花衣蝶/陨星虫/花魁蜂后/女王蜂
      atk_nature        加/无（默认无）
      atk_iv            攻击个体（默认10）
      bonus_power       奉献威力+20次数（默认0）
      bonus_hit         奉献连击+1次数（默认0）
      bonus_poison      奉献中毒+2次数（默认0）
      extra_power_pct   其他威力加成%（默认0）
      def_pokemon       防御方精灵名（可选）
      hp_base/iv/nature 防御方HP
      def_base/iv/nature 防御方物防
      def_buff_pct      物防buff%（默认0）
      mitigation_pct    减伤%（默认0）
      hp_remain_pct     剩余血量%（默认100）
    """
    ATTACKERS = {
        "花衣蝶":   {"atk_base": 67, "attrs": ["草", "虫"], "innate": 1.0},
        "陨星虫":   {"atk_base": 78, "attrs": ["虫"],       "innate": 1.0},
        "花魁蜂后": {"atk_base": 54, "attrs": ["翼", "虫"], "innate": 1.5},
        "女王蜂":   {"atk_base": 50, "attrs": ["翼", "虫"], "innate": 1.75},
    }
    attacker_name = body.get("attacker", "陨星虫")
    a = ATTACKERS.get(attacker_name, ATTACKERS["陨星虫"])

    atk_iv = int(body.get("atk_iv", 10))
    atk_nature = body.get("atk_nature", "无")
    atk_stat = round(calc_stat(a["atk_base"], atk_iv, atk_nature) * a["innate"])

    bonus_power = int(body.get("bonus_power", 0))
    bonus_hit = int(body.get("bonus_hit", 0))
    bonus_poison = int(body.get("bonus_poison", 0))
    extra_pct = float(body.get("extra_power_pct", 0)) / 100

    base_power = 20 + bonus_power * 20
    hit_count = 1 + bonus_hit
    stab = 1.25  # 虫系技能，3只都含虫系

    # 克制
    def_p = POKEMON_MAP.get(body.get("def_pokemon", ""))
    type_mult = type_effectiveness("虫", def_p["attributes_list"]) if def_p else 1.0

    eff_power = base_power * stab * type_mult * (1 + extra_pct)

    def_buff = 1 + float(body.get("def_buff_pct", 0)) / 100
    mitigation = 1 - float(body.get("mitigation_pct", 0)) / 100
    hp_remain = float(body.get("hp_remain_pct", 100)) / 100

    hp_base = int(body.get("hp_base", def_p["stats"]["hp"] if def_p else 100))
    hp_iv = int(body.get("hp_iv", 10))
    hp_nature = body.get("hp_nature", "无")
    def_base = int(body.get("def_base", def_p["stats"]["defense"] if def_p else 100))
    def_iv = int(body.get("def_iv", 0))
    def_nature = body.get("def_nature", "无")

    hp_max = calc_hp(hp_base, hp_iv, hp_nature)
    def_stat = round(calc_stat(def_base, def_iv, def_nature) * def_buff)
    hp_cur = max(1, round(hp_max * hp_remain))

    damage = int(round(atk_stat * hit_count * eff_power * mitigation * 37 / 41) / def_stat)

    poison_layers = bonus_poison * 2
    poison_per_turn = math.floor(hp_max * 0.03) * poison_layers

    instant_kill = damage >= hp_cur
    poison_finish = not instant_kill and poison_layers > 0 and poison_per_turn >= (hp_cur - damage)

    return {
        "damage": damage,
        "hp_cur": hp_cur,
        "hp_max": hp_max,
        "pct": round(100 * damage / hp_cur, 1),
        "instant_kill": instant_kill,
        "poison_finish": poison_finish,
        "poison_per_turn": poison_per_turn,
        "kill_turn": 1 if instant_kill else math.ceil(hp_cur / damage),
        "atk_stat": atk_stat,
        "def_stat": def_stat,
        "eff_power": round(eff_power, 2),
        "type_mult": type_mult,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    def send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "pokemon": len(POKEMON_MAP), "skills": len(SKILL_MAP)})
        elif self.path == "/defense_skills":
            self.send_json(200, list(DEFENSE_SKILLS.values()))
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except Exception:
            self.send_json(400, {"error": "invalid JSON"})
            return

        try:
            if self.path == "/damage":
                self.send_json(200, calc_damage_full(body))
            elif self.path == "/swarm":
                self.send_json(200, calc_swarm(body))
            else:
                self.send_json(404, {"error": "not found"})
        except (KeyError, ValueError) as e:
            self.send_json(400, {"error": str(e)})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"API server running on http://localhost:{port}")
    print("  GET  /health")
    print("  GET  /defense_skills")
    print("  POST /damage")
    print("  POST /swarm")
    server.serve_forever()
