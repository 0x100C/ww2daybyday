import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hist"))
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from core import world, to_grid
import political_1939
from units import UNITS
from border_towns import TOWNS_1939
C = political_1939.build()
W0 = world()
C = political_1939.fill_coast(C, W0.land)
W = world()
code = {u["id"]: u["code"] for u in UNITS}
bad = 0
for name, lat, lon, exp in TOWNS_1939:
    gx, gy = to_grid(lat, lon)
    v = code.get(int(C[int(gy), int(gx)]), "?")
    if v != exp:
        bad += 1
        print(f"FAIL {name:20s} expected {exp:4s} got {v}")
print(f"{len(TOWNS_1939) - bad}/{len(TOWNS_1939)} towns correct")
print("unassigned land cells:", int((W.land & (C == 0)).sum()))
np.save(os.path.join(os.path.dirname(__file__), "..", "cache", "country_1939.npy"), C)
