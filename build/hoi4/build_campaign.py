"""Build a replay of a HOI4 campaign for the WW2 Day by Day map.

    python3 build/hoi4/build_campaign.py <game.log> <hoi4_states.json> [out_dir]

Inputs
  game.log          written by the WW2DBD logger mod
  hoi4_states.json  written by build/hoi4/extract_states.mjs from your HOI4 install

Output (default data/hoi4/) - the same files the historical map uses, plus one:
  meta.json         epoch, units (one per country tag, with faction timeline), wars, captions
  territory.bin     who controls every map cell over time (state control changes become
                    smooth advances; same format and runtime as the historical map)
  campaign.json     events with map positions, division/army markers per 3-day snapshot,
                    state positions, country names

How HOI4 states are placed on the map
  * Longitude is linear in the HOI4 map's x; latitude is a Mercator-style function of y.
    Both are fitted on country capitals whose real positions are known (outliers dropped).
  * With the 0.2 states file (grid of state ids) each map cell takes its state from the grid.
    With the 0.1 file (centres only) cells take the nearest state centre (rougher shapes).
"""
import base64
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "hist"))

import geo  # noqa: E402
import import_log  # noqa: E402
from compiler import Group, sweep_fracs, write_stream  # noqa: E402
from core import world  # noqa: E402

# capital cities (lat, lon) of HOI4 tags, used to fit the HOI4 map to the real world
ANCHORS = {
    "GER": (52.52, 13.40), "ENG": (51.51, -0.13), "FRA": (48.86, 2.35), "SOV": (55.75, 37.62), "POL": (52.23, 21.01),
    "ITA": (41.90, 12.50), "SPR": (40.42, -3.70), "TUR": (39.93, 32.86), "ROM": (44.43, 26.10), "HUN": (47.50, 19.04),
    "GRE": (37.98, 23.73), "YUG": (44.80, 20.46), "BUL": (42.70, 23.32), "FIN": (60.17, 24.94), "SWE": (59.33, 18.07),
    "NOR": (59.91, 10.75), "DEN": (55.68, 12.57), "HOL": (52.37, 4.90), "BEL": (50.85, 4.35), "SWI": (46.95, 7.45),
    "EGY": (30.04, 31.24), "IRQ": (33.31, 44.37), "PER": (35.69, 51.39), "POR": (38.72, -9.14), "IRE": (53.35, -6.26),
    "ALB": (41.33, 19.82), "AFG": (34.53, 69.17), "LIT": (54.69, 25.28), "LAT": (56.95, 24.11), "EST": (59.44, 24.75),
    "CZE": (50.08, 14.44), "AUS": (48.21, 16.37), "SAU": (24.71, 46.68),
}
# colour class of a faction by its leader (colours come from js/factions.js)
LEADER_CLASS = {"GER": "axis", "JAP": "axis", "ITA": "axis", "ENG": "allied", "FRA": "allied", "USA": "allied",
                "SOV": "soviet", "CHI": "allied_c"}


def merc(lat):
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def inv_merc(m):
    return np.degrees(2 * np.arctan(np.exp(m)) - np.pi / 2)


def calibrate(st):
    """lon = ax*x + bx ; merc(lat) = ay*y + by, fitted robustly on capitals."""
    S, C = st["states"], st["capitals"]
    tags = [t for t in ANCHORS if str(C.get(t)) in S]
    x = np.array([S[str(C[t])]["x"] for t in tags]); y = np.array([S[str(C[t])]["y"] for t in tags])
    lat = np.array([ANCHORS[t][0] for t in tags]); lon = np.array([ANCHORS[t][1] for t in tags])
    ok = np.ones(len(tags), bool)
    for _ in range(5):
        cx = np.polyfit(x[ok], lon[ok], 1)
        cy = np.polyfit(y[ok], merc(lat[ok]), 1)
        ex = np.polyval(cx, x) - lon
        ey = inv_merc(np.polyval(cy, y)) - lat
        thr = max(1.5, 2.5 * np.median(np.hypot(ex[ok], ey[ok])))
        ok = np.hypot(ex, ey) < thr
    err_km = np.hypot(ex * 111 * np.cos(np.radians(lat)), ey * 111)
    print(f"calibration: {ok.sum()}/{len(tags)} anchors, median error {np.median(err_km[ok]):.0f} km, max {err_km[ok].max():.0f} km")
    return {"lon": [float(cx[0]), float(cx[1])], "mlat": [float(cy[0]), float(cy[1])], "anchors": int(ok.sum()),
            "median_km": float(np.median(err_km[ok]))}


def px_to_lonlat(cal, x, y):
    return cal["lon"][0] * x + cal["lon"][1], float(inv_merc(cal["mlat"][0] * y + cal["mlat"][1]))


