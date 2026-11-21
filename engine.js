'use strict';
// Deck Delve — a co-op dice-and-cards dungeon crawl for phones.
// All cards, heroes, dungeons and numbers here are original to this project.
const crypto = require('crypto');

const d6 = () => crypto.randomInt(1, 7);
const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = crypto.randomInt(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const clone = (o) => JSON.parse(JSON.stringify(o));
const COLORS = ['str', 'agi', 'mag'];
const CNAME = { str: 'Strength', agi: 'Agility', mag: 'Magic', emp: 'Empowered' };
const XP_NEED = { 1: 4, 2: 6, 3: 8 };
const POTION_HEAL = 3;

const own = (o, k) => typeof k === 'string' && Object.prototype.hasOwnProperty.call(o, k);
function err(msg) { const e = new Error(msg); e.user = true; return e; }

// ---------- card helpers ----------
const box = (color, value, o = {}) => ({ color, value, wide: !!o.w, armor: !!o.a, dmg: o.d || 0, time: o.t || 0, skull: o.k || 0 });
const S = (v, o) => box('str', v, o), A = (v, o) => box('agi', v, o), M = (v, o) => box('mag', v, o);
const sk = (name, kind, amt = 0, cost = {}) => ({ name, kind, amt, cost });
const mon = (name, xp, item, skill, ...boxes) => ({ type: 'monster', name, xp, item, skill, boxes });
const per = (name, xp, item, skill, a, b) => ({ type: 'peril', name, xp, item, skill,
  options: [a, b].map(([label, cost, bx]) => ({ label, cost, box: bx })) });

// ---------- heroes ----------
const HEROES = {
  warrior: { name: 'Warrior', solo: { str: 4, agi: 2, mag: 1, hp: 6 }, duo: { str: 3, agi: 1, mag: 1, hp: 5 }, start: sk('Shield Wall', 'ward', 2, { color: 'str' }) },
  rogue:   { name: 'Rogue',   solo: { str: 2, agi: 4, mag: 1, hp: 5 }, duo: { str: 1, agi: 3, mag: 1, hp: 4 }, start: sk('Shadowstep', 'haste', 2, { color: 'agi' }) },
  mage:    { name: 'Mage',    solo: { str: 1, agi: 2, mag: 4, hp: 5 }, duo: { str: 1, agi: 1, mag: 3, hp: 4 }, start: sk('Arcane Shift', 'transmute', 0, { color: 'mag' }) },
  archer:  { name: 'Archer',  solo: { str: 2, agi: 3, mag: 2, hp: 5 }, duo: { str: 1, agi: 2, mag: 2, hp: 4 }, start: sk('Steady Aim', 'boost', 2, {}) },
  paladin: { name: 'Paladin', solo: { str: 3, agi: 1, mag: 3, hp: 6 }, duo: { str: 2, agi: 1, mag: 2, hp: 5 }, start: sk('Lay on Hands', 'heal', 1, { min: 4 }) },
};

// ---------- encounter deck (42 cards) ----------
const MONSTERS = [
  mon('Goblin Scout', 1, { agi: 1 }, sk('Quick Draw', 'boost', 2, { color: 'agi' }), A(3, { d: 1 }), S(4, { d: 1 }), M(3, { t: 1 })),
  mon('Giant Rat', 1, { hp: 1 }, sk('Scurry', 'haste', 1), S(3, { d: 1 }), A(4, { t: 1 }), A(7, { w: 1, d: 1 })),
  mon('Rattling Skeleton', 1, { str: 1 }, sk('Bone Guard', 'ward', 1, { color: 'str' }), S(4, { a: 1, d: 1 }), S(5, { d: 1 }), M(3, { t: 1 })),
  mon('Ooze', 1, { mag: 1 }, sk('Reform', 'reroll', 0, { color: 'mag' }), M(4, { d: 1 }), S(8, { w: 1, d: 1 }), A(3, { t: 1 })),
  mon('Road Bandit', 2, { agi: 1 }, sk('Dirty Trick', 'boost', 3, { min: 5 }), A(5, { d: 1 }), A(4, { t: 1 }), S(4, { d: 1 }), M(6, { w: 1, t: 1 })),
  mon('Hooded Cultist', 1, { mag: 1 }, sk('Dark Pact', 'transmute', 0, { color: 'mag' }), M(5, { d: 1 }), M(4, { d: 1 }), A(3, { t: 1 })),
  mon('Kobold Trapper', 1, { agi: 1 }, sk('Shortcut', 'haste', 2, { color: 'agi', min: 3 }), A(4, { d: 1 }), A(8, { w: 1, t: 1 }), S(3, { d: 1 })),
  mon('Orc Brute', 2, { str: 1, hp: 1 }, sk('Iron Hide', 'ward', 2, { color: 'str', min: 4 }), S(5, { a: 1, d: 1 }), S(10, { w: 1, d: 2 }), A(4, { t: 1 })),
  mon('Will-o-Wisp', 1, { mag: 1 }, sk('Spark', 'summon', 1, { color: 'mag', min: 4 }), M(5, { d: 1 }), A(5, { t: 1 }), M(3, { d: 1 })),
  mon('Shambler', 1, { hp: 1 }, sk('Second Wind', 'heal', 1, { min: 5 }), S(4, { d: 1 }), S(4, { d: 1 }), M(4, { t: 1 })),
  mon('Dire Wolf', 2, { agi: 1 }, sk('Pack Tactics', 'boost', 2), A(5, { d: 1 }), A(5, { d: 1 }), S(7, { w: 1, d: 1 }), M(3, { t: 1 })),
  mon('Spider Swarm', 1, { agi: 1 }, sk('Skitter', 'reroll', 0, { color: 'agi' }), A(9, { w: 1, d: 2 }), M(3, { t: 1 }), S(3, { d: 1 })),
  mon('Gargoyle', 2, { str: 1 }, sk('Stone Skin', 'ward', 1), S(5, { a: 1, t: 1 }), M(5, { d: 1 }), S(4, { d: 1 })),
  mon('Cackling Imp', 1, { mag: 1 }, sk('Blink', 'haste', 1, { color: 'mag' }), M(4, { d: 1 }), A(4, { d: 1 }), M(3, { t: 1 })),
  mon('Treasure Mimic', 2, { hp: 2 }, sk('Lucky Find', 'summon', 1, { min: 5 }), S(5, { d: 1 }), M(5, { d: 1 }), A(5, { d: 1 })),
  mon('Marsh Lurker', 1, { str: 1 }, sk('Hone', 'boost', 2, { color: 'str' }), S(4, { d: 1 }), A(4, { d: 1 }), S(7, { w: 1, t: 1 })),
  mon('Bog Witch', 2, { mag: 1, agi: 1 }, sk('Hex Swap', 'transmute', 0, { min: 4 }), M(5, { d: 2 }), M(9, { w: 1, t: 1 }), A(3, { d: 1 })),
  mon('Crypt Ghoul', 1, { hp: 1 }, sk('Grave Ward', 'ward', 1, { color: 'mag' }), S(4, { d: 1 }), M(5, { d: 1 }), A(3, { t: 1 })),
  mon('Hobgoblin Captain', 2, { str: 1 }, sk('Battle Cry', 'boost', 3, { color: 'str', min: 4 }), S(4, { a: 1, d: 1 }), S(5, { d: 1 }), A(5, { d: 1 }), M(3, { t: 1 })),
  mon('Cave Bats', 1, { agi: 1 }, sk('Echo', 'haste', 1, { color: 'agi' }), A(8, { w: 1, d: 1 }), S(3, { t: 1 })),
  mon('Stone Golem', 2, { str: 1, hp: 1 }, sk('Bulwark', 'ward', 2, { color: 'str', min: 5 }), S(6, { a: 1, d: 1 }), S(12, { w: 1, d: 2 }), M(3, { t: 1 })),
  mon('Wailing Banshee', 2, { mag: 1 }, sk('Unnerve', 'reroll'), M(5, { d: 1 }), M(5, { t: 1 }), A(4, { d: 1 })),
  mon('Harpy', 1, { agi: 1 }, sk('Swoop', 'boost', 2, { color: 'agi' }), A(5, { d: 1 }), M(3, { d: 1 }), S(3, { t: 1 })),
  mon('Necromancer', 2, { mag: 1, hp: 1 }, sk('Raise Dead', 'summon', 1, { color: 'mag' }), M(4, { a: 1, d: 1 }), M(8, { w: 1, d: 1 }), S(4, { d: 1 })),
  mon('Bridge Troll', 2, { hp: 2 }, sk('Regenerate', 'heal', 1, { color: 'str', min: 4 }), S(5, { d: 2 }), S(9, { w: 1, d: 1 }), A(4, { t: 1 })),
  mon('Living Shadow', 1, { agi: 1 }, sk('Umbral Shift', 'transmute', 0, { color: 'agi' }), A(5, { d: 1 }), M(4, { d: 1 }), A(3, { t: 1 })),
  mon('Ogre', 2, { str: 1 }, sk('Smash', 'boost', 2, { color: 'str' }), S(5, { d: 1 }), S(5, { d: 1 }), A(3, { t: 1 }), M(3, { t: 1 })),
  mon('Fire Beetle', 1, { mag: 1 }, sk('Ember Dash', 'haste', 1, { min: 4 }), M(4, { d: 1 }), S(4, { t: 1 }), A(4, { d: 1 })),
  mon('Wraith Knight', 2, { str: 1, mag: 1 }, sk('Spectral Aegis', 'ward', 2, { color: 'mag', min: 4 }), S(5, { a: 1, d: 1 }), M(5, { d: 1 }), A(4, { t: 1 })),
  mon('Fungal Creeper', 1, { hp: 1 }, sk('Spores', 'reroll', 0, { color: 'str' }), S(3, { d: 1 }), M(6, { w: 1, d: 1 }), A(6, { w: 1, t: 1 })),
];

const PERILS = [
  per('Collapsing Floor', 1, { agi: 1 }, sk('Footwork', 'haste', 1, { color: 'agi' }), ['Leap clear', 0, A(5, { d: 2 })], ['Brace and hold', 1, S(9, { w: 1, d: 1 })]),
  per('Poison Gas', 1, { hp: 1 }, sk('Antidote', 'heal', 1, { color: 'mag' }), ['Hold your breath', 0, S(5, { d: 2 })], ['Dispel it', 1, M(8, { w: 1, d: 1 })]),
  per('Spike Trap', 1, { agi: 1 }, sk('Trap Sense', 'ward', 1, { color: 'agi' }), ['Dodge through', 0, A(10, { w: 1, d: 2 })], ['Disarm it', 1, M(4, { d: 1 })]),
  per('Locked Vault', 2, { str: 1 }, sk('Crowbar', 'boost', 2, { color: 'str' }), ['Smash it open', 0, S(10, { w: 1, t: 2 })], ['Pick the lock', 0, A(5, { t: 2 })]),
  per('Rune Door', 1, { mag: 1 }, sk('Glyph Reading', 'transmute', 0, { color: 'mag', min: 3 }), ['Decipher', 0, M(5, { d: 1, t: 1 })], ['Force it', 1, S(11, { w: 1, d: 1 })]),
  per('Rushing River', 1, { str: 1 }, sk('Strong Swimmer', 'boost', 2, { color: 'str' }), ['Swim across', 0, S(9, { w: 1, d: 1, t: 1 })], ['Swing over', 0, A(5, { d: 2 })]),
  per('Cursed Altar', 2, { mag: 1 }, sk('Blessing', 'summon', 1, { min: 5 }), ['Purify it', 0, M(10, { w: 1, d: 2 })], ['Walk past', 1, A(4, { d: 1 })]),
  per('Swinging Blades', 1, { agi: 1 }, sk('Timing', 'reroll', 0, { color: 'agi' }), ['Time your run', 0, A(6, { d: 2 })], ['Block them', 1, S(8, { w: 1, d: 1 })]),
  per('Snake Pit', 1, { str: 1 }, sk('Grip', 'ward', 1, { color: 'str' }), ['Climb out', 0, S(5, { d: 2 })], ['Charm them', 0, M(5, { d: 1, t: 1 })]),
  per('Magical Darkness', 1, { mag: 1 }, sk('Light', 'haste', 1, { color: 'mag' }), ['Cast light', 0, M(4, { t: 2 })], ['Feel your way', 1, A(9, { w: 1, t: 1 })]),
  per('Rockslide', 1, { hp: 1 }, sk('Brace', 'ward', 1), ['Outrun it', 0, A(11, { w: 1, d: 2 })], ['Take shelter', 1, S(5, { d: 1 })]),
  per('Mirror Maze', 1, { agi: 1 }, sk('Reflection', 'boost', 2), ['See through it', 0, M(9, { w: 1, t: 2 })], ['Smash mirrors', 0, S(5, { d: 1, t: 1 })]),
];

// ---------- dungeons ----------
const MODS = {
  none: { text: 'No special rule.' },
  extraTime: { extraTime: 1, text: 'Twisting halls: entering a room costs ⏳1 extra.' },
  extraDamage: { extraDamage: 1, text: 'Vicious foes: if any box is left uncovered, take 💥1 extra.' },
  perilCost: { perilCost: 1, text: 'Treacherous: every peril option costs ⏳1 extra.' },
  noCombine: { noCombine: 1, text: 'Anti-magic: you cannot combine dice into Empowered dice.' },
};
const DUNGEONS = {
  warren: { name: 'Goblin Warren', stars: 1, floors: ['none', 'extraTime', 'extraDamage'],
    boss: { name: 'Goblin King', hp: 8, boxes: [S(4, { a: 1, d: 1 }), S(5, { d: 1, k: 1 }), A(5, { d: 1, k: 1 }), M(9, { w: 1, d: 1, k: 1 }), S(12, { w: 1, d: 2, k: 2 })] } },
  crypt: { name: 'Sunken Crypt', stars: 2, floors: ['extraTime', 'extraDamage', 'noCombine'],
    boss: { name: 'Bone Tyrant', hp: 10, boxes: [M(5, { a: 1, d: 1 }), S(5, { d: 1, k: 1 }), M(6, { d: 2, k: 1 }), A(10, { w: 1, d: 1, k: 1 }), M(12, { w: 1, d: 2, k: 2 })] } },
  forge: { name: 'Ember Forge', stars: 3, floors: ['extraDamage', 'perilCost', 'extraTime'],
    boss: { name: 'Magma Wyrm', hp: 12, boxes: [S(5, { a: 1, d: 1 }), A(5, { a: 1, d: 1 }), S(6, { d: 2, k: 1 }), M(6, { d: 1, k: 1 }), A(12, { w: 1, d: 2, k: 2 }), M(14, { w: 1, d: 2, k: 2 })] } },
};

// ---------- state ----------
function newState() {
  return { phase: 'lobby', seats: [null, null, null, null], dungeonId: 'warren', log: ['Welcome! Pick a hero and a seat.'], seq: 1 };
}
function log(s, msg) { s.log.push(msg); if (s.log.length > 80) s.log.splice(0, s.log.length - 80); }
const uid = (s) => 'x' + (s.seq++);
const mod = (s) => (s.floor >= 1 && s.floor <= 3 ? MODS[DUNGEONS[s.dungeonId].floors[s.floor - 1]] : MODS.none);
const itemCap = (s) => s.party.level + 1;
const skillCap = (s) => s.party.level;

function heroStats(h) {
  const st = { ...h.base };
  for (const it of h.items) for (const k of ['str', 'agi', 'mag', 'hp']) st[k] += it.bonus[k] || 0;
  return st;
}
function heroBySeat(s, seat) { const h = (s.heroes || []).find((x) => x.seat === Number(seat)); if (!h) throw err('No such hero'); return h; }

function scaleBox(b, floor, players = 1) {
  const add = Math.max(0, Math.min(3, floor) - 1);
  const nb = { ...b };
  if (b.wide) nb.value = b.value + 3 * add + (players >= 2 ? 3 : 0) + 7 * Math.max(0, players - 2); // more heroes, more dice: wide boxes grow
  else if (add) nb.value = Math.min(6, b.value + add);
  return nb;
}
const np = (s) => (s.heroes ? s.heroes.length : 1);

// ---------- descriptions ----------
function skillDesc(k) {
  const c = k.cost || {};
  const what = `${c.min ? c.min + '+ ' : ''}${c.color ? CNAME[c.color] + ' ' : ''}die`;
  const cost = `Discard ${/^[AEIOU8]/.test(what) ? 'an' : 'a'} ${what}`;
  const eff = {
    boost: `+${k.amt} to another die`,
    reroll: 'reroll all your other unplaced dice',
    ward: `prevent 💥${k.amt} this fight`,
    haste: `prevent ⏳${k.amt} this fight`,
    transmute: 'turn another die Empowered (any colour)',
    heal: `heal ${k.amt} damage on the most-hurt hero`,
    summon: `roll ${k.amt} new Empowered ${k.amt > 1 ? 'dice' : 'die'}`,
  }[k.kind];
  return `${cost}: ${eff}.`;
}
function itemDesc(b) {
  const parts = [];
  for (const c of COLORS) if (b[c]) parts.push(`+${b[c]} ${CNAME[c]} ${b[c] > 1 ? 'dice' : 'die'}`);
  if (b.hp) parts.push(`+${b.hp} Health`);
  return parts.join(', ');
}

// ---------- core mechanics ----------
function damageParty(s, n, why) {
  if (n <= 0) return;
  const hit = {};
  for (let i = 0; i < n; i++) {
    const alive = s.heroes.slice().sort((a, b) => (heroStats(b).hp - b.damage) - (heroStats(a).hp - a.damage) || a.seat - b.seat);
    alive[0].damage++;
    hit[alive[0].name] = (hit[alive[0].name] || 0) + 1;
  }
  log(s, `💥 ${why}: ` + Object.entries(hit).map(([k, v]) => `${k} takes ${v}`).join(', ') + '.');
  checkDeath(s);
}
function checkDeath(s) {
  for (const h of s.heroes) {
    const hp = heroStats(h).hp;
    while (h.damage >= hp) {
      if (s.party.potions > 0) {
        s.party.potions--; h.damage = Math.max(0, h.damage - POTION_HEAL);
        log(s, `🧪 ${h.name} was about to fall and gulps an emergency potion!`);
      } else {
        s.phase = 'lost'; s.combat = null;
        log(s, `☠️ ${h.name} has fallen. The dungeon wins this time.`);
        return true;
      }
    }
  }
  return false;
}
function spendTime(s, n, why) {
  if (n <= 0 || s.phase === 'lost') return;
  let disc = 0;
  for (let i = 0; i < n; i++) {
    if (s.deck.length) { s.discard.push(s.deck.pop()); disc++; }
    else {
      s.stairsTokens++;
      if (s.stairsTokens >= 3) { s.stairsTokens -= 3; damageParty(s, 1, 'Lingering by the stairs'); if (s.phase === 'lost') return; }
    }
  }
  log(s, `⏳ ${why}: ${n} time${disc < n ? ` (${n - disc} on the stairs)` : ''}.`);
  revealStairs(s);
}
function revealStairs(s) {
  if (!s.deck.length && !s.stairs) { s.stairs = true; log(s, '🪜 The deck is empty — the stairs are revealed! Time spent now hurts.'); }
}
function rollDice(s, only) {
  const dice = [];
  for (const h of s.heroes) {
    const st = heroStats(h);
    for (const c of COLORS) {
      if (only && c !== only) continue;
      for (let i = 0; i < st[c]; i++) dice.push({ id: uid(s), color: c, value: d6(), hero: h.seat, box: null });
    }
  }
  for (let i = 0; i < s.party.level - 1; i++) dice.push({ id: uid(s), color: 'emp', value: d6(), hero: null, box: null });
  return dice;
}
function setupCombat(s, boxes, only, boss, round) {
  s.combat = { boxes: boxes.map((b) => ({ ...b, dice: [], covered: false })), dice: rollDice(s, only), only: only || null,
    used: {}, ward: 0, haste: 0, boss: !!boss, round: round || 1 };
  s.phase = 'combat';
}
function startEncounter(s, idx) {
  const door = s.doors[idx];
  s.doors.splice(idx, 1);
  s.current = door.card;
  if (door.card.type === 'monster') {
    setupCombat(s, door.card.boxes.map((b) => scaleBox(b, s.floor, np(s))));
    log(s, `⚔️ The party fights the ${door.card.name}!`);
  } else {
    s.phase = 'perilChoice';
    log(s, `⚠️ Peril: ${door.card.name}. Choose how to deal with it.`);
  }
}
function dieOf(c, id) { const d = c.dice.find((x) => x.id === id); if (!d) throw err('That die is gone'); return d; }
function boxSum(c, b) { return b.dice.reduce((t, id) => t + dieOf(c, id).value, 0); }

function placeDie(s, dieId, boxIdx) {
  const c = s.combat; const d = dieOf(c, dieId);
  if (d.box !== null) throw err('That die is already placed');
  const b = c.boxes[boxIdx]; if (!b) throw err('No such box');
  if (b.covered) throw err('That box is already covered');
  if (!b.armor && c.boxes.some((x) => x.armor && !x.covered)) throw err('Cover the 🛡 armor boxes first');
  if (d.color !== 'emp' && d.color !== b.color) throw err(`Needs a ${CNAME[b.color]} (or Empowered) die`);
  if (!b.wide) {
    if (d.value < b.value) throw err(`Needs a ${b.value} or higher`);
    b.dice = [d.id]; b.covered = true;
  } else {
    b.dice.push(d.id); b.covered = boxSum(c, b) >= b.value;
  }
  d.box = boxIdx;
}
function clearBox(s, idx) {
  const c = s.combat; const b = c.boxes[idx]; if (!b) throw err('No such box');
  const list = b.armor ? [b, ...c.boxes.filter((x) => !x.armor)] : [b];
  for (const x of list) { for (const id of x.dice) dieOf(c, id).box = null; x.dice = []; x.covered = false; }
}
function useSkill(s, seat, skillId, costId, targetId) {
  const c = s.combat; const h = heroBySeat(s, seat);
  const k = skillId === 'start' ? h.start : h.skills.find((x) => x.id === skillId);
  if (!k) throw err('No such skill');
  const key = `${h.seat}:${k.id}`;
  if (c.used[key]) throw err(`${k.name} was already used this ${c.boss ? 'round' : 'fight'}`);
  if (!costId) throw err(`Select a die to pay for ${k.name} first`);
  const cd = dieOf(c, costId);
  if (cd.box !== null) throw err('The cost die must be unplaced');
  const need = k.cost || {};
  if (need.color && cd.color !== need.color && cd.color !== 'emp') throw err(`${k.name} needs a ${CNAME[need.color]} die`);
  if (need.min && cd.value < need.min) throw err(`${k.name} needs a ${need.min}+ die`);
  let td = null;
  if (k.kind === 'boost' || k.kind === 'transmute') {
    if (!targetId) throw err(`Select a second die for ${k.name} to affect`);
    td = dieOf(c, targetId);
    if (td.id === cd.id) throw err('Pick two different dice');
    if (td.box !== null) throw err('The target die must be unplaced');
  }
  c.dice = c.dice.filter((x) => x.id !== cd.id);
  switch (k.kind) {
    case 'boost': td.value = Math.min(6, td.value + k.amt); break;
    case 'reroll': for (const d of c.dice) if (d.box === null) d.value = d6(); break;
    case 'ward': c.ward += k.amt; break;
    case 'haste': c.haste += k.amt; break;
    case 'transmute': td.color = 'emp'; break;
    case 'heal': {
      const t = s.heroes.slice().sort((a, b) => b.damage - a.damage)[0];
      t.damage = Math.max(0, t.damage - k.amt); break;
    }
    case 'summon': for (let i = 0; i < k.amt; i++) c.dice.push({ id: uid(s), color: 'emp', value: d6(), hero: null, box: null }); break;
  }
  c.used[key] = true;
  log(s, `✨ ${h.name} uses ${k.name}.`);
}
function resolveCombat(s) {
  const c = s.combat; let dmg = 0, time = 0, skulls = 0;
  for (const b of c.boxes) { if (b.covered) skulls += b.skull; else { dmg += b.dmg; time += b.time; } }
  if (!c.boss && mod(s).extraDamage && c.boxes.some((b) => !b.covered)) dmg += 1;
  dmg = Math.max(0, dmg - c.ward); time = Math.max(0, time - c.haste);
  if (c.boss) {
    s.boss.damage += skulls;
    log(s, `💀 Round ${c.round}: the party deals ${skulls} damage to the ${s.boss.name} (${Math.max(0, s.boss.hp - s.boss.damage)} left).`);
    if (s.boss.damage >= s.boss.hp) { s.phase = 'won'; s.combat = null; log(s, `🏆 The ${s.boss.name} is defeated! The dungeon is conquered!`); return; }
    damageParty(s, dmg, `The ${s.boss.name} strikes`);
    if (s.phase === 'lost') return;
    setupCombat(s, bossBoxes(s), null, true, c.round + 1);
    return;
  }
  const name = s.current.name;
  damageParty(s, dmg, name);
  if (s.phase === 'lost') return;
  spendTime(s, time, name);
  if (s.phase === 'lost') return;
  if (!dmg && !time) log(s, `✅ ${name} overcome cleanly!`);
  s.combat = null; s.phase = 'reward';
}
function checkLevel(s) {
  const p = s.party;
  while (p.level < 4 && p.xp >= XP_NEED[p.level]) {
    p.xp -= XP_NEED[p.level]; p.level++; p.potions++;
    log(s, `⭐ Level up! Party is level ${p.level}: +1 potion, +1 item & skill slot, ${p.level - 1} bonus Empowered dice per fight.`);
  }
  while (p.level >= 4 && p.xp >= 5) { p.xp -= 5; p.potions++; log(s, '🧪 5 XP traded for a potion.'); }
}
function claim(s, a) {
  const card = s.current;
  if (a.as === 'xp') { s.party.xp += card.xp; log(s, `📈 ${card.name} taken as ${card.xp} XP.`); }
  else if (a.as === 'potion') { s.party.potions++; log(s, `🧪 ${card.name} taken as a potion.`); }
  else if (a.as === 'item' || a.as === 'skill') {
    const h = heroBySeat(s, a.seat);
    const list = a.as === 'item' ? h.items : h.skills;
    const cap = a.as === 'item' ? itemCap(s) : skillCap(s);
    if (a.as === 'skill') {
      const names = [h.start.name, ...h.skills.filter((_, i) => i !== a.replace).map((x) => x.name)];
      if (names.includes(card.skill.name)) throw err(`${h.name} already knows ${card.skill.name}`);
    }
    if (list.length >= cap) {
      if (a.replace == null || !list[a.replace]) throw err(`${h.name} has no free ${a.as} slot — pick one to replace`);
      const old = list.splice(a.replace, 1)[0];
      s.party.xp += old.xp;
      log(s, `♻️ ${h.name}'s ${old.name} becomes ${old.xp} XP.`);
    }
    if (a.as === 'item') h.items.push({ id: uid(s), name: card.name, bonus: card.item, xp: card.xp });
    else h.skills.push({ id: uid(s), ...card.skill, xp: card.xp });
    log(s, `🎁 ${h.name} takes ${card.name} as ${a.as === 'item' ? 'an item' : 'a skill'}.`);
    checkDeath(s);
  } else throw err('Choose a reward');
  s.current = null;
  if (s.phase !== 'lost') { s.phase = 'turn'; s.turn++; }
  checkLevel(s);
}
function descend(s) {
  s.discard.push(...s.doors.map((d) => d.card));
  s.doors = []; s.deck = shuffle(s.discard); s.discard = []; s.stairs = false; s.stairsTokens = 0; s.floor++;
  if (s.floor > 3) {
    const B = DUNGEONS[s.dungeonId].boss;
    s.boss = { name: B.name, hp: B.hp + 4 * (np(s) - 1) + 3 * Math.max(0, np(s) - 2), damage: 0 };
    log(s, `👑 The party reaches the depths and faces the ${B.name}!`);
    setupCombat(s, bossBoxes(s), null, true, 1);
  } else {
    log(s, `🪜 The party descends to floor ${s.floor}. ${mod(s).text}`);
    revealStairs(s);
  }
}

const bossBoxes = (s) => DUNGEONS[s.dungeonId].boss.boxes.map((b) => scaleBox(b, 1, np(s)));

function startGame(s) {
  const seated = s.seats.map((x, i) => x && { ...x, seat: i }).filter(Boolean);
  if (!seated.length) throw err('Nobody is seated yet');
  const mode = seated.length === 1 ? 'solo' : 'duo';
  s.heroes = seated.map((x) => {
    const H = HEROES[x.hero];
    return { seat: x.seat, name: x.name || H.name, heroId: x.hero, cls: H.name, base: { ...H[mode] }, damage: 0, items: [], skills: [], start: { id: 'start', ...H.start } };
  });
  s.party = { level: 1, xp: 0, potions: 1 };
  s.deck = shuffle([...MONSTERS, ...PERILS].map((c) => ({ ...clone(c), id: uid(s) })));
  Object.assign(s, { discard: [], doors: [], floor: 1, stairs: false, stairsTokens: 0, current: null, combat: null, boss: null, phase: 'turn', turn: 1, log: [] });
  log(s, `🏰 ${s.heroes.map((h) => `${h.name} the ${h.cls}`).join(' & ')} enter the ${DUNGEONS[s.dungeonId].name}. ${mod(s).text}`);
}

// ---------- action dispatcher ----------
function apply(s, token, a) {
  const mySeat = s.seats.findIndex((x) => x && x.token === token);
  const t = a.t;

  if (t === 'claimSeat') { // rejoin from another phone/browser — no passwords, trust the table
    const seat = Number(a.seat); if (!(seat >= 0 && seat < 4) || !s.seats[seat]) throw err('That seat is empty');
    s.seats.forEach((x) => { if (x && x.token === token) x.token = null; });
    s.seats[seat].token = token; return;
  }
  if (s.phase === 'lobby') {
    if (t === 'sit') {
      const seat = Number(a.seat);
      if (!(seat >= 0 && seat < 4)) throw err('Bad seat');
      if (s.seats[seat] && s.seats[seat].token !== token) throw err('Seat taken');
      if (!own(HEROES, a.hero)) throw err('Pick a hero');
      if (s.seats.some((x, i) => x && i !== seat && x.token !== token && x.hero === a.hero)) throw err('Someone else is playing that hero');
      s.seats = s.seats.map((x) => (x && x.token === token ? null : x));
      s.seats[seat] = { token, name: String(a.name || '').trim().slice(0, 16) || HEROES[a.hero].name, hero: a.hero };
      return;
    }
    if (t === 'leave') { s.seats = s.seats.map((x) => (x && x.token === token ? null : x)); return; }
    if (t === 'kick') { const k = Number(a.seat); if (!(k >= 0 && k < 4)) throw err('Bad seat'); s.seats[k] = null; return; }
    if (t === 'dungeon') { if (!own(DUNGEONS, a.id)) throw err('No such dungeon'); s.dungeonId = a.id; return; }
    if (mySeat < 0) throw err('Take a seat first');
    if (t === 'start') { startGame(s); return; }
    throw err('Not now');
  }
  if (mySeat < 0) throw err('You are watching — take a seat to play');
  if (t === 'lobby') { s.phase = 'lobby'; s.combat = null; s.current = null; log(s, 'Back to the lobby.'); return; }
  if (t === 'potion') {
    if (!['turn', 'reveal', 'perilChoice', 'combat', 'reward'].includes(s.phase)) throw err('Not now');
    const h = heroBySeat(s, a.seat);
    if (s.party.potions < 1) throw err('No potions left');
    if (!h.damage) throw err(`${h.name} is not hurt`);
    s.party.potions--; h.damage = Math.max(0, h.damage - POTION_HEAL); log(s, `🧪 ${h.name} drinks a potion.`); return;
  }
  switch (s.phase) {
    case 'turn':
      if (t === 'explore') {
        if (s.stairs) throw err('The stairs are revealed — no more exploring on this floor');
        if (s.doors.length >= 4) throw err('There are already 4 doors');
        spendTime(s, 2, 'Start of turn'); if (s.phase === 'lost') return;
        let n = 0; while (s.doors.length < 4 && s.deck.length) { s.doors.push({ card: s.deck.pop(), open: false }); n++; }
        log(s, `🔦 Exploring reveals ${n} new door${n === 1 ? '' : 's'}.`); revealStairs(s); s.turn++; return;
      }
      if (t === 'enter') {
        const i = Number(a.door); const door = s.doors[i]; if (!door) throw err('No such door');
        spendTime(s, 2 + (mod(s).extraTime || 0), 'Start of turn'); if (s.phase === 'lost') return;
        if (!door.open) { door.open = true; s.phase = 'reveal'; s.enc = { door: i }; s.current = door.card; log(s, `🚪 The door opens: ${door.card.name}!`); }
        else startEncounter(s, i);
        return;
      }
      if (t === 'descend') { if (!s.stairs) throw err('The stairs are not revealed yet'); descend(s); return; }
      break;
    case 'reveal':
      if (t === 'flee') { s.phase = 'turn'; s.current = null; s.turn++; log(s, '🏃 The party backs away; the door stays open.'); return; }
      if (t === 'fight') { startEncounter(s, s.enc.door); return; }
      break;
    case 'perilChoice': {
      if (t !== 'choose') break;
      const o = s.current.options[Number(a.opt)]; if (!o) throw err('Pick an option');
      spendTime(s, o.cost + (mod(s).perilCost || 0), o.label); if (s.phase === 'lost') return;
      const b = scaleBox(o.box, s.floor, np(s));
      setupCombat(s, [b], b.color);
      log(s, `➡️ ${o.label}: rolling ${CNAME[b.color]} and Empowered dice.`);
      return;
    }
    case 'combat': {
      if (t === 'place') { const ids = Array.isArray(a.dice) ? a.dice : [a.die]; for (const id of ids) placeDie(s, id, Number(a.box)); return; }
      if (t === 'clear') { clearBox(s, Number(a.box)); return; }
      if (t === 'resetDice') { for (let i = 0; i < s.combat.boxes.length; i++) if (s.combat.boxes[i].dice.length) clearBox(s, i); return; }
      if (t === 'combine') {
        if (mod(s).noCombine) throw err('Anti-magic: no combining on this floor');
        const c = s.combat; const x = dieOf(c, a.a), y = dieOf(c, a.b);
        if (x.id === y.id) throw err('Pick two different dice');
        if (x.box !== null || y.box !== null) throw err('Both dice must be unplaced');
        c.dice = c.dice.filter((d) => d.id !== x.id && d.id !== y.id);
        c.dice.push({ id: uid(s), color: 'emp', value: Math.min(x.value, y.value), hero: null, box: null });
        return;
      }
      if (t === 'skill') { useSkill(s, a.seat, a.skill, a.cost, a.target); return; }
      if (t === 'resolve') { resolveCombat(s); return; }
      break;
    }
    case 'reward': if (t === 'claim') { claim(s, a); return; } break;
    case 'won': case 'lost':
      if (t === 'again') { s.phase = 'lobby'; s.log = ['New adventure — pick heroes and a dungeon.']; return; }
      break;
  }
  throw err('Not now');
}

// ---------- client view (hides face-down cards and tokens) ----------
function cardView(card, floor, n) {
  if (!card) return null;
  const v = { id: card.id, type: card.type, name: card.name, xp: card.xp, item: itemDesc(card.item), skill: { name: card.skill.name, desc: skillDesc(card.skill) } };
  if (card.type === 'monster') v.boxes = card.boxes.map((b) => scaleBox(b, floor, n));
  else v.options = card.options.map((o) => ({ label: o.label, cost: o.cost, box: scaleBox(o.box, floor, n) }));
  return v;
}
function view(s, token, online) {
  const D = DUNGEONS[s.dungeonId];
  const v = {
    phase: s.phase, you: s.seats.findIndex((x) => x && x.token === token), log: s.log.slice(-25),
    seats: s.seats.map((x) => x && { name: x.name, hero: x.hero, online: !!(x.token && online.has(x.token)) }),
    heroCatalog: Object.fromEntries(Object.entries(HEROES).map(([k, h]) => [k, { name: h.name, solo: h.solo, duo: h.duo, start: { name: h.start.name, desc: skillDesc(h.start) } }])),
    dungeons: Object.fromEntries(Object.entries(DUNGEONS).map(([k, d]) => [k, { name: d.name, stars: d.stars, boss: d.boss.name, floors: d.floors.map((f) => MODS[f].text) }])),
    dungeonId: s.dungeonId,
  };
  if (s.phase === 'lobby' || !s.heroes) return v;
  const floor = s.floor;
  Object.assign(v, {
    floor, turn: s.turn, deck: s.deck.length, discard: s.discard.length, stairs: s.stairs, stairsTokens: s.stairsTokens,
    party: { ...s.party, need: XP_NEED[s.party.level] || 5, itemCap: itemCap(s), skillCap: skillCap(s) },
    modText: floor <= 3 ? mod(s).text : 'Boss fight!', noCombine: !!mod(s).noCombine,
    heroes: s.heroes.map((h) => {
      const st = heroStats(h);
      return { seat: h.seat, name: h.name, cls: h.cls, heroId: h.heroId, stats: st, damage: h.damage,
        items: h.items.map((i) => ({ name: i.name, desc: itemDesc(i.bonus) })),
        skills: [{ id: 'start', name: h.start.name, desc: skillDesc(h.start), start: true },
          ...h.skills.map((k) => ({ id: k.id, name: k.name, desc: skillDesc(k) }))] };
    }),
    doors: s.doors.map((d) => (d.open ? { open: true, card: cardView(d.card, floor, np(s)) } : { open: false })),
    current: cardView(s.current, floor, np(s)),
    boss: s.boss, combat: s.combat,
    canFlee: s.phase === 'reveal',
  });
  return v;
}

module.exports = { newState, apply, view, HEROES, DUNGEONS, MONSTERS, PERILS };
