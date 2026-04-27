"""业务逻辑层：被 CLI / REPL / API 共享。

每个 cmd_* 函数：
- 接收原始参数（精灵名、session_id 等）
- 操作 session 状态
- 返回结构化数据（dict），不直接 print
- 错误抛 ValueError
"""

from . import core, session as ss


# === Session 管理 ===

def cmd_new(session_id: str) -> dict:
    sess = ss.create(session_id)
    return {"created": session_id, "session": sess}


def cmd_list() -> dict:
    return {"sessions": ss.list_sessions()}


def cmd_status(session_id: str) -> dict:
    sess = ss.load(session_id)
    return {"session": sess}


def cmd_delete(session_id: str) -> dict:
    ss.delete(session_id)
    return {"deleted": session_id}


def cmd_end(session_id: str, save: bool = False) -> dict:
    """结束对战。默认删除 session，加 --save 则保留。"""
    if not ss.exists(session_id):
        raise ValueError(f"session '{session_id}' 不存在")
    if save:
        return {"session_id": session_id, "action": "saved", "path": str(ss._path(session_id))}
    ss.delete(session_id)
    return {"session_id": session_id, "action": "deleted"}


def cmd_infer_atk(session_id: str, skill_name: str, actual_damage: int) -> dict:
    """根据实际伤害反推对方攻击能力值，并匹配可能的个体/性格组合。"""
    sess = ss.load(session_id)
    me = _active(sess, "my")
    enemy = _active(sess, "enemy")
    if not me or not enemy:
        raise ValueError("双方在场精灵都需要先设置")

    my_p = core.POKEMON[me["pokemon"]]
    enemy_p = core.POKEMON[enemy["pokemon"]]

    skill = core.SKILLS.get(skill_name)
    if not skill:
        raise ValueError(f"未知技能：{skill_name}")

    sp = core.shown_power(skill_name, enemy_p, my_p)
    if not sp:
        raise ValueError(f"无法计算 {skill_name} 的显示威力")

    def_field = "defense" if sp["category"] == "物攻" else "special_defense"
    def_iv = me.get("ivs", {}).get(def_field, 0)
    def_nature = me.get("natures", {}).get(def_field, "无")
    def_stat = core.calc_stat(int(my_p["stats"][def_field]), def_iv, def_nature)

    # 反推攻击能力值（新公式）
    # damage = INT(ROUND(atk × hit × shown × 37/41) / def)
    # → ROUND(...) ∈ [damage × def, (damage+1) × def)
    # → atk × hit × shown × 37/41 ∈ [damage × def - 0.5, (damage+1) × def - 0.5)
    # → atk ∈ [(damage × def - 0.5) × 41/37 / (hit × shown), ((damage+1) × def - 0.5) × 41/37 / (hit × shown))
    hit = sp["hit_count"]
    shown = sp["shown"]
    factor = hit * shown * 37 / 41
    atk_min = (actual_damage * def_stat - 0.5) / factor
    atk_max = ((actual_damage + 1) * def_stat - 0.5) / factor

    atk_field = "attack" if sp["category"] == "物攻" else "special_attack"
    base = int(enemy_p["stats"][atk_field])

    # 枚举所有 iv(0-10) × nature(加/无/减) 组合，找落在区间内的
    matches = []
    for iv in range(11):
        for nat in ("加", "无", "减"):
            stat = core.calc_stat(base, iv, nat)
            if atk_min <= stat <= atk_max:
                matches.append({"iv": iv, "nature": nat, "atk_stat": stat})

    # 存入 session
    enemy["confirmed_stats"][atk_field] = round((atk_min + atk_max) / 2)
    ss.save(sess)

    return {
        "skill": skill_name,
        "actual_damage": actual_damage,
        "shown_power": round(shown, 1),
        "def_stat": def_stat,
        "inferred_atk": enemy["confirmed_stats"][atk_field],
        "inferred_atk_range": [round(atk_min, 1), round(atk_max, 1)],
        "saved_to": f"enemy.confirmed_stats.{atk_field}",
    }

    """结束对战。默认删除 session，加 --save 则保留。"""
    if not ss.exists(session_id):
        raise ValueError(f"session '{session_id}' 不存在")
    if save:
        return {"session_id": session_id, "action": "saved", "path": str(ss._path(session_id))}
    ss.delete(session_id)
    return {"session_id": session_id, "action": "deleted"}





