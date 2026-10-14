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
        arr = np.frombuffer(base64.b64decode(g["data"]), dtype="<u2").reshape(g["h"], g["w"])
        gx = np.floor(hx / g["scale"]).astype(int); gy = np.floor(hy / g["scale"]).astype(int)
        okx = (gx >= 0) & (gx < g["w"]); oky = (gy >= 0) & (gy < g["h"])
        out = arr[np.clip(gy, 0, g["h"] - 1)[:, None], np.clip(gx, 0, g["w"] - 1)[None, :]]
        out = np.where(oky[:, None] & okx[None, :], out, 0).astype(np.uint16)
        print("state shapes: from the grid in the states file")
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

    def set_fac(tag, t, cls):
        if tag in fac and (not fac[tag] or fac[tag][-1][1] != cls):
            fac[tag].append((iso(day0, T(t)), cls))
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
        if not fac[t]:
            fac[t].append((iso(day0, 0), "neutral"))
        fac[t].sort()

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
    base_ctl = lut_ctl[cs]; base_cty = lut_cty[cs]
    base_cty = np.where(base_cty == 0, base_ctl, base_cty).astype(np.uint8)

    # ---- state -> cells
    order = np.argsort(csf, kind="stable")
    sorted_ids = csf[order]
    bounds = np.searchsorted(sorted_ids, np.arange(65537))
    def cells_of(sid):
        return np.sort(order[bounds[sid]:bounds[sid + 1]])

    # ---- control changes -> groups
    ctl = base_ctl.copy()
    cur = dict(first)                                            # replayed state -> tag
    water = ~land
    timeline = [("c", t, r) for t, *r in [(c[0], c[1], c[2], c[3]) for c in camp["control"]]]
    for s in snaps[1:]:
        timeline.append(("s", s["t"], s["states"]))
    timeline.sort(key=lambda r: (r[1], 0 if r[0] == "c" else 1))
    groups = []

    def move(sid, newtag, t, src):
        sid_i = int(sid)
        cells = cells_of(sid_i)
        if cells.size == 0 or newtag not in uid:
            cur[sid] = newtag
            return
        new = uid[newtag]
        yy, xx = cells // Wd, cells % Wd
        y0, y1, x0, x1 = max(0, yy.min() - 3), min(H, yy.max() + 4), max(0, xx.min() - 3), min(Wd, xx.max() + 4)
        mask = np.zeros((y1 - y0, x1 - x0), bool); mask[yy - y0, xx - x0] = True
        prev = ctl[y0:y1, x0:x1]
        fr = sweep_fracs(mask, new, prev, water[y0:y1, x0:x1])
        frac = np.clip(np.round(fr[yy - y0, xx - x0] * 255), 0, 255).astype(np.uint8)
        tt = T(t)
        groups.append(Group(0, max(0.0, tt - 1.0), tt, cells.astype(np.int64), np.full(cells.size, new, np.uint8), frac, src))
        ctl[yy, xx] = new
        cur[sid] = newtag

    n_ev = n_fix = 0
    for kind, t, payload in timeline:
        if kind == "c":
            sid, _frm, to = payload
            if cur.get(sid) != to:
                move(sid, to, t, "control"); n_ev += 1
        else:
            for sid, tag in payload.items():
                if cur.get(sid) != tag:
                    move(sid, tag, t, "snapshot"); n_fix += 1
    t_end = T(max([e["t"] for e in camp["events"]] + [s["t"] for s in snaps] + [r["t"] for r in camp["divisions"]] + [0.0]))
    os.makedirs(out_dir, exist_ok=True)
    nbytes = write_stream(os.path.join(out_dir, "territory.bin"), base_cty, base_ctl, groups, t_end)
    print(f"territory: {len(groups)} advances ({n_ev} from control events, {n_fix} corrected from monthly snapshots), "
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

    # ---- meta and campaign files
    units = [{"id": uid[t], "code": t, "name": cname(t), "kind": "state", "factions": fac[t]} for t in tags]
    meta = {"epoch": day0.strftime("%Y-%m-%dT00:00:00Z"), "tEnd": t_end, "grid": {"w": int(Wd), "h": int(H)},
            "units": units, "captions": sorted(captions, key=lambda c: c["t"]), "labels": [], "fronts": {},
            "wars": wars, "campaign": True}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    campaign = {"format": "ww2dbd-hoi4-replay/0.1", "start": camp["start"], "end": camp["end"], "calibration": cal,
                "events": ev_out, "forces": forces, "statePos": state_pos,
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
