"""Shared Eastern Front objects (Axis / Soviet main front, Finnish front).

The main front is one line from the Baltic (north end) to the Black Sea
(south end). Side W (Axis) applies to Soviet lands, side E (Soviet) to
Axis lands (only from 1943 on, when the Red Army re-enters territory
that is not Soviet).
"""
from ctools import Front

_F = {}

AXIS_LANDS = ["GER", "GG", "PRO", "SVK", "HUN", "ROU", "BGR", "LTU", "LVA", "EST", "YUG", "SRB",
              "CRO", "DAN", "POL", "AUT", "CSR"]

# closures (see ctools.Front): W from the south end around the west to the north end
CL_W = [(44.5, 30.5), (42.5, 29.0), (41.0, 22.0), (44.0, 12.0), (55.0, 10.0), (57.5, 16.0), (59.5, 22.0),
        (60.2, 26.0)]
# E from the north end around the east to the south end
CL_E = [(61.5, 30.5), (70.0, 45.0), (70.0, 62.0), (38.0, 62.0), (40.5, 40.0), (42.5, 36.0)]


def main(tl):
    if "main" not in _F:
        f = Front(tl, "east", "GER", "SOV", ["SOV"], AXIS_LANDS, CL_W, CL_E, order=60,
                  jitter_amp=3.0, jitter_seg=9.0, seed=41)
        f.e_active = False  # switched on when the Red Army reaches non-Soviet territory (1944)
        _F["main"] = f
    return _F["main"]