# === 我方设置 ===

def cmd_list_teams() -> dict:
    """列出 battle/teams/ 下所有可用队伍。"""
    return {"teams": ss.list_teams()}


def cmd_load_my_team(session_id: str, team_name: str) -> dict:
    """从 battle/teams/<team_name>.json 加载我方队伍到 session。"""
    sess = ss.load(session_id)
    entries = ss.load_team_file(team_name)

    my_team = []
    invalid_skills = []
    for entry in entries:
        if entry["pokemon"] not in core.POKEMON:
            raise ValueError(f"未知精灵: {entry['pokemon']}")
        for s in (entry.get("skills") or []):
            if s and s not in core.SKILLS:
                invalid_skills.append(s)
        my_team.append(ss.team_entry_to_my_pokemon(entry))

    if invalid_skills:
        raise ValueError(f"未知技能: {', '.join(invalid_skills)}")

    sess["my_team"] = my_team
    ss.log_event(sess, f"load my team from {team_name}")
    ss.save(sess)
    return {
        "team_name": team_name,
        "loaded": len(my_team),
        "my_team": [
            {"pokemon": m["pokemon"], "skills": m["skills"], "bloodline": m["bloodline"]}
            for m in my_team
        ],
    }


def cmd_set_my_team(session_id: str, names: list) -> dict:
    """一次性设置我方 6 只精灵（仅名字，技能等后续单独设置）。"""
    sess = ss.load(session_id)
    for n in names:
        if n not in core.POKEMON:
            raise ValueError(f"未知精灵：{n}")
    sess["my_team"] = [ss.make_my_pokemon(n) for n in names]
    ss.log_event(sess, f"set my team: {names}")
    ss.save(sess)
    return {"my_team": [m["pokemon"] for m in sess["my_team"]]}


def cmd_set_my_skills(session_id: str, pokemon: str, skills: list) -> dict:
    """设置我方某只精灵的 4 个技能。"""
    sess = ss.load(session_id)
    target = next((m for m in sess["my_team"] if m["pokemon"] == pokemon), None)
    if not target:
        raise ValueError(f"我方队伍中没有：{pokemon}")
    for s in skills:
        if s not in core.SKILLS:
            raise ValueError(f"未知技能：{s}")
    target["skills"] = skills
    ss.log_event(sess, f"set skills for {pokemon}: {skills}")
    ss.save(sess)
    return {"pokemon": pokemon, "skills": skills}


def cmd_set_my_ivs(session_id: str, pokemon: str, ivs: dict, natures: dict = None) -> dict:
    """设置我方某只精灵的个体值和性格（可选）。"""
    sess = ss.load(session_id)
    target = next((m for m in sess["my_team"] if m["pokemon"] == pokemon), None)
    if not target:
        raise ValueError(f"我方队伍中没有：{pokemon}")
    target["ivs"].update(ivs)
    if natures:
        target["natures"].update(natures)
    ss.save(sess)
    return {"pokemon": pokemon, "ivs": target["ivs"], "natures": target["natures"]}


# === 对方设置 ===

