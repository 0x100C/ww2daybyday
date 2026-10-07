// Scrub/jump/replay determinism: the state at time t must not depend on how
// the player got there. Run: node build/tests/determinism.mjs
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { loadTerritory } from '../../js/territory.js';

globalThis.fetch = async (url) => new Response(await readFile(new URL('../../' + url, import.meta.url)));
const T = await loadTerritory('data/territory.bin');
const h = () => createHash('sha1').update(T.control).update(T.country).digest('hex');

let seed = 12345;
const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 2 ** 32);
const times = Array.from({ length: 40 }, () => +(rnd() * T.tEnd).toFixed(3)).sort((a, b) => a - b);

// 1. forward playback in small steps, recording the hash at each sample time
const forward = new Map();
let k = 0;
for (let t = 0; k < times.length; t += 0.37) {
  while (k < times.length && times[k] <= t) { T.stateAt(times[k]); forward.set(times[k], h()); k++; }
  T.stateAt(t);
}
// 2. random-order jumps (backward jumps reset and replay)
let fail = 0;
const shuffled = [...times].sort(() => rnd() - 0.5);
for (const t of shuffled) { T.stateAt(t); if (h() !== forward.get(t)) { fail++; console.log('MISMATCH jump', t); } }
// 3. fresh load
const T2 = await loadTerritory('data/territory.bin');
for (const t of times.slice(0, 10)) {
  T2.stateAt(t);
  const hh = createHash('sha1').update(T2.control).update(T2.country).digest('hex');
  if (hh !== forward.get(t)) { fail++; console.log('MISMATCH reload', t); }
}
console.log(`${times.length} sample times, tEnd ${T.tEnd.toFixed(2)} days: ${fail ? fail + ' mismatches' : 'all identical'}`);
process.exit(fail ? 1 : 0);
