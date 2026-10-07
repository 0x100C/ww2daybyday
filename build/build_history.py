"""Compile the historical territory stream.

    python3 build/build_history.py [--snap 1939-09-10,1939-09-20 ...]

Writes data/territory.bin (gzip) and data/meta.json.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "hist"))
sys.path.insert(0, os.path.join(HERE, "hist", "campaigns"))

import numpy as np  # noqa: E402

import political_1939  # noqa: E402
from core import world  # noqa: E402
from timeline import Timeline, T, date_str  # noqa: E402
from compiler import compile_timeline, write_stream  # noqa: E402
from units import UNITS  # noqa: E402
import campaigns_index  # noqa: E402

OUT = os.path.join(HERE, "..", "data")


def main():
    def export_fronts(tl):
        """Front key lines for troop labels that follow the fronts: each key is
        resampled to 48 points by arc length so the runtime can interpolate
        between keys point by point; 'ws' is +1 when side W lies to the right
        of the line's direction at its midpoint, -1 when to the left."""
        import numpy as np
        from shapely.geometry import Point, Polygon
        out = {}
        for F in getattr(tl, "fronts", []):
            keys = []
            for date, line, cw in sorted(F.lines, key=lambda k: T(k[0])):
                a = np.array([(lo * np.cos(np.radians(la)), la) for la, lo in line])
                seg = np.r_[0, np.cumsum(np.hypot(*np.diff(a, axis=0).T))]
                if seg[-1] <= 0:
                    continue
                s = np.linspace(0, seg[-1], 48)
                lat = np.interp(s, seg, [p[0] for p in line])
                lon = np.interp(s, seg, [p[1] for p in line])
                i = 24
                dx = (lon[i + 1] - lon[i - 1]) * np.cos(np.radians(lat[i])); dy = lat[i + 1] - lat[i - 1]
                n = np.hypot(dx, dy) or 1.0
                rx, ry = dy / n, -dx / n                       # right-hand normal (east-ish, north)
                probe = Point(lon[i] + 0.3 * rx / np.cos(np.radians(lat[i])), lat[i] + 0.3 * ry)
                try:
                    ring = Polygon([(lo, la) for la, lo in list(line) + list(cw)]).buffer(0)
                    ws = 1 if ring.contains(probe) else -1
                except Exception:
                    ws = 1
                keys.append([round(T(date), 4), ws, [[round(float(x), 3), round(float(y), 3)] for x, y in zip(lat, lon)]])
            end = [k[0] for k in F.Lw.sorted_keys() if k[1] is None]
            out[F.name] = {"w": F.w, "e": F.e, "end": end[-1] if end else None, "keys": keys}
        return out

    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default="")
    ap.add_argument("--snapdir", default=os.path.join(HERE, "cache", "snaps"))
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    t0 = time.time()
    W = world()
    base = political_1939.fill_coast(political_1939.build(), W.land)
    tl = Timeline(base)
    campaigns_index.build_all(tl, only=args.only.split(",") if args.only else None)
    snaps = [T(s) for s in args.snap.split(",") if s]
    print(f"timeline: {len(tl.layers)} layers, {len(tl.ops)} political ops", file=sys.stderr)
    bc, bk, groups, snapd, t_end = compile_timeline(tl, checkpoints=snaps)
    os.makedirs(OUT, exist_ok=True)
    n = write_stream(os.path.join(OUT, "territory.bin"), bc, bk, groups, t_end)
    meta = {
        "epoch": "1939-09-01T00:00:00Z",
        "tEnd": t_end,
        "grid": {"w": int(bc.shape[1]), "h": int(bc.shape[0])},
        "units": [{"id": u["id"], "code": u["code"], "name": u["name"], "kind": u["kind"],
                   "factions": u["factions"]} for u in UNITS],
        "captions": [{"t": t, "text": s} for t, s in sorted(tl.notes)],
        "labels": tl.labels,
        "fronts": export_fronts(tl),
    }
    with open(os.path.join(OUT, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=0)
    print(f"groups {len(groups)}  cells {sum(g.idx.size for g in groups)}  raw {n/1e6:.1f} MB  "
          f"gz {os.path.getsize(os.path.join(OUT, 'territory.bin'))/1e6:.1f} MB  {time.time()-t0:.0f}s",
          file=sys.stderr)
    if snapd:
        os.makedirs(args.snapdir, exist_ok=True)
        for t, (c, k) in snapd.items():
            np.save(os.path.join(args.snapdir, f"c_{date_str(t)}.npy"), c)
            np.save(os.path.join(args.snapdir, f"k_{date_str(t)}.npy"), k)


if __name__ == "__main__":
    main()