def cmd_set_enemy(session_id: str, slot: int, name: str) -> dict:
    """设置敌方第 slot 位（0~5）。

    name="?" 表示盲选占位符（精灵未知）；
    name=精灵名 表示已知构成（个体/性格/技能仍未知，自动拉热门配招推测）。
    """
    sess = ss.load(session_id)
    if slot < 0 or slot > 5:
        raise ValueError("slot 必须在 0~5")
    while len(sess["enemy_team"]) <= slot:
        sess["enemy_team"].append(None)

    if name == "?":
        entry = {"pokemon": None, "observed_skills": [], "guessed_skills": [],
                 "buff_layers": {"attack": 0, "defense": 0, "special_defense": 0, "speed": 0}}
        sess["enemy_team"][slot] = entry
        ss.log_event(sess, f"enemy slot {slot}: unknown (placeholder)")
        ss.save(sess)
        return {"slot": slot, "pokemon": None, "mode": "blind"}

    if name not in core.POKEMON:
        raise ValueError(f"未知精灵：{name}")
    entry = ss.make_enemy_pokemon(name)
    entry["guessed_skills"] = list(core.HOT_SKILLS.get(name, []))
    sess["enemy_team"][slot] = entry
    ss.log_event(sess, f"enemy slot {slot}: {name}")
    ss.save(sess)
    return {"slot": slot, "pokemon": name, "mode": "known", "guessed_skills": entry["guessed_skills"]}


def cmd_set_enemy_team(session_id: str, names: list) -> dict:
    """一次性设置敌方队伍（已知构成模式）。names 中可用 '?' 表示未知位。"""
    sess = ss.load(session_id)
    if len(names) > 6:
        raise ValueError("最多 6 只精灵")
    for n in names:
        if n != "?" and n not in core.POKEMON:
            raise ValueError(f"未知精灵：{n}")

    sess["enemy_team"] = []
    for n in names:
        if n == "?":
            sess["enemy_team"].append({"pokemon": None, "observed_skills": [], "guessed_skills": [],
                                       "buff_layers": {"attack": 0, "defense": 0, "special_defense": 0, "speed": 0}})
        else:
            entry = ss.make_enemy_pokemon(n)
            entry["guessed_skills"] = list(core.HOT_SKILLS.get(n, []))
            sess["enemy_team"].append(entry)

    ss.log_event(sess, f"set enemy team: {names}")
    ss.save(sess)
    return {"enemy_team": [e["pokemon"] for e in sess["enemy_team"]]}


def cmd_bench_threats(session_id: str) -> dict:
    """计算敌方场下所有精灵的技能对我方在场精灵的伤害威胁。"""
    sess = ss.load(session_id)
    me = _active(sess, "my")
    if not me:
        raise ValueError("我方在场精灵未设置")
    enemy_active_idx = sess["active"].get("enemy_index")
    my_p = core.POKEMON[me["pokemon"]]
    my_buff = me.get("buff_layers", {})

    results = []
    for i, enemy in enumerate(sess["enemy_team"]):
        if not enemy or enemy.get("pokemon") is None:
            continue
        if i == enemy_active_idx:
            continue
        enemy_p = core.POKEMON.get(enemy["pokemon"])
        if not enemy_p:
            continue

        skills_to_eval = []
        for s in enemy.get("observed_skills", []):
            skills_to_eval.append((s, "observed"))
        for s in enemy.get("guessed_skills", []):
            if s not in [x[0] for x in skills_to_eval]:
                skills_to_eval.append((s, "guessed"))

        skill_results = []
        for skill_name, source in skills_to_eval:
            r = _eval_attack(enemy, enemy_p, me, my_p, skill_name, my_buff)
            r["source"] = source
            skill_results.append(r)

        atk_skills = [r for r in skill_results if r.get("damage", 0) > 0]
        atk_skills.sort(key=lambda r: r.get("damage", 0), reverse=True)

        results.append({
            "pokemon": enemy["pokemon"],
            "slot": i,
            "hp_pct": enemy.get("hp_pct", 100),
            "skills": atk_skills,
        })

    return {"defender": me["pokemon"], "bench_threats": results}


