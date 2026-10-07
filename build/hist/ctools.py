"""Helpers for authoring campaign keyframes."""
from core import jitter, river, path, world


def J(points, amp=2.5, seg=7.0, seed=0):
    """Roughen a hand-drawn front line (deterministic per segment)."""
    return jitter(list(points), amp_km=amp, seg_km=seg, seed=seed)


def ring(front, closure):
    """Polygon from a front polyline plus closure points around the held side."""
    return list(front) + list(closure)


def circle(lat, lon, r_km, n=24):
    import math
    k = math.cos(math.radians(lat))
    return [(lat + r_km / 111.3 * math.sin(a), lon + r_km / (111.3 * k) * math.cos(a))
            for a in [2 * math.pi * i / n for i in range(n)]]


def blob(points, amp=1.8, seed=1):
    """Closed irregular ring through the given points (for pockets)."""
    pts = list(points) + [points[0]]
    return J(pts, amp=amp, seg=5.0, seed=seed)[:-1]


class Front:
    """A front line between two sides, authored once and used for both.

    west/east are simply the two sides of the line: `closure_w` closes the
    polygon around side W (owner `w`), `closure_e` around side E (owner `e`).
    Side W's layer only applies to cells whose country is in `w_within`
    (the other side's lands) and vice versa, so the line can run through
    an area without repainting either side's own territory.

    key(date, line, w_pockets=[], e_pockets=[])
        w_pockets: rings held by W inside E's side (e.g. Demyansk);
        e_pockets: rings held by E inside W's side (e.g. Leningrad).
    end(date): both layers dissolve.
    """

    def __init__(self, tl, name, w, e, w_within, e_within, closure_w, closure_e,
                 order=30, jitter_amp=2.5, jitter_seg=8.0, seed=0):
        self.Lw = tl.layer(name + ":" + w, w, within=w_within, order=order)
        self.Le = tl.layer(name + ":" + e, e, within=e_within, order=order + 1) if e_within else None
        self.cw, self.ce = list(closure_w), list(closure_e)
        self.amp, self.seg, self.seed = jitter_amp, jitter_seg, seed
        self.e_active = True
        # raw key lines, exported for front-following troop labels
        self.name, self.w, self.e = name, w, e
        self.lines = []
        if not hasattr(tl, "fronts"):
            tl.fronts = []
        tl.fronts.append(self)

    def key(self, date, line, w_pockets=(), e_pockets=(), raw=False, src="", span=None, cw=None, ce=None):
        ln = list(line) if raw or self.amp <= 0 else J(line, amp=self.amp, seg=self.seg, seed=self.seed)
        cw = self.cw if cw is None else list(cw)
        if not raw:
            self.lines.append((date, list(line), list(cw)))
        ce = self.ce if ce is None else list(ce)
        wr = [ln + cw] + [list(p) for p in e_pockets]
        self.Lw.key(date, wr[0], src=src, span=span)
        # holes: E pockets cut out of W; W pockets added
        self.Lw.keys[-1] = (self.Lw.keys[-1][0], ([[ln + cw] + [list(p) for p in e_pockets]] +
                                                   [list(p) for p in w_pockets], None), False, src)
        if self.Le is not None and self.e_active:
            self.Le.key(date, src=src, span=span)
            self.Le.keys[-1] = (self.Le.keys[-1][0], ([[ln[::-1] + ce] + [list(p) for p in w_pockets]] +
                                                       [list(p) for p in e_pockets], None), False, src)
        return self

    def end(self, date):
        self.Lw.end(date)
        if self.Le is not None:
            self.Le.end(date)
