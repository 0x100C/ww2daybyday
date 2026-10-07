"""Minimal TopoJSON decoder (CShapes 2.0 ships as TopoJSON)."""
import json


def decode(path):
    t = json.load(open(path))
    tr = t.get("transform")
    arcs = []
    for a in t["arcs"]:
        if tr:
            sx, sy = tr["scale"]; tx, ty = tr["translate"]
            x = y = 0; pts = []
            for dx, dy in a:
                x += dx; y += dy
                pts.append((x * sx + tx, y * sy + ty))
        else:
            pts = [tuple(p) for p in a]
        arcs.append(pts)

    def arc(i):
        return arcs[i] if i >= 0 else arcs[~i][::-1]

    def ring(idx):
        pts = []
        for i in idx:
            a = arc(i)
            pts.extend(a if not pts else a[1:])
        return pts

    feats = []
    for name, obj in t["objects"].items():
        geoms = obj["geometries"] if obj["type"] == "GeometryCollection" else [obj]
        for g in geoms:
            if g["type"] == "Polygon":
                coords = [ring(r) for r in g["arcs"]]
                geom = {"type": "Polygon", "coordinates": coords}
            elif g["type"] == "MultiPolygon":
                geom = {"type": "MultiPolygon", "coordinates": [[ring(r) for r in p] for p in g["arcs"]]}
            else:
                continue
            feats.append({"type": "Feature", "properties": g.get("properties", {}), "geometry": geom})
    return feats