def cmd_update_enemy(session_id: str, pokemon: str,
                     hp_pct: int = None, energy: int = None,
                     poison: int = None, burn: int = None, freeze: int = None) -> dict:
    """更新敌方精灵的状态。所有参数可选，None 表示不更新。"""
    sess = ss.load(session_id)
    target = next((e for e in sess["enemy_team"] if e and e.get("pokemon") == pokemon), None)
    if not target:
        raise ValueError(f"敌方队伍中没有：{pokemon}")
    if hp_pct is not None:
        if not 0 <= hp_pct <= 100:
            raise ValueError("hp_pct 必须在 0~100")
        target["hp_pct"] = hp_pct
    if energy is not None:
        if not 0 <= energy <= 10:
            raise ValueError("energy 必须在 0~10")
        target["energy"] = energy
    target.setdefault("dots", {"poison": 0, "burn": 0, "freeze": 0})
    if poison is not None: target["dots"]["poison"] = max(0, poison)
    if burn is not None: target["dots"]["burn"] = max(0, burn)
    if freeze is not None: target["dots"]["freeze"] = max(0, freeze)
    ss.log_event(sess, f"update enemy {pokemon}: hp={hp_pct}% energy={energy} dots={target['dots']}")
    ss.save(sess)
    return {"pokemon": pokemon, "hp_pct": target.get("hp_pct"),
            "energy": target.get("energy"), "dots": target["dots"]}
    sess = ss.load(session_id)
    if skill not in core.SKILLS:
        raise ValueError(f"未知技能：{skill}")
    if side == "enemy":
        target = next((e for e in sess["enemy_team"] if e and e["pokemon"] == pokemon), None)
        if not target:
            raise ValueError(f"敌方队伍中没有：{pokemon}")
        if skill not in target["observed_skills"]:
            target["observed_skills"].append(skill)
    else:
        target = next((m for m in sess["my_team"] if m["pokemon"] == pokemon), None)
        if not target:
            raise ValueError(f"我方队伍中没有：{pokemon}")
    ss.log_event(sess, f"observe {side} {pokemon} use {skill}")
    ss.save(sess)
    return {"side": side, "pokemon": pokemon, "skill": skill}


def cmd_set_custom_skill(session_id: str, side: str, slot: int,
                         name: str, shown_power: float,
                         hit_count: int = 1,
                         extra_mult: float = 1.0) -> dict:
    """为精灵的某个技能位设置自定义显示威力（绕过基础威力推算）。

    显示威力已包含本系/克制/攻防buff/特性等所有公开乘区。
    extra_mult 用于隐藏乘区（顺风、应对成功等）。
    DoT 层数用 update-enemy --poison/--burn/--freeze 单独维护（总层数）。
    """
    sess = ss.load(session_id)
    team_key = "my_team" if side == "my" else "enemy_team"
    idx = sess["active"].get("my_index" if side == "my" else "enemy_index")
    if idx is None:
        raise ValueError(f"{side} 在场精灵未设置")
    target = sess[team_key][idx]
    if not target or not target.get("pokemon"):
        raise ValueError(f"{side} 在场精灵不存在")

    target.setdefault("custom_skills", {})
    target["custom_skills"][str(slot)] = {
        "name": name,
        "shown_power": float(shown_power),
        "hit_count": int(hit_count),
        "extra_mult": float(extra_mult),
    }
    ss.log_event(sess, f"set custom skill {side}#{idx} slot{slot}: {name} power={shown_power}")
    ss.save(sess)
    return {"side": side, "slot": slot, "custom": target["custom_skills"][str(slot)]}


