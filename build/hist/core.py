"""Raster toolkit used to author the historical territorial states.

All territorial state lives on one Web Mercator grid (geo.GRID_W x
geo.GRID_H cells, about 1.7 km at 50N). Polygons are authored in
(lat, lon) order and rasterised with PIL.

Building blocks
  W.unit(code)            modern Natural Earth admin-0 unit mask
  W.prov(code, name)      modern Natural Earth admin-1 unit mask
  W.poly(points)          mask of a polygon (lat, lon) ring, holes allowed
  W.lake/W.land           1939 land mask on the grid
  river(name, a, b)       points following a Natural Earth river between a and b
  path(...)               concatenates points and river runs into one polyline
"""
import heapq
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape, box, Polygon, MultiPolygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import geo  # noqa: E402

CACHE = os.path.join(os.path.dirname(HERE), "cache")
NE = os.path.join(CACHE, "ne")
GW, GH = geo.GRID_W, geo.GRID_H
CLIP = box(geo.LON_W - 3, geo.LAT_S - 3, geo.LON_E + 3, geo.LAT_N + 2)


def to_grid(lat, lon):
    gx, gy = geo.lonlat_to_grid(lon, lat)
    return gx, gy


def _polys(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += _polys(x)
        return out
    return []


def _draw_geom(draw, g, value, ss=1):
    for p in _polys(g):
        ext = [tuple(c * ss for c in geo.lonlat_to_grid(x, y)) for x, y in p.exterior.coords]
        if len(ext) >= 3:
            draw.polygon(ext, fill=value)
        for h in p.interiors:
            hc = [tuple(c * ss for c in geo.lonlat_to_grid(x, y)) for x, y in h.coords]
            if len(hc) >= 3:
                draw.polygon(hc, fill=0)


def _load(name):
    with open(os.path.join(NE, name + ".geojson")) as f:
        return json.load(f)["features"]


class World:
    """Static rasters shared by every authoring module."""

    def __init__(self):
        cache = os.path.join(CACHE, "world_rasters.npz")
        if os.path.exists(cache):
            z = np.load(cache, allow_pickle=True)
            self.land = z["land"]
            self.adm0 = z["adm0"]
            self.adm1 = z["adm1"]
            self.adm0_codes = list(z["adm0_codes"])
            self.adm1_keys = [tuple(k) for k in z["adm1_keys"]]
        else:
            self._build()
            np.savez_compressed(cache, land=self.land, adm0=self.adm0, adm1=self.adm1,
                                adm0_codes=np.array(self.adm0_codes, dtype=object),
                                adm1_keys=np.array(self.adm1_keys, dtype=object))
        self.adm0_index = {c: i for i, c in enumerate(self.adm0_codes)}
        self.adm1_index = {k: i for i, k in enumerate(self.adm1_keys)}
        self._rivers = None

    # ---------------------------------------------------------------- build
    def _build(self):
        print("building world rasters", file=sys.stderr)
        ss = 2
        img = Image.new("L", (GW * ss, GH * ss), 0)
        d = ImageDraw.Draw(img)
        for name in ("ne_10m_land", "ne_10m_minor_islands"):
            for ft in _load(name):
                g = shape(ft["geometry"])
                if g.intersects(CLIP):
                    _draw_geom(d, g.intersection(CLIP), 255, ss)
        sys.path.insert(0, os.path.dirname(HERE))
        from build_basemap import POST_WAR_RESERVOIRS, POST_WAR_UNNAMED, FLEVOLAND
        for name in ("ne_10m_lakes", "ne_10m_lakes_europe"):
            for ft in _load(name):
                g = shape(ft["geometry"])
                nm = ft["properties"].get("name") or ""
                if not g.intersects(CLIP) or nm in POST_WAR_RESERVOIRS:
                    continue
                c = g.centroid
                if any(abs(c.x - x) < 0.15 and abs(c.y - y) < 0.15 for x, y in POST_WAR_UNNAMED):
                    continue
                _draw_geom(d, g, 0, ss)
        _draw_geom(d, FLEVOLAND, 0, ss)
        a = np.asarray(img.resize((GW, GH), Image.BOX))
        self.land = a >= 64  # >= 25 % land

        img = Image.new("I", (GW, GH), 0)
        d = ImageDraw.Draw(img)
        self.adm0_codes = [""]
        for ft in _load("ne_10m_admin_0_countries"):
            g = shape(ft["geometry"])
            if not g.intersects(CLIP):
                continue
            code = ft["properties"]["ADM0_A3"]
            self.adm0_codes.append(code)
            _draw_geom(d, g.intersection(CLIP), len(self.adm0_codes) - 1)
        self.adm0 = np.asarray(img, dtype=np.int32).astype(np.uint8)

        img = Image.new("I", (GW, GH), 0)
        d = ImageDraw.Draw(img)
        self.adm1_keys = [("", "")]
        for ft in _load("ne_10m_admin_1_states_provinces"):
            g = shape(ft["geometry"])
            if not g.intersects(CLIP):
                continue
            p = ft["properties"]
            self.adm1_keys.append((p["adm0_a3"], p["name"] or ""))
            _draw_geom(d, g.intersection(CLIP), len(self.adm1_keys) - 1)
        self.adm1 = np.asarray(img, dtype=np.int32).astype(np.uint16)

    # ---------------------------------------------------------------- masks
    def unit(self, *codes):
        m = np.zeros((GH, GW), bool)
        for c in codes:
            m |= self.adm0 == self.adm0_index[c]
        return m

    def prov(self, code, *names):
        m = np.zeros((GH, GW), bool)
        for n in names:
            k = (code, n)
            if k not in self.adm1_index:
                raise KeyError(f"admin-1 unit not found: {k}")
            m |= self.adm1 == self.adm1_index[k]
        return m

    def poly(self, *rings):
        """Mask of polygon(s). Each ring is a list of (lat, lon). The first ring
        of each call is filled, later rings are holes."""
        img = Image.new("L", (GW, GH), 0)
        d = ImageDraw.Draw(img)
        for i, ring in enumerate(rings):
            pts = [to_grid(lat, lon)[::1] for lat, lon in ring]
            pts = [(x, y) for x, y in pts]
            if len(pts) >= 3:
                d.polygon(pts, fill=255 if i == 0 else 0)
        return np.asarray(img) > 127

    def polys(self, *polys):
        m = np.zeros((GH, GW), bool)
        for p in polys:
            m |= self.poly(*p) if isinstance(p[0][0], (list, tuple)) else self.poly(p)
        return m

    # ---------------------------------------------------------------- rivers
    def rivers(self):
        if self._rivers is None:
            self._rivers = {}
            for name in ("ne_10m_rivers_europe", "ne_10m_rivers_lake_centerlines"):
                for ft in _load(name):
                    if not ft["geometry"]:
                        continue
                    nm = ft["properties"].get("name") or ft["properties"].get("name_en")
                    if not nm:
                        continue
                    g = shape(ft["geometry"])
                    if not g.intersects(CLIP):
                        continue
                    lines = list(g.geoms) if hasattr(g, "geoms") else [g]
                    self._rivers.setdefault(nm, []).extend([list(l.coords) for l in lines])
        return self._rivers


_W = None


def world():
    global _W
    if _W is None:
        _W = World()
    return _W


def _dist(a, b):
    # equirectangular km
    dx = (a[0] - b[0]) * 111.3 * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = (a[1] - b[1]) * 111.3
    return math.hypot(dx, dy)


def river(names, a, b):
    """Points (lat, lon) along the named river(s) from near a to near b.
    a and b are (lat, lon). Several names may be given for rivers whose
    Natural Earth parts carry different names (e.g. 'Dnepr', 'Dnipro')."""
    if isinstance(names, str):
        names = [names]
    R = world().rivers()
    nodes = {}
    adj = {}

    def nid(p):
        k = (round(p[0], 4), round(p[1], 4))
        if k not in nodes:
            nodes[k] = k
            adj[k] = []
        return k

    for n in names:
        for line in R.get(n, []):
            prev = None
            for p in line:
                k = nid(p)
                if prev is not None and prev != k:
                    w = _dist(prev, k)
                    adj[prev].append((k, w))
                    adj[k].append((prev, w))
                prev = k
    if not nodes:
        raise KeyError(f"river not found: {names}")
    keys = list(nodes)
    # join near-coincident endpoints of separate parts
    arr = np.array(keys)
    deg = {k: len(v) for k, v in adj.items()}
    ends = [k for k in keys if deg[k] <= 1]
    for e in ends:
        d = np.hypot((arr[:, 0] - e[0]) * math.cos(math.radians(e[1])), arr[:, 1] - e[1])
        for j in np.argsort(d)[1:4]:
            if d[j] < 0.03 and keys[j] != e:
                w = _dist(e, keys[j])
                adj[e].append((keys[j], w))
                adj[keys[j]].append((e, w))

    def nearest(latlon):
        lon, lat = latlon[1], latlon[0]
        d = np.hypot((arr[:, 0] - lon) * math.cos(math.radians(lat)), arr[:, 1] - lat)
        return keys[int(np.argmin(d))]

    s, t = nearest(a), nearest(b)
    dist = {s: 0}
    prev = {}
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if t not in dist:
        raise ValueError(f"no river path {names} {a} -> {b}")
    out = [t]
    while out[-1] != s:
        out.append(prev[out[-1]])
    out.reverse()
    return [(p[1], p[0]) for p in out]


def path(*parts):
    """Concatenate (lat, lon) points and lists of points into one polyline."""
    out = []
    for p in parts:
        if isinstance(p, tuple) and len(p) == 2 and isinstance(p[0], (int, float)):
            out.append(p)
        else:
            out.extend(list(p))
    # drop consecutive duplicates
    res = []
    for p in out:
        if not res or (abs(res[-1][0] - p[0]) > 1e-9 or abs(res[-1][1] - p[1]) > 1e-9):
            res.append(p)
    return res


def jitter(line, amp_km=2.5, seg_km=6.0, seed=0):
    """Deterministic fractal roughening of an authored front line so that
    fronts carry the irregular texture of real positions. Each segment is
    seeded from its endpoints so identical segments stay identical between
    keyframes (no flicker)."""
    out = [line[0]]
    for a, b in zip(line, line[1:]):
        L = _dist((a[1], a[0]), (b[1], b[0]))
        n = max(1, int(L / seg_km))
        h = hash((round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4), seed)) & 0xffffffff
        rng = np.random.default_rng(h)
        # perpendicular unit (in degrees, scaled for latitude)
        kx = math.cos(math.radians((a[0] + b[0]) / 2))
        dx, dy = (b[1] - a[1]) * kx, (b[0] - a[0])
        ln = math.hypot(dx, dy) or 1
        px, py = -dy / ln, dx / ln
        # 1/f noise along the segment, zero at both ends
        k = np.arange(1, n)
        noise = np.zeros(n + 1)
        for octave, amp in ((1, 1.0), (2, 0.55), (4, 0.3), (8, 0.18)):
            phase = rng.uniform(0, 2 * math.pi)
            noise += amp * np.sin(np.linspace(0, math.pi * octave, n + 1) + phase * (octave > 1)) * rng.uniform(-1, 1)
        noise[0] = noise[-1] = 0
        noise *= amp_km / 111.3
        for i in range(1, n + 1):
            t = i / n
            lat = a[0] + (b[0] - a[0]) * t + py * noise[i]
            lon = a[1] + (b[1] - a[1]) * t + px * noise[i] / kx
            out.append((lat, lon))
    return out
