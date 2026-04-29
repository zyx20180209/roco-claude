// ── 状态 ──────────────────────────────────────────────
let replay = null;
let pendingChanges = [];
let pokemonState = {};

const DOT_ZH = { poison: '毒', burn: '灼', freeze: '冻' };
const BUFF_ZH = { attack: '物攻', special_attack: '魔攻', defense: '物防', special_defense: '魔防', speed: '速', hit_count: '连击', power: '威力' };

// ── 初始化 ────────────────────────────────────────────
window.onload = () => {
  for (let i = 0; i < 6; i++) {
    document.getElementById('my-team-inputs').innerHTML +=
      `<input type="text" placeholder="我方精灵 ${i+1}" id="my-p${i}">`;
    document.getElementById('enemy-team-inputs').innerHTML +=
      `<input type="text" placeholder="敌方精灵 ${i+1}" id="enemy-p${i}">`;
  }
};

function getTeam(side) {
  return Array.from({length: 6}, (_, i) =>
    document.getElementById(`${side}-p${i}`).value.trim()
  ).filter(Boolean);
}

function startReplay() {
  const id = document.getElementById('replay-id').value.trim() || `r${Date.now()}`;
  const myTeam = getTeam('my');
  const enemyTeam = getTeam('enemy');
  if (!myTeam.length || !enemyTeam.length) { alert('请填写双方队伍'); return; }
  replay = { id, created_at: new Date().toISOString(), my_team: myTeam, enemy_team: enemyTeam, turns: [] };
  initPokemonState(myTeam, enemyTeam);
  showRecordUI();
  saveToStorage();
}

function initPokemonState(myTeam, enemyTeam) {
  pokemonState = {};
  const init = (side, team) => team.forEach((name, i) => {
    pokemonState[`${side}_${name}`] = {
      hp_pct: 100, hp_cur: null, hp_max: null, energy: 10,
      buffs: { attack: 0, special_attack: 0, defense: 0, special_defense: 0, speed: 0, hit_count: 0, power: 0 },
      dots: { poison: 0, burn: 0, freeze: 0 },
      passive_effects: {
        attack_pct: 0, special_attack_pct: 0, defense_pct: 0, special_defense_pct: 0,
        speed_flat: 0, power_flat: 0, hit_count: 0, moe: 0,
      },
      marks: [], active: i === 0, fainted: false, boss: false,
    };
  });
  init('my', myTeam);
  init('enemy', enemyTeam);
}

function showRecordUI() {
  document.getElementById('setup-section').style.display = 'none';
  ['state-section','input-section','action-section','history-section'].forEach(id => {
    document.getElementById(id).style.display = 'block';
  });
  renderTeams();
  updateTurnLabel();
}

// ── 精灵状态面板 ──────────────────────────────────────
function renderTeams() {
  renderTeamDisplay('my', replay.my_team);
  renderTeamDisplay('enemy', replay.enemy_team);
}

function renderTeamDisplay(side, team) {
  const container = document.getElementById(`${side}-team-display`);
  container.innerHTML = team.map(name => {
    const s = pokemonState[`${side}_${name}`] || {};
    const hp = s.hp_pct ?? 100;
    const hpClass = hp > 50 ? '' : hp > 25 ? 'low' : 'critical';
    const hpLabel = (side === 'my' && s.hp_cur != null && s.hp_max != null)
      ? `${s.hp_cur}/${s.hp_max}` : `${hp}%`;
    const dots = Object.entries(s.dots || {}).filter(([,v]) => v > 0)
      .map(([k,v]) => `<span class="tag tag-dot">${DOT_ZH[k]}${v}</span>`).join('');
    const buffs = Object.entries(s.buffs || {}).filter(([,v]) => v !== 0)
      .map(([k,v]) => `<span class="tag ${v>0?'tag-buff':'tag-debuff'}">${BUFF_ZH[k]}${v>0?'+'+v:v}</span>`).join('');
    const PE_ZH = { attack_pct: '物攻', special_attack_pct: '魔攻', defense_pct: '物防', special_defense_pct: '魔防', speed_flat: '速', power_flat: '威力', hit_count: '连击', moe: '萌' };
    const PE_UNIT = { attack_pct: '%', special_attack_pct: '%', defense_pct: '%', special_defense_pct: '%', speed_flat: '', power_flat: '', hit_count: '', moe: '' };
    const passive = Object.entries(s.passive_effects || {}).filter(([,v]) => v !== 0)
      .map(([k,v]) => `<span class="tag" style="background:#1a2a3a;color:#80cbc4">${PE_ZH[k]}${v>0?'+':''}${v}${PE_UNIT[k]}</span>`).join('');
    const marks = (s.marks || []).map(m => `<span class="tag tag-mark">${m}</span>`).join('');
    const bossTag = s.boss ? '<span class="tag tag-boss">首领</span>' : '';
    const classes = ['pokemon-card', s.active?'active':'', s.fainted?'fainted':'', s.boss?'boss':''].filter(Boolean).join(' ');
    return `<div class="${classes}">
      <div class="pokemon-name">${name}</div>
      <div class="hp-bar"><div class="hp-fill ${hpClass}" style="width:${hp}%"></div></div>
      <div style="font-size:0.7rem;color:#aaa;margin-bottom:2px">${hpLabel}</div>
      <div class="stat-row">
        <span class="tag tag-energy">⚡${s.energy ?? 10}</span>
        ${bossTag}${passive}${dots}${buffs}${marks}
      </div>
    </div>`;
  }).join('');
}

