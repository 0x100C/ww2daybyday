// Territory stream: decoding, deterministic state replay and per-day
// window buffers for the GPU.
//
// State at time t is always computed by replaying events from the base
// rasters (or forward from the last computed time), so scrubbing, jumping
// and replaying give identical results for the same t.

export async function loadTerritory(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`territory stream: HTTP ${res.status}`);
  let buf = new Uint8Array(await res.arrayBuffer());
  if (buf[0] === 0x1f && buf[1] === 0x8b) {
    const ds = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    buf = new Uint8Array(await new Response(ds).arrayBuffer());
  }
  return new Territory(buf.buffer);
}

class Territory {
  constructor(ab) {
    const dv = new DataView(ab);
    const magic = String.fromCharCode(...new Uint8Array(ab, 0, 4));
    if (magic !== 'WW2T') throw new Error('bad territory stream');
    let o = 4;
    const version = dv.getUint32(o, true); o += 4;
    this.W = dv.getUint32(o, true); o += 4;
    this.H = dv.getUint32(o, true); o += 4;
    const nGroups = dv.getUint32(o, true); o += 4;
    this.tEnd = dv.getFloat32(o, true); o += 4;
    const N = this.W * this.H;
    this.N = N;
    this.baseCountry = new Uint8Array(ab, o, N); o += N;
    this.baseControl = new Uint8Array(ab, o, N); o += N;

    // Flatten groups into two event lists (control, country) sorted by arrival.
    const lists = [[], []];
    for (let g = 0; g < nGroups; g++) {
      const kind = dv.getUint8(o); o += 4;
      const t0 = dv.getFloat32(o, true); o += 4;
      const t1 = dv.getFloat32(o, true); o += 4;
      const nRuns = dv.getUint32(o, true); o += 4;
      const nCells = dv.getUint32(o, true); o += 4;
      const rs = new Uint32Array(ab.slice(o, o + 4 * nRuns)); o += 4 * nRuns;
      const rl = new Uint32Array(ab.slice(o, o + 4 * nRuns)); o += 4 * nRuns;
      const owner = new Uint8Array(ab, o, nCells); o += nCells;
      const frac = new Uint8Array(ab, o, nCells); o += nCells;
      o += (4 - (o % 4)) % 4;
      lists[kind].push({ t0, t1, rs, rl, owner, frac, nCells, order: g });
    }
    this.ctl = this._flatten(lists[0]);
    this.cty = this._flatten(lists[1]);
    this.ctlGroups = lists[0].map((g) => this._expand(g)).sort((p, q) => p.t0 - q.t0);
    this.version = version;
    this._resetState();
  }

  _expand(g) {
    const idx = new Uint32Array(g.nCells), arr = new Float32Array(g.nCells);
    let c = 0;
    for (let r = 0; r < g.rs.length; r++) {
      const s = g.rs[r], L = g.rl[r];
      for (let j = 0; j < L; j++, c++) { idx[c] = s + j; arr[c] = g.t0 + (g.frac[c] / 255) * (g.t1 - g.t0); }
    }
    return { t0: g.t0, t1: g.t1, idx, arr, owner: g.owner };
  }

  _flatten(groups) {
    let n = 0;
    for (const g of groups) n += g.nCells;
    const idx = new Uint32Array(n), owner = new Uint8Array(n);
    const arr = new Float64Array(n), start = new Float32Array(n);
    let k = 0;
    for (const g of groups) {
      let c = 0;
      for (let r = 0; r < g.rs.length; r++) {
        const s = g.rs[r], L = g.rl[r];
        for (let j = 0; j < L; j++, c++, k++) {
          idx[k] = s + j;
          owner[k] = g.owner[c];
          // tiny ordinal tie-breaker keeps group order for equal arrivals
          arr[k] = g.t0 + (g.frac[c] / 255) * (g.t1 - g.t0) + g.order * 1e-9;
          start[k] = g.t0;
        }
      }
    }
    // stable LSD radix sort on quarter-minute keys
    const key = new Uint32Array(n);
    for (let i = 0; i < n; i++) key[i] = Math.max(0, Math.round(arr[i] * 5760));
    let ord = new Uint32Array(n), tmp = new Uint32Array(n);
    for (let i = 0; i < n; i++) ord[i] = i;
    for (let shift = 0; shift < 32; shift += 11) {
      const cnt = new Uint32Array(2049);
      for (let i = 0; i < n; i++) cnt[((key[ord[i]] >>> shift) & 2047) + 1]++;
      for (let b = 0; b < 2048; b++) cnt[b + 1] += cnt[b];
      for (let i = 0; i < n; i++) tmp[cnt[(key[ord[i]] >>> shift) & 2047]++] = ord[i];
      [ord, tmp] = [tmp, ord];
    }
    const out = {
      n,
      idx: new Uint32Array(n), owner: new Uint8Array(n),
      arr: new Float32Array(n), start: new Float32Array(n),
    };
    for (let i = 0; i < n; i++) {
      const j = ord[i];
      out.idx[i] = idx[j]; out.owner[i] = owner[j]; out.arr[i] = arr[j]; out.start[i] = start[j];
    }
    return out;
  }

