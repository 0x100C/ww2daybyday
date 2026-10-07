import { Renderer } from './renderer.js';
import { loadTerritory, WindowBuffers } from './territory.js';
import { GEO, mercX, millerY } from './geo.js';
import { palette, warMatrix, dayOf } from './factions.js';

const $ = (id) => document.getElementById(id);
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const EPOCH = Date.UTC(1939, 8, 1);

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
    fetch('data/meta.json').then((x) => x.json()),
    loadTerritory('data/territory.bin'),
  ]);
  app.meta = meta;
  // front strengths: dated anchors -> per-day interpolated label tracks
  const parseT = (s) => {
    const [d, h] = s.split(' ');
    return (Date.parse(d + 'T00:00:00Z') - EPOCH) / 864e5 + (h ? +h / 24 : 0);
  };
  const strengths = await fetch('data/strengths.json').then((x) => (x.ok ? x.json() : { fronts: [] })).catch(() => ({ fronts: [] }));
  const tracks = [];
  for (const f of strengths.fronts) for (const s of f.sides) {
    tracks.push({ side: s.label_side || s.side, a: s.a.map(([d, n, lat, lon, ang]) => ({ t: parseT(d), n, lat, lon, ang })) });
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
  if (params.get('play') === '1') app.playing = true;
  if (params.get('speed')) app.speed = +params.get('speed');

  const ctx = overlay.getContext('2d');

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
    }
    r.resize();
    setWindow(app.t);
    r.uploadPalette(palette(meta.units, app.t));
    const day = Math.floor(app.t * 4) / 4;
    if (day !== app.warDay) { r.uploadWar(warMatrix(meta.units, app.t)); app.warDay = day; }
    r.draw(app.t - app.win);
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
      const n = lerp(p.n, q.n);
      if (n < 500) continue;
      const fade = Math.min(1, (t - a[0].t) * 2, (a[a.length - 1].t - t) * 2);
      const [sx, sy] = rr.toScreen(mercX(lerp(p.lon, q.lon)), millerY(lerp(p.lat, q.lat)));
      const x = sx / rr.dpr, y = sy / rr.dpr;
      c.save();
      c.globalAlpha = fade;
      c.translate(x, y);
      c.rotate(lerp(p.ang, q.ang) * Math.PI / 180);
      c.font = '600 26px "Segoe UI", "Open Sans", Calibri, Arial, sans-serif';
      c.textAlign = 'center'; c.textBaseline = 'middle';
      c.lineJoin = 'round';
      c.lineWidth = 4;
      const allied = tr.side === 'allied';
      c.strokeStyle = allied ? 'rgba(40,70,130,0.7)' : 'rgba(25,27,30,0.6)';
      c.strokeText(fmt(n), 0, 0);
      c.fillStyle = allied ? '#e6eeff' : '#ffffff';
      c.fillText(fmt(n), 0, 0);
      c.restore();
    }
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
    if ($('opt-numbers').checked) drawStrengths(c, rr, t);
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
      if (L.text) {
        c.font = '600 17px "Segoe UI", "Open Sans", Calibri, Arial, sans-serif';
        c.textAlign = 'center'; c.textBaseline = 'bottom';
        c.lineWidth = 4; c.strokeStyle = 'rgba(25,27,30,0.75)';
        c.strokeText(L.text, x, y - rad - 10);
        c.fillStyle = '#ffffff';
        c.fillText(L.text, x, y - rad - 10);
        c.textAlign = 'left';
      }
      c.globalAlpha = 1;
    }
  }

  // ---------------------------------------------------------------- input
  slider.addEventListener('input', () => { app.t = +slider.value; });
  $('play').addEventListener('click', () => { if (app.t >= app.tEnd) app.t = 0; app.playing = !app.playing; });
  $('speed').addEventListener('change', (e) => { app.speed = +e.target.value; });
  $('speed').value = String(app.speed);
  $('reset').addEventListener('click', () => fitCamera(r, canvas.clientWidth, canvas.clientHeight));
  $('opt-borders').addEventListener('change', (e) => { r.opts.borders = e.target.checked; });
  $('opt-fronts').addEventListener('change', (e) => { r.opts.fronts = e.target.checked; });
  $('opt-hatch').addEventListener('change', (e) => { r.opts.hatch = e.target.checked; });
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' && e.target.type !== 'range') return;
    if (e.code === 'Space') { app.playing = !app.playing; e.preventDefault(); }
    const step = e.shiftKey ? 7 : 1;
    if (e.code === 'ArrowRight') app.t = Math.min(app.tEnd, Math.floor(app.t) + step);
    if (e.code === 'ArrowLeft') app.t = Math.max(0, Math.ceil(app.t) - step);
  });
  let drag = null;
  canvas.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    r.cam.x -= (e.clientX - drag.x) / r.cam.s;
    r.cam.y -= (e.clientY - drag.y) / r.cam.s;
    drag = { x: e.clientX, y: e.clientY };
    clampCamera(r);
  });
  canvas.addEventListener('pointerup', () => { drag = null; });
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