// ── 变化表单 ──────────────────────────────────────────
function updatePokemonSelect() {
  const side = document.getElementById('f-side').value;
  const team = side === 'my' ? replay.my_team : replay.enemy_team;
  document.getElementById('f-pokemon').innerHTML = team.map(n => `<option value="${n}">${n}</option>`).join('');
  // 切换血量输入模式
  document.getElementById('hp-my-box').style.display = side === 'my' ? 'flex' : 'none';
  document.getElementById('hp-enemy-box').style.display = side === 'enemy' ? 'flex' : 'none';
}

function openChangeForm() {
  document.getElementById('change-form').style.display = 'block';
  updatePokemonSelect();
  const ids = ['f-skill','f-hp-cur','f-hp-max','f-hp-pct','f-energy',
    'f-dmg-direct','f-dmg-dot','f-poison','f-burn','f-freeze',
    'f-atk','f-satk','f-def','f-sdef','f-spd','f-hit','f-pow',
    'f-marks-add','f-marks-rm',
    'f-pe-atk','f-pe-satk','f-pe-def','f-pe-sdef','f-pe-spd','f-pe-pow','f-pe-hit','f-pe-moe'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  ['f-entered','f-exited','f-fainted','f-boss'].forEach(id => {
    const el = document.getElementById(id); if (el) el.checked = false;
  });
}

function cancelChange() {
  document.getElementById('change-form').style.display = 'none';
}

function numOrNull(id) {
  const v = document.getElementById(id)?.value;
  return (v !== '' && v != null) ? parseFloat(v) : null;
}

function addChange() {
  const side = document.getElementById('f-side').value;
  const pokemon = document.getElementById('f-pokemon').value;

  // 血量
  let hp_pct = null, hp_cur = null, hp_max = null;
  if (side === 'my') {
    hp_cur = numOrNull('f-hp-cur');
    hp_max = numOrNull('f-hp-max');
    if (hp_cur != null && hp_max != null && hp_max > 0) hp_pct = Math.round(hp_cur / hp_max * 100);
  } else {
    hp_pct = numOrNull('f-hp-pct');
  }

  const buffs = {};
  [['f-atk','attack'],['f-satk','special_attack'],['f-def','defense'],
   ['f-sdef','special_defense'],['f-spd','speed'],['f-hit','hit_count'],['f-pow','power']
  ].forEach(([id,key]) => { const v = numOrNull(id); if (v != null) buffs[key] = v; });

  const dots = {};
  [['f-poison','poison'],['f-burn','burn'],['f-freeze','freeze']].forEach(([id,key]) => {
    const v = numOrNull(id); if (v != null) dots[key] = v;
  });

  const dmgDirect = numOrNull('f-dmg-direct');
  const dmgDot = numOrNull('f-dmg-dot');
  const damage_received = (dmgDirect != null || dmgDot != null) ? {
    direct: dmgDirect, dot: dmgDot,
  } : null;

  const marks_added = document.getElementById('f-marks-add').value.split(',').map(s=>s.trim()).filter(Boolean);
  const marks_removed = document.getElementById('f-marks-rm').value.split(',').map(s=>s.trim()).filter(Boolean);
  const passive_effects = {};
  [['f-pe-atk','attack_pct'],['f-pe-satk','special_attack_pct'],['f-pe-def','defense_pct'],
   ['f-pe-sdef','special_defense_pct'],['f-pe-spd','speed_flat'],['f-pe-pow','power_flat'],
   ['f-pe-hit','hit_count'],['f-pe-moe','moe']
  ].forEach(([id,key]) => { const v = numOrNull(id); if (v != null) passive_effects[key] = v; });

  const change = {
    side, pokemon,
    entered: document.getElementById('f-entered').checked || undefined,
    exited: document.getElementById('f-exited').checked || undefined,
    fainted: document.getElementById('f-fainted').checked || undefined,
    boss: document.getElementById('f-boss').checked || undefined,
    skill: document.getElementById('f-skill').value.trim() || undefined,
    hp_pct: hp_pct ?? undefined,
    hp_cur: hp_cur ?? undefined,
    hp_max: hp_max ?? undefined,
    energy_delta: numOrNull('f-energy') ?? undefined,
    damage_received: damage_received ?? undefined,
    buffs: Object.keys(buffs).length ? buffs : undefined,
    dots: Object.keys(dots).length ? dots : undefined,
    marks_added: marks_added.length ? marks_added : undefined,
    marks_removed: marks_removed.length ? marks_removed : undefined,
    passive_effects: Object.keys(passive_effects).length ? passive_effects : undefined,
  };
  // strip undefined
  Object.keys(change).forEach(k => { if (change[k] === undefined) delete change[k]; });

  pendingChanges.push(change);
  renderPendingChanges();
  cancelChange();
}

function renderPendingChanges() {
  const list = document.getElementById('changes-list');
  list.innerHTML = pendingChanges.map((c, i) => {
    const parts = [];
    if (c.entered) parts.push('换入');
    if (c.exited) parts.push('换出');
    if (c.boss) parts.push('首领化');
    if (c.skill) parts.push(c.skill);
    if (c.hp_pct != null) parts.push(`HP→${c.hp_pct}%`);
    if (c.hp_cur != null) parts.push(`HP→${c.hp_cur}/${c.hp_max}`);
    if (c.energy_delta != null) parts.push(`能量${c.energy_delta>0?'+':''}${c.energy_delta}`);
    if (c.damage_received) {
      if (c.damage_received.direct) parts.push(`直伤${c.damage_received.direct}`);
      if (c.damage_received.dot) parts.push(`DoT${c.damage_received.dot}`);
    }
    if (c.fainted) parts.push('⚔️战死');
    return `<div style="background:#16213e;border-radius:4px;padding:6px 8px;font-size:0.8rem">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span><b>${c.side==='my'?'我方':'敌方'} ${c.pokemon}</b>：${parts.join(' / ')}</span>
        <span style="display:flex;gap:4px">
          <button class="primary" style="padding:1px 6px;font-size:0.75rem" onclick="editChange(${i})">编辑</button>
          <button style="background:#5c1a1a;border:none;color:#f88;border-radius:3px;padding:1px 6px;cursor:pointer;font-size:0.75rem" onclick="removeChange(${i})">×</button>
        </span>
      </div>
      <input type="text" placeholder="备注（可选）" value="${c.note||''}"
        style="width:100%;margin-top:4px;font-size:0.78rem;background:#0f3460;color:#e0e0e0;border:1px solid #334;border-radius:3px;padding:2px 6px"
        oninput="pendingChanges[${i}].note=this.value">
    </div>`;
  }).join('');
}

function removeChange(i) {
  pendingChanges.splice(i, 1);
  renderPendingChanges();
}

function editChange(i) {
  const c = pendingChanges[i];
  openChangeForm();
  document.getElementById('f-side').value = c.side;
  updatePokemonSelect();
  document.getElementById('f-pokemon').value = c.pokemon;
  document.getElementById('f-entered').checked = !!c.entered;
  document.getElementById('f-exited').checked = !!c.exited;
  document.getElementById('f-fainted').checked = !!c.fainted;
  document.getElementById('f-boss').checked = !!c.boss;
  document.getElementById('f-skill').value = c.skill || '';
  if (c.side === 'my') {
    document.getElementById('f-hp-cur').value = c.hp_cur ?? '';
    document.getElementById('f-hp-max').value = c.hp_max ?? '';
  } else {
    document.getElementById('f-hp-pct').value = c.hp_pct ?? '';
  }
  document.getElementById('f-energy').value = c.energy_delta ?? '';
  document.getElementById('f-dmg-direct').value = c.damage_received?.direct ?? '';
  document.getElementById('f-dmg-dot').value = c.damage_received?.dot ?? '';
  [['f-atk','attack'],['f-satk','special_attack'],['f-def','defense'],
   ['f-sdef','special_defense'],['f-spd','speed'],['f-hit','hit_count'],['f-pow','power']
  ].forEach(([id,key]) => { document.getElementById(id).value = c.buffs?.[key] ?? ''; });
  [['f-poison','poison'],['f-burn','burn'],['f-freeze','freeze']].forEach(([id,key]) => {
    document.getElementById(id).value = c.dots?.[key] ?? '';
  });
  document.getElementById('f-marks-add').value = (c.marks_added||[]).join(',');
  document.getElementById('f-marks-rm').value = (c.marks_removed||[]).join(',');
  [['f-pe-atk','attack_pct'],['f-pe-satk','special_attack_pct'],['f-pe-def','defense_pct'],
   ['f-pe-sdef','special_defense_pct'],['f-pe-spd','speed_flat'],['f-pe-pow','power_flat'],
   ['f-pe-hit','hit_count'],['f-pe-moe','moe']
  ].forEach(([id,key]) => { document.getElementById(id).value = c.passive_effects?.[key] ?? ''; });
  // remove old entry, new one will be added on confirm
  pendingChanges.splice(i, 1);
  renderPendingChanges();
}

// ── 回合提交 ──────────────────────────────────────────
function submitTurn() {
  if (!pendingChanges.length) { alert('请先添加变化'); return; }
  const turn = { turn: replay.turns.length + 1, changes: [...pendingChanges] };
  replay.turns.push(turn);
  pendingChanges.forEach(applyChange);
  pendingChanges = [];
  renderPendingChanges();
  renderTeams();
  renderHistory();
  updateTurnLabel();
  saveToStorage();
}

function applyChange(c) {
  const key = `${c.side}_${c.pokemon}`;
  const s = pokemonState[key];
  if (!s) return;
  if (c.hp_pct != null) s.hp_pct = c.hp_pct;
  if (c.hp_cur != null) s.hp_cur = c.hp_cur;
  if (c.hp_max != null) s.hp_max = c.hp_max;
  if (c.energy_delta != null) s.energy = Math.max(0, Math.min(10, s.energy + c.energy_delta));
  if (c.boss) s.boss = true;
  if (c.fainted) { s.fainted = true; s.hp_pct = 0; s.active = false; }
  if (c.entered) {
    const team = c.side === 'my' ? replay.my_team : replay.enemy_team;
    team.forEach(n => { if (pokemonState[`${c.side}_${n}`]) pokemonState[`${c.side}_${n}`].active = false; });
    s.active = true;
  }
  if (c.exited) {
    s.active = false;
    // 清空临时 buff/debuff
    Object.keys(s.buffs).forEach(k => { s.buffs[k] = 0; });
    // 清空毒/灼烧，保留冻结
    s.dots.poison = 0;
    s.dots.burn = 0;
  }
  if (c.buffs) Object.entries(c.buffs).forEach(([k,v]) => { s.buffs[k] = (s.buffs[k]||0) + v; });
  if (c.dots) Object.entries(c.dots).forEach(([k,v]) => { s.dots[k] = Math.max(0, (s.dots[k]||0) + v); });
  if (c.marks_added) s.marks.push(...c.marks_added);
  if (c.marks_removed) s.marks = s.marks.filter(m => !c.marks_removed.includes(m));
  if (c.passive_effects) Object.entries(c.passive_effects).forEach(([k,v]) => { s.passive_effects[k] = (s.passive_effects[k]||0) + v; });
}

function undoTurn() {
  if (!replay.turns.length) return;
  replay.turns.pop();
  initPokemonState(replay.my_team, replay.enemy_team);
  replay.turns.forEach(t => t.changes.forEach(applyChange));
  renderTeams(); renderHistory(); updateTurnLabel(); saveToStorage();
}

// ── 历史 ──────────────────────────────────────────────
function renderHistory() {
  const container = document.getElementById('turn-history');
  container.innerHTML = [...replay.turns].reverse().map(t => {
    const summary = t.changes.map(c => {
      const parts = [c.side==='my'?'我':'敌', c.pokemon];
      if (c.boss) parts.push('首领化');
      if (c.skill) parts.push(c.skill);
      if (c.fainted) parts.push('战死');
      return parts.join(' ');
    }).join('  |  ');
    return `<div class="turn-item"><span class="turn-label">第${t.turn}回合</span><span class="change-summary">${summary}</span></div>`;
  }).join('');
}

function updateTurnLabel() {
  document.getElementById('turn-label').textContent = `第 ${replay.turns.length + 1} 回合`;
}

// ── 导出 / 存储 ───────────────────────────────────────
function exportJSON() {
  const blob = new Blob([JSON.stringify(replay, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${replay.id}.json`;
  a.click();
}

function saveToStorage() {
  localStorage.setItem('roco_replay', JSON.stringify({ replay, pokemonState }));
}

function loadFromStorage() {
  const raw = localStorage.getItem('roco_replay');
  if (!raw) { alert('没有找到上次记录'); return; }
  const data = JSON.parse(raw);
  replay = data.replay;
  pokemonState = data.pokemonState;
  replay.my_team.forEach((n, i) => { const el = document.getElementById(`my-p${i}`); if (el) el.value = n; });
  replay.enemy_team.forEach((n, i) => { const el = document.getElementById(`enemy-p${i}`); if (el) el.value = n; });
  document.getElementById('replay-id').value = replay.id;
  showRecordUI();
  renderHistory();
}

function resetAll() {
  if (!confirm('确认重置？当前记录将丢失')) return;
  localStorage.removeItem('roco_replay');
  location.reload();
}
