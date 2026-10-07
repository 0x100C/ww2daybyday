"""Compose a zoom level into a single neutral-coloured preview PNG (dev aid)."""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import geo
z = int(sys.argv[1]); out = sys.argv[2]
x0, x1, y0, y1 = geo.tile_range(z)
D = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tiles", str(z))
W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
L = np.zeros((H, W), np.float32); M = np.zeros((H, W, 3), np.float32)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        sx, sy = (x - x0) * 256, (y - y0) * 256
        L[sy:sy+256, sx:sx+256] = np.asarray(Image.open(f"{D}/{x}_{y}_s.jpg"), np.float32) / 255
        M[sy:sy+256, sx:sx+256] = np.asarray(Image.open(f"{D}/{x}_{y}_m.webp").convert("RGB"), np.float32) / 255
ink, water, snow = M[..., 0:1], M[..., 1:2], M[..., 2:3]
base = np.array([240, 235, 224], np.float32) / 255
land = base * (L[..., None] / 0.80)
land = land * (1 - ink * 0.55) + snow * 0.0
wat = np.array([218, 227, 241], np.float32) / 255
img = land * (1 - water) + wat * water
img = np.clip(img, 0, 1)
Image.fromarray((img * 255).astype(np.uint8)).save(out)
