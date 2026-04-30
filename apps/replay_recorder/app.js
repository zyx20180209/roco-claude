// ── 状态 ──────────────────────────────────────────────
let replay = null;
let pendingChanges = [];
let pokemonState = {};
let fieldState = { my: { marks: [] }, enemy: { marks: [] } };
let editingTurn = null;  // 正在编辑的回合号，null=新增回合

const DOT_ZH = { poison: '毒', burn: '灼', freeze: '冻' };
const BUFF_ZH = { attack: '物攻', special_attack: '魔攻', defense: '物防', special_defense: '魔防', speed: '速', hit_count: '连击', power: '威力' };

// ── 初始化 ────────────────────────────────────────────
window.onload = () => {
  for (let i = 0; i < 6; i++) {
    document.getElementById('my-team-inputs').innerHTML +=
      `<input type="text" placeholder="我方精灵 ${i+1}" id="my-p${i}" oninput="updateStarterOptions()">`;
    document.getElementById('enemy-team-inputs').innerHTML +=
      `<input type="text" placeholder="敌方精灵 ${i+1}" id="enemy-p${i}" oninput="updateStarterOptions()">`;
  }
};

function updateStarterOptions() {
  ['my','enemy'].forEach(side => {
    const sel = document.getElementById(`${side}-starter`);
    const cur = sel.value;
    const team = Array.from({length:6}, (_,i) => document.getElementById(`${side}-p${i}`)?.value.trim()).filter(Boolean);
    sel.innerHTML = '<option value="">-- 选择 --</option>' + team.map(n => `<option value="${n}">${n}</option>`).join('');
    if (cur && team.includes(cur)) sel.value = cur;
  });
}

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
  const myStarter = document.getElementById('my-starter').value || myTeam[0];
  const enemyStarter = document.getElementById('enemy-starter').value || enemyTeam[0];
  replay = {
    id, created_at: new Date().toISOString(),
    my_team: myTeam, enemy_team: enemyTeam,
    starting_active: { my: myStarter, enemy: enemyStarter },
    turns: [], result: null
  };
  initPokemonState(myTeam, enemyTeam, myStarter, enemyStarter);
  showRecordUI();
  saveToStorage();
}

function initPokemonState(myTeam, enemyTeam, myStarter, enemyStarter) {
  pokemonState = {};
  fieldState = { my: { marks: [] }, enemy: { marks: [] } };
  const init = (side, team, starter) => team.forEach((name) => {
    pokemonState[`${side}_${name}`] = {
      hp_pct: 100, hp_cur: null, hp_max: null, energy: 10,
      buffs: { attack: 0, special_attack: 0, defense: 0, special_defense: 0, speed: 0, hit_count: 0, power: 0 },
      dots: { poison: 0, burn: 0, freeze: 0 },
      passive_effects: {
        attack_pct: 0, special_attack_pct: 0, defense_pct: 0, special_defense_pct: 0,
        speed_flat: 0, power_flat: 0, hit_count: 0, moe: 0,
      },
      active: name === (starter || team[0]), fainted: false, boss: false,
    };
  });
  init('my', myTeam, myStarter);
  init('enemy', enemyTeam, enemyStarter);
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
  ['my','enemy'].forEach(side => {
    const marks = fieldState[side].marks;
    const el = document.getElementById(`${side}-field-marks`);
    if (el) el.innerHTML = marks.length
      ? '场地印记：' + marks.map(m => `<span class="tag tag-mark">${m}</span>`).join(' ')
      : '';
  });
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
    const bossTag = s.boss ? '<span class="tag tag-boss">首领</span>' : '';
    const classes = ['pokemon-card', s.active?'active':'', s.fainted?'fainted':'', s.boss?'boss':''].filter(Boolean).join(' ');
    return `<div class="${classes}">
      <div class="pokemon-name">${name}</div>
      <div class="hp-bar"><div class="hp-fill ${hpClass}" style="width:${hp}%"></div></div>
      <div style="font-size:0.7rem;color:#aaa;margin-bottom:2px">${hpLabel}</div>
      <div class="stat-row">
        <span class="tag tag-energy">⚡${s.energy ?? 10}</span>
        ${bossTag}${passive}${dots}${buffs}
      </div>
    </div>`;
  }).join('');
}

