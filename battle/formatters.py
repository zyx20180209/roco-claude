"""命令结果的文本格式化。"""

import json


def format_status(result: dict) -> str:
    sess = result["session"]
    lines = [f"=== Session {sess['id']} ==="]
    lines.append(f"创建：{sess.get('created_at')}")

    lines.append("\n[我方队伍]")
    if not sess["my_team"]:
        lines.append("  （未设置）")
    for i, m in enumerate(sess["my_team"]):
        skills = "/".join(m["skills"]) if m["skills"] else "（未设技能）"
        lines.append(f"  {i}. {m['pokemon']:8} 技能: {skills}")

    lines.append("\n[敌方队伍]")
    if not sess["enemy_team"]:
        lines.append("  （未设置）")
    for i, e in enumerate(sess["enemy_team"]):
        if not e:
            lines.append(f"  {i}. （未知）")
            continue
        obs = e.get("observed_skills", [])
        guess = e.get("guessed_skills", [])
        lines.append(f"  {i}. {e['pokemon']}")
        if obs:
            lines.append(f"     已观察: {'/'.join(obs)}")
        if guess:
            lines.append(f"     推测: {'/'.join(guess[:4])}...")

    active = sess.get("active", {})
    lines.append(f"\n[在场] 我方#{active.get('my_index')} / 敌方#{active.get('enemy_index')}")
    return "\n".join(lines)


def format_damages(result: dict) -> str:
    lines = [f"=== {result['attacker']} → {result['defender']} ==="]
    if not result["skills"]:
        return "\n".join(lines + ["  （无技能）"])

    has_tiers = any("tiers" in s for s in result["skills"])

    if has_tiers:
        # 三档展示：min/mid/max
        lines.append(f"  {'技能':10} {'属性':4} {'威力':>6} {'连击':>4} {'弱':>14} {'中':>14} {'强':>14}  备注")
        lines.append("  " + "-" * 95)
    else:
        lines.append(f"  {'技能':10} {'属性':4} {'威力':>6} {'连击':>4} {'伤害':>6} {'占比':>6} {'秒杀':>4}  备注")
        lines.append("  " + "-" * 75)

    for s in result["skills"]:
        if "error" in s:
            lines.append(f"  {s['skill_name']:10} {s['error']}")
            continue
        if s.get("category") in ("状态", "防御"):
            lines.append(f"  {s['skill_name']:10} [{s['category']}] {s.get('description', '')[:40]}")
            continue
        hits = f"{s['hit_count']}{'?' if s.get('hits_unknown') else ''}"
        source = s.get("source", "")
        flag = "🟢" if source == "observed" else ("🟡" if source == "guessed" else "")

        if "tiers" in s:
            # 三档输出
            def fmt_tier(t):
                kill = "✅" if t["one_shot"] else ""
                return f"{t['damage']:>4} {t['pct']:>5.1f}% {kill:>1}"
            tiers = {t["tier"]: t for t in s["tiers"]}
            lines.append(
                f"  {s['skill_name']:10} {s['attribute']:4} "
                f"{s['shown_power']:>6.1f} {hits:>4} "
                f"{fmt_tier(tiers['min']):>14} {fmt_tier(tiers['mid']):>14} {fmt_tier(tiers['max']):>14}  {flag}"
            )
        else:
            kill = "✅" if s.get("one_shot") else f"{s.get('kill_in', '-')}次"
            lines.append(
                f"  {s['skill_name']:10} {s['attribute']:4} "
                f"{s['shown_power']:>6.1f} {hits:>4} "
                f"{s['damage']:>6} {s['pct']:>5.1f}% {kill:>4}  {flag}"
            )
    if has_tiers:
        lines.append("  弱=0个体无性格 / 中=满个体无性格 / 强=满个体加攻性格")
    return "\n".join(lines)


def format_speed(result: dict) -> str:
    my = result["my"]
    en = result["enemy"]
    lines = [f"=== 速度比较 ==="]
    lines.append(f"  我方 {my['pokemon']:10} 速度 {my['current']}")
    lines.append(f"  敌方 {en['pokemon']:10} 极速 {en['max']} / 中位 {en['mid']} / 最低 {en['min']}")
    lines.append(f"  → {result['outspeed']}")
    return "\n".join(lines)


def format_kill_chain(result: dict) -> str:
    lines = [f"=== 斩杀推演：{result['attacker']} → {result['defender']} ==="]
    hp = result["enemy_hp"]
    hp_max = result["enemy_hp_max"]
    pct = round(100 * hp / hp_max, 1)
    lines.append(f"  敌方当前 HP: {hp}/{hp_max} ({pct}%)")
    lines.append("")

    for sk in result["skills"]:
        lines.append(f"  [{sk['slot']}] {sk['skill']}  威力 {sk['shown_power']}  连击 {sk['hit_count']}")
        for sc in sk["scenarios"]:
            def_label = f"对方用 {sc['defense_skill']}（减伤{sc['mitigation']}%）" if sc["defense_skill"] else "对方不防御"
            dmg = sc["damage"]
            rem = sc["remaining"]
            if sc["instant_kill"]:
                verdict = f"✅ 秒杀（溢出 {dmg - hp}）"
            elif sc["freeze_kill"]:
                verdict = f"❄️ 冻结斩杀（剩余 {rem} ≤ 冻结线 {sc['freeze_threshold']}）"
            elif sc["dot_kill"]:
                verdict = f"☠️ 回合末毒死（剩余 {rem}，DoT {sc['dot_dmg']}）"
            else:
                verdict = f"❌ 剩余 {rem}"
            lines.append(f"    {def_label:30} → {dmg:>4} 伤害  {verdict}")
        lines.append("")
    return "\n".join(lines)
    lines = [f"=== 敌方场下威胁 → {result['defender']} ==="]
    if not result["bench_threats"]:
        return "\n".join(lines + ["  （无场下精灵）"])
    for entry in result["bench_threats"]:
        hp = entry.get("hp_pct", 100)
        lines.append(f"\n  [{entry['slot']}] {entry['pokemon']}  HP {hp}%")
        if not entry["skills"]:
            lines.append("    （无已知攻击技能）")
            continue
        for s in entry["skills"][:3]:  # 只显示前 3 个最高伤害
            if "tiers" in s:
                t = {t["tier"]: t for t in s["tiers"]}
                lines.append(
                    f"    {s['skill_name']:10} 弱{t['min']['damage']:>4}({t['min']['pct']:>5.1f}%) "
                    f"中{t['mid']['damage']:>4}({t['mid']['pct']:>5.1f}%) "
                    f"强{t['max']['damage']:>4}({t['max']['pct']:>5.1f}%)"
                    f"{'  ✅' if t['max']['one_shot'] else ''}"
                )
            else:
                kill = "✅" if s.get("one_shot") else ""
                lines.append(f"    {s['skill_name']:10} {s['damage']:>4} ({s['pct']:>5.1f}%) {kill}")
    return "\n".join(lines)


def format_list(result) -> str:
    if isinstance(result, dict):
        sess_list = result.get("sessions", [])
    else:
        sess_list = result
    if not sess_list:
        return "（无 session）"
    return "Sessions:\n  " + "\n  ".join(sess_list)


def format_generic(result: dict) -> str:
    """通用格式化：直接 JSON 输出。"""
    return json.dumps(result, ensure_ascii=False, indent=2)

