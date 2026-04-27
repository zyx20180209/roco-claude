"""
批量生成所有精灵的战术定位报告
基于规则推导（不调用AI），存入 data/meta/deep_analysis/{精灵名}.md
"""

import json
from pathlib import Path
from data_repo import DataRepo
from battle_logic import build_battle_logic

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = DATA_DIR / "meta" / "deep_analysis"
OUTPUT_DIR.mkdir(exist_ok=True)

MULTI_TO_ONE_BOSS = {
    '霜翼领主': ['岚鸟冬天的样子', '岚鸟春天的样子', '岚鸟夏天的样子', '岚鸟秋天的样子'],
    '棋契陛下': ['棋绮后白子', '棋绮后黑子', '棋骑士白子', '棋骑士黑子',
                 '棋齐垒白子', '棋齐垒黑子', '棋祈督白子', '棋祈督黑子'],
    '钻石蜗': ['晶石蜗西瓜碧玺的样子', '晶石蜗莲花刚玉的样子', '晶石蜗星彩榴石的样子',
              '晶石蜗火山琉璃的样子', '晶石蜗蓝锥矿的样子', '晶石蜗烧蓝黄金的样子'],
}


def effective_total(stats: dict) -> tuple[int, str]:
    hp = int(stats['hp']); atk = int(stats['attack']); sa = int(stats['special_attack'])
    df = int(stats['defense']); sdf = int(stats['special_defense']); spd = int(stats['speed'])
    if atk >= sa:
        return hp + atk + df + sdf + spd, 'special_attack'
    return hp + sa + df + sdf + spd, 'attack'

def get_boss_form(name: str) -> str | None:
    for boss, sources in MULTI_TO_ONE_BOSS.items():
        if name in sources:
            return boss
    return None


def infer_tactical_roles(p: dict, stats: dict, skill_details: list, defense_profile: dict) -> list[str]:
    """推断精灵的战术定位（7种）"""
    roles = []
    hp = int(stats['hp']); atk = int(stats['attack']); sa = int(stats['special_attack'])
    df = int(stats['defense']); sdf = int(stats['special_defense']); spd = int(stats['speed'])
    bulk = hp + df + sdf
    offense = max(atk, sa)
    eff, _ = effective_total(stats)
    ability = p.get('abilities_text', '') or ''

    # 技能描述文本
    all_desc = ability + ' '.join(
        (s.get('description', '') or '') + (s.get('beizhu', '') or '')
        for s in skill_details
    )

    # 收割：高速+高攻+先手技 或 强化后秒杀路线（速度必须够快）
    from queries import max_speed as ms
    max_spd = ms(spd)
    has_priority = any('先手+' in (s.get('description','') or '') for s in skill_details)
    has_setup = '永久' in all_desc or '双攻+100%' in all_desc or '物攻+100%' in all_desc
    # 有0能高威力终结技也算收割（如彗星0能240威力）
    has_zero_cost_nuke = any(
        str(s.get('energy_consumption','99')) == '0' and
        int(s.get('power','0') if str(s.get('power','0')).lstrip('-').isdigit() else '0') >= 150
        for s in skill_details if s.get('category') in ('物攻','魔攻')
    )
    if max_spd >= 230 and offense >= 120 and (has_priority or max_spd >= 250):
        roles.append('收割')
    elif has_setup and offense >= 130 and max_spd >= 220:
        roles.append('收割')
    elif has_zero_cost_nuke and offense >= 100:
        roles.append('收割')

    # 炮台：有效种族≥550+攻击≥110+bulk≥270
    if eff >= 550 and offense >= 110 and bulk >= 270:
        roles.append('炮台')

    # 拦截：多种实现方式
    is_intercept = False
    if bulk >= 310:
        is_intercept = True
    if any(kw in ability for kw in ['复活', '不朽', '化茧', '3条命', '少损失1点魔力']):
        is_intercept = True
    if any(kw in ability for kw in ['减伤', '伤害-50%', '伤害-40%']):
        is_intercept = True
    has_high_reduce = sum(1 for s in skill_details
                         if s.get('category') == '防御' and
                         any(kw in (s.get('description','') or '') for kw in ['减伤80%','减伤90%','减伤100%','减伤70%'])) >= 2
    if has_high_reduce:
        is_intercept = True
    if any(kw in ability for kw in ['双攻-', '物攻-', '魔攻-']) and '入场' in ability:
        is_intercept = True
    if is_intercept:
        roles.append('拦截')

    # 破盾：DOT特性/技能（需要更严格的条件）
    dot_ability = any(kw in ability for kw in ['灼烧', '中毒', '冻结', '衰减变为增长', '蚀刻', '复方汤剂', '触发次数+1', '能耗每有1点'])
    dot_skills = sum(1 for s in skill_details
                    if any(kw in (s.get('description', '') or '') for kw in
                           ['层灼烧', '层中毒', '层冻结', '中毒印记', '冻结印记'])
                    and s.get('category') in ('状态', '魔攻', '物攻'))
    if dot_ability or dot_skills >= 4:
        roles.append('破盾')
    elif eff >= 600 and offense >= 150 and max_spd >= 220:
        roles.append('破盾')

    # 工兵：印记铺设/强化传递/天气/奉献
    work_signals = ['印记', '奉献', '天气改为', '传递', '击鼓传花', '入场时获得', '湿润', '星陨', '降灵', '继承']
    work_ability = any(kw in ability for kw in ['传递', '继承', '奉献', '印记'])
    if sum(1 for kw in work_signals if kw in all_desc) >= 2 or work_ability:
        roles.append('工兵')

    # 清场：驱散技能
    clear_skills = sum(1 for s in skill_details
                      if any(kw in (s.get('description','') or '') for kw in ['驱散敌方', '驱散双方', '驱散自己']))
    if clear_skills >= 1:
        roles.append('清场')

    # 中转：主动换人技/特性
    pivot_ability = any(kw in ability for kw in ['脱离', '换人', '洁癖', '哨兵'])
    pivot_skills = sum(1 for s in skill_details
                      if any(kw in (s.get('description','') or '') for kw in ['脱离', '吓退', '紧急脱离', '强制换人']))
    if pivot_ability or pivot_skills >= 1:
        roles.append('中转')

    return list(dict.fromkeys(roles)) if roles else ['辅助']


