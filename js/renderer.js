// WebGL2 map renderer.
//
// Pass 1 (only when the camera moves or tiles arrive): the basemap tile
// pyramid is drawn into an offscreen "terrain" buffer holding, per screen
// pixel, terrain lightness, ink (cities, roads, rail), water coverage and
// snow. Terrain is therefore identical from frame to frame.
//
// Pass 2 (every frame): one full-screen shader colours land by the
// controlling power on the territory grid, draws the pale band over ground
// that is being taken, white front lines between powers at war, pink
// national borders and the coastline.

import { GEO, millerY, invMercY } from './geo.js';

const VS = `#version 300 es
in vec2 aPos; in vec2 aUv; out vec2 vUv;
uniform vec4 uRect; // x0 y0 x1 y1 in clip space
void main(){ vUv = aUv; vec2 p = mix(uRect.xy, uRect.zw, aPos); gl_Position = vec4(p, 0.0, 1.0); }`;

// tile meshes: vertices already in clip space (rows warped Mercator -> Miller)
const VS_MESH = `#version 300 es
in vec2 aPos; in vec2 aUv; out vec2 vUv;
void main(){ vUv = aUv; gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FS_TILE = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uShade; uniform sampler2D uMask;
void main(){
  float L = texture(uShade, vUv).r;
  vec3 m = texture(uMask, vUv).rgb;
  o = vec4(L, m.r, m.g, m.b);
}`;

