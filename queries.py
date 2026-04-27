"""精灵查询工具库（可复用）

常用查询场景：
1. 按属性筛选（单属性/双属性）
2. 按技能筛选（能学某个技能的精灵）
3. 按种族值范围筛选（高速/高攻/高耐等）
4. 按特性关键词筛选
5. 极速/满速计算
6. 属性克制查询

使用：
    from queries import *
    repo = get_repo()
    # 所有会闪击的翼系精灵
    result = find_by_skill('闪击', attribute='翼')
    # 极速>=260的物攻核心
    result = find_by_stats(min_attack=120, min_max_speed=260)
"""

from data_repo import DataRepo

_repo_cache = None


def get_repo() -> DataRepo:
    global _repo_cache
    if _repo_cache is None:
        _repo_cache = DataRepo()
    return _repo_cache


def max_speed(speed_stat: int, nature_boost: bool = True) -> float:
    """计算极速：[1.1×(种族+30)+10]×性格系数+50"""
    factor = 1.2 if nature_boost else 1.0
    return (1.1 * (speed_stat + 30) + 10) * factor + 50


def all_pokemon_skills(p: dict, include_tujian: bool = False) -> set[str]:
    """收集精灵所有可用技能（按来源去重）。include_tujian 已废弃（raw 数据不再保留 tujian）。"""
    keys = ('moves', 'jinengshi', 'xuemai')
    names = set()
    for k in keys:
        v = p.get('skills', {}).get(k, [])
        # xuemai 是 dict，moves/jinengshi 是 list
        if isinstance(v, dict):
            names.update(v.values())
        else:
            names.update(v)
    return names


def find_by_skill(skill_name: str, attribute: str = None,
                  min_attack: int = 0, min_max_speed: float = 0) -> list[dict]:
    """查找能学某技能的精灵，可叠加属性/面板筛选"""
    repo = get_repo()
    results = []
    for p in repo.pokemon:
        if attribute and attribute not in p['attributes_list']:
            continue
        if skill_name not in all_pokemon_skills(p):
            continue
        stats = p['stats']
        max_offense = max(int(stats['attack']), int(stats['special_attack']))
        if max_offense < min_attack:
            continue
        spd = int(stats['speed'])
        if max_speed(spd) < min_max_speed:
            continue
        results.append(p)
    return results


def find_by_attribute(attributes: list[str], match_all: bool = False) -> list[dict]:
    """查找匹配属性的精灵。match_all=True 要求全部匹配，False 要求至少一个匹配"""
    repo = get_repo()
    results = []
    for p in repo.pokemon:
        types = p['attributes_list']
        if match_all:
            if all(a in types for a in attributes):
                results.append(p)
        else:
            if any(a in types for a in attributes):
                results.append(p)
    return results


def find_by_stats(min_hp: int = 0, min_attack: int = 0, min_sp_attack: int = 0,
                  min_defense: int = 0, min_sp_defense: int = 0,
                  min_speed: int = 0, min_max_speed: float = 0,
                  min_total: int = 0,
                  max_hp: int = 999, max_speed_stat: int = 999) -> list[dict]:
    """按种族值范围筛选"""
    repo = get_repo()
    results = []
    for p in repo.pokemon:
        s = p['stats']
        if int(s['hp']) < min_hp or int(s['hp']) > max_hp: continue
        if int(s['attack']) < min_attack: continue
        if int(s['special_attack']) < min_sp_attack: continue
        if int(s['defense']) < min_defense: continue
        if int(s['special_defense']) < min_sp_defense: continue
        if int(s['speed']) < min_speed or int(s['speed']) > max_speed_stat: continue
        if max_speed(int(s['speed'])) < min_max_speed: continue
        if int(s['total']) < min_total: continue
        results.append(p)
    return results


def find_by_ability(keyword: str) -> list[dict]:
    """按特性关键词筛选"""
    repo = get_repo()
    return [p for p in repo.pokemon if keyword in (p.get('ability') or '')]


def find_skills_by_keyword(keyword: str, attribute: str = None,
                           category: str = None) -> list[dict]:
    """按关键词搜索技能"""
    repo = get_repo()
    results = []
    for name, s in repo.skill_by_name.items():
        desc = (s.get('description') or '') + (s.get('beizhu') or '')
        if keyword not in desc:
            continue
        if attribute and s.get('attribute') != attribute:
            continue
        if category and s.get('category') != category:
            continue
        results.append(s)
    return results


def is_boss_form(p: dict) -> bool:
    """判断是否首领形态（不能独立入队，战中首领化后才出现）"""
    return p.get('form_name') == '首领形态'


