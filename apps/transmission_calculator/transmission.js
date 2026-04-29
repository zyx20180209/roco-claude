/**
 * 传动核心计算模块
 *
 * Config 格式:
 *   { skills: [{name, trans}], lockedSlots: [1,3,...], slotTransValues: [0,1,0,0] }
 *
 * positions: 长度N的数组，positions[slot] = skillIdx (0-based)
 */

export function stepPositions(positions, config) {
  const { skills, lockedSlots = [], slotTransValues = [0,0,0,0] } = config;
  const N = positions.length;
  const lockedSlotSet = new Set(lockedSlots.map(s => s - 1));
  const freeSlots = Array.from({length: N}, (_, i) => i).filter(s => !lockedSlotSet.has(s));
  if (freeSlots.length === 0) return [...positions];

  let cur = [...positions];

  // Compute each skill's total moves this turn (fixed at turn start)
  const totalMoves = new Array(N).fill(0);
  freeSlots.forEach(slot => {
    const skillIdx = cur[slot];
    totalMoves[skillIdx] = (skills[skillIdx]?.trans || 0) + (slotTransValues[slot] || 0);
  });

  const maxSteps = Math.max(0, ...totalMoves);
  for (let step = 1; step <= maxSteps; step++) {
    const freeSkills = freeSlots.map(s => cur[s]);
    const movers = [], stayers = [];
    freeSkills.forEach((skillIdx, fi) => {
      if (totalMoves[skillIdx] >= step) movers.push({ skillIdx, origFi: fi });
      else stayers.push({ skillIdx, origFi: fi });
    });

    const Nf = freeSlots.length;
    const targetFi = new Array(Nf).fill(null);
    for (const m of movers) {
      let p = (m.origFi + 1) % Nf;
      while (targetFi[p] !== null) p = (p + 1) % Nf;
      targetFi[p] = m.skillIdx;
    }
    const rem = [];
    for (let fi = 0; fi < Nf; fi++) if (targetFi[fi] === null) rem.push(fi);
    stayers.sort((a, b) => a.origFi - b.origFi);
    stayers.forEach((s, i) => { targetFi[rem[i]] = s.skillIdx; });

    const newPos = [...cur];
    freeSlots.forEach((slot, fi) => { newPos[slot] = targetFi[fi]; });
    cur = newPos;
  }
  return cur;
}

/** 模拟 turns 回合，返回每回合后的 positions 数组（含初始状态） */
export function simulate(initialPositions, config, turns) {
  const history = [initialPositions];
  let cur = initialPositions;
  for (let t = 0; t < turns; t++) {
    cur = stepPositions(cur, config);
    history.push(cur);
  }
  return history;
}
