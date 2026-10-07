"""Compile a Timeline into the runtime territory stream.

For every instant at which some key or political operation takes effect,
the full country and control rasters are composited. Cells whose value
changes are grouped by cause; each group receives a time span and, for
control changes, a per-cell arrival fraction from a geodesic sweep that
starts at the cells bordering the gaining power's existing territory.
This makes advances spread from the actual front, pockets shrink from
their perimeter and corridors close progressively, while every keyframe
state is reproduced exactly at its key time.

Output (little endian, gzip):
  'WW2T' u32 version, u32 W, u32 H, u32 nGroups, f32 tEnd
  u8[W*H] base country, u8[W*H] base control
  per group: u8 kind (0 control, 1 country), u8 mode, u16 pad,
             f32 t0, f32 t1, u32 nRuns, u32 nCells,
             u32[nRuns] runStart, u32[nRuns] runLen,
             u8[nCells] owner, u8[nCells] frac, pad to 4
"""
import gzip
import struct
import sys
from collections import defaultdict

import numpy as np
from scipy import ndimage
from skimage.graph import MCP_Geometric

from core import world
from timeline import rasterize, MAX_SPAN, T
from units import BY_CODE

# country units whose own territory is held by another power's forces
CONTROLLED_BY = {"GG": "GER", "PRO": "GER"}

STRUCT8 = np.ones((3, 3), bool)


class Group:
    __slots__ = ("kind", "t0", "t1", "idx", "owner", "frac", "src")

    def __init__(self, kind, t0, t1, idx, owner, frac, src=""):
        self.kind, self.t0, self.t1 = kind, t0, t1
        self.idx, self.owner, self.frac, self.src = idx, owner, frac, src


_MOBILITY = None


def mobility():
    """Per-cell advance cost (lower = faster). Armies advance along roads and
    railways and through towns, so spearheads push ahead along the transport
    network and leave slower ground behind, giving the jagged, finger-like
    fronts seen in the reference. Built from the basemap ink channel (roads,
    rail, built-up areas) of the z6 tiles, resampled to the grid, plus a
    little deterministic noise; cached in build/cache/mobility.npy."""
    global _MOBILITY
    if _MOBILITY is not None:
        return _MOBILITY
    import os
    from PIL import Image
    here = os.path.dirname(os.path.abspath(__file__))
    cache = os.path.join(here, "..", "cache", "mobility.npy")
    if os.path.exists(cache):
        _MOBILITY = np.load(cache)
        return _MOBILITY
    sys.path.insert(0, os.path.join(here, ".."))
    import geo
    z = 6
    x0, x1, y0, y1 = geo.tile_range(z)
    T = geo.TILE
    mos = np.zeros(((y1 - y0 + 1) * T, (x1 - x0 + 1) * T), np.float32)
    tiles = os.path.join(here, "..", "..", "data", "tiles", str(z))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            p = os.path.join(tiles, f"{x}_{y}_m.webp")
            if os.path.exists(p):
                mos[(y - y0) * T:(y - y0 + 1) * T, (x - x0) * T:(x - x0 + 1) * T] = \
                    np.asarray(Image.open(p).convert("RGB"))[:, :, 0] / 255.0
    n = 2 ** z
    gy = (geo.MY0 + (np.arange(geo.GRID_H) + 0.5) / geo.GRID_H * (geo.MY1 - geo.MY0)) * n * T - y0 * T
    gx = (geo.MX0 + (np.arange(geo.GRID_W) + 0.5) / geo.GRID_W * (geo.MX1 - geo.MX0)) * n * T - x0 * T
    ink = ndimage.map_coordinates(mos, np.meshgrid(gy, gx, indexing="ij"), order=1)
    # the ink channel also holds coastlines and lake shores: drop ink near water
    from core import world
    water = ~world().land
    ink = np.where(ndimage.binary_dilation(water, iterations=3), 0, ink)
    ink = ndimage.maximum_filter(ink, 2)                     # keep thin roads after resampling
    # road/rail density over ~10-15 km: armoured columns advance along corridors
    dens = ndimage.gaussian_filter(ink, 4.0)
    dens = np.clip(dens / (np.percentile(dens[dens > 0], 97) + 1e-6), 0, 1)
    # large-scale unevenness (~40 km): salients and lagging sectors of the front
    rng = np.random.default_rng(1939)
    noise = ndimage.gaussian_filter(rng.standard_normal(ink.shape).astype(np.float32), 14)
    noise /= np.percentile(np.abs(noise), 99) + 1e-6
    cost = (0.25 + 0.95 * (1.0 - dens) ** 1.5) * (1.0 + 0.6 * np.clip(noise, -1, 1))
    _MOBILITY = np.clip(cost, 0.12, 2.0).astype(np.float32)
    np.save(cache, _MOBILITY)
    return _MOBILITY