def smooth_states(arr, scale, hx, hy, sigma=1.2, floor=0.35):
    """Round the 4x4-pixel stair steps of the state grid. Each state's indicator is blurred and every
    map cell takes the state with the strongest blurred value (so borders between states stay shared
    and gap-free, and coasts barely move). Cells no state reaches are left 0 and filled afterwards."""
    h, w = arr.shape
    H, W = len(hy), len(hx)
    gxf = hx / scale - 0.5
    gyf = hy / scale - 0.5
    best = np.full((H, W), floor, np.float32)
    out = np.zeros((H, W), np.uint16)
    objs = ndimage.find_objects(arr)
    rng = np.random.default_rng(7)
    def field(step, sg):                                         # smooth noise on a coarse lattice, roughly -1..1
        f = ndimage.gaussian_filter(rng.standard_normal((h // step + 3, w // step + 3)).astype(np.float32), sg)
        return f / (np.percentile(np.abs(f), 99) + 1e-6), step
    warps = [field(9, 1.2), field(3, 1.0)]                       # ~35 km wobble and ~12 km ruggedness (HOI4 grid cells)
    amps = [1.1, 0.35]
    def warp(gy, gx):
        dy = np.zeros_like(gy); dx = np.zeros_like(gx)
        for (f, st), a in zip(warps, amps):
            dy += a * ndimage.map_coordinates(f, [gy / st, gx / st], order=1, mode="nearest")
            dx += a * ndimage.map_coordinates(f, [(gy + 7.3) / st, (gx + 3.1) / st], order=1, mode="nearest")
        return gy + dy, gx + dx
    for k, sl in enumerate(objs):
        if sl is None:
            continue
        sid = k + 1
        y0, y1 = max(0, sl[0].start - 5), min(h, sl[0].stop + 5)
        x0, x1 = max(0, sl[1].start - 5), min(w, sl[1].stop + 5)
        sm = ndimage.gaussian_filter((arr[y0:y1, x0:x1] == sid).astype(np.float32), sigma, mode="constant")
        rows = np.nonzero((gyf >= y0) & (gyf <= y1 - 1))[0]
        cols = np.nonzero((gxf >= x0) & (gxf <= x1 - 1))[0]
        if rows.size == 0 or cols.size == 0:
            continue
        r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
        yy, xx = np.meshgrid(gyf[r0:r1] - y0, gxf[c0:c1] - x0, indexing="ij")
        v = ndimage.map_coordinates(sm, [yy, xx], order=1, mode="nearest")
        sub = best[r0:r1, c0:c1]
        m = v > sub
        best[r0:r1, c0:c1] = np.where(m, v, sub)
        out[r0:r1, c0:c1] = np.where(m, sid, out[r0:r1, c0:c1])
    return out


def cell_states(st, cal, land):
    """State id of every map cell (uint16 H x W)."""
    H, W = land.shape
    # grid cell centre -> lon/lat (separable)
    xs = geo.MX0 + (np.arange(W) + 0.5) / W * (geo.MX1 - geo.MX0)
    ys = geo.MY0 + (np.arange(H) + 0.5) / H * (geo.MY1 - geo.MY0)
    lon = xs * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * ys))))
    hx = (lon - cal["lon"][1]) / cal["lon"][0]                   # HOI4 pixel x per column
    hy = (merc(lat) - cal["mlat"][1]) / cal["mlat"][0]           # HOI4 pixel y per row
    if "grid" in st:
        g = st["grid"]
        arr = np.frombuffer(base64.b64decode(g["data"]), dtype="<u2").reshape(g["h"], g["w"]).astype(np.int32)
        out = smooth_states(arr, g["scale"], hx, hy)
        print("state shapes: from the grid in the states file, edges smoothed")
    else:
        from scipy.spatial import cKDTree
        ids = np.array([int(k) for k in st["states"]])
        pts = np.array([[v["x"], v["y"]] for v in st["states"].values()])
        tree = cKDTree(pts)
        out = np.zeros((H, W), np.uint16)
        for r0 in range(0, H, 256):
            r1 = min(H, r0 + 256)
            P = np.stack(np.broadcast_arrays(hx[None, :], hy[r0:r1, None]), -1).reshape(-1, 2)
            d, i = tree.query(P, distance_upper_bound=60)
            res = np.where(np.isfinite(d), ids[np.minimum(i, len(ids) - 1)], 0)
            out[r0:r1] = res.reshape(r1 - r0, W)
        print("state shapes: nearest state centre (rough - re-run extract_states.mjs for exact shapes)")
    # land cells without a state take the nearest state; sea cells stay 0
    hole = land & (out == 0)
    if hole.any() and (out > 0).any():
        idx = ndimage.distance_transform_edt(out == 0, return_distances=False, return_indices=True)
        out = np.where(hole, out[idx[0], idx[1]], out)
    return np.where(land, out, 0).astype(np.uint16)


def iso(day0, t):
    """ISO date string of the day t days after the epoch."""
    from datetime import timedelta
    return (day0 + timedelta(days=int(math.floor(t)))).strftime("%Y-%m-%d")


