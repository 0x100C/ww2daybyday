// "Upload your game.log" screen for ?campaign=hoi4. The local server (node server.js) receives the files,
// builds the replay with Python (build/hoi4/build_campaign.py) and reports progress; when it is done the
// page reloads and plays it.
const $ = (id) => document.getElementById(id);
const api = (path, opts) => fetch(path, opts).then((r) => r.json());

function upload(kind, file, onPct) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open('POST', `/api/hoi4/upload?kind=${kind}`);
    x.upload.onprogress = (e) => { if (e.lengthComputable) onPct(Math.round((100 * e.loaded) / e.total)); };
    x.onload = () => (x.status === 200 ? resolve() : reject(new Error(x.responseText || `upload failed (${x.status})`)));
    x.onerror = () => reject(new Error('upload failed: is the server (node server.js) still running?'));
    x.send(file);
  });
}

// Resolves true when a built replay already exists (page can play it), false when the uploader took over.
export async function prepareCampaign() {
  let st;
  try { st = await api('/api/hoi4/status'); } catch { st = null; }
  if (st && st.ready && st.job.state !== 'running') return true;
  showUploader(st);
  return false;
}

export function openUploader() { api('/api/hoi4/status').then(showUploader).catch(() => showUploader(null)); }

function showUploader(st) {
  const box = $('uploader');
  const loading = $('loading'); if (loading) loading.hidden = true;
  box.hidden = false;
  if (!st) {
    box.innerHTML = '<h2>Replay a Hearts of Iron IV campaign</h2><p class="err">Cannot reach the local server. Start it with <code>node server.js</code> and reload this page.</p>';
    return;
  }
  const needStates = !st.haveStates;
  box.innerHTML = `
    <h2>Replay a Hearts of Iron IV campaign</h2>
    <p>Pick the <b>game.log</b> that the WW2 Day by Day logger mod wrote while you played. It is built into a replay here on your computer (a few minutes for a long game).</p>
    <label class="pick"><span>1. game.log</span><input id="up-log" type="file" accept=".log,.txt"></label>
    <small>Windows: <code>Documents\\Paradox Interactive\\Hearts of Iron IV\\logs\\game.log</code> (copy it before you start HOI4 again, the game overwrites it).</small>
    ${needStates ? `<label class="pick"><span>2. hoi4_states.json</span><input id="up-states" type="file" accept=".json"></label>
    <small>Needed once. Create it with <code>node build/hoi4/extract_states.mjs "&lt;your Hearts of Iron IV folder&gt;"</code> and pick the file it writes (data/hoi4_states.json).</small>` : '<small>hoi4_states.json: already on this computer.</small>'}
    <div class="row"><button id="up-go">Build replay</button><span id="up-msg"></span></div>
    <div id="up-bar" hidden><i></i></div>
    <p id="up-err" class="err" hidden></p>
    <p class="alt">${st.ready ? '<a href="?campaign=hoi4" id="up-cur">Play your last replay</a> &middot; ' : ''}Samples: <a href="?campaign=hoi4_demo">1939 game</a> &middot; <a href="?campaign=hoi4_1936">1936-41 game</a> &middot; <a href="./">historical map</a></p>`;
  const bar = $('up-bar'), msg = $('up-msg'), err = $('up-err'), go = $('up-go');
  const setBar = (p) => { bar.hidden = false; bar.firstChild.style.width = p + '%'; };
  const fail = (m) => { err.hidden = false; err.textContent = m; go.disabled = false; msg.textContent = ''; };

  async function poll() {
    for (;;) {
      let s;
      try { s = await api('/api/hoi4/status'); } catch { fail('Lost contact with the server.'); return; }
      const j = s.job;
      if (j.state === 'running') { setBar(j.pct); msg.textContent = j.msg; }
      else if (j.state === 'done') { setBar(100); msg.textContent = 'Done, loading the replay...'; location.href = '?campaign=hoi4'; return; }
      else if (j.state === 'error') { fail(j.error); return; }
      await new Promise((r) => setTimeout(r, 1000));
    }
  }

  go.addEventListener('click', async () => {
    err.hidden = true;
    const log = $('up-log').files[0];
    const states = needStates ? $('up-states').files[0] : null;
    if (!log) return fail('Choose your game.log first.');
    if (needStates && !states) return fail('Choose hoi4_states.json too (see the note under it).');
    go.disabled = true;
    try {
      if (states) { msg.textContent = 'Uploading hoi4_states.json...'; await upload('states', states, () => {}); }
      msg.textContent = 'Uploading game.log...';
      await upload('log', log, (p) => { msg.textContent = `Uploading game.log... ${p}%`; });
      msg.textContent = 'Starting the build...';
      const r = await api('/api/hoi4/build', { method: 'POST' });
      if (r.error) return fail(r.error);
      if (r.job && r.job.state === 'error') return fail(r.job.error);
      poll();
    } catch (e) { fail(String(e.message || e)); }
  });
  if (st.job && st.job.state === 'running') { go.disabled = true; poll(); }
  if (st.job && st.job.state === 'error') fail(st.job.error);
}
