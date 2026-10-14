import { Renderer } from './renderer.js';
import { loadTerritory, WindowBuffers } from './territory.js';
import { GEO, mercX, millerY } from './geo.js';
import { palette, warMatrix, dayOf, setEpoch } from './factions.js';

const $ = (id) => document.getElementById(id);
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
let EPOCH = Date.UTC(1939, 8, 1);
// ?campaign=hoi4 replays a recorded Hearts of Iron IV campaign (data/hoi4/) instead of the 1939-45 history
const CAMPAIGN = new URLSearchParams(location.search).get('campaign');
const DATA = CAMPAIGN ? `data/${CAMPAIGN}` : 'data';

// Reference camera: Ireland to the Caspian, North Cape region to Libya.
const REF_VIEW = { lon: 17.67, lat: 47.90, span: 76.56 };

const app = {
  t: 0, playing: false, speed: 2.6, lastFrame: 0, win: null, warDay: null,
};

function fmtDate(t) {
  const d = new Date(EPOCH + t * 864e5);
  return {
    day: String(d.getUTCDate()).padStart(2, '0'),
    mon: MONTHS[d.getUTCMonth()],
    year: d.getUTCFullYear(),
    hour: `${String(d.getUTCHours()).padStart(2, '0')}:00`,
    iso: d.toISOString().slice(0, 10),
  };
}

function fitCamera(r, cssW) {
  // reference framing (Miller projection), fitted on ten landmarks of a reference frame
  r.setCamera({ x: mercX(REF_VIEW.lon), y: millerY(REF_VIEW.lat), s: cssW / (REF_VIEW.span / 360) });
  clampCamera(r);
}

function clampCamera(r) {
  const c = r.cam, cw = r.canvas.clientWidth, ch = r.canvas.clientHeight;
  const minS = Math.max(cw / (GEO.MX1 - GEO.MX0), ch / (GEO.NY1 - GEO.NY0));
  const maxS = 256 * 2 ** 8.2;
  c.s = Math.min(maxS, Math.max(minS, c.s));
  const hw = cw / 2 / c.s, hh = ch / 2 / c.s;
  c.x = Math.min(GEO.MX1 - hw, Math.max(GEO.MX0 + hw, c.x));
  c.y = Math.min(GEO.NY1 - hh, Math.max(GEO.NY0 + hh, c.y));
  r.terrainDirty = true;
}

