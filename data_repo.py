"""数据加载与程序层计算：种族值横向对比、抗性与打击面"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"


def _load(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        path = DATA_DIR / "raw" / filename
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # 兼容头部 JS 风格注释
    start = content.find("{") if content.lstrip().startswith("/*") else -1
    if start == -1:
        start = content.find("[") if content.lstrip().startswith("/*") else -1
    if start > 0:
        content = content[start:]
    return json.loads(content)


class DataRepo:
    def __init__(self):
        raw = _load("pokemon.json")
        self.pokemon: list[dict] = raw if isinstance(raw, list) else list(raw.values())
        skills_raw = _load("skills.json")
        skills_list = skills_raw if isinstance(skills_raw, list) else list(skills_raw.values())
        self.skill_by_name: dict[str, dict] = {s["name"]: s for s in skills_list}
        raw_chart = _load("type_chart.json")
        self.type_chart: dict = raw_chart.get("multiplier_matrix", {})
        self._stat_ranks = self._build_stat_ranks()

    def find(self, query: str) -> Optional[dict]:
        for p in self.pokemon:
            if p["base_name"] == query or p["display_name"] == query or p["pokemon_key"] == query:
                return p
        for p in self.pokemon:
            if query in p["base_name"] or query in p["display_name"]:
                return p
        return None

    def _build_stat_ranks(self) -> dict[str, list[int]]:
        keys = ["hp", "attack", "special_attack", "defense", "special_defense", "speed", "total"]
        ranks: dict[str, list[int]] = {k: [] for k in keys}
        for p in self.pokemon:
            s = p.get("stats", {})
            for k in keys:
                try:
                    ranks[k].append(int(s.get(k, 0)))
                except (ValueError, TypeError):
                    ranks[k].append(0)
        for k in ranks:
            ranks[k].sort()
        return ranks

    def stat_percentile(self, stat_key: str, value: int) -> int:
        """返回该数值在全精灵中的百分位（0-100）"""
        arr = self._stat_ranks.get(stat_key, [])
        if not arr:
            return 0
        count = sum(1 for v in arr if v <= value)
        return round(count / len(arr) * 100)

    def get_type_effectiveness(self, attacking_type: str, defending_types: list[str]) -> float:
        """PVP属性倍率规则：
        - 任一防守属性免疫 → 0
        - 单属性：直接取倍率
        - 双属性：双克=3x，双抗=1/3x，一克一抗=1x，单克=2x，单抗=0.5x
        """
        chart = self.type_chart.get(attacking_type, {})
        mults = [chart.get(dt, 1.0) for dt in defending_types]
        if any(m == 0 for m in mults):
            return 0.0
        if len(mults) == 1:
            return mults[0]
        eff = sum(1 for m in mults if m > 1)
        resist = sum(1 for m in mults if m < 1)
        if eff == 2: return 3.0
        if resist == 2: return 1 / 3
        if eff == 1 and resist == 1: return 1.0
        if eff == 1: return 2.0
        if resist == 1: return 0.5
        return 1.0

    def compute_defense_profile(self, defending_types: list[str]) -> dict:
        """计算精灵的防御属性分布（PVP规则：双克3x，双抗1/3）"""
        takes_3x, takes_2x, takes_half, takes_third, immune = [], [], [], [], []
        all_types = list(self.type_chart.keys())
        for atk_type in all_types:
            mult = self.get_type_effectiveness(atk_type, defending_types)
            if mult == 0:
                immune.append(atk_type)
            elif mult >= 3:
                takes_3x.append(atk_type)
            elif mult == 2:
                takes_2x.append(atk_type)
            elif abs(mult - 1/3) < 0.01:
                takes_third.append(atk_type)
            elif mult == 0.5:
                takes_half.append(atk_type)
        return {
            "takes_3x_from": takes_3x,
            "takes_2x_from": takes_2x,
            "resists_half": takes_half,
            "resists_third": takes_third,
            "immune_to": immune,
        }

    def compute_coverage(self, skill_names: list[str], defending_types: list[str]) -> dict:
        """计算技能池对各属性的打击面"""
        effective, neutral, resisted = [], [], []
        for name in skill_names:
            skill = self.skill_by_name.get(name)
            if not skill:
                continue
            atk_type = skill.get("attribute")
            if not atk_type:
                continue
            mult = self.get_type_effectiveness(atk_type, defending_types)
            if mult > 1:
                effective.append(name)
            elif mult < 1:
                resisted.append(name)
            else:
                neutral.append(name)
        return {"effective": effective, "neutral": neutral, "resisted": resisted}

    def build_stat_comparison(self, stats: dict) -> dict:
        """种族值横向对比，返回各项百分位"""
        result = {}
        for key in ["hp", "attack", "special_attack", "defense", "special_defense", "speed", "total"]:
            try:
                val = int(stats.get(key, 0))
            except (ValueError, TypeError):
                val = 0
            result[key] = {"value": val, "percentile": self.stat_percentile(key, val)}
        return result
