"""Draw geojson outlines over a basemap preview (dev aid). usage: overlay.py z preview.png out.png file.geojson [crop x0 y0 x1 y1]"""
import sys, os, json
from PIL import Image, ImageDraw
from shapely.geometry import shape
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import geo
z=int(sys.argv[1]); im=Image.open(sys.argv[2]).convert('RGB'); out=sys.argv[3]; src=sys.argv[4]
x0,_,y0,_=geo.tile_range(z); S=256*2**z
d=ImageDraw.Draw(im)
def P(c): return [(geo.merc_x(x)*S-x0*256, geo.merc_y(y)*S-y0*256) for x,y in c]
for f in [f for f in json.load(open(src))['features'] if f['geometry']]:
    g=shape(f['geometry'])
    for p in getattr(g,'geoms',[g]):
        d.line(P(p.exterior.coords), fill=(220,40,40), width=1)
        for h in p.interiors: d.line(P(h.coords), fill=(40,40,220), width=1)
if len(sys.argv)>5:
    im=im.crop(tuple(int(v) for v in sys.argv[5:9]))
im.save(out)