// ── 变化表单 ──────────────────────────────────────────
function updatePokemonSelect() {
  const side = document.getElementById('f-side').value;
  const team = side === 'my' ? replay.my_team : replay.enemy_team;
  document.getElementById('f-pokemon').innerHTML = team.map(n => `<option value="${n}">${n}</option>`).join('');
  const activeName = team.find(n => pokemonState[`${side}_${n}`]?.active);
  if (activeName) document.getElementById('f-pokemon').value = activeName;
  document.getElementById('hp-my-box').style.display = side === 'my' ? 'flex' : 'none';
  document.getElementById('hp-enemy-box').style.display = side === 'enemy' ? 'flex' : 'none';
}

function openChangeForm() {
  document.getElementById('change-form').style.display = 'block';
  updatePokemonSelect();
  // 默认选中当前在场精灵
  const side = document.getElementById('f-side').value;
  const team = side === 'my' ? replay.my_team : replay.enemy_team;
  const activeName = team.find(n => pokemonState[`${side}_${n}`]?.active);
  if (activeName) document.getElementById('f-pokemon').value = activeName;
  const ids = ['f-skill','f-hp-cur','f-hp-max','f-hp-pct','f-energy',
    'f-dmg-direct','f-dmg-dot','f-poison','f-burn','f-freeze',
    'f-atk','f-satk','f-def','f-sdef','f-spd','f-hit','f-pow',
    'f-marks-add','f-marks-rm',
    'f-pe-atk','f-pe-satk','f-pe-def','f-pe-sdef','f-pe-spd','f-pe-pow','f-pe-hit','f-pe-moe'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  ['f-entered','f-exited','f-fainted','f-boss','f-defeated','f-surrender'].forEach(id => {
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
    defeated: document.getElementById('f-defeated').checked || undefined,
    surrender: document.getElementById('f-surrender').checked || undefined,
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
  document.getElementById('f-defeated').checked = !!c.defeated;
  document.getElementById('f-surrender').checked = !!c.surrender;
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
function recomputeResult() {
  // 扫描所有回合，找最早的战败/投降标记
  for (const t of replay.turns) {
    for (const c of t.changes) {
      if (c.defeated || c.surrender) {
        const loser = c.side;
        const winner = loser === 'my' ? 'enemy' : 'my';
        const reason = c.surrender ? 'surrender' : 'defeated';
        replay.result = { winner, loser, reason, ended_at_turn: t.turn };
        return;
      }
    }
  }
  replay.result = null;
}

function submitTurn() {
  if (!pendingChanges.length) { alert('请先添加变化'); return; }
  if (editingTurn !== null) {
    // 替换该回合
    const idx = replay.turns.findIndex(t => t.turn === editingTurn);
    if (idx >= 0) replay.turns[idx] = { turn: editingTurn, changes: [...pendingChanges] };
    editingTurn = null;
    pendingChanges = [];
    // 重算所有状态到最新
    initPokemonState(replay.my_team, replay.enemy_team, replay.starting_active?.my, replay.starting_active?.enemy);
    replay.turns.forEach(t => {
      t.changes.forEach(applyChange);
      // 灼烧减半（每回合末，留场精灵）
      const exitedThisTurn = new Set(t.changes.filter(c => c.exited || c.fainted).map(c => `${c.side}_${c.pokemon}`));
      Object.entries(pokemonState).forEach(([key, s]) => {
        if (!s.active || exitedThisTurn.has(key)) return;
        if (s.dots.burn > 0) s.dots.burn = Math.floor(s.dots.burn / 2);
      });
    });
  } else {
    const turn = { turn: replay.turns.length + 1, changes: [...pendingChanges] };
    replay.turns.push(turn);
    pendingChanges.forEach(applyChange);
    const exitedThisTurn = new Set(pendingChanges.filter(c => c.exited || c.fainted).map(c => `${c.side}_${c.pokemon}`));
    Object.entries(pokemonState).forEach(([key, s]) => {
      if (!s.active || exitedThisTurn.has(key)) return;
      if (s.dots.burn > 0) s.dots.burn = Math.floor(s.dots.burn / 2);
    });
    pendingChanges = [];
  }
  renderPendingChanges();
  renderTeams();
  recomputeResult();
  renderHistory();
  renderResult();
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
  if (c.marks_added) fieldState[c.side].marks.push(...c.marks_added);
  if (c.marks_removed) fieldState[c.side].marks = fieldState[c.side].marks.filter(m => !c.marks_removed.includes(m));
  if (c.passive_effects) Object.entries(c.passive_effects).forEach(([k,v]) => { s.passive_effects[k] = (s.passive_effects[k]||0) + v; });
}

function prevTurn() {
  if (!replay.turns.length) return;
  const lastTurn = replay.turns.pop();
  pendingChanges = lastTurn.changes;
  initPokemonState(replay.my_team, replay.enemy_team, replay.starting_active?.my, replay.starting_active?.enemy);
  replay.turns.forEach(t => t.changes.forEach(applyChange));
  renderPendingChanges();
  renderTeams(); renderHistory(); updateTurnLabel(); saveToStorage();
}
// ── 历史 ──────────────────────────────────────────────
function renderResult() {
  const banner = document.getElementById('result-banner');
  if (!banner) return;
  if (!replay.result) {
    banner.style.display = 'none';
    return;
  }
  const r = replay.result;
  const winnerZh = r.winner === 'my' ? '我方胜' : '敌方胜';
  const reasonZh = r.reason === 'surrender' ? '投降' : '战败';
  const loserZh = r.loser === 'my' ? '我方' : '敌方';
  banner.style.display = 'block';
  banner.textContent = `🏁 战斗结束（第${r.ended_at_turn}回合）：${loserZh}${reasonZh}，${winnerZh}`;
}

function renderHistory() {
  const container = document.getElementById('turn-history');
  container.innerHTML = [...replay.turns].reverse().map(t => {
    const lines = t.changes.map(c => formatChangeDetail(c));
    return `<div style="border-bottom:1px solid #223;padding:8px 0">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span class="turn-label">第${t.turn}回合</span>
        <button class="primary" style="padding:1px 8px;font-size:0.72rem" onclick="rewindTo(${t.turn})">返回此回合</button>
      </div>
      <div style="font-size:0.78rem;line-height:1.6">${lines.join('')}</div>
    </div>`;
  }).join('');
}

function formatChangeDetail(c) {
  const sideLabel = c.side === 'my'
    ? `<span style="color:#a5d6a7">我方</span>`
    : `<span style="color:#f48fb1">敌方</span>`;
  const parts = [];
  if (c.entered) parts.push(`<span style="color:#90caf9">⬆换入</span>`);
  if (c.exited) parts.push(`<span style="color:#aaa">⬇换出</span>`);
  if (c.boss) parts.push(`<span style="color:#ffd700">👑首领化</span>`);
  if (c.fainted) parts.push(`<span style="color:#f44336">💀战死</span>`);
  if (c.defeated) parts.push(`<span style="color:#f44336;font-weight:bold">🏳战败</span>`);
  if (c.surrender) parts.push(`<span style="color:#ffd700;font-weight:bold">🏳投降</span>`);
  if (c.skill) parts.push(`<span style="color:#fff176">${c.skill}</span>`);
  if (c.energy_delta != null) {
    const sign = c.energy_delta > 0 ? '+' : '';
    parts.push(`<span style="color:#90caf9">⚡${sign}${c.energy_delta}</span>`);
  }
  if (c.hp_cur != null) {
    parts.push(`<span style="color:#aaa">HP→${c.hp_cur}/${c.hp_max}(${c.hp_pct}%)</span>`);
  } else if (c.hp_pct != null) {
    parts.push(`<span style="color:#aaa">HP→${c.hp_pct}%</span>`);
  }
  if (c.damage_received) {
    const d = c.damage_received;
    if (d.direct) parts.push(`<span style="color:#ef9a9a">直伤${d.direct}</span>`);
    if (d.dot) parts.push(`<span style="color:#ef9a9a">DoT${d.dot}</span>`);
  }
  if (c.dots) {
    Object.entries(c.dots).forEach(([k,v]) => {
      if (v !== 0) parts.push(`<span style="color:#f88">${DOT_ZH[k]}${v>0?'+':''}${v}</span>`);
    });
  }
  if (c.buffs) {
    Object.entries(c.buffs).forEach(([k,v]) => {
      if (v !== 0) {
        const color = v > 0 ? '#a5d6a7' : '#ce93d8';
        parts.push(`<span style="color:${color}">${BUFF_ZH[k]}${v>0?'+':''}${v}</span>`);
      }
    });
  }
  if (c.passive_effects) {
    Object.entries(c.passive_effects).forEach(([k,v]) => {
      if (v !== 0) {
        const PE_ZH = { attack_pct: '物攻', special_attack_pct: '魔攻', defense_pct: '物防', special_defense_pct: '魔防', speed_flat: '速', power_flat: '威力', hit_count: '连击', moe: '萌' };
        const PE_UNIT = { attack_pct: '%', special_attack_pct: '%', defense_pct: '%', special_defense_pct: '%' };
        parts.push(`<span style="color:#80cbc4">永久${PE_ZH[k]}${v>0?'+':''}${v}${PE_UNIT[k]||''}</span>`);
      }
    });
  }
  if (c.marks_added && c.marks_added.length) parts.push(`<span style="color:#fff176">+印记[${c.marks_added.join(',')}]</span>`);
  if (c.marks_removed && c.marks_removed.length) parts.push(`<span style="color:#aaa">-印记[${c.marks_removed.join(',')}]</span>`);
  const noteHtml = c.note ? `<div style="color:#999;font-size:0.72rem;margin-left:14px">📝 ${c.note}</div>` : '';
  return `<div>　${sideLabel} <b>${c.pokemon}</b>：${parts.join(' / ')}</div>${noteHtml}`;
}

function rewindTo(turnNum) {
  const target = replay.turns.find(t => t.turn === turnNum);
  if (!target) return;
  editingTurn = turnNum;
  pendingChanges = JSON.parse(JSON.stringify(target.changes));
  // 状态回到该回合之前
  initPokemonState(replay.my_team, replay.enemy_team, replay.starting_active?.my, replay.starting_active?.enemy);
  replay.turns.filter(t => t.turn < turnNum).forEach(t => t.changes.forEach(applyChange));
  renderPendingChanges();
  renderTeams(); renderHistory(); updateTurnLabel(); saveToStorage();
}

function cancelEdit() {
  editingTurn = null;
  pendingChanges = [];
  // 重建到最新状态
  initPokemonState(replay.my_team, replay.enemy_team, replay.starting_active?.my, replay.starting_active?.enemy);
  replay.turns.forEach(t => t.changes.forEach(applyChange));
  renderPendingChanges();
  renderTeams(); renderHistory(); updateTurnLabel(); saveToStorage();
}

function updateTurnLabel() {
  const el = document.getElementById('turn-label');
  const btnSubmit = document.getElementById('btn-submit');
  const btnPrev = document.getElementById('btn-prev');
  const btnCancel = document.getElementById('btn-cancel-edit');
  if (editingTurn !== null) {
    el.textContent = `编辑第 ${editingTurn} 回合`;
    el.style.color = '#ffd700';
    if (btnSubmit) btnSubmit.textContent = '保存修改';
    if (btnPrev) btnPrev.style.display = 'none';
    if (btnCancel) btnCancel.style.display = '';
  } else {
    el.textContent = `第 ${replay.turns.length + 1} 回合`;
    el.style.color = '#a0c4ff';
    if (btnSubmit) btnSubmit.textContent = '提交本回合';
    if (btnPrev) btnPrev.style.display = '';
    if (btnCancel) btnCancel.style.display = 'none';
  }
}

// ── 导出 / 存储 ───────────────────────────────────────
function exportJSON() {
  const blob = new Blob([JSON.stringify(replay, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${replay.id}.json`;
  a.click();
}

function importJSON(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = JSON.parse(e.target.result);
      if (!data.my_team || !data.enemy_team || !data.turns) {
        alert('JSON 格式不正确'); return;
      }
      replay = data;
      initPokemonState(replay.my_team, replay.enemy_team, replay.starting_active?.my, replay.starting_active?.enemy);
      replay.turns.forEach(t => t.changes.forEach(applyChange));
      // 恢复队伍输入框
      replay.my_team.forEach((n, i) => { const el = document.getElementById(`my-p${i}`); if (el) el.value = n; });
      replay.enemy_team.forEach((n, i) => { const el = document.getElementById(`enemy-p${i}`); if (el) el.value = n; });
      document.getElementById('replay-id').value = replay.id;
      showRecordUI();
      recomputeResult();
      renderHistory();
      renderResult();
      saveToStorage();
    } catch { alert('JSON 解析失败'); }
  };
  reader.readAsText(file);
}

function saveToStorage() {
  localStorage.setItem('roco_replay', JSON.stringify({ replay, pokemonState, fieldState }));
}

function loadFromStorage() {
  const raw = localStorage.getItem('roco_replay');
  if (!raw) { alert('没有找到上次记录'); return; }
  const data = JSON.parse(raw);
  replay = data.replay;
  pokemonState = data.pokemonState;
  fieldState = data.fieldState || { my: { marks: [] }, enemy: { marks: [] } };
  replay.my_team.forEach((n, i) => { const el = document.getElementById(`my-p${i}`); if (el) el.value = n; });
  replay.enemy_team.forEach((n, i) => { const el = document.getElementById(`enemy-p${i}`); if (el) el.value = n; });
  document.getElementById('replay-id').value = replay.id;
  showRecordUI();
  recomputeResult();
  renderHistory();
  renderResult();
}

function resetAll() {
  if (!confirm('确认重置？当前记录将丢失')) return;
  localStorage.removeItem('roco_replay');
  location.reload();
}