const FS_MAP = `#version 300 es
precision highp float;
precision highp int;
out vec4 o;
uniform sampler2D uTerrain;
uniform sampler2D uState;   // R ctl before, G ctl after, B country before, A country after
uniform sampler2D uTime;    // R arrival (bilinear), G pending start, B arrival exact, A country switch
uniform sampler2D uPal;     // 256 x 1: rgb colour, a = 1 for neutral
uniform sampler2D uWar;     // 256 x 256: r > .5 when at war
uniform vec2 uRes;
uniform vec2 uGridSize;
uniform vec2 uW0;           // display-world coords (x mercator, y Miller) of screen pixel (0,0)
uniform vec2 uWs;           // display-world units per screen pixel
uniform vec2 uM0;           // mercator coords of the grid origin
uniform vec2 uGsc;          // grid cells per mercator unit
uniform float uTn;          // time within the current one-day window, 0..1
uniform float uPx;          // device pixel ratio
uniform float uBorders, uFronts;

const float PI = 3.14159265358979;
// screen pixel -> territory grid coords. x is linear; the Miller -> Mercator
// row mapping depends only on the screen row, so it is precomputed per row
// on the CPU (uRowY) instead of evaluating exp/atan/log/tan per fragment.
uniform highp sampler2D uRowY;
vec2 gridAt(vec2 px){
  float wx = uW0.x + px.x * uWs.x;
  int row = clamp(int(floor(px.y)), 0, int(uRes.y) - 1);
  return vec2((wx - uM0.x) * uGsc.x, texelFetch(uRowY, ivec2(row, 0), 0).r);
}

ivec2 cellOf(vec2 g){ return clamp(ivec2(floor(g)), ivec2(0), ivec2(uGridSize) - 1); }

// Smoothed ownership: instead of the nearest cell's owner (which draws grid
// stair-steps), take the owner with the largest bilinear weight among the
// four surrounding cells - the 0.5 contour of each owner's coverage, so
// borders and fronts follow smooth diagonals through the same cell edges.
vec3 ownerCell(ivec2 c, vec2 g);
vec3 ownerAt(vec2 g){
  vec2 h = g - 0.5;
  ivec2 b = ivec2(floor(h));
  vec2 f = fract(h);
  ivec2 hi = ivec2(uGridSize) - 1;
  vec3 o0 = ownerCell(clamp(b, ivec2(0), hi), g);
  vec3 o1 = ownerCell(clamp(b + ivec2(1, 0), ivec2(0), hi), g);
  vec3 o2 = ownerCell(clamp(b + ivec2(0, 1), ivec2(0), hi), g);
  vec3 o3 = ownerCell(clamp(b + ivec2(1, 1), ivec2(0), hi), g);
  float w0 = (1.0 - f.x) * (1.0 - f.y), w1 = f.x * (1.0 - f.y), w2 = (1.0 - f.x) * f.y, w3 = f.x * f.y;
  vec3 o[4] = vec3[](o0, o1, o2, o3);
  float w[4] = float[](w0, w1, w2, w3);
  float bestC = -1.0, bestY = -1.0, ctl = o0.x, cty = o0.y;
  for (int i = 0; i < 4; i++) {
    float sc = 0.0, sy = 0.0;
    for (int j = 0; j < 4; j++) {
      if (o[j].x == o[i].x) sc += w[j];
      if (o[j].y == o[i].y) sy += w[j];
    }
    if (sc > bestC) { bestC = sc; ctl = o[i].x; }
    if (sy > bestY) { bestY = sy; cty = o[i].y; }
  }
  float pend = w0 * o0.z + w1 * o1.z + w2 * o2.z + w3 * o3.z;
  return vec3(ctl, cty, pend);
}

// one cell: control id, country id, pending amount
vec3 ownerCell(ivec2 c, vec2 g){
  vec4 st = texelFetch(uState, c, 0);
  vec4 tm = texelFetch(uTime, c, 0);
  float arr = texture(uTime, g / uGridSize).r;
  float ctl = (uTn >= arr) ? st.g : st.r;
  float cty = (uTn >= tm.a) ? st.a : st.b;
  float pend = 0.0;
  bool started = tm.g <= uTn;
  bool within = (st.r != st.g) && (uTn < tm.b);
  bool beyond = tm.b > 0.999;
  if (started && (within || beyond) && ctl == st.r) pend = tm.g <= 0.0 ? 1.0 : clamp((uTn - tm.g) * 6.0, 0.0, 1.0);
  return vec3(floor(ctl * 255.0 + 0.5), floor(cty * 255.0 + 0.5), pend);
}

vec4 pal(float id){ return texelFetch(uPal, ivec2(int(id), 0), 0); }
bool atWar(float a, float b){ return texelFetch(uWar, ivec2(int(a), int(b)), 0).r > 0.5; }

void main(){
  vec2 px = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);
  vec4 ter = texelFetch(uTerrain, ivec2(gl_FragCoord.xy), 0);
  float L = ter.r, ink = ter.g, water = ter.b, snow = ter.a;
  vec2 g = gridAt(px);
  vec3 me = ownerAt(g);
  vec4 pc = pal(me.x);
  vec3 col = pc.rgb;
  // soft advancing edge: blend old/new owner colour across ~1.5 px of the moving arrival front
  {
    ivec2 cc = cellOf(g);
    vec4 st = texelFetch(uState, cc, 0);
    if (st.r != st.g) {
      float arr = texture(uTime, g / uGridSize).r;
      float w = max(fwidth(arr) * 1.5, 0.004);
      float a = smoothstep(arr - w, arr + w, uTn);
      vec3 cb = pal(floor(st.r * 255.0 + 0.5)).rgb, ca = pal(floor(st.g * 255.0 + 0.5)).rgb;
      col = mix(cb, ca, a);
    }
  }
  if (me.z > 0.0) col = mix(col, vec3(1.0), 0.45 * me.z);

  // terrain shading
  float shade = L / 0.80;
  vec3 land = col * shade;
  land = mix(land, vec3(0.97, 0.97, 0.98), snow * (pc.a > 0.5 ? 0.7 : 0.4));

  // edges of control and country
  float d = 1.0 * uPx;
  vec2 offs[4] = vec2[](vec2(d,0.0), vec2(-d,0.0), vec2(0.0,d), vec2(0.0,-d));
  float front = 0.0, edge = 0.0, border = 0.0;
  for (int i = 0; i < 4; i++){
    vec3 n = ownerAt(gridAt(px + offs[i]));
    if (n.x != me.x){
      if (atWar(me.x, n.x)) front = 1.0;
      else if (pc.a < 0.5) edge = 1.0;
    }
    if (n.y != me.y && n.y > me.y) border = 1.0;  // one side only: 1 px line
  }
  if (edge > 0.0) land = mix(land, vec3(1.0), 0.28);

  float wmask = clamp((water - 0.5) * 1.6 + 0.5, 0.0, 1.0);
  vec3 wcol = vec3(218.0, 227.0, 241.0) / 255.0;
  vec3 c = mix(land, wcol, wmask);
  // ink: built-up areas, roads, railways and the coastline
  c *= 1.0 - ink * (pc.a > 0.5 ? 0.36 : 0.44);

  float onLand = 1.0 - wmask;
  if (uBorders > 0.5) c = mix(c, vec3(0.93, 0.52, 0.52), border * 0.62 * onLand);
  if (uFronts > 0.5) c = mix(c, vec3(1.0), front * 0.95 * onLand);
  o = vec4(c, 1.0);
}`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}