def compute_fronts(forces, base_ctl, adv_rec, wars, uid, spos, Wd, H, T, tags, land):
    """Frontline tracks. At every force snapshot: find the boundary cells between countries that are at war,
    group them into connected fronts, sum the troops each side keeps near that front, and follow each front
    from snapshot to snapshot. Troop figures are the log's lower bounds (men), not a count of the real army."""
    DS = 4
    tag_of = {v: k for k, v in uid.items()}
    gx0, gy0 = None, None
    def lonlat(cx, cy):
        return geo.grid_to_lonlat((cx * DS + DS / 2) * geo.GRID_W / Wd, (cy * DS + DS / 2) * geo.GRID_H / H)
    war_list = [(uid[a], uid[b], w0, w1) for a, b, w0, w1 in wars]
    def at_war(x, y, t):
        for a, b, t0, t1 in war_list:
            if ((a == x and b == y) or (a == y and b == x)) and t >= t0 and (t1 is None or t < t1):
                return True
        return False
    sid_ll = {int(k): v for k, v in spos.items()}
    sids = np.array(sorted(sid_ll)); sll = np.array([sid_ll[i] for i in sids])
    sids_idx = {int(i): k for k, i in enumerate(sids)}
    H4, W4 = H // DS, Wd // DS
    land4 = land[DS // 2::DS, DS // 2::DS][:H4, :W4]
    land_lab, _ = ndimage.label(land4, np.ones((3, 3)))          # separate landmasses: troops never count across water
    _, (near_y, near_x) = ndimage.distance_transform_edt(~land4, return_indices=True)
    def ds_cell(lon, lat):
        gx, gy = geo.lonlat_to_grid(lon, lat)
        cx = int(min(W4 - 1, max(0, gx / DS))); cy = int(min(H4 - 1, max(0, gy / DS)))
        return int(near_y[cy, cx]), int(near_x[cy, cx])
    pockets, open_pk = [], []
    tracks, open_tr = [], []
    flat_ctl = base_ctl.ravel().copy()
    adv_i = 0
    adv_sorted = sorted(range(len(adv_rec)), key=lambda i: adv_rec[i][2].min())
    for fs in forces:
        t = fs["t"]
        ctl = base_ctl.copy()
        for idx, new, arr in adv_rec:
            m = arr <= t
            if m.any():
                ctl.ravel()[idx[m]] = new
        d = ctl[DS // 2::DS, DS // 2::DS][:H4, :W4]
        # encirclements: a piece of a country at war that is entirely ringed by its enemies and cut off from its main body
        seen_pk = []
        for who in np.unique(d):
            who = int(who)
            if who == 0 or not any(at_war(who, o, t) for o in np.unique(d) if o):
                continue
            lab_c, n_c = ndimage.label(d == who, np.ones((3, 3)))
            if n_c < 2:
                continue
            sizes = np.bincount(lab_c.ravel())[1:]
            main = int(sizes.argmax()) + 1
            for c in range(1, n_c + 1):
                if c == main or sizes[c - 1] < 15:
                    continue
                cm_ = lab_c == c
                ring = ndimage.binary_dilation(cm_) & ~cm_
                nb = d[ring]; nb = nb[nb > 0]
                if len(nb) < 8:
                    continue
                if np.mean([at_war(who, int(x), t) for x in nb]) < 0.9:
                    continue
                ys_, xs_ = np.nonzero(cm_)
                k_ = np.argmin((ys_ - ys_.mean()) ** 2 + (xs_ - xs_.mean()) ** 2)
                men_in = 0
                for row in fs["r"]:
                    if row[0] == who and row[1] in sids_idx:
                        la, lo = sll[sids_idx[row[1]]][1], sll[sids_idx[row[1]]][0]
                        yy_, xx_ = ds_cell(lo, la)
                        if cm_[yy_, xx_]:
                            men_in += row[4]
                seen_pk.append((who, float(xs_[k_]), float(ys_[k_]), men_in))
        used_pk = set()
        for who, px_, py_, men_in in seen_pk:
            hit = None
            for pk in open_pk:
                if id(pk) not in used_pk and pk["who"] == who and math.hypot(pk["x"] - px_, pk["y"] - py_) < 22:
                    hit = pk; break
            if hit is None:
                hit = {"who": who, "t0": t, "n": 0, "men": 0}
                pockets.append(hit)
            hit.update(x=px_, y=py_, t1=t, men=max(hit["men"], men_in)); hit["n"] += 1
            hit["ll"] = lonlat(px_, py_)
            used_pk.add(id(hit))
        open_pk = [pk for pk in pockets if pk["t1"] == t]
        pts = {}
        for dy, dx in ((0, 1), (1, 0)):
            a = d[:H4 - dy, :W4 - dx]; b = d[dy:, dx:]
            diff = (a != b) & (a > 0) & (b > 0)
            ys, xs = np.nonzero(diff)
            for y, x in zip(ys, xs):
                u, v = int(a[y, x]), int(b[y, x])
                if u > v: u, v = v, u
                if at_war(u, v, t):
                    pts.setdefault((u, v), []).append((x + dx / 2, y + dy / 2))
        cur = []
        for (u, v), P in pts.items():
            P = np.array(P)
            m = np.zeros((H4, W4), bool); m[P[:, 1].astype(int), P[:, 0].astype(int)] = True
            lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=7), np.ones((3, 3)))
            lp = lab[P[:, 1].astype(int), P[:, 0].astype(int)]
            for c in range(1, n + 1):
                Q = P[lp == c]
                if len(Q) < 10:
                    continue
                cen = Q.mean(0)
                w, vec = np.linalg.eigh(np.cov(Q.T) if len(Q) > 2 else np.eye(2))
                ax = vec[:, 1]
                ang = math.degrees(math.atan2(ax[1], ax[0]))
                if ang > 90: ang -= 180
                if ang <= -90: ang += 180
                # direction from side v towards side u, using where each country holds ground near the front
                x0, x1 = int(max(0, Q[:, 0].min() - 8)), int(min(W4, Q[:, 0].max() + 9))
                y0, y1 = int(max(0, Q[:, 1].min() - 8)), int(min(H4, Q[:, 1].max() + 9))
                sub = d[y0:y1, x0:x1]
                cm = np.zeros(sub.shape, bool)
                qx = (Q[:, 0] - x0).astype(int).clip(0, sub.shape[1] - 1); qy = (Q[:, 1] - y0).astype(int).clip(0, sub.shape[0] - 1)
                cm[qy, qx] = True
                near = ndimage.binary_dilation(cm, iterations=10)
                yu, xu = np.nonzero(near & (sub == u)); yv, xv = np.nonzero(near & (sub == v))
                if len(xu) == 0 or len(xv) == 0:
                    continue
                nv = np.array([xu.mean() - xv.mean(), yu.mean() - yv.mean()])
                nn = np.hypot(*nv)
                if nn < 1e-6:
                    continue
                nv /= nn
                # label anchors: walk from the front centre into each side's own ground and stop halfway
                anch = []
                for who, sg in ((u, 1), (v, -1)):
                    run, inside = 0, False
                    for k in range(1, 40):
                        px = int(round(cen[0] + nv[0] * sg * k)); py = int(round(cen[1] + nv[1] * sg * k))
                        if not (0 <= px < W4 and 0 <= py < H4):
                            break
                        if d[py, px] == who:
                            inside = True; run += 1
                        elif inside:
                            break
                        elif k > 4:
                            break
                    off = float(np.clip(0.5 * run + 1.0, 2.5, 13.0)) if inside else 2.5
                    anch.append(lonlat(cen[0] + nv[0] * sg * off, cen[1] + nv[1] * sg * off))
                cy_, cx_ = int(cen[1]), int(cen[0])
                comp_lab = land_lab[Q[len(Q) // 2][1].astype(int), Q[len(Q) // 2][0].astype(int)]
                cur.append({"u": u, "v": v, "cen": cen, "ang": ang, "anch": anch, "land": int(comp_lab), "pts": Q})
        # troops: each division group goes to the nearest front where its country is on one of the sides
        sums = [[0, 0, 0, 0] for _ in cur]                        # men u, men v, divisions u, divisions v
        if cur:
            fll = []
            for f in cur:
                sub = f["pts"][:: max(1, len(f["pts"]) // 40)]
                fll.append(np.array([lonlat(x, y) for x, y in sub]))
            for row in fs["r"]:
                tag_id, sid, n, arm, men = row
                if sid not in sids_idx:
                    continue
                lon, lat = sll[sids_idx[sid]]
                dcy, dcx = ds_cell(lon, lat)
                dl = int(land_lab[dcy, dcx])
                best, bi, side = 1e9, -1, 0
                for i, f in enumerate(cur):
                    if f["land"] != dl:
                        continue
                    if tag_id == f["u"] or (tag_id != f["v"] and at_war(tag_id, f["v"], t) and not at_war(tag_id, f["u"], t)):
                        sd = 0
                    elif tag_id == f["v"] or (at_war(tag_id, f["u"], t) and not at_war(tag_id, f["v"], t)):
                        sd = 1
                    else:
                        continue
                    dk = np.min(np.hypot((fll[i][:, 0] - lon) * math.cos(math.radians(lat)), fll[i][:, 1] - lat)) * 111.0
                    if dk < best:
                        best, bi, side = dk, i, sd
                if bi >= 0 and best <= 320:
                    sums[bi][side] += men; sums[bi][2 + side] += n
        # follow fronts from the previous snapshot
        new_open = []
        used = set()
        for f, sm in zip(cur, sums):
            lon, lat = lonlat(*f["cen"])
            best, bt = 1e9, None
            for tr in open_tr:
                if id(tr) in used or (tr["u"], tr["v"]) != (f["u"], f["v"]) or t - tr["s"][-1][0] > 4.0:
                    continue
                dk = math.hypot((tr["s"][-1][1] - lon) * math.cos(math.radians(lat)), tr["s"][-1][2] - lat) * 111.0
                if dk < best and dk < 600:
                    best, bt = dk, tr
            ang = f["ang"]
            if bt is not None:
                pa = bt["s"][-1][3]
                while ang - pa > 90: ang -= 180
                while ang - pa < -90: ang += 180
                used.add(id(bt))
            else:
                bt = {"u": f["u"], "v": f["v"], "s": []}
                tracks.append(bt)
            bt["s"].append([t, round(lon, 3), round(lat, 3), round(ang, 1),
                            round(f["anch"][0][0], 3), round(f["anch"][0][1], 3), round(f["anch"][1][0], 3), round(f["anch"][1][1], 3),
                            int(sm[0]), int(sm[1]), int(sm[2]), int(sm[3])])
            new_open.append(bt)
        open_tr = new_open
    # a front needs a few snapshots to be worth labelling; smooth its troop totals over neighbours
    out = []
    for tr in tracks:
        s = tr["s"]
        if len(s) < 3:
            continue
        for k in (8, 9):
            vals = [r[k] for r in s]
            for i, r in enumerate(s):
                win = vals[max(0, i - 1): i + 2]
                r[k] = int(sum(win) / len(win))
        out.append({"a": tr["u"], "b": tr["v"], "s": s})
    labels = []
    for pk in pockets:
        if pk["n"] < 2:
            continue
        text = (f"{int(round(pk['men'], -3)):,} encircled" if pk["men"] >= 2000 else "Encircled")
        labels.append({"t0": pk["t0"] - 0.5, "t1": pk["t1"] + 2.0, "lon": round(pk["ll"][0], 3), "lat": round(pk["ll"][1], 3),
                       "text": text, "side": "allied", "who": tag_of.get(pk["who"], ""), "src": "HOI4 campaign"})
    return out, labels


def snap_to_borders(cs, start_tag, land, hist_units):
    """Sharpen country borders. HOI4 states are coarse; the historical map knows the real 1939 borders.
    Each historical unit is matched to the HOI4 country that mostly holds it, and any cell whose state
    belongs to a different country is handed to the nearest state of the matching country, so the
    border between two countries follows the real line while states keep their own shapes inside."""
    from scipy import ndimage
    out = cs.copy()
    tag = start_tag[cs]                                           # country holding each cell's state at the start
    tgt = np.zeros(cs.shape, np.uint8)
    n_fix = 0
    for h in np.unique(hist_units):
        if h == 0:
            continue
        m = hist_units == h
        cnt = np.bincount(tag[m & (tag > 0)], minlength=256)
        if cnt.sum() < 50:
            continue
        dom = int(cnt.argmax())
        if cnt[dom] / cnt.sum() < 0.7:
            continue
        tgt[m] = dom
    bad = land & (tgt > 0) & (tag != tgt)
    for dom in np.unique(tgt[bad]):
        good = (tag == dom) & land
        if not good.any():
            continue
        todo = bad & (tgt == dom)
        ys, xs = np.nonzero(todo)
        y0, y1, x0, x1 = max(0, ys.min() - 60), ys.max() + 61, max(0, xs.min() - 60), xs.max() + 61
        iy, ix = ndimage.distance_transform_edt(~good[y0:y1, x0:x1], return_distances=False, return_indices=True)
        sub = out[y0:y1, x0:x1]
        t_ = todo[y0:y1, x0:x1]
        sub[t_] = cs[y0:y1, x0:x1][iy[t_], ix[t_]]
        n_fix += int(t_.sum())
    return out, n_fix


def build(log_path, states_path, out_dir):
    from datetime import datetime
    camp = import_log.load(log_path)
    with open(states_path, encoding="utf-8") as f:
        st = json.load(f)
    cal = calibrate(st)
    W_ = world()
    land = W_.land
    H, Wd = land.shape
    cs = cell_states(st, cal, land)
    csf = cs.ravel()

    start = datetime.strptime(camp["start"], "%Y-%m-%d %H")
    day0 = datetime(start.year, start.month, start.day)
    shift = start.hour / 24.0                                   # log times are relative to the first line
    T = lambda t: round(t + shift, 4)                           # noqa: E731  days since the epoch

    # ---- units (one per country tag that appears)
    tags = []
    def add(tag):
        if tag and tag not in tags:
            tags.append(tag)
    snaps = camp["snapshots"]
    for tag in snaps[0]["states"].values():
        add(tag)
    for tag in camp["owners"].values():
        add(tag)
    for _, _, a, b in camp["control"]:
        add(a); add(b)
    for t in camp["countries"]:
        add(t)
    tags = tags[:254]
    uid = {t: i + 1 for i, t in enumerate(tags)}

    # ---- faction timeline per tag
    leaders_seen = {l for s in camp["factions"] for l in s["leaders"]}
    fclass = lambda leader: LEADER_CLASS.get(leader, "axis" if leader in {"GER", "ITA", "JAP"} else "neutral")  # noqa: E731
    fac = {t: [] for t in tags}

    trans = {t: [] for t in tags}                                 # (time, class) in any order; resolved chronologically below

    def set_fac(tag, t, cls):
        if tag in trans:
            trans[tag].append((T(t), cls))
    for snap in camp["factions"]:
        al = snap["allies"]
        for tag in tags:
            cls = "neutral"
            if tag in snap["leaders"]:
                cls = fclass(tag)
            else:
                for l in snap["leaders"]:
                    if l in al.get(tag, []):
                        cls = fclass(l); break
            set_fac(tag, snap["t"], cls)
    for e in camp["events"]:
        if e["kind"] == "FACTION_JOIN" and len(e["tags"]) >= 2:
            set_fac(e["tags"][0], e["t"], fclass(e["tags"][1]))
    for t in tags:
        for tm, cls in sorted(trans[t], key=lambda r: r[0]):
            if not fac[t] or fac[t][-1][1] != cls:
                fac[t].append((iso(day0, tm), cls))
        if not fac[t]:
            fac[t].append((iso(day0, 0), "neutral"))

    # ---- wars
    wars = []
    end_t = {}
    for e in camp["events"]:
        if e["kind"] == "CAPITULATION" and e["tags"]:
            end_t.setdefault(e["tags"][0], e["t"])
    seen = set()
    # AT_WAR lines are not in camp["events"] (not an event kind); re-read them from the log
    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "|AT_WAR|" not in line and "|DECLARE_WAR|" not in line:
                continue
            seg = line.split("WW2DBD|", 1)[-1].strip().split("|")
            try:
                tt = (import_log.parse_date(seg[0]) - start).total_seconds() / 86400.0
            except ValueError:
                continue
            a, b = import_log.clean(seg[2]), import_log.clean(seg[3])
            if (a, b) in seen or (b, a) in seen or a not in uid or b not in uid:
                continue
            seen.add((a, b))
            t1 = min(end_t.get(a, 1e9), end_t.get(b, 1e9))
            wars.append([a, b, T(tt), None if t1 >= 1e9 else T(t1)])

    # ---- base control and country
    first = dict(snaps[0]["states"])
    owner_of = dict(camp["owners"])
    lut_ctl = np.zeros(65536, np.uint8); lut_cty = np.zeros(65536, np.uint8)
    for sid, tag in first.items():
        lut_ctl[int(sid)] = uid.get(tag, 0)
    for sid, tag in owner_of.items():
        lut_cty[int(sid)] = uid.get(tag, 0)
    import political_1939 as P1939
    cs, n_snap = snap_to_borders(cs, lut_ctl, land, P1939.build())
    csf = cs.ravel()
    print(f"borders: {n_snap} cells re-assigned to follow the real 1939 country borders")
    base_ctl = lut_ctl[cs]; base_cty = lut_cty[cs]
    base_cty = np.where(base_cty == 0, base_ctl, base_cty).astype(np.uint8)

    # ---- state -> cells
    order = np.argsort(csf, kind="stable")
    sorted_ids = csf[order]
    bounds = np.searchsorted(sorted_ids, np.arange(65537))
    def cells_of(sid):
        return np.sort(order[bounds[sid]:bounds[sid + 1]])

    # ---- control changes -> smooth advances
    # 1. which states really change hands, and when (control events + monthly snapshot corrections)
    cur = dict(first)
    timeline = [("c", c[0], (c[1], c[2], c[3])) for c in camp["control"]]
    for sn in snaps[1:]:
        timeline.append(("s", sn["t"], sn["states"]))
    timeline.sort(key=lambda r: (r[1], 0 if r[0] == "c" else 1))
    changes = []                                                 # (t, state, new tag, source)
    for kind, t, payload in timeline:
        if kind == "c":
            sid, _frm, to = payload
            if cur.get(sid) != to:
                changes.append((t, sid, to, "control")); cur[sid] = to
        else:
            for sid, tag in payload.items():
                if cur.get(sid) != tag:
                    changes.append((t, sid, tag, "snapshot")); cur[sid] = tag
    n_fix = sum(1 for c in changes if c[3] == "snapshot")

    # 2. captures by the same country within a few days form ONE advance, so the front flows through
    #    the states instead of flipping them one at a time
    GAP, MAXSPAN = 10.0, 60.0
    clusters = []
    open_c = {}
    for ch in sorted(changes, key=lambda c: c[0]):
        c = open_c.get(ch[2])
        if c and ch[0] - c["last"] <= GAP and ch[0] - c["first"] <= MAXSPAN:
            c["ev"].append(ch); c["last"] = ch[0]
        else:
            c = {"tag": ch[2], "first": ch[0], "last": ch[0], "ev": [ch]}
            open_c[ch[2]] = c; clusters.append(c)
    clusters.sort(key=lambda c: c["first"])

    from skimage.graph import MCP_Geometric
    from compiler import mobility
    mob = mobility()
    ctl = base_ctl.copy()
    groups = []
    adv_rec = []                                                  # (cell index, new owner, arrival day) per advance
    war_t0 = {}
    for wa, wb, w0, _w1 in wars:
        war_t0[(uid[wa], uid[wb])] = war_t0[(uid[wb], uid[wa])] = w0
    GAMMA = 3.0                                                   # >1 sharpens road/rail corridors into spearheads
    DEFAULT_SPAN, MIN_SPAN, MAX_SPAN_S = 6.0, 2.0, 14.0
    for cl in clusters:
        new = uid.get(cl["tag"])
        evs = [(t, sid) for t, sid, _tag, _src in cl["ev"] if cells_of(int(sid)).size]
        if new is None or not evs:
            continue
        cells_list = [cells_of(int(sid)) for _t, sid in evs]
        allc = np.concatenate(cells_list)
        yy, xx = allc // Wd, allc % Wd
        y0, y1, x0, x1 = max(0, yy.min() - 4), min(H, yy.max() + 5), max(0, xx.min() - 4), min(Wd, xx.max() + 5)
        shp = (y1 - y0, x1 - x0)
        mask = np.zeros(shp, bool); mask[yy - y0, xx - x0] = True
        smask = []                                               # per-state mask in the local window
        for cells in cells_list:
            sm_ = np.zeros(shp, bool); sm_[cells // Wd - y0, cells % Wd - x0] = True; smask.append(sm_)
        lab, nl = ndimage.label(mask, np.ones((3, 3)))
        prev = ctl[y0:y1, x0:x1]
        atk = ndimage.binary_dilation(prev == new, np.ones((3, 3)))
        cost_all = np.maximum(mob[y0:y1, x0:x1], 0.3) ** GAMMA
        for comp in range(1, nl + 1):
            cm = lab == comp
            seeds = cm & atk
            if not seeds.any():                                   # landing from the sea / paradrop: start at the coast
                seeds = cm & ndimage.binary_dilation((~land[y0:y1, x0:x1]) & ~cm, np.ones((3, 3)))
            if not seeds.any():
                cy, cx = np.nonzero(cm); k = np.argmin((cy - cy.mean()) ** 2 + (cx - cx.mean()) ** 2)
                seeds = np.zeros(shp, bool); seeds[cy[k], cx[k]] = True
            dist, _ = MCP_Geometric(np.where(cm, cost_all, np.inf)).find_costs(list(zip(*np.nonzero(seeds))))
            dist = np.where(cm & np.isfinite(dist), dist, 0.0)
            members = [k for k in range(len(evs)) if (smask[k] & cm).any()]
            tk = {k: T(evs[k][0]) for k in members}
            dil = {k: ndimage.binary_dilation(smask[k] & cm, np.ones((3, 3)), iterations=2) for k in members}
            arrival = np.zeros(shp, np.float32)
            for k in members:
                sm = smask[k] & cm
                d = dist[sm]
                # previous capture next to this state by the same attacker: the advance into it started then
                prevs = [tk[j] for j in members if j != k and tk[j] <= tk[k] - 0.02 and (dil[k] & smask[j] & cm).any()]
                span = tk[k] - max(prevs) if prevs else DEFAULT_SPAN
                span = float(np.clip(span, MIN_SPAN, MAX_SPAN_S))
                old = np.bincount(prev[sm].astype(int)).argmax()
                w0 = war_t0.get((new, int(old)))
                ts = tk[k] - span
                if w0 is not None:
                    ts = min(max(ts, w0), tk[k] - 0.5)
                lo, hi = np.percentile(d, 3), np.percentile(d, 97)
                u = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
                arrival[sm] = ts + (tk[k] - ts) * u
            ys2, xs2 = np.nonzero(cm)
            arr_c = arrival[ys2, xs2]
            t_lo = max(0.0, float(arr_c.min())); t_hi = max(float(arr_c.max()), t_lo + 0.05)
            frac = np.clip(np.round((arr_c - t_lo) / (t_hi - t_lo) * 255), 0, 255).astype(np.uint8)
            idx = ((ys2 + y0) * Wd + (xs2 + x0)).astype(np.int64)
            o2 = np.argsort(idx)
            groups.append(Group(0, t_lo, t_hi, idx[o2], np.full(idx.size, new, np.uint8), frac[o2], "advance"))
            adv_rec.append((idx[o2], new, t_lo + (t_hi - t_lo) * frac[o2] / 255.0))
        ctl[y0:y1, x0:x1][mask] = new
    n_ev = len(groups)
    t_end = T(max([e["t"] for e in camp["events"]] + [sn["t"] for sn in snaps] + [r["t"] for r in camp["divisions"]] + [0.0]))
    os.makedirs(out_dir, exist_ok=True)
    nbytes = write_stream(os.path.join(out_dir, "territory.bin"), base_cty, base_ctl, groups, t_end)
    print(f"territory: {len(changes)} state captures merged into {n_ev} continuous advances ({n_fix} corrected from monthly snapshots), "
          f"{nbytes / 1e6:.1f} MB raw")

    # ---- positions
    S = st["states"]
    spos = {sid: px_to_lonlat(cal, v["x"], v["y"]) for sid, v in S.items()}
    cap_state = {t: str(s) for t, s in st["capitals"].items()}
    cap_state.update({t: s for t, s in camp["capitals"].items()})
    def cap_pos(tag):
        s = cap_state.get(tag)
        return spos.get(s) if s else None

    # ---- events with positions
    cname = lambda t: camp["countries"].get(t, {}).get("name", t)  # noqa: E731
    ev_out, captions = [], []
    for e in camp["events"]:
        k, tg = e["kind"], e["tags"]
        pos = None
        if k == "CAPITULATION" and tg:
            pos = cap_pos(tg[0]); typ, title = "capital", f"{cname(tg[0])} capitulates"
            text = f"{cname(tg[0])} capitulates to {cname(tg[1]) if len(tg) > 1 else 'its enemies'}."
        elif k == "DECLARE_WAR" and len(tg) >= 2:
            pos = cap_pos(tg[1]); typ, title = "breakthrough", f"{cname(tg[0])} declares war on {cname(tg[1])}"
            text = title + "."
        elif k in ("NAVAL_INVASION", "PARADROP"):
            pos = spos.get(e.get("to")); typ = "breakthrough"
            title = f"{cname(tg[0]) if tg else '?'} {'naval invasion' if k == 'NAVAL_INVASION' else 'airborne landing'}"
            text = title + " (recorded landing)."
        elif k == "ANNEX" and len(tg) >= 2:
            pos = cap_pos(tg[1]); typ, title = "capital", f"{cname(tg[1])} annexed by {cname(tg[0])}"
            text = title + "."
        else:
            captions.append({"t": T(e["t"]), "text": e["title"]})
            continue
        captions.append({"t": T(e["t"]), "text": title})
        if pos:
            ev_out.append({"id": e["id"], "type": typ, "date": None, "t": T(e["t"]), "title": title, "text": text,
                           "lon": round(pos[0], 3), "lat": round(pos[1], 3), "zoom": 6.0, "src": "HOI4 campaign log"})

    # ---- forces markers
    by_t = {}
    for r in camp["divisions"]:
        by_t.setdefault(r["t"], []).append(r)
    forces = []
    for t in sorted(by_t):
        rows = [[uid[r["tag"]], int(r["state"]), r["n"], r["armor"], r["men"]] for r in by_t[t] if r["tag"] in uid]
        forces.append({"t": T(t), "r": rows})
    used = {row[1] for f in forces for row in f["r"]}
    state_pos = {str(s): [round(spos[str(s)][0], 3), round(spos[str(s)][1], 3)] for s in used if str(s) in spos}


    # ---- fronts: where two countries at war meet, with the troops on each side
    fronts, pocket_labels = compute_fronts(forces, base_ctl, adv_rec, wars, uid, spos, Wd, H, T, tags, land)
    print(f"fronts: {len(fronts)} tracks, {len(pocket_labels)} encirclements")

    # ---- meta and campaign files
    units = [{"id": uid[t], "code": t, "name": cname(t), "kind": "state", "factions": fac[t]} for t in tags]
    meta = {"epoch": day0.strftime("%Y-%m-%dT00:00:00Z"), "tEnd": t_end, "grid": {"w": int(Wd), "h": int(H)},
            "units": units, "captions": sorted(captions, key=lambda c: c["t"]), "labels": pocket_labels, "fronts": {},
            "wars": wars, "campaign": True}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    campaign = {"format": "ww2dbd-hoi4-replay/0.1", "start": camp["start"], "end": camp["end"], "calibration": cal,
                "events": ev_out, "forces": forces, "fronts": fronts, "statePos": state_pos,
                "countries": {t: camp["countries"].get(t, {}).get("name", t) for t in tags},
                "casualties": camp["casualties"], "leaders": camp["leaders"][-400:]}
    with open(os.path.join(out_dir, "campaign.json"), "w", encoding="utf-8") as f:
        json.dump(campaign, f, ensure_ascii=False)
    print(f"{len(units)} countries, {len(wars)} wars, {len(ev_out)} timeline events, {len(forces)} force snapshots "
          f"({sum(len(f['r']) for f in forces)} markers) -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "..", "..", "data", "hoi4"))
