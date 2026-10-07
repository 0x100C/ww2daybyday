"""Contact sheet of compiler snapshots: sheet.py out.png lat0 lon0 lat1 lon1 cols w h"""
import sys, glob, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hist'))
import numpy as np
from PIL import Image, ImageDraw
from render_state import render
out = sys.argv[1]; crop = [float(v) for v in sys.argv[2:6]]; cols = int(sys.argv[6]); W_, H_ = int(sys.argv[7]), int(sys.argv[8])
ims = []
d0 = os.path.join(os.path.dirname(__file__), '..', 'cache', 'snaps')
for f in sorted(glob.glob(d0 + '/c_*.npy')):
    d = os.path.basename(f)[2:12]
    im = render(np.load(f), np.load(d0 + '/k_' + d + '.npy'), d, crop).resize((W_, H_))
    ImageDraw.Draw(im).rectangle((0, 0, 70, 12), fill=(255, 255, 255)); ImageDraw.Draw(im).text((2, 1), d, fill=(0, 0, 0))
    ims.append(im)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (W_ * cols, H_ * rows), (255, 255, 255))
for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * W_, (i // cols) * H_))
sheet.save(out)
