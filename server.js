// Minimal static server: node server.js [port]
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const PORT = +(process.argv[2] || process.env.PORT || 3847);
const ROOT = __dirname;
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.png': 'image/png',
  '.bin': 'application/octet-stream', '.svg': 'image/svg+xml',
};


// ---------------------------------------------------------------- HOI4 campaign upload and build
// The page uploads a game.log (and, once, hoi4_states.json); this builds the replay with
// build/hoi4/build_campaign.py (Python 3 with numpy, scipy, scikit-image) into data/hoi4_user.
const USER = path.join(ROOT, 'user');
const OUT = path.join(ROOT, 'data', 'hoi4_user');
const OUT_TMP = path.join(ROOT, 'data', 'hoi4_user.tmp');
const UPLOADS = { log: 'game.log', states: 'hoi4_states.json' };
let job = { state: 'idle', pct: 0, msg: '', error: '', startedAt: 0 };

function findPython() {
  const tries = [['python3'], ['python'], ['py', '-3']];
  let lastErr = '';
  for (const t of tries) {
    const r = spawnSync(t[0], [...t.slice(1), '-c', 'import numpy, scipy, skimage; print(1)'], { encoding: 'utf8' });
    if (r.error && r.error.code === 'ENOENT') continue;
    if (r.status === 0) return { cmd: t };
    lastErr = (r.stderr || '').trim().split('\n').pop();
    if (/No module named/.test(lastErr)) return { missing: lastErr, cmd: t };
  }
  return { none: true, missing: lastErr };
}

function startBuild() {
  const py = findPython();
  if (py.none) { job = { state: 'error', pct: 0, msg: '', error: 'Python 3 was not found. Install Python 3 from python.org (tick "Add to PATH"), then try again.' }; return; }
  if (py.missing) {
    job = { state: 'error', pct: 0, msg: '', error: `Python is missing a package (${py.missing}). Run this once, then try again:  ${py.cmd.join(' ')} -m pip install numpy scipy scikit-image` };
    return;
  }
  fs.rmSync(OUT_TMP, { recursive: true, force: true });
  job = { state: 'running', pct: 0, msg: 'Starting', error: '', startedAt: Date.now() };
  const args = [...py.cmd.slice(1), '-u', path.join(ROOT, 'build', 'hoi4', 'build_campaign.py'),
    path.join(USER, UPLOADS.log), path.join(USER, UPLOADS.states), OUT_TMP];
  const child = spawn(py.cmd[0], args, { cwd: ROOT });
  let err = '', buf = '';
  child.stdout.on('data', (d) => {
    buf += d.toString();
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      const m = /^PROGRESS\|(\d+)\|(.*)$/.exec(line);
      if (m) { job.pct = +m[1]; job.msg = m[2]; }
    }
  });
  child.stderr.on('data', (d) => { err = (err + d.toString()).slice(-4000); });
  child.on('error', (e) => { job = { state: 'error', pct: 0, msg: '', error: String(e) }; });
  child.on('close', (code) => {
    if (code === 0 && fs.existsSync(path.join(OUT_TMP, 'meta.json'))) {
      fs.rmSync(OUT, { recursive: true, force: true });
      fs.renameSync(OUT_TMP, OUT);
      job = { state: 'done', pct: 100, msg: 'Done', error: '' };
    } else {
      job = { state: 'error', pct: job.pct, msg: '', error: 'The build failed. ' + (err.trim().split('\n').slice(-6).join('\n') || `exit code ${code}`) };
    }
  });
}

function api(req, res, url) {
  const send = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(obj)); };
  if (req.method === 'GET' && url.pathname === '/api/hoi4/status') {
    return send(200, {
      haveLog: fs.existsSync(path.join(USER, UPLOADS.log)), haveStates: fs.existsSync(path.join(USER, UPLOADS.states)),
      ready: fs.existsSync(path.join(OUT, 'meta.json')), job,
    });
  }
  if (req.method === 'POST' && url.pathname === '/api/hoi4/upload') {
    const kind = url.searchParams.get('kind');
    if (!UPLOADS[kind]) return send(400, { error: 'unknown upload' });
    if (job.state === 'running') return send(409, { error: 'a build is running' });
    fs.mkdirSync(USER, { recursive: true });
    const tmp = path.join(USER, UPLOADS[kind] + '.part');
    const out = fs.createWriteStream(tmp);
    req.pipe(out);
    out.on('finish', () => { fs.renameSync(tmp, path.join(USER, UPLOADS[kind])); send(200, { ok: true }); });
    out.on('error', (e) => send(500, { error: String(e) }));
    return;
  }
  if (req.method === 'POST' && url.pathname === '/api/hoi4/build') {
    if (job.state === 'running') return send(409, { error: 'a build is running' });
    if (!fs.existsSync(path.join(USER, UPLOADS.log))) return send(400, { error: 'no game.log uploaded yet' });
    if (!fs.existsSync(path.join(USER, UPLOADS.states))) return send(400, { error: 'no hoi4_states.json uploaded yet' });
    startBuild();
    return send(202, { job });
  }
  send(404, { error: 'not found' });
}

http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) return api(req, res, new URL(req.url, 'http://x'));
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const file = path.normalize(path.join(ROOT, p));
  if (!file.startsWith(ROOT) || /[\\/](build|user|\.git)[\\/]/.test(file.slice(ROOT.length))) {
    res.writeHead(403); res.end(); return;
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('404'); return; }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    res.end(data);
  });
}).listen(PORT, '127.0.0.1', () => console.log(`WWII Day by Day: http://127.0.0.1:${PORT}`));