def infer_counter_strategy(roles: list, defense_profile: dict, ability: str) -> list[str]:
    """根据战术定位推导反制策略"""
    strategies = []
    for role in roles:
        if role == '收割':
            strategies.append('减速印记压制先手；更快精灵先手击杀；吓退打断入场节奏')
        elif role == '炮台':
            strategies.append('控速（减速印记）；摇篮曲+3能耗；吓退强制下场；先手秒杀')
        elif role == '拦截':
            if any(kw in ability for kw in ['复活', '不朽', '化茧']):
                strategies.append('消耗战让它多次力竭消耗魔力；吓退强制下场清buff')
            elif any(kw in ability for kw in ['减伤', '伤害-50%']):
                strategies.append('百分比DOT绕过减伤（燃薪虫/裘卡）；等待减伤技CD')
            else:
                strategies.append('破盾（百分比DOT）；石锁禁换；找克制属性')
        elif role == '破盾':
            strategies.append('换上免疫该DOT属性的精灵；洗礼/除厄自清；快速秒杀破盾位')
        elif role == '工兵':
            strategies.append('晒太阳驱散buff；倾泻/食腐驱散印记；地刺打断状态技；先手秒杀工兵')
        elif role == '清场':
            strategies.append('在清场精灵入场前完成铺设；吓退打断清场节奏')
        elif role == '中转':
            strategies.append('当头棒喝（换人时+100威力）；石锁禁换；降灵印记扣入场能量')
    return strategies


