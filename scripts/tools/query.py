#!/usr/bin/env python3
"""
精灵检索工具 - 支持按系别、名称、种族值、技能检索
用法示例见文件末尾
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data_repo import DataRepo

repo = DataRepo()

def _stat(p, key):
    return int(p['stats'].get(key, 0))

def _bulk(p):
    return _stat(p, 'hp') + _stat(p, 'defense') + _stat(p, 'special_defense')

def _all_skills(p):
    names = []
    for k in ('moves', 'jinengshi', 'xuemai'):
        v = p.get('skills', {}).get(k, [])
        # xuemai 是 dict，其他是 list
        names.extend(list(v.values()) if isinstance(v, dict) else v)
    return names

def by_type(*types, require_all=False):
    """按系别检索。require_all=True时要求同时含所有指定系别"""
    types = set(types)
    result = []
    for p in repo.pokemon:
        attrs = set(p.get('attributes_list', []))
        if require_all:
            if types.issubset(attrs):
                result.append(p)
        else:
            if types & attrs:
                result.append(p)
    return result

def by_name(keyword, exact=False):
    """按名称检索（精确或模糊）"""
    result = []
    for p in repo.pokemon:
        name = p['display_name']
        if exact:
            if name == keyword:
                result.append(p)
        else:
            if keyword in name:
                result.append(p)
    return result

def by_stat(stat, min_val=0, max_val=9999):
    """按单项种族值范围检索。stat: hp/attack/special_attack/defense/special_defense/speed/total"""
    result = []
    for p in repo.pokemon:
        v = _stat(p, stat)
        if min_val <= v <= max_val:
            result.append(p)
    return result

def by_bulk(min_bulk=0):
    """按HP+双防总和检索"""
    return [p for p in repo.pokemon if _bulk(p) >= min_bulk]

def by_skills(*skill_names, require_all=True):
    """按技能检索。require_all=True要求同时会所有技能，False则任一即可"""
    skill_names = set(skill_names)
    result = []
    for p in repo.pokemon:
        skills = set(_all_skills(p))
        if require_all:
            if skill_names.issubset(skills):
                result.append(p)
        else:
            if skill_names & skills:
                result.append(p)
    return result

def by_percentile(stat, min_pct=0, max_pct=100):
    """按种族值百分位检索"""
    result = []
    for p in repo.pokemon:
        comp = repo.build_stat_comparison(p['stats'])
        pct = comp.get(stat, {}).get('percentile', 0)
        if min_pct <= pct <= max_pct:
            result.append(p)
    return result

def show(pokemon_list, sort_by='bulk', limit=20):
    """格式化输出检索结果"""
    if sort_by == 'bulk':
        pokemon_list = sorted(pokemon_list, key=_bulk, reverse=True)
    elif sort_by in ('hp','attack','special_attack','defense','special_defense','speed','total'):
        pokemon_list = sorted(pokemon_list, key=lambda p: _stat(p, sort_by), reverse=True)

    for p in pokemon_list[:limit]:
        s = p['stats']
        attrs = '/'.join(p.get('attributes_list', []))
        print(f"{p['display_name']:12s} [{attrs:8s}] "
              f"HP{s['hp']:>3} 攻{s['attack']:>3} 特攻{s['special_attack']:>3} "
              f"防{s['defense']:>3} 特防{s['special_defense']:>3} 速{s['speed']:>3} "
              f"耐久={_bulk(p)}")
    print(f"共 {len(pokemon_list)} 条结果，显示前 {min(limit, len(pokemon_list))} 条")


# ── 使用示例 ──────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='精灵检索工具')
    parser.add_argument('--type', nargs='+', help='按系别检索，多个系别用空格分隔')
    parser.add_argument('--all-types', action='store_true', help='要求同时含所有指定系别')
    parser.add_argument('--name', help='按名称模糊检索')
    parser.add_argument('--skill', nargs='+', help='按技能检索')
    parser.add_argument('--any-skill', action='store_true', help='任一技能即可（默认全部）')
    parser.add_argument('--min-bulk', type=int, default=0, help='最低HP+双防总和')
    parser.add_argument('--min-hp', type=int, default=0)
    parser.add_argument('--min-def', type=int, default=0)
    parser.add_argument('--min-spdef', type=int, default=0)
    parser.add_argument('--sort', default='bulk', help='排序字段')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()

    results = repo.pokemon[:]

    if args.type:
        results = [p for p in results if
                   (set(args.type).issubset(set(p.get('attributes_list',[]))) if args.all_types
                    else set(args.type) & set(p.get('attributes_list',[])))]
    if args.name:
        results = [p for p in results if args.name in p['display_name']]
    if args.skill:
        skill_set = set(args.skill)
        if args.any_skill:
            results = [p for p in results if skill_set & set(_all_skills(p))]
        else:
            results = [p for p in results if skill_set.issubset(set(_all_skills(p)))]
    if args.min_bulk:
        results = [p for p in results if _bulk(p) >= args.min_bulk]
    if args.min_hp:
        results = [p for p in results if _stat(p,'hp') >= args.min_hp]
    if args.min_def:
        results = [p for p in results if _stat(p,'defense') >= args.min_def]
    if args.min_spdef:
        results = [p for p in results if _stat(p,'special_defense') >= args.min_spdef]

    show(results, sort_by=args.sort, limit=args.limit)
