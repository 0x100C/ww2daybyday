"""Download the open data the build needs into build/cache.

Sources
  * Natural Earth 1:10m vector layers (public domain), via the
    nvkelso/natural-earth-vector GitHub mirror.
  * Mapzen/AWS Terrain Tiles, terrarium encoding (open data registry on AWS),
    used for the hillshaded relief.

Run:  python3 build/fetch_sources.py
"""
import concurrent.futures as cf
import os
import sys
import urllib.request

import geo

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
NE_LAYERS = [
    "ne_10m_land", "ne_10m_lakes", "ne_10m_lakes_europe", "ne_10m_minor_islands",
    "ne_10m_rivers_lake_centerlines", "ne_10m_rivers_europe", "ne_10m_railroads",
    "ne_10m_roads", "ne_10m_urban_areas", "ne_10m_populated_places_simple",
    "ne_10m_glaciated_areas",
]
DEM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
DEM_Z = geo.TILE_ZMAX


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                f.write(r.read())
            os.replace(tmp, dest)
            return dest
        except Exception as e:  # network hiccup: retry
            err = e
    raise RuntimeError(f"failed {url}: {err}")


def main():
    jobs = []
    for n in NE_LAYERS:
        jobs.append((NE_URL.format(n), os.path.join(CACHE, "ne", n + ".geojson")))
    x0, x1, y0, y1 = geo.tile_range(DEM_Z)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            jobs.append((DEM_URL.format(z=DEM_Z, x=x, y=y),
                         os.path.join(CACHE, "dem", str(DEM_Z), f"{x}_{y}.png")))
    done = 0
    with cf.ThreadPoolExecutor(16) as ex:
        for _ in ex.map(lambda j: fetch(*j), jobs):
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(jobs)}", file=sys.stderr)
    print("ok", len(jobs), "files")


if __name__ == "__main__":
    main()
