// Extract state positions from a Hearts of Iron IV installation.
//
//   node build/hoi4/extract_states.mjs "C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
//
// Reads (read-only):
//   map/provinces.bmp            province colours (24-bit BMP)
//   map/definition.csv           province id ; r ; g ; b ; ...
//   history/states/*.txt         state id and its province list
//   history/countries/*.txt      capital state of each country
// Writes data/hoi4_states.json (about 2 MB): for every state its centroid and bounding
// box in map pixels, every country's capital state, and a coarse grid of state ids
// (one per 4x4 pixels) giving the state shapes. The app converts
// pixels to real-world coordinates by fitting the capitals to their known locations.
//
// Nothing is copied from the game except numbers (ids, pixel positions).
import { readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = process.argv[2];
if (!root) { console.error('usage: node extract_states.mjs "<HOI4 install folder>" [out.json]'); process.exit(1); }
const out = process.argv[3] || join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'hoi4_states.json');
const p = (...a) => join(root, ...a);
for (const f of ['map/provinces.bmp', 'map/definition.csv', 'history/states', 'history/countries']) {
  if (!existsSync(p(f))) { console.error('missing: ' + p(f) + '\n(is that the game install folder, the one that contains "map" and "history"?)'); process.exit(1); }
}

// ---- province id by colour
const colour = new Map();
for (const line of readFileSync(p('map/definition.csv'), 'latin1').split(/\r?\n/)) {
  const c = line.split(';');
  if (c.length < 4) continue;
  const id = +c[0], r = +c[1], g = +c[2], b = +c[3];
  if (Number.isInteger(id) && id > 0) colour.set((r << 16) | (g << 8) | b, id);
}

// ---- state of each province
const stripComments = (t) => t.replace(/#[^\n]*/g, '');
const provState = new Map();
let nStates = 0;
for (const f of readdirSync(p('history/states'))) {
  if (!f.endsWith('.txt')) continue;
  const t = stripComments(readFileSync(p('history/states', f), 'utf8'));
  const id = /\bid\s*=\s*(\d+)/.exec(t);
  const prov = /\bprovinces\s*=\s*\{([^}]*)\}/.exec(t);
  if (!id || !prov) continue;
  nStates++;
  for (const n of prov[1].trim().split(/\s+/)) if (n) provState.set(+n, +id[1]);
}

// ---- capitals
const capitals = {};
for (const f of readdirSync(p('history/countries'))) {
  const m = /^([A-Z0-9]{3})\b/.exec(f);
  if (!m) continue;
  const t = stripComments(readFileSync(p('history/countries', f), 'utf8'));
  const c = /\bcapital\s*=\s*(\d+)/.exec(t);
  if (c) capitals[m[1]] = +c[1];
}

// ---- province bitmap
const bmp = readFileSync(p('map/provinces.bmp'));
if (bmp.toString('latin1', 0, 2) !== 'BM') { console.error('provinces.bmp is not a BMP file'); process.exit(1); }
const dataOff = bmp.readUInt32LE(10), W = bmp.readInt32LE(18), Hraw = bmp.readInt32LE(22), bpp = bmp.readUInt16LE(28);
const H = Math.abs(Hraw), topDown = Hraw < 0;
if (bpp !== 24 && bpp !== 32) { console.error(`unsupported BMP depth ${bpp} (expected 24)`); process.exit(1); }
const bytes = bpp / 8, rowSize = Math.ceil((W * bpp) / 32) * 4;
const acc = new Map();                                  // state -> [sumX, sumY, n, minX, minY, maxX, maxY]
// coarse state-shape grid: the state at the centre of every 4x4 block of map pixels (0 = sea/unassigned)
const SC = 4, GW = Math.ceil(W / SC), GH = Math.ceil(H / SC);
const grid = new Uint16Array(GW * GH);
for (let y = 0; y < H; y++) {
  const row = dataOff + (topDown ? y : H - 1 - y) * rowSize;   // y = 0 is the top of the map
  for (let x = 0; x < W; x++) {
    const o = row + x * bytes;
    const prov = colour.get((bmp[o + 2] << 16) | (bmp[o + 1] << 8) | bmp[o]);   // BMP stores B,G,R
    if (prov === undefined) continue;
    const st = provState.get(prov);
    if (st === undefined) continue;
    if ((x & 3) === 2 && (y & 3) === 2) grid[(y >> 2) * GW + (x >> 2)] = st;
    let a = acc.get(st);
    if (!a) { a = [0, 0, 0, x, y, x, y]; acc.set(st, a); }
    a[0] += x; a[1] += y; a[2]++;
    if (x < a[3]) a[3] = x; if (y < a[4]) a[4] = y; if (x > a[5]) a[5] = x; if (y > a[6]) a[6] = y;
  }
}
const states = {};
for (const [st, a] of acc) states[st] = { x: +(a[0] / a[2]).toFixed(1), y: +(a[1] / a[2]).toFixed(1), n: a[2], box: [a[3], a[4], a[5], a[6]] };
const gridB64 = Buffer.from(grid.buffer, grid.byteOffset, grid.byteLength).toString('base64');
writeFileSync(out, JSON.stringify({ format: 'ww2dbd-hoi4-states/0.2', width: W, height: H, states, capitals,
  grid: { scale: SC, w: GW, h: GH, encoding: 'uint16le-base64', data: gridB64 } }));
console.log(`map ${W}x${H}, ${colour.size} provinces, ${nStates} state files, ${Object.keys(states).length} states placed, ${Object.keys(capitals).length} capitals -> ${out}`);