  _resetState() {
    this.control = new Uint8Array(this.baseControl);
    this.country = new Uint8Array(this.baseCountry);
    this.pc = 0; this.py = 0; this.tState = -Infinity;
  }

  // Advance the authoritative state to time t (inclusive).
  stateAt(t) {
    if (t < this.tState) this._resetState();
    const C = this.ctl, Y = this.cty;
    while (this.pc < C.n && C.arr[this.pc] <= t) { this.control[C.idx[this.pc]] = C.owner[this.pc]; this.pc++; }
    while (this.py < Y.n && Y.arr[this.py] <= t) { this.country[Y.idx[this.py]] = Y.owner[this.py]; this.py++; }
    this.tState = t;
  }

  // First event position with arr > t (binary search).
  static upper(arr, t) {
    let lo = 0, hi = arr.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (arr[m] <= t) lo = m + 1; else hi = m; }
    return lo;
  }
}

// Builds and incrementally updates the two RGBA grid buffers for a one-day
// window [w0, w1]:
//   state: R control before, G control after, B country before, A country after
//   time : R arrival (smooth), G pending start, B arrival (exact), A country switch
// Fractions are window-relative 0..255; 255 in B/R means "not within window".
export class WindowBuffers {
  constructor(terr) {
    this.T = terr;
    const N = terr.N;
    this.state = new Uint8Array(N * 4);
    this.time = new Uint8Array(N * 4);
    this.touched = new Uint32Array(0);
    this.w0 = null;
    this.dirty = null;
    this.full = true;
  }

  build(w0, w1) {
    const T = this.T, W = T.W, H = T.H;
    const S = this.state, M = this.time;
    T.stateAt(w0);
    const ctl0 = T.control, cty0 = T.country;
    let x0 = W, y0 = H, x1 = -1, y1 = -1;
    const mark = (i) => {
      const x = i % W, y = (i / W) | 0;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    };
    const touchedList = [];
    const setDefault = (i) => {
      const c = ctl0[i], y = cty0[i], o = i * 4;
      S[o] = c; S[o + 1] = c; S[o + 2] = y; S[o + 3] = y;
      M[o] = 0; M[o + 1] = 255; M[o + 2] = 0; M[o + 3] = 0;
    };
    // Incremental reset is only valid for the next consecutive window; after a
    // jump (scrub, seek, backwards) any cell may have changed, so rebuild all.
    if (this.w0 === null || Math.abs(w0 - this.w0 - 1) > 1e-6) this.full = true;
    if (this.full) {
      for (let i = 0; i < T.N; i++) setDefault(i);
      x0 = 0; y0 = 0; x1 = W - 1; y1 = H - 1;
      this.full = false;
    } else {
      // reset cells touched by the previous window
      for (const i of this.touched) { setDefault(i); mark(i); }
    }
    const span = w1 - w0;
    const q = (t) => Math.max(0, Math.min(255, Math.round((t - w0) / span * 255)));
    // control groups overlapping the window: arrivals, pending band, halo
    const changing = [];
    for (const g of T.ctlGroups) {
      if (g.t0 >= w1) break;
      if (g.t1 <= w0) continue;
      const ps = q(g.t0);
      for (let c = 0; c < g.idx.length; c++) {
        const t = g.arr[c];
        if (t <= w0) continue;
        const i = g.idx[c], o = i * 4;
        if (ps < M[o + 1]) M[o + 1] = ps;
        if (t <= w1) {
          S[o + 1] = g.owner[c];
          const f = q(t);
          M[o] = f; M[o + 2] = f;
          changing.push(i);
        } else {
          M[o + 2] = 255;
        }
        touchedList.push(i); mark(i);
      }
    }
    for (const i of changing) {
      const x = i % W, y = (i / W) | 0, newOwner = S[i * 4 + 1];
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
        const j = yy * W + xx, oj = j * 4;
        if (S[oj] !== S[oj + 1]) continue;
        M[oj] = (S[oj] === newOwner) ? 0 : 255;
        touchedList.push(j); mark(j);
      }
    }
    // country events within (w0, w1]
    const Y = T.cty;
    const ya = Territory.upper(Y.arr, w0), yb = Territory.upper(Y.arr, w1);
    for (let k = ya; k < yb; k++) {
      const i = Y.idx[k], o = i * 4;
      S[o + 3] = Y.owner[k];
      M[o + 3] = q(Y.arr[k]);
      touchedList.push(i); mark(i);
    }
    this.touched = Uint32Array.from(touchedList);
    this.w0 = w0;
    this.dirty = x1 >= 0 ? { x0, y0, x1, y1 } : null;
    return this.dirty;
  }
}