async function main() {
  const canvas = $('map');
  const overlay = $('overlay');
  const r = new Renderer(canvas, 'data/tiles');
  r.resize();
  fitCamera(r, canvas.clientWidth, canvas.clientHeight);
  r.preload(5);

  $('loading').textContent = 'Loading historical data…';
  const [meta, terr] = await Promise.all([
    fetch(`${DATA}/meta.json`).then((x) => x.json()),
    loadTerritory(`${DATA}/territory.bin`),
  ]);
  app.meta = meta;
  if (CAMPAIGN && meta.epoch) { EPOCH = Date.parse(meta.epoch); setEpoch(EPOCH); }
  const campaign = CAMPAIGN ? await fetch(`${DATA}/campaign.json`).then((x) => x.json()) : null;
  app.campaign = campaign;
  // front strengths: dated anchors -> per-day interpolated label tracks
  const parseT = (s) => {
    const [d, h] = s.split(' ');
    return (Date.parse(d + 'T00:00:00Z') - EPOCH) / 864e5 + (h ? +h / 24 : 0);
  };
  const strengths = CAMPAIGN ? { fronts: [] } : await fetch('data/strengths.json').then((x) => (x.ok ? x.json() : { fronts: [] })).catch(() => ({ fronts: [] }));
  const tracks = [];
  for (const f of strengths.fronts) for (const s of f.sides) {
    tracks.push({
      side: s.label_side || s.side,
      a: s.a.map(([d, n, lat, lon, ang]) => ({ t: parseT(d), n, lat, lon, ang })),
      n: s.n ? s.n.map(([d, n]) => ({ t: parseT(d), n })) : null,
      track: f.track ? meta.fronts && meta.fronts[f.track] : null,
      onW: f.track ? (s.label_side || s.side) === f.wside : false,
    });
  }
  app.tracks = tracks;
  app.terr = terr;
  app.tEnd = meta.tEnd;
  r.initGrid(terr.W, terr.H);
  const wb = new WindowBuffers(terr);
  app.wb = wb;
  $('loading').remove();

  const slider = $('scrub');
  slider.max = String(app.tEnd);
  slider.step = String(1 / 24);

  const params = new URLSearchParams(location.search);
  if (params.get('date')) app.t = Math.max(0, dayOf(params.get('date')) + (+params.get('h') || 0) / 24);
  if (params.get('view') === 'poland') r.setCamera({ x: mercX(19.5), y: millerY(52.0), s: 256 * 2 ** 6.2 });
  if (params.get('cam')) {
    const [lon, lat, z] = params.get('cam').split(',').map(Number);
    r.setCamera({ x: mercX(lon), y: millerY(lat), s: 256 * 2 ** z });
  }
  if (params.get('play') === '1') app.playing = true;
  if (params.get('speed')) app.speed = +params.get('speed');

  const ctx = overlay.getContext('2d');

  // ---------------------------------------------------------------- major events
  // Clicking an event flies the camera to it and jumps to its date; for an
  // encirclement it replays the pocket from the start of the pincer movement
  // to its destruction at a slow, readable speed.
  const EV_TYPES = { capital: 'Capital captured', breakthrough: 'Breakthrough', collapse: 'Front collapse', encirclement: 'Encirclement' };
  const evData = campaign ? { events: campaign.events }
    : await fetch('data/events.json').then((x) => (x.ok ? x.json() : { events: [] })).catch(() => ({ events: [] }));
  const events = evData.events.map((e) => ({
    ...e, t: CAMPAIGN ? e.t : parseT(e.date), t0: e.form ? parseT(e.form) : null, t1: e.end ? parseT(e.end) : null,
  })).sort((a, b) => a.t - b.t);
  const evShown = new Set(Object.keys(EV_TYPES));
  const fmtN = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const fmtD = (t) => { const d = fmtDate(t); return `${+d.day} ${d.mon[0]}${d.mon.slice(1).toLowerCase()} ${d.year}`; };

  // keep the speed menu showing the actual speed, adding a temporary entry if needed
  function setSpeedUi(v) {
    const sel = $('speed');
    if (![...sel.options].some((o) => +o.value === v)) {
      sel.querySelectorAll('option[data-tmp]').forEach((o) => o.remove());
      const o = document.createElement('option');
      o.value = String(v); o.textContent = `${v} d/s`; o.dataset.tmp = '1';
      sel.appendChild(o);
    }
    sel.value = String(v);
  }
  app.setSpeedUi = setSpeedUi;

  function flyTo(lon, lat, zoom, ms = 1400) {
    const from = { ...r.cam };
    const to = { x: mercX(lon), y: millerY(lat), s: 256 * 2 ** zoom };
    app.fly = { from, to, start: performance.now(), ms };
  }
  function stepFly(now) {
    const f = app.fly;
    if (!f) return;
    let k = Math.min(1, (now - f.start) / f.ms);
    k = k < 0.5 ? 4 * k * k * k : 1 - (-2 * k + 2) ** 3 / 2;          // ease in-out
    const ls = Math.log(f.from.s) + (Math.log(f.to.s) - Math.log(f.from.s)) * k;
    r.setCamera({ x: f.from.x + (f.to.x - f.from.x) * k, y: f.from.y + (f.to.y - f.from.y) * k, s: Math.exp(ls) });
    clampCamera(r);
    if (k >= 1) app.fly = null;
  }
  app.stepFly = stepFly;

  function showCard(e) {
    const card = $('ev-card');
    const span = e.type === 'encirclement'
      ? `<div><b>${fmtN(e.trapped)}</b> men encircled · pincers ${fmtD(e.t0)}, closed ${fmtD(e.t)}, destroyed ${fmtD(e.t1)}</div>` : '';
    card.innerHTML = `<button class="x" title="Close">✕</button><h3>${e.title}</h3>
      <div class="meta">${EV_TYPES[e.type]} · ${fmtD(e.t)}</div><div>${e.text}</div>${span}
      <div class="actions">${e.type === 'encirclement' ? '<button data-a="replay">▶ Replay pocket</button>' : ''}<button data-a="go">Go to date</button></div>
      <div class="src">Source: ${e.src}</div>`;
    card.hidden = false;
    card.querySelector('.x').onclick = () => { card.hidden = true; app.replay = null; };
    card.querySelectorAll('.actions button').forEach((b) => { b.onclick = () => openEvent(e, b.dataset.a === 'replay'); });
  }

  function openEvent(e, replay = e.type === 'encirclement') {
    flyTo(e.lon, e.lat, e.zoom);
    document.querySelectorAll('#ev-list li').forEach((li) => li.classList.toggle('on', li.dataset.id === e.id));
    showCard(e);
    if (replay && e.t0 != null) {
      // show the pincers forming: from the start of the movement to destruction (long sieges: the first weeks)
      app.t = e.t0;
      const end = Math.min(e.t1, e.t + 12);
      const days = end - e.t0;
      app.replay = { end, prevSpeed: app.replay ? app.replay.prevSpeed : app.speed };
      app.speed = Math.round(Math.max(0.6, Math.min(2.6, days / 14)) * 10) / 10;   // ~10-15 s per pocket
      setSpeedUi(app.speed);
      app.playing = true;
    } else {
      app.t = e.t;
      app.playing = false;
    }
  }

  function renderEvents() {
    const filt = $('ev-filters');
    filt.innerHTML = Object.entries(EV_TYPES).map(([k, v]) =>
      `<label><input type="checkbox" data-k="${k}" ${evShown.has(k) ? 'checked' : ''}><span class="dot ev-${k}"></span>${v}</label>`).join('');
    filt.querySelectorAll('input').forEach((c) => { c.onchange = () => { c.checked ? evShown.add(c.dataset.k) : evShown.delete(c.dataset.k); renderEvents(); }; });
    const list = $('ev-list');
    list.innerHTML = events.filter((e) => evShown.has(e.type)).map((e) =>
      `<li data-id="${e.id}"><span class="dot ev-${e.type}"></span><b>${e.title}</b><small>${fmtD(e.t)}${e.trapped ? ' · ' + fmtN(e.trapped) + ' encircled' : ''}</small></li>`).join('');
    list.querySelectorAll('li').forEach((li) => { li.onclick = () => openEvent(events.find((e) => e.id === li.dataset.id)); });
    const ticks = $('ticks');
    ticks.innerHTML = events.filter((e) => evShown.has(e.type)).map((e) =>
      `<i class="ev-${e.type}" data-id="${e.id}" title="${fmtD(e.t)}: ${e.title}" style="left:${(e.t / app.tEnd * 100).toFixed(3)}%"></i>`).join('');
    ticks.querySelectorAll('i').forEach((i) => { i.onclick = () => openEvent(events.find((e) => e.id === i.dataset.id)); });
  }
  renderEvents();
  const togglePanel = () => { $('events').hidden = !$('events').hidden; };
  $('ev-btn').addEventListener('click', togglePanel);
  $('ev-close').addEventListener('click', togglePanel);
  window.addEventListener('keydown', (e) => { if (e.code === 'KeyE' && e.target.tagName !== 'INPUT') togglePanel(); });
  if (params.get('event')) { const e = events.find((x) => x.id === params.get('event')); if (e) openEvent(e); }

  function setWindow(t) {
    const w = Math.floor(t);
    if (w === app.win) return;
    const dirty = wb.build(w, w + 1);
    r.uploadGrid(wb.state, wb.time, dirty);
    app.win = w;
  }

  function frame(now) {
    const dt = app.lastFrame ? Math.min(0.1, (now - app.lastFrame) / 1000) : 0;
    app.lastFrame = now;
    if (app.playing) {
      app.t = Math.min(app.tEnd, app.t + dt * app.speed);
      if (app.t >= app.tEnd) app.playing = false;
      if (app.replay && app.t >= app.replay.end) {         // pocket replay finished
        app.playing = false;
        app.speed = app.replay.prevSpeed; app.setSpeedUi(app.speed);
        app.replay = null;
      }
    }
    if (app.stepFly) app.stepFly(now);
    r.resize();
    setWindow(app.t);
    app.pal = palette(meta.units, app.t);
    r.uploadPalette(app.pal);
    const day = Math.floor(app.t * 4) / 4;
    if (day !== app.warDay) { r.uploadWar(warMatrix(meta.units, app.t, meta.wars)); app.warDay = day; }
    // redraw the map only when something it depends on changed (time, camera, toggles, data)
    const camKey = `${r.cam.x},${r.cam.y},${r.cam.s},${r.canvas.width},${r.canvas.height},${r.opts.borders}${r.opts.fronts}`;
    if (app.t !== app.drawnT || camKey !== app.drawnCam || r.terrainDirty || app.win !== app.drawnWin) {
      r.draw(app.t - app.win);
      app.drawnT = app.t; app.drawnCam = camKey; app.drawnWin = app.win;
    }
    drawOverlay(ctx, r, app.t, now);
    syncUi();
    requestAnimationFrame(frame);
  }

  function syncUi() {
    if (document.activeElement !== slider) slider.value = String(app.t);
    $('play').textContent = app.playing ? '❚❚' : '▶';
    const d = fmtDate(app.t);
    $('ui-date').textContent = `${d.day} ${d.mon} ${d.year}`;
  }

  // Label anchor that follows a front: the front's key lines (48 points each)
  // are interpolated point by point in time; the label sits at the middle of
  // the line, offset to its own side, and is rotated along the front.
  function trackPlace(F, onW, t, rr) {
    const K = F.keys;
    if (!K.length || t < K[0][0] || (F.end != null && t > F.end)) return null;
    let i = 0;
    while (i < K.length - 2 && K[i + 1][0] <= t) i++;
    const A = K[i], B = K[i + 1] && K[i + 1][0] > A[0] ? K[i + 1] : A;
    const f = B === A ? 0 : Math.min(1, Math.max(0, (t - A[0]) / (B[0] - A[0])));
    const pt = (j) => {
      const la = A[2][j][0] + (B[2][j][0] - A[2][j][0]) * f, lo = A[2][j][1] + (B[2][j][1] - A[2][j][1]) * f;
      const [sx, sy] = rr.toScreen(mercX(lo), millerY(la));
      return [sx / rr.dpr, sy / rr.dpr];
    };
    const m = pt(24), a = pt(20), b = pt(28);
    let tx = b[0] - a[0], ty = b[1] - a[1];
    const len = Math.hypot(tx, ty) || 1; tx /= len; ty /= len;
    const ws = (f < 0.5 ? A[1] : B[1]);
    const side = (onW ? ws : -ws);
    const off = 64;                                    // px from the line
    const x = m[0] + side * -ty * off, y = m[1] + side * tx * off;
    let ang = Math.atan2(ty, tx);
    if (ang > Math.PI / 2) ang -= Math.PI; else if (ang < -Math.PI / 2) ang += Math.PI;
    return [x, y, ang];
  }

  // troop strength along each front, rotated with the front (reference style: 1.790.944)
  function drawStrengths(c, rr, t) {
    const fmt = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    for (const tr of app.tracks) {
      const a = tr.a;
      if (t < a[0].t || t > a[a.length - 1].t) continue;
      let i = 0;
      while (i < a.length - 2 && a[i + 1].t < t) i++;
      const p = a[i], q = a[i + 1] || p;
      const f = q.t > p.t ? Math.min(1, Math.max(0, (t - p.t) / (q.t - p.t))) : 0;
      const lerp = (u, v) => u + (v - u) * f;
      let n = lerp(p.n, q.n);
      if (tr.n) {
        const b = tr.n;
        let j = 0;
        while (j < b.length - 2 && b[j + 1].t < t) j++;
        const u = b[j], v = b[j + 1] || u;
        const g = v.t > u.t ? Math.min(1, Math.max(0, (t - u.t) / (v.t - u.t))) : 0;
        n = u.n + (v.n - u.n) * g;
      }
      if (n < 500) continue;
      const fade = Math.min(1, (t - a[0].t) * 2, (a[a.length - 1].t - t) * 2);
      let x, y, ang;
      const tp = tr.track ? trackPlace(tr.track, tr.onW, t, rr) : null;
      if (tp) {
        [x, y, ang] = tp;
      } else {
        const [sx, sy] = rr.toScreen(mercX(lerp(p.lon, q.lon)), millerY(lerp(p.lat, q.lat)));
        x = sx / rr.dpr; y = sy / rr.dpr; ang = lerp(p.ang, q.ang) * Math.PI / 180;
      }
      c.save();
      c.globalAlpha = fade;
      c.translate(x, y);
      c.rotate(ang);
      // reference style: bold white figures with a soft glow in the side's colour
      c.font = '700 27px "Open Sans", "Segoe UI", Calibri, Arial, sans-serif';
      c.textAlign = 'center'; c.textBaseline = 'middle';
      const glow = { allied: 'rgba(38,78,170,0.95)', soviet: 'rgba(120,40,25,0.85)' }[tr.side] || 'rgba(20,22,24,0.85)';
      c.shadowColor = glow; c.shadowBlur = 7;
      c.fillStyle = '#ffffff';
      c.fillText(fmt(n), 0, 0);
      c.shadowBlur = 3;
      c.fillText(fmt(n), 0, 0);
      c.restore();
    }
  }


  // ---------------------------------------------------------------- division markers (campaign replays)
  // The HOI4 logger records, every 3 days, how many divisions (and armoured divisions, and men) each
  // country has in each state - as lower bounds. Markers sit at the state centres; between snapshots
  // they cross-fade, so armies appear to move. Close together they merge into one marker per country.
  const unitById = Object.fromEntries(meta.units.map((u) => [u.id, u]));
  const smooth01 = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  function drawForces(c, rr, t) {
    app.markers = [];
    const F = app.campaign && app.campaign.forces;
    if (!F || !F.length || !$('opt-divisions').checked || t < F[0].t) return;
    let lo = 0, hi = F.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (F[m].t <= t) lo = m; else hi = m - 1; }
    const A = F[lo], B = F[lo + 1];
    const f = B ? smooth01((t - A.t) / (B.t - A.t)) : 0;
    const key = (r) => r[0] * 100000 + r[1];
    const nextMap = new Map(); if (B) for (const r of B.r) nextMap.set(key(r), r);
    const rows = [], seen = new Set();
    for (const r of A.r) {
      const nb = nextMap.get(key(r)); seen.add(key(r));
      rows.push({ id: r[0], st: r[1], n: nb ? r[2] + (nb[2] - r[2]) * f : r[2], arm: nb ? r[3] + (nb[3] - r[3]) * f : r[3],
        men: nb ? r[4] + (nb[4] - r[4]) * f : r[4], a: nb ? 1 : 1 - f });
    }
    if (B) for (const r of B.r) if (!seen.has(key(r))) rows.push({ id: r[0], st: r[1], n: r[2], arm: r[3], men: r[4], a: f });
    const W = overlay.clientWidth, H = overlay.clientHeight, CELL = 36;
    const cl = new Map();
    for (const r of rows) {
      if (r.a < 0.02) continue;
      const p = app.campaign.statePos[r.st];
      if (!p) continue;
      const [sx, sy] = rr.toScreen(mercX(p[0]), millerY(p[1]));
      const x = sx / rr.dpr, y = sy / rr.dpr;
      if (x < -30 || y < -30 || x > W + 30 || y > H + 30) continue;
      const k = `${r.id}:${Math.floor(x / CELL)}:${Math.floor(y / CELL)}`;
      let g = cl.get(k);
      if (!g) { g = { id: r.id, x: 0, y: 0, w: 0, n: 0, arm: 0, men: 0, a: 0, states: [] }; cl.set(k, g); }
      const w = Math.max(1, r.men);
      g.x += x * w; g.y += y * w; g.w += w; g.n += r.n; g.arm += r.arm; g.men += r.men; g.a = Math.max(g.a, r.a); g.states.push(r.st);
    }
    const list = [...cl.values()].map((g) => ({ ...g, x: g.x / g.w, y: g.y / g.w }));
    list.sort((p, q) => p.men - q.men);                     // big armies on top
    for (const g of list) {
      const rad = 7 + 2.6 * Math.log10(Math.max(1, g.men / 500));
      const pc = app.pal ? [app.pal[g.id * 4], app.pal[g.id * 4 + 1], app.pal[g.id * 4 + 2]] : [120, 120, 120];
      c.save();
      c.globalAlpha = g.a;
      c.beginPath(); c.arc(g.x, g.y, rad, 0, Math.PI * 2);
      c.fillStyle = `rgb(${pc[0] * 0.62 | 0},${pc[1] * 0.62 | 0},${pc[2] * 0.62 | 0})`; c.fill();
      c.lineWidth = 1.6; c.strokeStyle = '#fff'; c.stroke();
      if (g.arm >= 1) {                                      // armoured share as an orange arc
        c.beginPath(); c.arc(g.x, g.y, rad + 2.6, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, g.arm / Math.max(1, g.n)));
        c.lineWidth = 2.4; c.strokeStyle = '#ff9f1c'; c.stroke();
      }
      const code = (unitById[g.id] || {}).code || '';
      c.font = `700 ${Math.max(8, Math.min(11, rad * 0.8)) | 0}px "Segoe UI", Arial, sans-serif`;
      c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#fff';
      c.fillText(code, g.x, g.y + 0.5);
      if (g.n >= 1) {                                        // division count badge
        const bx = g.x + rad * 0.85, by = g.y + rad * 0.85;
        c.beginPath(); c.arc(bx, by, 7.5, 0, Math.PI * 2); c.fillStyle = '#16181c'; c.fill();
        c.fillStyle = '#fff'; c.font = '700 9.5px "Segoe UI", Arial, sans-serif';
        c.fillText(String(Math.round(g.n)), bx, by + 0.5);
      }
      c.restore();
      app.markers.push({ ...g, rad });
    }
  }

  // ---------------------------------------------------------------- front totals (campaign replays)
  // Each front is one track built by the compiler: its centre, direction, which way each side lies, and the
  // troops (men, a lower bound from the log) each side keeps near it. Labels sit on both sides of the front.
  function drawFronts(c, rr, t) {
    const FR = app.campaign && app.campaign.fronts;
    if (!FR || !$('opt-numbers').checked) return;
    const fmt = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    const side = (id) => {
      const k = app.pal ? [app.pal[id * 4], app.pal[id * 4 + 1], app.pal[id * 4 + 2]] : [60, 60, 60];
      return `rgba(${k[0] * 0.55 | 0},${k[1] * 0.55 | 0},${k[2] * 0.55 | 0},0.95)`;
    };
    for (const tr of FR) {
      const a = tr.s;
      if (t < a[0][0] - 1.5 || t > a[a.length - 1][0] + 1.5) continue;
      const tt = Math.min(a[a.length - 1][0], Math.max(a[0][0], t));
      let i = 0;
      while (i < a.length - 2 && a[i + 1][0] < tt) i++;
      const p = a[i], q = a[i + 1] || p;
      const f = q[0] > p[0] ? smooth01((tt - p[0]) / (q[0] - p[0])) : 0;
      const L = (k) => p[k] + (q[k] - p[k]) * f;
      const fade = Math.min(1, (t - a[0][0] + 1.5) / 1.5, (a[a.length - 1][0] + 1.5 - t) / 1.5);
      const [sx, sy] = rr.toScreen(mercX(L(1)), millerY(L(2)));
      const x = sx / rr.dpr, y = sy / rr.dpr;
      if (x < -80 || y < -80 || x > overlay.clientWidth + 80 || y > overlay.clientHeight + 80) continue;
      let ang = L(3);
      ang = ((ang + 90) % 180 + 180) % 180 - 90;
      const rad = ang * Math.PI / 180;
      let nx = L(4), ny = L(5);
      const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
      const off = 30;
      const sides = [[tr.a, L(6), 1], [tr.b, L(7), -1]];
      for (const [id, men, sg] of sides) {
        if (men < 500) continue;
        c.save();
        c.globalAlpha = Math.max(0, fade);
        c.translate(x + nx * off * sg, y + ny * off * sg);
        c.rotate(rad);
        c.font = '700 22px "Open Sans", "Segoe UI", Calibri, Arial, sans-serif';
        c.textAlign = 'center'; c.textBaseline = 'middle';
        c.shadowColor = side(id); c.shadowBlur = 7;
        c.fillStyle = '#ffffff';
        c.fillText(fmt(men), 0, 0);
        c.shadowBlur = 3;
        c.fillText(fmt(men), 0, 0);
        c.restore();
      }
    }
  }
  function showTip(e) {
    const tip = $('tip');
    if (!app.markers || !app.markers.length || !$('opt-divisions').checked) { tip.hidden = true; return; }
    const rect = overlay.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    let hit = null;
    for (let i = app.markers.length - 1; i >= 0; i--) {
      const g = app.markers[i];
      if ((g.x - mx) ** 2 + (g.y - my) ** 2 <= (g.rad + 4) ** 2) { hit = g; break; }
    }
    if (!hit) { tip.hidden = true; return; }
    const u = unitById[hit.id] || {};
    const fac = (app.pal ? '' : '');
    tip.innerHTML = `<b>${campaign.countries[u.code] || u.code}</b> <span class="dim">(${u.code})</span><br>` +
      `at least <b>${Math.round(hit.n)}</b> division${Math.round(hit.n) === 1 ? '' : 's'}` +
      (hit.arm >= 1 ? `, <b>${Math.round(hit.arm)}</b> armoured` : '') + `<br>` +
      `at least <b>${fmtN(hit.men)}</b> men<br>` +
      `<span class="dim">${hit.states.length} state${hit.states.length === 1 ? '' : 's'} - positions are per state, counts are lower bounds from the log</span>${fac}`;
    tip.hidden = false;
    tip.style.left = Math.min(window.innerWidth - 300, e.clientX + 14) + 'px';
    tip.style.top = Math.min(window.innerHeight - 120, e.clientY + 14) + 'px';
  }
  if (campaign) {
    $('lbl-divisions').hidden = false;
    $('opt-numbers').parentElement.lastChild.textContent = ' front troops';
    $('opt-divisions').checked = false;                     // front totals by default; per-state markers on request
    canvas.addEventListener('pointermove', (e) => { if (!app.dragging) showTip(e); });
    canvas.addEventListener('pointerleave', () => { $('tip').hidden = true; });
  }

  function drawOverlay(c, rr, t, now) {
    const W = overlay.clientWidth, H = overlay.clientHeight, dpr = rr.dpr;
    if (overlay.width !== Math.round(W * dpr) || overlay.height !== Math.round(H * dpr)) {
      overlay.width = Math.round(W * dpr); overlay.height = Math.round(H * dpr);
    }
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, W, H);
    // date block, top left (reference style)
    const d = fmtDate(t);
    c.fillStyle = '#1b1d22';
    c.font = '700 22px "Segoe UI", "Open Sans", Calibri, Arial, sans-serif';
    c.textBaseline = 'top';
    c.fillText(`${d.day}   ${d.mon}   ${d.year}`, 14, 10);
    c.font = '700 13px "Segoe UI", "Open Sans", Calibri, Arial, sans-serif';
    c.fillText(d.hour, 14, 37);
    // caption, bottom left: most recent event within the last 6 days
    const caps = meta.captions;
    let cap = null;
    for (const k of caps) { if (k.t <= t && t - k.t < 6) cap = k; }
    if (cap) {
      const a = Math.min(1, (t - cap.t) * 4) * Math.min(1, (6 - (t - cap.t)) * 2);
      c.globalAlpha = a;
      c.font = '700 20px "Segoe UI", "Open Sans", Calibri, Arial, sans-serif';
      c.textBaseline = 'alphabetic';
      c.fillStyle = '#16181c';
      c.fillText(cap.text, 14, H - 92);
      c.globalAlpha = 1;
    }
    if (!campaign && $('opt-numbers').checked) drawStrengths(c, rr, t);
    if (campaign) { drawFronts(c, rr, t); drawForces(c, rr, t); }
    if (!$('opt-labels').checked) return;
    // encirclement markers
    for (const L of meta.labels) {
      if (t < L.t0 || t > L.t1) continue;
      const a = Math.min(1, (t - L.t0) * 3, (L.t1 - t) * 3);
      const [sx, sy] = rr.toScreen(mercX(L.lon), millerY(L.lat));
      const x = sx / dpr, y = sy / dpr;
      c.globalAlpha = a;
      const rad = 13, n = 12, rot = now / 1600;
      c.lineCap = 'round';
      for (let i = 0; i < n; i++) {
        const ang = rot + i * Math.PI * 2 / n;
        const x0 = x + Math.cos(ang) * rad, y0 = y + Math.sin(ang) * rad;
        const x1 = x + Math.cos(ang) * (rad + 6), y1 = y + Math.sin(ang) * (rad + 6);
        c.strokeStyle = 'rgba(30,32,36,0.55)'; c.lineWidth = 4;
        c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
        c.strokeStyle = '#ffffff'; c.lineWidth = 2;
        c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
      }
      // reference style: "324.000 Encircled" (dots as thousands separators)
      const text = (L.text || '').replace(/(\d),(?=\d{3})/g, '$1.').replace(/\bc\. /g, '')
        .replace(/\b(encircled|captured|besieged|surrendered|cut off|evacuated)\b/, (w) => w[0].toUpperCase() + w.slice(1));
      if (text) {
        c.font = '700 19px "Open Sans", "Segoe UI", Calibri, Arial, sans-serif';
        c.textAlign = 'center'; c.textBaseline = 'bottom';
        c.shadowColor = 'rgba(20,22,24,0.85)'; c.shadowBlur = 6;
        c.fillStyle = '#ffffff';
        c.fillText(text, x, y - rad - 10);
        c.shadowBlur = 0;
        c.textAlign = 'left';
      }
      c.globalAlpha = 1;
    }
  }

  // ---------------------------------------------------------------- input
  slider.addEventListener('input', () => { app.t = +slider.value; if (app.replay) { app.speed = app.replay.prevSpeed; app.setSpeedUi(app.speed); app.replay = null; } });
  $('play').addEventListener('click', () => { if (app.t >= app.tEnd) app.t = 0; app.playing = !app.playing; });
  $('speed').addEventListener('change', (e) => { app.speed = +e.target.value; });
  $('speed').value = String(app.speed);
  $('reset').addEventListener('click', () => fitCamera(r, canvas.clientWidth, canvas.clientHeight));
  $('opt-borders').addEventListener('change', (e) => { r.opts.borders = e.target.checked; });
  $('opt-fronts').addEventListener('change', (e) => { r.opts.fronts = e.target.checked; });
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' && e.target.type !== 'range') return;
    if (e.code === 'Space') { app.playing = !app.playing; e.preventDefault(); }
    const step = e.shiftKey ? 7 : 1;
    if (e.code === 'ArrowRight') app.t = Math.min(app.tEnd, Math.floor(app.t) + step);
    if (e.code === 'ArrowLeft') app.t = Math.max(0, Math.ceil(app.t) - step);
  });
  let drag = null;
  canvas.addEventListener('pointerdown', (e) => { app.fly = null; app.dragging = true; drag = { x: e.clientX, y: e.clientY }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    r.cam.x -= (e.clientX - drag.x) / r.cam.s;
    r.cam.y -= (e.clientY - drag.y) / r.cam.s;
    drag = { x: e.clientX, y: e.clientY };
    clampCamera(r);
  });
  canvas.addEventListener('pointerup', () => { drag = null; app.dragging = false; });
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const k = Math.exp(-e.deltaY * 0.0015);
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left - rect.width / 2, my = e.clientY - rect.top - rect.height / 2;
    const wx = r.cam.x + mx / r.cam.s, wy = r.cam.y + my / r.cam.s;
    r.cam.s *= k;
    clampCamera(r);
    r.cam.x = wx - mx / r.cam.s; r.cam.y = wy - my / r.cam.s;
    clampCamera(r);
  }, { passive: false });
  window.addEventListener('resize', () => { r.resize(); clampCamera(r); });

  window.__app = app;
  window.__renderer = r;
  requestAnimationFrame(frame);
}

main().catch((e) => {
  console.error(e);
  const el = $('loading');
  if (el) el.textContent = `Failed to start: ${e.message}`;
});
