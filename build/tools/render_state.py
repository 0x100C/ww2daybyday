"""Render a country/control raster pair to PNG on the grid (dev aid).
usage: render_state.py country.npy control.npy date out.png [crop lat0 lon0 lat1 lon1]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hist"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from PIL import Image
from core import world, to_grid
from units import UNITS, faction_on
PAL = {"neutral": (240, 235, 224), "axis": (115, 114, 101), "vichy": (170, 172, 152), "allied": (113, 150, 205),
       "allied_c": (148, 176, 238), "soviet": (183, 127, 105), "partisan": (214, 104, 92), None: (255, 0, 255)}
def render(C, K, date, crop=None):
    W = world()
    lut = np.zeros((256, 3), np.uint8)
    for u in UNITS:
        lut[u["id"]] = PAL[faction_on(u["id"], date)]
    img = lut[K].astype(np.float32)
    water = ~W.land
    img[water] = (218, 227, 241)
    edge = np.zeros_like(water)
    edge[:, 1:] |= C[:, 1:] != C[:, :-1]
    edge[1:, :] |= C[1:, :] != C[:-1, :]
    edge &= W.land
    img[edge] = img[edge] * 0.3 + np.array([230, 90, 90]) * 0.7
    fe = np.zeros_like(water)
    fe[:, 1:] |= K[:, 1:] != K[:, :-1]
    fe[1:, :] |= K[1:, :] != K[:-1, :]
    fe &= W.land
    img[fe] = (255, 255, 255)
    im = Image.fromarray(img.astype(np.uint8))
    if crop:
        x0, y0 = to_grid(crop[0], crop[1]); x1, y1 = to_grid(crop[2], crop[3])
        im = im.crop((int(min(x0, x1)), int(min(y0, y1)), int(max(x0, x1)), int(max(y0, y1))))
    return im
if __name__ == "__main__":
    C = np.load(sys.argv[1]); K = np.load(sys.argv[2])
    crop = [float(v) for v in sys.argv[5:9]] if len(sys.argv) > 5 else None
    render(C, K, sys.argv[3], crop).save(sys.argv[4])