def cmd_kill_chain(session_id: str) -> dict:
    """跨回合斩杀推演：我方在场精灵能否在本回合斩杀对方。

    对每个我方技能（含自定义技能）：
    1. 计算直接伤害
    2. 枚举对方可能的防御技能（减伤后伤害）
    3. 加上回合末 DoT（中毒/灼烧/冻结）
    4. 判断是否斩杀
    """
    import re
    sess = ss.load(session_id)
    me = _active(sess, "my")
    enemy = _active(sess, "enemy")
    if not me or not enemy:
        raise ValueError("双方在场精灵都需要先设置")

    my_p = core.POKEMON[me["pokemon"]]
    enemy_p = core.POKEMON.get(enemy["pokemon"])
    if not enemy_p:
        raise ValueError(f"未知精灵：{enemy['pokemon']}")

    # 防御方当前血量
    hp_iv = me.get("ivs", {}).get("hp", 10)
    hp_nature = me.get("natures", {}).get("hp", "无")
    enemy_hp_max = core.calc_hp(int(enemy_p["stats"]["hp"]), 10, "无")
    enemy_hp_pct = enemy.get("hp_pct", 100) / 100
    enemy_hp_cur = max(1, round(enemy_hp_max * enemy_hp_pct))

    # 已有 DoT 层数（来自 enemy 的 buff_layers 或 session 扩展字段）
    existing_dots = enemy.get("dots", {"poison": 0, "burn": 0, "freeze": 0})

    # 对方能学的防御技能
    enemy_all_skills = core.all_skills_of(enemy["pokemon"])
    enemy_defense_skills = []
    for sk_name in enemy_all_skills:
        sk = core.SKILLS.get(sk_name)
        if not sk or sk.get("category") != "防御":
            continue
        m = re.search(r"减伤(\d+)%", sk.get("description", ""))
        is_interrupt = "打断" in sk.get("description", "") or "中断" in sk.get("description", "")
        mit = int(m.group(1)) if m else (100 if is_interrupt else 0)
        if mit > 0:
            enemy_defense_skills.append({
                "name": sk_name,
                "mitigation": mit,
                "is_interrupt": is_interrupt,
            })

    # 构建我方技能列表（custom_skills 优先，否则用 skills 列表）
    custom = me.get("custom_skills", {})
    skill_entries = []
    for i, sk_name in enumerate(me.get("skills", [])):
        if str(i) in custom:
            skill_entries.append(("custom", i, custom[str(i)]))
        elif sk_name:
            skill_entries.append(("db", i, sk_name))

    # 防御方能力值
    def_field_map = {"物攻": "defense", "魔攻": "special_defense"}
    enemy_buff = enemy.get("buff_layers", {})

    results = []
    for source, slot, skill_data in skill_entries:
        if source == "custom":
            shown = skill_data["shown_power"]
            hit_count = skill_data["hit_count"]
            extra_mult = skill_data["extra_mult"]
            skill_name = skill_data["name"]
            category = "物攻"  # 自定义技能默认物攻，用于选防御字段
        else:
            sk = core.SKILLS.get(skill_data)
            if not sk or sk.get("category") in ("状态", "防御"):
                continue
            sp = core.shown_power(skill_data, my_p, enemy_p,
                                  atk_buff_layers=me.get("buff_layers", {}).get("attack", 0))
            if not sp:
                continue
            shown = sp["shown"]
            hit_count = sp["hit_count"]
            extra_mult = 1.0
            dots_given = {"poison": 0, "burn": 0, "freeze": 0}
            skill_name = skill_data
            category = sp["category"]
        # 不再区分 dots_given，统一从 enemy.dots 读总层数

        def_field = def_field_map.get(category, "defense")
        def_iv = enemy.get("ivs", {}).get(def_field, 0)
        def_nature = enemy.get("natures", {}).get(def_field, "无")
        def_buff_layers = enemy_buff.get(def_field, 0)
        def_stat = round(core.calc_stat(int(enemy_p["stats"][def_field]), def_iv, def_nature)
                         * (1 + def_buff_layers * 0.1))

        # 攻击方能力值
        atk_field = "attack" if category == "物攻" else "special_attack"
        confirmed = me.get("confirmed_stats", {}).get(atk_field)
        if confirmed:
            atk_stat = confirmed
        else:
            atk_iv = me.get("ivs", {}).get(atk_field, 10)
            atk_nature = me.get("natures", {}).get(atk_field, "无")
            atk_stat = core.calc_stat(int(my_p["stats"][atk_field]), atk_iv, atk_nature)

        eff_power = shown * extra_mult

        # 无防御时伤害
        base_dmg = core.damage(atk_stat, def_stat, eff_power, hit_count)

        # 回合末 DoT（用 enemy.dots 总层数）
        total_poison = existing_dots.get("poison", 0)
        total_burn = existing_dots.get("burn", 0)
        total_freeze = existing_dots.get("freeze", 0)
        dot_dmg = (int(enemy_hp_max * 0.03) * total_poison +
                   int(enemy_hp_max * 0.02) * total_burn)
        freeze_threshold = int(enemy_hp_max * 0.05) * total_freeze

        # 枚举对方防御技能
        scenarios = [{"defense_skill": None, "mitigation": 0, "dmg": base_dmg}]
        for def_sk in enemy_defense_skills:
            mit = def_sk["mitigation"] / 100
            d = core.damage(atk_stat, def_stat, eff_power * (1 - mit), hit_count) if not def_sk["is_interrupt"] else 0
            scenarios.append({"defense_skill": def_sk["name"], "mitigation": def_sk["mitigation"], "dmg": d})

        # 判断每种场景的斩杀
        scenario_results = []
        for sc in scenarios:
            dmg = sc["dmg"]
            remaining = enemy_hp_cur - dmg
            instant_kill = dmg >= enemy_hp_cur
            # 回合末 DoT 斩杀
            dot_kill = not instant_kill and remaining > 0 and (remaining - dot_dmg) <= 0
            # 冻结斩杀
            freeze_kill = not instant_kill and not dot_kill and remaining > 0 and remaining <= freeze_threshold
            scenario_results.append({
                "defense_skill": sc["defense_skill"],
                "mitigation": sc["mitigation"],
                "damage": dmg,
                "remaining": max(0, remaining),
                "instant_kill": instant_kill,
                "dot_kill": dot_kill,
                "freeze_kill": freeze_kill,
                "dot_dmg": dot_dmg,
                "freeze_threshold": freeze_threshold,
            })

        results.append({
            "skill": skill_name,
            "slot": slot,
            "shown_power": round(shown, 1),
            "hit_count": hit_count,
            "atk_stat": atk_stat,
            "def_stat": def_stat,
            "scenarios": scenario_results,
        })

    return {
        "attacker": me["pokemon"],
        "defender": enemy["pokemon"],
        "enemy_hp": enemy_hp_cur,
        "enemy_hp_max": enemy_hp_max,
        "skills": results,
    }
    """清除自定义技能。slot=None 清除所有。"""
    sess = ss.load(session_id)
    team_key = "my_team" if side == "my" else "enemy_team"
    idx = sess["active"].get("my_index" if side == "my" else "enemy_index")
    if idx is None:
        raise ValueError(f"{side} 在场精灵未设置")
    target = sess[team_key][idx]
    if "custom_skills" not in target:
        return {"cleared": []}
    if slot is None:
        cleared = list(target["custom_skills"].keys())
        target["custom_skills"] = {}
    else:
        cleared = [str(slot)] if str(slot) in target["custom_skills"] else []
        target["custom_skills"].pop(str(slot), None)
    ss.save(sess)
    return {"cleared": cleared}