T_PEACE = T("1945-05-08 12")   # end of the war in Europe
ROUGH_BAND = 26  # cells (~45 km) either side of a drawn line


def roughen(m):
    """Ragged front edge: within ROUGH_BAND of a drawn boundary, fast cells
    (road and rail corridors) just outside are taken (spearheads) and slow
    cells just inside are given up (bypassed ground). Deterministic: depends
    only on the mask and the static mobility field. Small rings (pockets,
    beachheads) are not eroded so they cannot vanish."""
    if not m.any() or m.all():
        return m
    edge = m ^ ndimage.binary_erosion(m)
    if not edge.any():
        return m
    y0, y1, x0, x1 = bbox(edge, pad=ROUGH_BAND + 2)
    mc = m[y0:y1, x0:x1]
    cost = mobility()[y0:y1, x0:x1]
    d_out = ndimage.distance_transform_edt(~mc)
    d_in = ndimage.distance_transform_edt(mc)
    u = np.clip((cost - 0.3) / 1.4, 0, 1)          # 0 = fastest corridor, 1 = slowest ground
    add = (~mc) & (d_out <= ROUGH_BAND * np.clip((0.55 - u) / 0.55, 0, 1))
    lab, n = ndimage.label(mc)
    big = np.zeros(n + 1, bool)
    if n:
        sizes = ndimage.sum(mc, lab, index=np.arange(1, n + 1))
        big[1:] = sizes > 4000
    rem = mc & big[lab] & (d_in <= ROUGH_BAND * np.clip((u - 0.45) / 0.55, 0, 1))
    out = m.copy()
    out[y0:y1, x0:x1] = (mc | add) & ~rem
    return out


def sweep_fracs(cells_mask, new_owner, prev_control, water, cost_field=None):
    """Arrival fraction (0..1) for every cell of cells_mask (bool, cropped),
    by geodesic distance from cells adjacent to territory already held by
    the cell's new owner. Normalised per connected component."""
    frac = np.zeros(cells_mask.shape, np.float32)
    lab, n = ndimage.label(cells_mask, STRUCT8)
    if n == 0:
        return frac
    # seed cells: in group and touching (8-neigh) a non-group cell held by new owner
    seeds = np.zeros_like(cells_mask)
    held = (~cells_mask) & (prev_control == new_owner)
    held_d = ndimage.binary_dilation(held, STRUCT8)
    seeds = cells_mask & held_d
    coast = cells_mask & ndimage.binary_dilation(water & ~cells_mask, STRUCT8)
    comp_has_seed = np.zeros(n + 1, bool)
    comp_has_seed[np.unique(lab[seeds])] = True
    comp_has_coast = np.zeros(n + 1, bool)
    comp_has_coast[np.unique(lab[coast])] = True
    start = seeds.copy()
    for c in range(1, n + 1):
        if comp_has_seed[c]:
            continue
        if comp_has_coast[c]:
            start |= coast & (lab == c)
        else:
            ys, xs = np.nonzero(lab == c)
            k = np.argmin((ys - ys.mean()) ** 2 + (xs - xs.mean()) ** 2)
            start[ys[k], xs[k]] = True
    cost = np.where(cells_mask, 1.0 if cost_field is None else cost_field, np.inf)
    mcp = MCP_Geometric(cost)
    starts = list(zip(*np.nonzero(start)))
    dist, _ = mcp.find_costs(starts)
    dist = np.where(cells_mask, dist, 0)
    dist[~np.isfinite(dist)] = 0
    mx = ndimage.maximum(dist, lab, index=np.arange(1, n + 1))
    mx = np.concatenate([[1.0], np.maximum(np.asarray(mx, np.float32), 1.0)])
    frac = np.where(cells_mask, (dist + 0.5) / (mx[lab] + 0.5), 0).astype(np.float32)
    return np.clip(frac, 0, 1)


