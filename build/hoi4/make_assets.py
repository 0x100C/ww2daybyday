"""One-off: bundle the few raster layers the campaign builder needs (land mask, real 1939 country borders,
road/rail mobility) into hoi4/assets/world_lite.npz, so the builder runs without the big build cache.
Run by the maintainer only; users never need this."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "hist"))
from compiler import mobility  # noqa: E402
from core import world  # noqa: E402
import political_1939 as P  # noqa: E402

land = world().land.astype(bool)
hist = P.build().astype(np.uint8)
mob = mobility()
q = np.clip(np.round((mob - 0.5) / 0.8 * 255), 0, 255).astype(np.uint8)
os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
out = os.path.join(HERE, "assets", "world_lite.npz")
np.savez_compressed(out, land=np.packbits(land, axis=1), hist=hist, mob=q, shape=np.array(land.shape))
print(out, os.path.getsize(out) // 1024, "KB")
