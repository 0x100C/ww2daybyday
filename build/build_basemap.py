"""Build the basemap tile pyramid.

Every tile is split in two images so that the runtime shader can colour land
by its controller while keeping the terrain stable:

  {z}/{x}_{y}_s.jpg   grayscale terrain lightness (hillshade, mottling, snow)
  {z}/{x}_{y}_m.webp  lossless RGB masks
                       R = ink (built-up areas, roads, railways)
                       G = water coverage (sea, 1939 lakes), anti-aliased
                       B = snow / glacier brightness

Historical corrections to the modern Natural Earth geography:
  * reservoirs created after 1945 (Dnieper cascade, Volga cascade,
    Tsimlyansk, Ataturk ...) are removed, so the 1939 rivers show as land;
  * Flevoland (drained 1957 to 1968) is put back under the IJsselmeer.

Run:  python3 build/build_basemap.py  (after fetch_sources.py)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from shapely.geometry import box, shape, Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import unary_union

import geo

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(HERE, "..", "data", "tiles")
NE = os.path.join(CACHE, "ne")

POST_WAR_RESERVOIRS = {
    "Ataturk Barajt", "Buhayrat al-Assad", "Buhayrat ath Tharthar", "Cheboksary Reservoir",
    "Gorky Reservoir", "Kakhovka Reservoir", "Kama Reservoir", "Keban Baraji", "Kiev Reservoir",
    "Kostroma Reservoir", "Krasnodarsk Reservoir", "Kremenchuk Reservoir", "Mingevir Reservoir",
    "Nizhnekamsk Reservoir", "Rybinsk Reservoir", "Samara Reservoir", "Saratov Reservoir",
    "Saksak Dagi", "Sheksinskoe Reservoir", "Tsimlyansk Reservoir", "Volgograd Reservoir",
    "Votkinsk Reservoir", "Lokan Tekojarvi", "Porttipahta Reservoir", "Serebryanskoe Reservoir",
    "Sarygamysh Köli", "Qadisiyah",
}
# Unnamed post-war reservoirs (centroid lon, lat): Kamianske and Kaniv on the Dnieper.
POST_WAR_UNNAMED = [(34.1, 48.8), (31.5, 49.9)]

# Flevoland, still open water of the IJsselmeer in 1939-45 (approximate outline).
FLEVOLAND = Polygon([
    (5.09, 52.33), (5.17, 52.31), (5.28, 52.30), (5.42, 52.27), (5.53, 52.29), (5.62, 52.35),
    (5.72, 52.39), (5.82, 52.44), (5.87, 52.50), (5.80, 52.56), (5.70, 52.59), (5.58, 52.60),
    (5.50, 52.57), (5.43, 52.53), (5.36, 52.48), (5.28, 52.44), (5.19, 52.40), (5.12, 52.37),
])

CLIP = box(geo.LON_W - 2, geo.LAT_S - 2, geo.LON_E + 2, geo.LAT_N + 1)


def load(name):
    with open(os.path.join(NE, name + ".geojson")) as f:
        return json.load(f)["features"]


def clipped(features, pred=lambda p: True):
    out = []
    for ft in features:
        if not pred(ft["properties"]):
            continue
        g = shape(ft["geometry"])
        if not g.intersects(CLIP):
            continue
        g = g.intersection(CLIP)
        if not g.is_empty:
            out.append((ft["properties"], g))
    return out


def polys(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        r = []
        for x in g.geoms:
            r += polys(x)
        return r
    return []


def lines(g):
    if isinstance(g, LineString):
        return [g]
    if isinstance(g, MultiLineString):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        r = []
        for x in g.geoms:
            r += lines(x)
        return r
    return []


class Zoom:
    def __init__(self, z, ss=1):
        self.z = z
        self.ss = ss
        self.x0, self.x1, self.y0, self.y1 = geo.tile_range(z)
        self.W = (self.x1 - self.x0 + 1) * geo.TILE
        self.H = (self.y1 - self.y0 + 1) * geo.TILE
        self.scale = geo.TILE * 2 ** z

    def proj(self, coords):
        s = self.scale * self.ss
        ox = self.x0 * geo.TILE * self.ss
        oy = self.y0 * geo.TILE * self.ss
        return [(geo.merc_x(x) * s - ox, geo.merc_y(y) * s - oy) for x, y in coords]


def raster_polys(zm, geoms, value=255):
    img = Image.new("L", (zm.W * zm.ss, zm.H * zm.ss), 0)
    d = ImageDraw.Draw(img)
    for g in geoms:
        for p in polys(g):
            ext = zm.proj(p.exterior.coords)
            if len(ext) >= 3:
                d.polygon(ext, fill=value)
            for h in p.interiors:
                hc = zm.proj(h.coords)
                if len(hc) >= 3:
                    d.polygon(hc, fill=0)
    if zm.ss > 1:
        img = img.resize((zm.W, zm.H), Image.BOX)
    return np.asarray(img, dtype=np.float32) / 255.0


def raster_lines(zm, items, ss=2):
    """items: list of (geometry, width_px, value)."""
    img = Image.new("L", (zm.W * ss, zm.H * ss), 0)
    d = ImageDraw.Draw(img)
    s = zm.scale * ss
    ox, oy = zm.x0 * geo.TILE * ss, zm.y0 * geo.TILE * ss
    for g, w, v in items:
        for ln in lines(g):
            pts = [(geo.merc_x(x) * s - ox, geo.merc_y(y) * s - oy) for x, y in ln.coords]
            if len(pts) >= 2:
                d.line(pts, fill=int(v * 255), width=max(1, int(round(w * ss))), joint="curve")
    img = img.resize((zm.W, zm.H), Image.BOX)
    return np.asarray(img, dtype=np.float32) / 255.0


def load_dem():
    z = geo.TILE_ZMAX
    x0, x1, y0, y1 = geo.tile_range(z)
    H = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            p = os.path.join(CACHE, "dem", str(z), f"{x}_{y}.png")
            a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
            e = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
            H[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = e
    return H


def downsample(a, f):
    if f == 1:
        return a
    h, w = a.shape
    return a.reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def row_lats(zm):
    ys = (np.arange(zm.H) + 0.5 + zm.y0 * 256) / zm.scale
    return np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * ys))))


def hillshade(dem, zm):
    lat = row_lats(zm)
    cell = 40075016.686 / zm.scale * np.cos(np.radians(lat))[:, None]
    # Vertical exaggeration grows as we zoom out so relief stays legible.
    zf = 1.6 * 1.55 ** (geo.TILE_ZMAX - zm.z)
    e = ndimage.gaussian_filter(np.maximum(dem, 0), 1.1) * zf
    gy, gx = np.gradient(e)
    gx = gx / cell
    gy = gy / cell
    # surface normal; x east, y south (image rows), z up
    norm = np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx / norm, -gy / norm, 1 / norm

    def light(az, alt):
        az = math.radians(az)
        alt = math.radians(alt)
        lx = math.sin(az) * math.cos(alt)
        ly = -math.cos(az) * math.cos(alt)
        lz = math.sin(alt)
        return nx * lx + ny * ly + nz * lz

    hs = 0.65 * light(315, 40) + 0.35 * light(250, 55)
    flat = 0.65 * math.sin(math.radians(40)) + 0.35 * math.sin(math.radians(55))
    return hs - flat


def fbm_noise(h, w, seed, scales):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp_total = 0
    for sc, amp in scales:
        sh = max(2, h // sc + 2)
        sw = max(2, w // sc + 2)
        n = rng.standard_normal((sh, sw)).astype(np.float32)
        n = ndimage.zoom(n, (h / (sh - 1) * 1.0001, w / (sw - 1) * 1.0001), order=3)[:h, :w]
        out += n * amp
        amp_total += amp
    return out / amp_total


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    zmin = int(sys.argv[1]) if len(sys.argv) > 1 else geo.TILE_ZMIN
    zmax = int(sys.argv[2]) if len(sys.argv) > 2 else geo.TILE_ZMAX
    print("loading vectors", flush=True)
    land = [g for _, g in clipped(load("ne_10m_land"))]
    land += [g for _, g in clipped(load("ne_10m_minor_islands"))]
    lakes = []
    for name in ("ne_10m_lakes", "ne_10m_lakes_europe"):
        for p, g in clipped(load(name)):
            nm = p.get("name") or ""
            if nm in POST_WAR_RESERVOIRS:
                continue
            c = g.centroid
            if any(abs(c.x - x) < 0.15 and abs(c.y - y) < 0.15 for x, y in POST_WAR_UNNAMED):
                continue
            lakes.append(g)
    lakes.append(FLEVOLAND)
    urban = [(p, g) for p, g in clipped(load("ne_10m_urban_areas"))]
    rails = clipped(load("ne_10m_railroads"))
    roads = clipped(load("ne_10m_roads"), lambda p: p.get("type") in ("Major Highway", "Secondary Highway", "Road"))
    glaciers = [g for _, g in clipped(load("ne_10m_glaciated_areas"))]
    places = [(p, g) for p, g in clipped(load("ne_10m_populated_places_simple"))]

    print("loading dem", flush=True)
    dem7 = load_dem()

    for z in range(zmin, zmax + 1):
        zm = Zoom(z, ss=2 if z >= 5 else 4)
        print("zoom", z, zm.W, zm.H, flush=True)
        f = 2 ** (geo.TILE_ZMAX - z)
        d7 = downsample(dem7, f)
        x70, _, y70, _ = geo.tile_range(geo.TILE_ZMAX)
        ox = x70 * 256 // f - zm.x0 * 256
        oy = y70 * 256 // f - zm.y0 * 256
        dem = np.zeros((zm.H, zm.W), np.float32)
        dem[oy:oy + d7.shape[0], ox:ox + d7.shape[1]] = d7
        landm = raster_polys(zm, land)
        lakem = raster_polys(zm, lakes)
        water = np.clip(1 - landm + lakem, 0, 1)
        if z >= 6:
            # NE land at 1:10m misses some tiny islets; keep the mask crisp.
            water = ndimage.gaussian_filter(water, 0.35)

        # --- terrain lightness ---
        hs = hillshade(dem, zm)
        lat = row_lats(zm)[:, None]
        noise = fbm_noise(zm.H, zm.W, 7 + z, [(int(160 / f) + 4, 1.0), (int(40 / f) + 3, 0.6), (int(10 / f) + 2, 0.35)])
        L = 0.82 + 1.25 * hs + 0.018 * noise
        # gentle darkening of lowlands vs plateaus so plains are not flat
        L += 0.03 * smoothstep(200, 1200, dem)
        # --- snow ---
        snowline = 2350 - (np.clip(lat, 30, 75) - 45) * 80
        snow = smoothstep(snowline - 500, snowline + 700, dem)
        glac = raster_polys(Zoom(z, ss=1), glaciers)
        snow = np.clip(np.maximum(snow * 0.85, glac), 0, 1)
        L = L + snow * 0.05
        L = np.clip(L, 0.42, 1.0)

        # --- ink: built-up areas, roads, railways ---
        road_max = {3: 2, 4: 3, 5: 4, 6: 6, 7: 8}[z]
        rail_max = {3: 3, 4: 4, 5: 5, 6: 7, 7: 9}[z]
        w = {3: 0.55, 4: 0.6, 5: 0.7, 6: 0.85, 7: 1.0}[z]
        items = []
        for p, g in roads:
            if (p.get("scalerank") or 10) <= road_max:
                items.append((g, w, 0.55))
        for p, g in rails:
            if (p.get("scalerank") or 10) <= rail_max:
                items.append((g, w, 0.45))
        ink = raster_lines(zm, items, ss=4 if z <= 5 else 2)
        urb_geoms = [g for p, g in urban if (p.get("scalerank") or 10) <= {3: 5, 4: 6, 5: 8, 6: 9, 7: 10}[z]]
        urb = raster_polys(Zoom(z, ss=2), urb_geoms)
        urb = ndimage.gaussian_filter(urb, 0.6)
        # city cores: darker blot at populated places, sized by population
        cores = Image.new("L", (zm.W, zm.H), 0)
        d = ImageDraw.Draw(cores)
        for p, g in places:
            pop = p.get("pop_max") or 0
            if pop < {3: 900000, 4: 400000, 5: 150000, 6: 60000, 7: 20000}[z]:
                continue
            (x, y), = Zoom(z).proj([(g.x, g.y)])
            r = max(0.7, (pop / 1e6) ** 0.35 * 2 ** (z - 5) * 1.3)
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        cores = ndimage.gaussian_filter(np.asarray(cores, np.float32) / 255, 0.7)
        ink = np.clip(np.maximum(ink, urb * 0.62) + cores * 0.35, 0, 1)
        ink *= (1 - water)
        # coastline: thin anti-aliased line on the land/water boundary (both sides)
        gy_, gx_ = np.gradient(ndimage.gaussian_filter(water, 0.5))
        coast = np.clip(np.hypot(gx_, gy_) * 2.2, 0, 1) ** 0.8
        ink = np.maximum(ink, coast * 0.62)

        # --- write tiles ---
        Lq = (L * 255 + 0.5).astype(np.uint8)
        M = np.stack([(ink * 255 + 0.5).astype(np.uint8),
                      (water * 255 + 0.5).astype(np.uint8),
                      (snow * (1 - water) * 255 + 0.5).astype(np.uint8)], -1)
        d = os.path.join(OUT, str(z))
        os.makedirs(d, exist_ok=True)
        for tx in range(zm.x0, zm.x1 + 1):
            for ty in range(zm.y0, zm.y1 + 1):
                sx = (tx - zm.x0) * 256
                sy = (ty - zm.y0) * 256
                m = M[sy:sy + 256, sx:sx + 256]
                s = Lq[sy:sy + 256, sx:sx + 256]
                Image.fromarray(s, "L").save(os.path.join(d, f"{tx}_{ty}_s.jpg"), quality=82)
                Image.fromarray(m, "RGB").save(os.path.join(d, f"{tx}_{ty}_m.webp"), lossless=True, quality=60, method=4)
    print("done")


if __name__ == "__main__":
    main()