def effective_total(stats: dict) -> dict:
    """有效种族值：去除弱势攻击后的5条之和"""
    hp = int(stats['hp']); atk = int(stats['attack']); sa = int(stats['special_attack'])
    df = int(stats['defense']); sdf = int(stats['special_defense']); spd = int(stats['speed'])
    if atk >= sa:
        removed_key, removed_val = 'special_attack', sa
    else:
        removed_key, removed_val = 'attack', atk
    eff = hp + max(atk, sa) + df + sdf + spd
    return {'effective_total': eff, 'removed': removed_key, 'removed_value': removed_val}
    """有效种族值：去除弱势攻击后的5条之和
    绝大部分精灵只专注物理或魔法其中一种，另一种约等于无效
    """
    hp = int(stats['hp'])
    atk = int(stats['attack'])
    sa = int(stats['special_attack'])
    df = int(stats['defense'])
    sdf = int(stats['special_defense'])
    spd = int(stats['speed'])
    if atk >= sa:
        removed_key, removed_val = 'special_attack', sa
    else:
        removed_key, removed_val = 'attack', atk
    eff = hp + max(atk, sa) + df + sdf + spd
    return {'effective_total': eff, 'removed': removed_key, 'removed_value': removed_val}



    """判断是否首领形态（不能独立入队，战中首领化后才出现）"""
    return p.get('form_name') == '首领形态'


def base_of_boss(p: dict) -> str | None:
    """获取首领形态对应的基础精灵名"""
    return p.get('base_name') if is_boss_form(p) else None


def find_all_boss_forms() -> list[dict]:
    """列出所有首领形态精灵"""
    repo = get_repo()
    return [p for p in repo.pokemon if is_boss_form(p)]


def find_independent_pokemon(pokemon_list: list[dict]) -> list[dict]:
    """从候选中筛掉首领形态，只保留可独立入队的精灵"""
    return [p for p in pokemon_list if not is_boss_form(p)]


# 已知的"多对一"首领化规则：多只基础形态精灵首领化后变同一个首领形态
# 这类精灵组内互斥（只能选一只入队），但首领化后都变同一形态
MULTI_TO_ONE_BOSS = {
    '霜翼领主': ['岚鸟冬天的样子', '岚鸟春天的样子', '岚鸟夏天的样子', '岚鸟秋天的样子'],
    '棋契陛下': ['棋绮后白子', '棋绮后黑子', '棋骑士白子', '棋骑士黑子',
                 '棋齐垒白子', '棋齐垒黑子', '棋祈督白子', '棋祈督黑子'],
    '钻石蜗': ['晶石蜗西瓜碧玺的样子', '晶石蜗莲花刚玉的样子', '晶石蜗星彩榴石的样子',
              '晶石蜗火山琉璃的样子', '晶石蜗蓝锥矿的样子', '晶石蜗烧蓝黄金的样子'],
}


def get_boss_form_sources(boss_name: str) -> list[str]:
    """获取某首领形态对应的所有基础形态名
    返回list——大多数首领是1对1，部分是多对一（如霜翼领主/棋契陛下）"""
    if boss_name in MULTI_TO_ONE_BOSS:
        return MULTI_TO_ONE_BOSS[boss_name]
    repo = get_repo()
    for p in repo.pokemon:
        if p.get('display_name') == boss_name and is_boss_form(p):
            return [p.get('base_name')]
    return []


def get_boss_form_of(base_name: str) -> str | None:
    """获取基础形态对应的首领形态名"""
    # 先查多对一规则
    for boss, sources in MULTI_TO_ONE_BOSS.items():
        if base_name in sources:
            return boss
    # 查1对1：在数据库中找 base_name 匹配的首领形态
    repo = get_repo()
    for p in repo.pokemon:
        if is_boss_form(p) and p.get('base_name') == base_name:
            return p.get('display_name')
    return None


def summary(p: dict) -> str:
    """打印精灵简要信息（标注首领形态）"""
    s = p['stats']
    spd = int(s['speed'])
    boss_mark = '【首领形态】' if is_boss_form(p) else ''
    return (f"{boss_mark}{p['display_name']} {p['attributes_list']} | "
            f"HP{s['hp']}/攻{s['attack']}/特攻{s['special_attack']}/"
            f"防{s['defense']}/特防{s['special_defense']}/速{spd} | "
            f"极速{max_speed(spd):.0f} | 特性:{(p.get('ability') or '')[:40]}")


if __name__ == '__main__':
    # 使用示例
    print('=== 所有会闪击的翼系精灵 ===')
    for p in find_by_skill('闪击', attribute='翼'):
        print(' ', summary(p))