function program(gl, vs, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs));
  gl.bindAttribLocation(p, 0, 'aPos');
  gl.bindAttribLocation(p, 1, 'aUv');
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) {
    const info = gl.getActiveUniform(p, i);
    u[info.name.replace(/\[0\]$/, '')] = gl.getUniformLocation(p, info.name);
  }
  return { p, u };
}

const invMillerLat = (y) => {
  const Y = (0.5 - y) * 2 * Math.PI / 1.25;
  return Math.max(-80, Math.min(80, (Math.atan(Math.exp(Y)) - Math.PI / 4) / 0.4 * 180 / Math.PI));
};
const mercYc = (lat) => {
  const t = Math.sin(lat * Math.PI / 180);
  return 0.5 - Math.log((1 + t) / (1 - t)) / (4 * Math.PI);
};

export class Renderer {
  constructor(canvas, tileBase) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl2', { antialias: false, premultipliedAlpha: false, preserveDrawingBuffer: true });
    if (!gl) throw new Error('WebGL2 is required');
    this.gl = gl;
    this.tileBase = tileBase;
    this.progTile = program(gl, VS_MESH, FS_TILE);
    this.meshBuf = gl.createBuffer();
    this.meshVao = gl.createVertexArray();
    gl.bindVertexArray(this.meshVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.meshBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 16, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 16, 8);
    gl.bindVertexArray(null);
    this.progMap = program(gl, VS, FS_MAP);
    const quad = new Float32Array([0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0]);
    // aPos (x,y), aUv: tile uv where v=0 is the image top
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      0, 0, 0, 0,
      1, 0, 1, 0,
      0, 1, 0, 1,
      1, 1, 1, 1,
    ]), gl.STATIC_DRAW);
    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 16, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 16, 8);
    void quad;
    this.tiles = new Map();
    this.terrainDirty = true;
    this.cam = { x: 0.5, y: 0.5, s: 4096 };
    this.dpr = 1;
    this.opts = { borders: true, fronts: true };
  }

  // ---------------------------------------------------------------- grid
  initGrid(W, H) {
    const gl = this.gl;
    this.gridW = W; this.gridH = H;
    const mk = (linear) => {
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, W, H);
      const f = linear ? gl.LINEAR : gl.NEAREST;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      return t;
    };
    this.texState = mk(false);
    this.texTime = mk(true);
    this.texPal = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.texPal);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, 256, 1);
    for (const p of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, p, gl.NEAREST);
    this.texWar = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.texWar);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.R8, 256, 256);
    for (const p of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, p, gl.NEAREST);
  }

  uploadGrid(state, time, rect) {
    const gl = this.gl, W = this.gridW;
    const r = rect || { x0: 0, y0: 0, x1: W - 1, y1: this.gridH - 1 };
    const w = r.x1 - r.x0 + 1, h = r.y1 - r.y0 + 1;
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.pixelStorei(gl.UNPACK_ROW_LENGTH, W);
    gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, r.x0);
    gl.pixelStorei(gl.UNPACK_SKIP_ROWS, r.y0);
    gl.bindTexture(gl.TEXTURE_2D, this.texState);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, r.x0, r.y0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, state);
    gl.bindTexture(gl.TEXTURE_2D, this.texTime);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, r.x0, r.y0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, time);
    gl.pixelStorei(gl.UNPACK_ROW_LENGTH, 0);
    gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, 0);
    gl.pixelStorei(gl.UNPACK_SKIP_ROWS, 0);
  }

  uploadPalette(rgba) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.texPal);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
  }

  uploadWar(m) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.texWar);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 256, 256, gl.RED, gl.UNSIGNED_BYTE, m);
  }

  // ---------------------------------------------------------------- camera
  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(this.canvas.clientWidth * dpr), h = Math.round(this.canvas.clientHeight * dpr);
    if (w !== this.canvas.width || h !== this.canvas.height || dpr !== this.dpr) {
      this.canvas.width = w; this.canvas.height = h; this.dpr = dpr;
      this._allocTerrain();
      this.terrainDirty = true;
    }
  }

  _allocTerrain() {
    const gl = this.gl;
    if (this.fbo) { gl.deleteFramebuffer(this.fbo); gl.deleteTexture(this.texTerrain); }
    this.texTerrain = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.texTerrain);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, this.canvas.width, this.canvas.height);
    for (const p of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, p, gl.NEAREST);
    this.fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.texTerrain, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  setCamera(c) { this.cam = { ...c }; this.terrainDirty = true; }

  // display world (x: mercator 0..1, y: Miller, same scale) -> screen px (device pixels)
  toScreen(wx, wy) {
    const c = this.cam, W = this.canvas.width, H = this.canvas.height, s = c.s * this.dpr;
    return [(wx - c.x) * s + W / 2, (wy - c.y) * s + H / 2];
  }

  // ---------------------------------------------------------------- tiles
  _tile(z, x, y) {
    const key = `${z}/${x}/${y}`;
    let t = this.tiles.get(key);
    if (t) { t.used = performance.now(); return t; }
    const gl = this.gl;
    t = { z, x, y, ready: 0, used: performance.now(), tex: [null, null] };
    this.tiles.set(key, t);
    const names = [`${this.tileBase}/${z}/${x}_${y}_s.jpg`, `${this.tileBase}/${z}/${x}_${y}_m.webp`];
    names.forEach((src, i) => {
      const img = new Image();
      img.decoding = 'async';
      img.onload = () => {
        const tex = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        t.tex[i] = tex;
        t.ready++;
        if (t.ready === 2) this.terrainDirty = true;
      };
      img.onerror = () => { t.failed = true; };
      img.src = src;
    });
    return t;
  }

  preload(zmax) {
    for (let z = GEO.zmin; z <= zmax; z++) {
      const r = GEO.tileRange(z);
      for (let x = r.x0; x <= r.x1; x++) for (let y = r.y0; y <= r.y1; y++) this._tile(z, x, y);
    }
  }

  _drawTerrain() {
    const gl = this.gl, W = this.canvas.width, H = this.canvas.height;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fbo);
    gl.viewport(0, 0, W, H);
    gl.clearColor(0.8, 0.0, 1.0, 0.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.progTile.p);
    gl.uniform1i(this.progTile.u.uShade, 0);
    gl.uniform1i(this.progTile.u.uMask, 1);
    const c = this.cam, s = c.s * this.dpr;
    const wx0 = c.x - W / 2 / s, wx1 = c.x + W / 2 / s;
    // visible Miller rows -> Mercator rows for tile selection
    const lat0 = invMillerLat(c.y - H / 2 / s), lat1 = invMillerLat(c.y + H / 2 / s);
    const my0 = mercYc(lat0), my1 = mercYc(lat1);
    // Mercator stretches by ~1.2 relative to Miller at these latitudes: pick tiles by the Mercator scale
    const want = Math.max(GEO.zmin, Math.min(GEO.zmax, Math.ceil(Math.log2(s * 1.2 / 256) - 0.35)));
    gl.bindVertexArray(this.meshVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.meshBuf);
    for (let z = GEO.zmin; z <= want; z++) {
      const n = 2 ** z, r = GEO.tileRange(z);
      const tx0 = Math.max(r.x0, Math.floor(wx0 * n)), tx1 = Math.min(r.x1, Math.floor(wx1 * n));
      const ty0 = Math.max(r.y0, Math.floor(my0 * n)), ty1 = Math.min(r.y1, Math.floor(my1 * n));
      const rows = z <= 4 ? 48 : 12;
      const v = new Float32Array((rows + 1) * 2 * 4);
      for (let x = tx0; x <= tx1; x++) for (let y = ty0; y <= ty1; y++) {
        const t = (z === want || z <= GEO.zmin + 1) ? this._tile(z, x, y) : this.tiles.get(`${z}/${x}/${y}`);
        if (!t || t.ready < 2) continue;
        for (let i = 0; i <= rows; i++) {
          const fv = i / rows, ny = millerY(invMercY((y + fv) / n));
          const [sx0, sy] = this.toScreen(x / n, ny);
          const [sx1] = this.toScreen((x + 1) / n, ny);
          const k = i * 8;
          v[k] = sx0 / W * 2 - 1; v[k + 1] = 1 - sy / H * 2; v[k + 2] = 0; v[k + 3] = fv;
          v[k + 4] = sx1 / W * 2 - 1; v[k + 5] = 1 - sy / H * 2; v[k + 6] = 1; v[k + 7] = fv;
        }
        gl.bufferData(gl.ARRAY_BUFFER, v, gl.STREAM_DRAW);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, t.tex[0]);
        gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, t.tex[1]);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, (rows + 1) * 2);
      }
    }
    gl.bindVertexArray(this.vao);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this._evict();
  }

  _evict() {
    if (this.tiles.size < 700) return;
    const gl = this.gl;
    const arr = [...this.tiles.values()].filter((t) => t.z > GEO.zmin + 2).sort((a, b) => a.used - b.used);
    for (const t of arr.slice(0, 200)) {
      t.tex.forEach((x) => x && gl.deleteTexture(x));
      this.tiles.delete(`${t.z}/${t.x}/${t.y}`);
    }
  }

  // ---------------------------------------------------------------- frame
  draw(tn) {
    const gl = this.gl, W = this.canvas.width, H = this.canvas.height;
    if (this.terrainDirty) { this.terrainDirty = false; this._drawTerrain(); }
    gl.viewport(0, 0, W, H);
    gl.useProgram(this.progMap.p);
    const u = this.progMap.u;
    const c = this.cam, s = c.s * this.dpr;
    const wx0 = c.x - W / 2 / s, wy0 = c.y - H / 2 / s;
    const gsx = this.gridW / (GEO.MX1 - GEO.MX0), gsy = this.gridH / (GEO.MY1 - GEO.MY0);
    gl.uniform2f(u.uRes, W, H);
    gl.uniform2f(u.uGridSize, this.gridW, this.gridH);
    gl.uniform2f(u.uW0, wx0, wy0);
    gl.uniform2f(u.uWs, 1 / s, 1 / s);
    gl.uniform2f(u.uM0, GEO.MX0, GEO.MY0);
    gl.uniform2f(u.uGsc, gsx, gsy);
    // per-row grid y (Miller display row -> latitude -> Mercator grid row)
    const rowKey = `${c.y},${s},${H}`;
    if (rowKey !== this.rowKey) {
      this.rowKey = rowKey;
      const rows = new Float32Array(H);
      for (let j = 0; j < H; j++) {
        const lat = invMillerLat(wy0 + (j + 0.5) / s);
        rows[j] = (mercYc(lat) - GEO.MY0) * gsy;
      }
      if (!this.texRow || this.texRowH !== H) {
        if (this.texRow) gl.deleteTexture(this.texRow);
        this.texRow = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, this.texRow);
        gl.texStorage2D(gl.TEXTURE_2D, 1, gl.R32F, H, 1);
        for (const p of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, p, gl.NEAREST);
        this.texRowH = H;
      }
      gl.bindTexture(gl.TEXTURE_2D, this.texRow);
      gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, H, 1, gl.RED, gl.FLOAT, rows);
    }
    gl.uniform1f(u.uTn, tn);
    gl.uniform1f(u.uPx, this.dpr);
    gl.uniform1f(u.uBorders, this.opts.borders ? 1 : 0);
    gl.uniform1f(u.uFronts, this.opts.fronts ? 1 : 0);
    const bind = (unit, tex, name) => { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(u[name], unit); };
    bind(0, this.texTerrain, 'uTerrain');
    bind(1, this.texState, 'uState');
    bind(2, this.texTime, 'uTime');
    bind(3, this.texPal, 'uPal');
    bind(4, this.texWar, 'uWar');
    bind(5, this.texRow, 'uRowY');
    gl.uniform4f(u.uRect, -1, -1, 1, 1);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
}