# === 在场设置 ===

def cmd_set_active(session_id: str, side: str, index: int) -> dict:
    sess = ss.load(session_id)
    key = "my_index" if side == "my" else "enemy_index"
    sess["active"][key] = index
    ss.save(sess)
    return {"active": sess["active"]}


# === 伤害计算 ===

def cmd_my_damages(session_id: str) -> dict:
    """计算我方在场精灵的 4 个技能对敌方在场精灵造成的伤害。"""
    sess = ss.load(session_id)
    me = _active(sess, "my")
    enemy = _active(sess, "enemy")
    if not me or not enemy:
        raise ValueError("双方在场精灵都需要先设置（cmd_set_active）")

    my_p = core.POKEMON[me["pokemon"]]
    enemy_p = core.POKEMON[enemy["pokemon"]]
    enemy_buff = enemy.get("buff_layers", {})

    results = []
    for skill_name in me.get("skills", []):
        results.append(_eval_attack(me, my_p, enemy, enemy_p, skill_name, enemy_buff))
    return {
        "attacker": me["pokemon"],
        "defender": enemy["pokemon"],
        "skills": results,
    }


def cmd_enemy_damages(session_id: str, include_guessed: bool = True) -> dict:
    """计算敌方在场精灵所有可能技能对我方在场精灵造成的伤害。

    include_guessed=True 时把热门配招的推测技能也纳入。
    """
    sess = ss.load(session_id)
    me = _active(sess, "my")
    enemy = _active(sess, "enemy")
    if not me or not enemy:
        raise ValueError("双方在场精灵都需要先设置")

    my_p = core.POKEMON[me["pokemon"]]
    enemy_p = core.POKEMON[enemy["pokemon"]]
    my_buff = me.get("buff_layers", {})

    skills_to_eval = []
    for s in enemy.get("observed_skills", []):
        skills_to_eval.append((s, "observed"))
    if include_guessed:
        for s in enemy.get("guessed_skills", []):
            if s not in [x[0] for x in skills_to_eval]:
                skills_to_eval.append((s, "guessed"))

    results = []
    for skill_name, source in skills_to_eval:
        eval_result = _eval_attack(enemy, enemy_p, me, my_p, skill_name, my_buff)
        eval_result["source"] = source
        results.append(eval_result)

    # 按伤害降序排
    results.sort(key=lambda r: r.get("damage", 0), reverse=True)
    return {
        "attacker": enemy["pokemon"],
        "defender": me["pokemon"],
        "skills": results,
    }


