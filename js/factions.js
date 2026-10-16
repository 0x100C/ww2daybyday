// Faction colours (sampled from the reference video over flat terrain) and
// the rules deciding where a white front line is drawn.

export const COLORS = {
  neutral: [240, 235, 224],
  axis: [113, 113, 99],
  vichy: [170, 171, 150],
  allied: [108, 146, 205],
  allied_c: [138, 169, 226],
  soviet: [186, 124, 101],
  partisan: [214, 98, 86],
  // neutral countries that go to war (civil wars, minor powers) get their own colour so both sides show
  minor1: [196, 170, 108],
  minor2: [118, 166, 150],
  minor3: [178, 138, 176],
  minor4: [214, 150, 98],
};

let EPOCH = Date.UTC(1939, 8, 1);
// Campaign replays have their own start date (meta.epoch)
export const setEpoch = (ms) => { EPOCH = ms; };
export const dayOf = (iso) => (Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) - EPOCH) / 864e5;

export function factionAt(unit, t) {
  let f = null, since = -1e9;
  for (const [d, fac] of unit.factions) {
    const td = dayOf(d);
    if (td <= t) { f = fac; since = td; }
  }
  return { f, since };
}

// Wars between specific units or factions, as [a, b, from, to] (inclusive days).
const UNIT_WARS = [
  ['SOV', 'POL', '1939-09-17', '1939-10-06'],
  ['SOV', 'FIN', '1939-11-30', '1940-03-13'],
  ['SOV', 'FIN', '1941-06-25', '1944-09-19'],
  ['VIC', 'GBR', '1940-07-03', '1940-07-05'],
  ['SYR', 'WAL', '1941-06-08', '1941-07-14'], ['LBN', 'WAL', '1941-06-08', '1941-07-14'],
  ['SYR', 'FFR', '1941-06-08', '1941-07-14'], ['LBN', 'FFR', '1941-06-08', '1941-07-14'],
  ['MAR', 'WAL', '1942-11-08', '1942-11-11'], ['DZA', 'WAL', '1942-11-08', '1942-11-11'],
  ['MAR', 'USA', '1942-11-08', '1942-11-11'], ['DZA', 'USA', '1942-11-08', '1942-11-11'],
  ['IRN', 'GBR', '1941-08-25', '1941-08-31'], ['IRN', 'SOV', '1941-08-25', '1941-08-31'],
  ['IRN', 'WAL', '1941-08-25', '1941-08-31'],
];

export function warMatrix(units, t, wars) {
  const m = new Uint8Array(256 * 256);
  if (wars) {
    // campaign replay: wars come from the log as [tagA, tagB, startDay, endDay|null]
    const id = Object.fromEntries(units.map((u) => [u.code, u.id]));
    for (const [a, b, t0, t1] of wars) {
      if (t >= t0 && (t1 == null || t < t1) && id[a] && id[b]) { m[id[a] * 256 + id[b]] = 255; m[id[b] * 256 + id[a]] = 255; }
    }
    return m;
  }
  const fac = new Array(256).fill(null);
  for (const u of units) fac[u.id] = factionAt(u, t).f;
  const AX = new Set(['axis']);
  const isWest = (f) => f === 'allied' || f === 'allied_c' || f === 'partisan';
  for (let a = 1; a < 256; a++) {
    const fa = fac[a];
    if (!fa) continue;
    for (let b = 1; b < 256; b++) {
      const fb = fac[b];
      if (!fb || a === b) continue;
      let w = false;
      if (AX.has(fa) && isWest(fb)) w = true;
      if (AX.has(fa) && fb === 'soviet' && t >= dayOf('1941-06-22')) w = true;
      if (w) { m[a * 256 + b] = 255; m[b * 256 + a] = 255; }
    }
  }
  const byCode = Object.fromEntries(units.map((u) => [u.code, u.id]));
  for (const [a, b, d0, d1] of UNIT_WARS) {
    if (t >= dayOf(d0) && t < dayOf(d1) + 1 && byCode[a] && byCode[b]) {
      m[byCode[a] * 256 + byCode[b]] = 255;
      m[byCode[b] * 256 + byCode[a]] = 255;
    }
  }
  return m;
}

// Palette for time t with a one-day crossfade after a side change.
export function palette(units, t) {
  const out = new Uint8Array(256 * 4);
  out.set([218, 227, 241, 0], 0);
  for (const u of units) {
    const { f } = factionAt(u, t);
    const prev = factionAt(u, t - 1).f;
    let c = COLORS[f] || COLORS.neutral;
    if (prev && prev !== f) {
      const { since } = factionAt(u, t);
      const k = Math.min(1, Math.max(0, t - since));
      const p = COLORS[prev] || COLORS.neutral;
      c = c.map((v, i) => Math.round(p[i] + (v - p[i]) * k));
    }
    const o = u.id * 4;
    out[o] = c[0]; out[o + 1] = c[1]; out[o + 2] = c[2];
    out[o + 3] = (f === 'neutral' || !f) ? 255 : 0;
  }
  return out;
}
