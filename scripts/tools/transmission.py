"""
传动核心计算模块

Config 格式:
  {
    "skills": [{"name": str, "trans": int}, ...],  # 按初始槽位顺序
    "locked_slots": [1, 3, ...],                   # 1-based，主轴槽位
    "slot_trans_values": [0, 1, 0, 0]              # 0-based，各槽位槽传值
  }

positions: 长度N的列表，positions[slot] = skillIdx (0-based)
"""


def step_positions(positions, config):
    skills = config.get("skills", [])
    locked_slots = set(s - 1 for s in config.get("locked_slots", []))
    slot_trans = config.get("slot_trans_values", [0] * len(positions))
    N = len(positions)
    free_slots = [s for s in range(N) if s not in locked_slots]
    if not free_slots:
        return list(positions)

    cur = list(positions)
    total_moves = [0] * N
    for slot in free_slots:
        idx = cur[slot]
        total_moves[idx] = skills[idx].get("trans", 0) + (slot_trans[slot] if slot < len(slot_trans) else 0)

    max_steps = max(total_moves) if total_moves else 0
    Nf = len(free_slots)

    for step in range(1, max_steps + 1):
        free_skills = [cur[s] for s in free_slots]
        movers = [(si, fi) for fi, si in enumerate(free_skills) if total_moves[si] >= step]
        stayers = [(si, fi) for fi, si in enumerate(free_skills) if total_moves[si] < step]

        target = [None] * Nf
        for si, orig_fi in movers:
            p = (orig_fi + 1) % Nf
            while target[p] is not None:
                p = (p + 1) % Nf
            target[p] = si

        rem = [fi for fi in range(Nf) if target[fi] is None]
        stayers.sort(key=lambda x: x[1])
        for i, (si, _) in enumerate(stayers):
            target[rem[i]] = si

        new_pos = list(cur)
        for fi, slot in enumerate(free_slots):
            new_pos[slot] = target[fi]
        cur = new_pos

    return cur


def simulate(initial_positions, config, turns):
    """返回 turns+1 个状态（含初始）"""
    history = [list(initial_positions)]
    cur = list(initial_positions)
    for _ in range(turns):
        cur = step_positions(cur, config)
        history.append(list(cur))
    return history


if __name__ == "__main__":
    # 示例：帕帕斯卡（1号位槽传1）+ 钢铁洪流（传动2）在1号位
    config = {
        "skills": [
            {"name": "钢铁洪流", "trans": 2},
            {"name": "技能2", "trans": 0},
            {"name": "技能3", "trans": 0},
            {"name": "技能4", "trans": 0},
        ],
        "locked_slots": [],
        "slot_trans_values": [1, 0, 0, 0],
    }
    history = simulate([0, 1, 2, 3], config, 4)
    names = [s["name"] for s in config["skills"]]
    for t, pos in enumerate(history):
        label = "初始" if t == 0 else f"第{t}回合后"
        print(f"{label}: {[names[pos[s]] for s in range(4)]}")