# === 速度比较 ===

def cmd_speed(session_id: str) -> dict:
    """比较双方在场精灵的速度档位。"""
    sess = ss.load(session_id)
    me = _active(sess, "my")
    enemy = _active(sess, "enemy")
    if not me or not enemy:
        raise ValueError("双方在场精灵都需要先设置")

    my_speeds = _speed_range(me, "my")
    enemy_speeds = _speed_range(enemy, "enemy")

    return {
        "my": {"pokemon": me["pokemon"], **my_speeds},
        "enemy": {"pokemon": enemy["pokemon"], **enemy_speeds},
        "outspeed": _outspeed_summary(my_speeds, enemy_speeds),
    }


# === 内部辅助 ===

def _active(sess: dict, side: str) -> dict:
    key = "my_index" if side == "my" else "enemy_index"
    idx = sess["active"].get(key)
    if idx is None:
        return None
    team = sess["my_team"] if side == "my" else sess["enemy_team"]
    if idx >= len(team) or team[idx] is None:
        return None
    return team[idx]


def _eval_attack(attacker_entry: dict, attacker_p: dict,
                 defender_entry: dict, defender_p: dict,
                 skill_name: str, defender_buff: dict) -> dict:
    skill = core.SKILLS.get(skill_name)
    if not skill:
        return {"skill_name": skill_name, "error": "未知技能"}

    # 状态/防御技能：不直接伤害
    if skill["category"] in ("状态", "防御"):
        return {
            "skill_name": skill_name,
            "category": skill["category"],
            "energy": int(skill["energy_consumption"]) if skill["energy_consumption"] else 0,
            "description": skill["description"],
            "damage": 0,
        }

    atk_buff = attacker_entry.get("buff_layers", {}).get("attack", 0)
    sp = core.shown_power(skill_name, attacker_p, defender_p, atk_buff_layers=atk_buff)
    if sp is None:
        return {"skill_name": skill_name, "error": "无法计算"}

    atk_field = "attack" if sp["category"] == "物攻" else "special_attack"
    def_field = "defense" if sp["category"] == "物攻" else "special_defense"

    # 防御方能力值
    def_iv = defender_entry.get("ivs", {}).get(def_field, 0)
    def_nature = defender_entry.get("natures", {}).get(def_field, "无")
    def_buff_layers = defender_buff.get(def_field, 0)
    def_stat = round(core.calc_stat(int(defender_p["stats"][def_field]), def_iv, def_nature) * (1 + def_buff_layers * 0.1))

    # HP
    hp_iv = defender_entry.get("ivs", {}).get("hp", 10)
    hp_nature = defender_entry.get("natures", {}).get("hp", "无")
    hp_max = core.calc_hp(int(defender_p["stats"]["hp"]), hp_iv, hp_nature)

    # 攻击方：confirmed_stats 优先 → ivs → 三档
    confirmed = attacker_entry.get("confirmed_stats", {}).get(atk_field)
    has_known_atk = confirmed is not None or ("ivs" in attacker_entry and attacker_entry["ivs"].get(atk_field) is not None)

    if has_known_atk:
        if confirmed is not None:
            atk_stat = confirmed
        else:
            atk_iv = attacker_entry["ivs"].get(atk_field, 10)
            atk_nature = attacker_entry.get("natures", {}).get(atk_field, "无")
            atk_stat = core.calc_stat(int(attacker_p["stats"][atk_field]), atk_iv, atk_nature)
        dmg = core.damage(atk_stat, def_stat, sp["shown"], hit_count=sp["hit_count"])
        pct = round(100 * dmg / hp_max, 1)
        return {
            "skill_name": skill_name,
            "attribute": sp["attribute"],
            "category": sp["category"],
            "shown_power": round(sp["shown"], 1),
            "hit_count": sp["hit_count"],
            "hits_unknown": sp["hits_unknown"],
            "energy": sp["energy"],
            "atk_stat": atk_stat,
            "damage": dmg,
            "pct": pct,
            "kill_in": 1 if dmg >= hp_max else (hp_max + dmg - 1) // dmg,
            "one_shot": dmg >= hp_max,
        }

    # 三档：弱(0个体/无)、中(满个体/无)、强(满个体/加)
    base = int(attacker_p["stats"][atk_field])
    tiers = []
    for label, iv, nat in [("min", 0, "无"), ("mid", 10, "无"), ("max", 10, "加")]:
        atk_stat = core.calc_stat(base, iv, nat)
        d = core.damage(atk_stat, def_stat, sp["shown"], hit_count=sp["hit_count"])
        tiers.append({
            "tier": label,
            "atk_stat": atk_stat,
            "damage": d,
            "pct": round(100 * d / hp_max, 1),
            "one_shot": d >= hp_max,
        })

    return {
        "skill_name": skill_name,
        "attribute": sp["attribute"],
        "category": sp["category"],
        "shown_power": round(sp["shown"], 1),
        "hit_count": sp["hit_count"],
        "hits_unknown": sp["hits_unknown"],
        "energy": sp["energy"],
        "tiers": tiers,
        "damage": tiers[1]["damage"],          # 兼容旧字段，取中档
        "pct": tiers[1]["pct"],
        "kill_in": 1 if tiers[1]["one_shot"] else (hp_max + tiers[1]["damage"] - 1) // tiers[1]["damage"],
        "one_shot": tiers[1]["one_shot"],
    }


