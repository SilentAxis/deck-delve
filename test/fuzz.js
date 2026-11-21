// Plays many full games with a simple greedy bot to catch crashes and gauge difficulty.
const E = require('../engine');
const pick = (a) => a[Math.floor(Math.random() * a.length)];

function tryAct(s, tok, a) {
  const backup = JSON.stringify(s);
  try { E.apply(s, tok, a); return true; } catch (e) {
    if (!e.user) { console.error('ENGINE BUG', a, e); process.exit(1); }
    Object.keys(s).forEach((k) => delete s[k]); Object.assign(s, JSON.parse(backup)); return false;
  }
}

function play(players, dungeon) {
  const s = E.newState();
  const heroes = Object.keys(E.HEROES).sort(() => Math.random() - 0.5);
  for (let i = 0; i < players; i++) tryAct(s, 't' + i, { t: 'sit', seat: i, hero: heroes[i], name: 'P' + i });
  tryAct(s, 't0', { t: 'dungeon', id: dungeon });
  tryAct(s, 't0', { t: 'start' });
  const tok = () => 't' + Math.floor(Math.random() * players);
  for (let step = 0; step < 5000; step++) {
    const v = E.view(s, 't0', new Set());
    JSON.stringify(v); // view must serialise
    switch (s.phase) {
      case 'won': case 'lost': return { result: s.phase, floor: s.floor, level: s.party.level };
      case 'turn':
        if (s.stairs && (!s.doors.length || Math.random() < 0.6)) tryAct(s, tok(), { t: 'descend' });
        else if (!s.stairs && s.doors.length < 4 && (Math.random() < 0.4 || !s.doors.length)) tryAct(s, tok(), { t: 'explore' });
        else if (s.doors.length) tryAct(s, tok(), { t: 'enter', door: Math.floor(Math.random() * s.doors.length) });
        if (Math.random() < 0.3) for (const h of s.heroes) if (h.damage >= 2) tryAct(s, tok(), { t: 'potion', seat: h.seat });
        break;
      case 'reveal': tryAct(s, tok(), { t: Math.random() < 0.15 ? 'flee' : 'fight' }); break;
      case 'perilChoice': tryAct(s, tok(), { t: 'choose', opt: Math.floor(Math.random() * 2) }); break;
      case 'combat': {
        const c = s.combat;
        // random skill attempts
        for (const h of s.heroes) for (const k of [{ id: 'start' }, ...h.skills]) {
          if (Math.random() < 0.5) continue;
          const free = c.dice.filter((d) => d.box === null).sort((a, b) => a.value - b.value);
          if (free.length < 2) continue;
          tryAct(s, tok(), { t: 'skill', seat: h.seat, skill: k.id, cost: free[0].id, target: free[free.length - 1].id });
        }
        if (Math.random() < 0.3) {
          const free = s.combat.dice.filter((d) => d.box === null);
          if (free.length >= 2) tryAct(s, tok(), { t: 'combine', a: free[0].id, b: free[1].id });
        }
        const order = s.combat.boxes.map((b, i) => i).sort((a, b) => s.combat.boxes[b].armor - s.combat.boxes[a].armor);
        for (const bi of order) {
          const free = s.combat.dice.filter((d) => d.box === null).sort((a, b) => a.value - b.value);
          for (const d of free) { if (s.combat.boxes[bi].covered) break; tryAct(s, tok(), { t: 'place', die: d.id, box: bi }); }
        }
        if (Math.random() < 0.05) tryAct(s, tok(), { t: 'resetDice' });
        else tryAct(s, tok(), { t: 'resolve' });
        break;
      }
      case 'reward': {
        const h = pick(s.heroes);
        const as = pick(['item', 'item', 'skill', 'xp', 'potion']);
        if (!tryAct(s, tok(), { t: 'claim', as, seat: h.seat, replace: 0 })) tryAct(s, tok(), { t: 'claim', as: 'xp' });
        break;
      }
      default: throw new Error('stuck in ' + s.phase);
    }
  }
  throw new Error('game did not finish');
}

for (const players of (process.env.P||"1,2,4").split(",").map(Number)) for (const dg of (process.env.D ? process.env.D.split(",") : Object.keys(E.DUNGEONS))) {
  const N = Number(process.env.N) || 60; let won = 0; const floors = {};
  for (let i = 0; i < N; i++) { const r = play(players, dg); if (r.result === 'won') won++; floors[r.floor] = (floors[r.floor] || 0) + 1; }
  console.log(`${players}P ${dg.padEnd(7)} win ${(100 * won / N).toFixed(0)}%  reached floor:`, floors);
}
console.log('fuzz OK');
