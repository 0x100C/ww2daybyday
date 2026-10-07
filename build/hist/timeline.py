"""Timeline model: political operations and military control layers.

Time is measured in days (float) since 1939-09-01 00:00.

Political operation
    changes the country (de facto political unit) of the cells in a mask,
    optionally only where the current country is in `where`.

Control layer
    a power (`owner`) holding the region given by its latest key. A key is
    a list of polygons (each: [outer ring, hole, hole ...]) in (lat, lon),
    or a callable returning a mask. `inverse=True` keys describe the area
    the layer does NOT hold (useful to author the shrinking defender's
    perimeter). `within` restricts the layer to cells whose country is in
    the given set at that instant.

The composite control raster at an instant is the controller implied by
the country raster (each country controls itself) overpainted by every
active layer in `order`.

Keys are stepwise in this model; the visual interpolation between two keys
of a layer is produced by the compiler (geodesic sweep from the side that
gains ground), spread over the interval between the layer's own keys.
"""
import datetime as _dt

import numpy as np

from core import world
from units import BY_CODE

EPOCH = _dt.datetime(1939, 9, 1)
MAX_SPAN = 30.0


def T(s):
    """'1939-09-17', '1939-09-17 06' or '1939-09-17 06:30' -> float days."""
    if isinstance(s, (int, float)):
        return float(s)
    s = s.strip()
    fmt = {10: "%Y-%m-%d", 13: "%Y-%m-%d %H", 16: "%Y-%m-%d %H:%M"}[len(s)]
    d = _dt.datetime.strptime(s, fmt)
    return (d - EPOCH).total_seconds() / 86400.0


def date_str(t):
    return (EPOCH + _dt.timedelta(days=t)).strftime("%Y-%m-%d")


def uid(code):
    return BY_CODE[code]["id"]


class Layer:
    def __init__(self, tl, name, owner, within=None, order=0, note=""):
        self.tl = tl
        self.name = name
        self.owner = uid(owner)
        self.within = None if within is None else {uid(c) for c in within}
        self.order = order
        self.keys = []  # (t, spec, inverse, source)
        self.spans = {}  # key index (insertion order) -> transition span in days
        self.note = note

    def key(self, when, *polys, inverse=False, mask=None, src="", span=None):
        """polys: each a ring (list of (lat, lon)) or [ring, hole, ...].
        span: duration (days) of the visual transition ending at this key;
        default: the time since the layer's previous key, capped at MAX_SPAN."""
        self.keys.append((T(when), (list(polys), mask), inverse, src))
        if span is not None:
            self.spans[len(self.keys) - 1] = span
        return self

    def end(self, when, span=0.5):
        self.keys.append((T(when), None, False, "end"))
        self.spans[len(self.keys) - 1] = span
        return self

    def sorted_keys(self):
        order = sorted(range(len(self.keys)), key=lambda i: self.keys[i][0])
        return [self.keys[i] for i in order]

    def sorted_spans(self):
        order = sorted(range(len(self.keys)), key=lambda i: self.keys[i][0])
        return [self.spans.get(i) for i in order]


class Timeline:
    def __init__(self, base_country):
        self.base_country = base_country
        self.ops = []      # (t, dur, mask_fn, unit, where, label)
        self.layers = []
        self.notes = []    # (t, text) captions
        self.labels = []   # map annotations (encirclements etc.)

    def political(self, when, mask, unit, where=None, dur=1.0, label=""):
        self.ops.append((T(when), dur, mask, uid(unit),
                         None if where is None else {uid(c) for c in where}, label))

    def layer(self, name, owner, within=None, order=0, note=""):
        L = Layer(self, name, owner, within, order, note)
        self.layers.append(L)
        return L

    def caption(self, when, text):
        self.notes.append((T(when), text))

    def pocket(self, start, end, lat, lon, text, side="allied", src=""):
        self.labels.append({"t0": T(start), "t1": T(end), "lat": lat, "lon": lon,
                            "text": text, "side": side, "src": src})


def rasterize(spec):
    """Mask for a key spec ((polys, mask_fn))."""
    W = world()
    polys, mask_fn = spec
    m = np.zeros(W.land.shape, bool)
    for p in polys:
        if not p:
            continue
        if isinstance(p[0][0], (int, float)):
            m |= W.poly(p)
        else:
            m |= W.poly(*p)
    if mask_fn is not None:
        m |= mask_fn()
    return m