def generate_report(p: dict, repo: DataRepo) -> str:
    """生成单只精灵的战术定位报告"""
    name = p['display_name']
    stats = p['stats']
    attrs = p.get('attributes_list', [])
    ability = p.get('abilities_text', '') or ''
    is_boss = p.get('form_name') == '首领形态'
    boss_form = get_boss_form(name)

    # 技能池
    all_names = []
    for k in ('moves', 'jinengshi', 'xuemai'):
        v = p.get('skills', {}).get(k, [])
        # xuemai 是 dict
        all_names.extend(list(v.values()) if isinstance(v, dict) else v)
    skill_details = [repo.skill_by_name[n] for n in set(all_names) if n in repo.skill_by_name]

    defense_profile = repo.compute_defense_profile(attrs)
    logic = build_battle_logic(p, skill_details, defense_profile)
    eff, removed = effective_total(stats)
    roles = infer_tactical_roles(p, stats, skill_details, defense_profile)
    counter_strategies = infer_counter_strategy(roles, defense_profile, ability)

    from queries import max_speed as ms
    spd = int(stats['speed'])

    lines = [
        f"---",
        f"pokemon: {name}",
        f"attributes: {attrs}",
        f"analyzed_date: 2026-04-20",
        f"tactical_roles: {roles}",
        f"effective_total: {eff}",
        f"is_boss_form: {is_boss}",
    ]
    if boss_form:
        lines.append(f"boss_form: {boss_form}")
    lines += ["---", "", f"# {name} 战术定位报告", ""]

    # 基础信息
    lines += [
        "## 基础信息",
        "",
        f"- **属性**：{'/'.join(attrs)}",
        f"- **特性**：{ability}",
        f"- **种族值**：HP{stats['hp']}/攻{stats['attack']}/特攻{stats['special_attack']}/防{stats['defense']}/特防{stats['special_defense']}/速{spd}",
        f"- **总种族**：{stats['total']} | **有效种族**：{eff}（去除{removed}）",
        f"- **极速**：{ms(spd):.0f}",
        "",
    ]

    # 战术定位
    lines += ["## 战术定位", ""]
    role_desc = {
        '收割': '高攻高速先手击杀状态不满的精灵',
        '炮台': '伤害高+有出手权+有赖场能力',
        '拦截': '在场上存活并承受伤害，反手压低对方状态',
        '破盾': '百分比伤害或超高输出逼迫拦截位下场',
        '工兵': '铺设场地/印记/传递强化',
        '清场': '清理对方的印记、强化buff',
        '中转': '主动换人建立节奏优势',
        '辅助': '辅助支援型',
    }
    for r in roles:
        lines.append(f"- **{r}**：{role_desc.get(r, '')}")
    lines.append("")

    # 防御面
    lines += [
        "## 属性抗性",
        "",
        f"- **2x弱点**：{defense_profile['takes_2x_from'] or '无'}",
        f"- **3x弱点**：{defense_profile['takes_3x_from'] or '无'}",
        f"- **半抗**：{defense_profile['resists_half']}",
        f"- **免疫**：{defense_profile['immune_to'] or '无'}",
        "",
    ]

    # 反制策略
    lines += ["## 反制策略", ""]
    for s in counter_strategies:
        lines.append(f"- {s}")
    lines.append("")

    # 首领化信息
    if boss_form:
        lines += [f"## 首领化", "", f"- 首领化形态：**{boss_form}**", ""]
    if is_boss:
        lines += [f"## 注意", "", f"- 这是首领化形态，不能独立入队", ""]

    return '\n'.join(lines)


def batch_generate():
    repo = DataRepo()
    existing = {f.stem for f in OUTPUT_DIR.glob('*.md')}
    total = len(repo.pokemon)
    generated = 0
    skipped = 0

    for p in repo.pokemon:
        name = p['display_name']
        # 已有深度分析的跳过（保留人工分析）
        if name in existing:
            skipped += 1
            continue
        try:
            report = generate_report(p, repo)
            (OUTPUT_DIR / f"{name}.md").write_text(report, encoding='utf-8')
            generated += 1
        except Exception as e:
            print(f"  ⚠️ {name} 失败: {e}")

        if generated % 20 == 0 and generated > 0:
            print(f"  进度: {generated + skipped}/{total}")

    print(f"\n完成：新生成 {generated} 只，跳过已有分析 {skipped} 只，共 {total} 只")


if __name__ == "__main__":
    batch_generate()