def bbox(mask, pad=2):
    ys = np.nonzero(mask.any(axis=1))[0]
    xs = np.nonzero(mask.any(axis=0))[0]
    H, W = mask.shape
    return (max(0, ys[0] - pad), min(H, ys[-1] + pad + 1), max(0, xs[0] - pad), min(W, xs[-1] + pad + 1))


def compile_timeline(tl, log=sys.stderr, checkpoints=None):
    W = world()
    water = ~W.land
    H, Wd = W.land.shape
    country = tl.base_country.copy()
    base_country = country.copy()

    inst = set(op[0] for op in tl.ops)
    key_at = defaultdict(list)
    for L in tl.layers:
        for i, k in enumerate(L.sorted_keys()):
            inst.add(k[0])
            key_at[k[0]].append((L, i))
    ops_at = defaultdict(list)
    for op in tl.ops:
        ops_at[op[0]].append(op)
    inst = sorted(inst)

    lay = {L: {"mask": None, "inv": False, "t": None} for L in tl.layers}
    layers_sorted = sorted(tl.layers, key=lambda L: L.order)
    # only land and a narrow coastal margin ever change hands
    paintable = ndimage.binary_dilation(W.land, STRUCT8, iterations=3)
    lut = np.arange(256, dtype=np.uint8)
    for a, b in CONTROLLED_BY.items():
        lut[BY_CODE[a]["id"]] = BY_CODE[b]["id"]

    def composite():
        ctl = lut[country]
        for L in layers_sorted:
            st = lay[L]
            if st["mask"] is None:
                continue
            m = ~st["mask"] if st["inv"] else st["mask"]
            m = m & paintable
            if L.within is not None:
                m = m & np.isin(country, list(L.within))
            ctl[m] = L.owner
        return ctl

    control = composite()
    base_control = control.copy()
    last_ctl = np.full(control.size, -np.inf)   # time of each cell's latest scheduled control change
    groups = []
    snaps = {}
    checkpoints = sorted(checkpoints or [])

    for ti, t in enumerate(inst):
        # snapshots for verification just before t
        while checkpoints and checkpoints[0] < t:
            snaps[checkpoints.pop(0)] = (country.copy(), control.copy())
        prev_country = country.copy()
        prev_control = control
        # political operations
        op_spans = []
        for (tt, dur, mask_fn, unit, where, label) in ops_at.get(t, []):
            m = mask_fn() if callable(mask_fn) else rasterize(mask_fn)
            m = m & paintable
            if where is not None:
                m &= np.isin(country, list(where))
            country[m] = unit
            op_spans.append((m, t - dur, label))
        # layer keys
        deltas = []
        for (L, i) in key_at.get(t, []):
            keys = L.sorted_keys()
            tk, spec, inv, src = keys[i]
            kspan = L.sorted_spans()[i]
            st = lay[L]
            old = None if st["mask"] is None else (~st["mask"] if st["inv"] else st["mask"])
            if spec is None:
                st["mask"], st["inv"] = None, False
                new = None
            else:
                m = rasterize(spec)
                # hand-drawn polygons get the ragged, road-driven front edge while
                # the war lasts; final post-surrender states keep crisp lines so no
                # trimmed cell can fall back to a defeated power
                if spec[0] and t < T_PEACE:
                    m = roughen(m)
                st["mask"], st["inv"] = m, inv
                new = ~st["mask"] if inv else st["mask"]
            prev_t = st["t"]
            st["t"] = t
            if old is None and new is None:
                continue
            if old is None:
                d = new
            elif new is None:
                d = old
            else:
                d = old ^ new
            t0 = prev_t if prev_t is not None else t - 0.25
            t0 = max(t0, t - MAX_SPAN)
            if kspan is not None:
                t0 = t - kspan
            deltas.append((d, t0, f"{L.name}#{i}"))
        control = composite()

        # ---- country change groups (crossfaded borders) ----
        cchg = country != prev_country
        if cchg.any():
            remaining = cchg.copy()
            for (m, t0, label) in op_spans:
                g = remaining & m
                if g.any():
                    idx = np.flatnonzero(g)
                    groups.append(Group(1, t0, t, idx, country.ravel()[idx].copy(),
                                        np.full(idx.size, 128, np.uint8), label))
                    remaining &= ~g
            if remaining.any():
                idx = np.flatnonzero(remaining)
                groups.append(Group(1, t - 0.25, t, idx, country.ravel()[idx].copy(),
                                    np.full(idx.size, 128, np.uint8), "country"))

        # ---- control change groups (geodesic sweep) ----
        chg = control != prev_control
        if not chg.any():
            continue
        remaining = chg.copy()
        spans = [(d, t0, src) for (d, t0, src) in deltas] + [(m, t0, lab) for (m, t0, lab) in op_spans]
        spans.append((np.ones_like(chg), t - 0.25, "misc"))
        for (d, t0, src) in spans:
            g = remaining & d
            if not g.any():
                continue
            remaining &= ~g
            y0, y1, x0, x1 = bbox(g, pad=3)
            gc = g[y0:y1, x0:x1]
            newc = control[y0:y1, x0:x1]
            prevc = prev_control[y0:y1, x0:x1]
            wat = water[y0:y1, x0:x1]
            mob = mobility()[y0:y1, x0:x1]
            fr = np.zeros(gc.shape, np.float32)
            for owner in np.unique(newc[gc]):
                sub = gc & (newc == owner)
                f = sweep_fracs(sub, owner, prevc, wat, mob)
                fr[sub] = f[sub]
            yy, xx = np.nonzero(gc)
            idx = (yy + y0) * Wd + (xx + x0)
            order = np.argsort(idx)
            idx = idx[order]
            f = fr[yy, xx][order]
            # A cell's change can never be scheduled before its previous change:
            # a long sweep starting at t0 may overlap events at earlier instants,
            # and replay in time order would otherwise apply them out of order
            # (e.g. a withdrawal timed before the occupation it undoes).
            if t > t0:
                f = np.maximum(f, (last_ctl[idx] - t0) / (t - t0))
            frac = np.clip(np.ceil(f * 255 - 1e-6), 0, 255).astype(np.uint8)
            last_ctl[idx] = t0 + frac / 255.0 * (t - t0)
            groups.append(Group(0, t0, t, idx, control.ravel()[idx].copy(), frac, src))
        if ti % 25 == 0:
            print(f"  instant {ti + 1}/{len(inst)}  groups {len(groups)}", file=log)

    for c in checkpoints:
        snaps[c] = (country.copy(), control.copy())
    t_end = inst[-1] if inst else 0.0
    return base_country, base_control, groups, snaps, t_end


def write_stream(path, base_country, base_control, groups, t_end):
    H, W = base_country.shape
    out = bytearray()
    out += b"WW2T" + struct.pack("<IIIIf", 1, W, H, len(groups), t_end)
    out += base_country.tobytes() + base_control.tobytes()
    for g in groups:
        idx = g.idx.astype(np.int64)
        brk = np.flatnonzero(np.diff(idx) != 1) + 1
        starts = np.concatenate([[0], brk])
        ends = np.concatenate([brk, [idx.size]])
        rs = idx[starts].astype(np.uint32)
        rl = (ends - starts).astype(np.uint32)
        out += struct.pack("<BBHffII", g.kind, 0, 0, g.t0, g.t1, rs.size, idx.size)
        out += rs.tobytes() + rl.tobytes()
        out += g.owner.astype(np.uint8).tobytes() + g.frac.astype(np.uint8).tobytes()
        pad = (-len(out)) % 4
        out += b"\0" * pad
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(bytes(out))
    return len(out)