def _speed_range(entry: dict, side: str) -> dict:
    """返回精灵速度的最低/中等/最高三档。"""
    p = core.POKEMON[entry["pokemon"]]
    base = int(p["stats"]["speed"])
    iv = entry.get("ivs", {}).get("speed", 10 if side == "my" else None)
    nature = entry.get("natures", {}).get("speed", "无" if side == "my" else None)
    buff_layers = entry.get("buff_layers", {}).get("speed", 0)

    if side == "my":
        # 已知配置：直接算
        cur = round(core.calc_stat(base, iv, nature) * (1 + buff_layers * 0.1))
        return {"current": cur, "base": base}
    else:
        # 敌方配置未知：算极速、加速性格满个体、无性格满个体三档
        max_spd = round(core.calc_stat(base, 10, "加") * (1 + buff_layers * 0.1))
        mid_spd = round(core.calc_stat(base, 10, "无") * (1 + buff_layers * 0.1))
        min_spd = round(core.calc_stat(base, 0, "减") * (1 + buff_layers * 0.1))
        return {"max": max_spd, "mid": mid_spd, "min": min_spd, "base": base}


def _outspeed_summary(my: dict, enemy: dict) -> str:
    my_cur = my["current"]
    if my_cur >= enemy.get("max", 0):
        return f"我方稳定先手（{my_cur} >= 敌方极速 {enemy.get('max')}）"
    if my_cur >= enemy.get("mid", 0):
        return f"我方先手（敌方需加速性格才能反超）"
    if my_cur >= enemy.get("min", 0):
        return f"速度接近，敌方加速即反超"
    return f"我方落后于敌方（{my_cur} < 敌方最低 {enemy.get('min')}）"
