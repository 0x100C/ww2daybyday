"""Shared projection and grid definitions for every build step.

Everything is Web Mercator. The territory grid and the basemap tile pyramid
share one extent so the runtime can map between them with a single affine.
"""
import math

# Geographic extent of the atlas (degrees). Covers the reference video's
# camera (Ireland to the Caspian, North Cape to the Libyan desert) with
# room to pan.
LON_W, LON_E = -25.0, 60.0
LAT_S, LAT_N = 24.0, 71.5

# Territory grid width in cells. Height follows from Mercator.
GRID_W = 4096

TILE = 256
TILE_ZMIN, TILE_ZMAX = 3, 7


def merc_x(lon):
    return (lon + 180.0) / 360.0


def merc_y(lat):
    s = math.sin(math.radians(max(-85.0, min(85.0, lat))))
    return 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)


def inv_merc_x(x):
    return x * 360.0 - 180.0


def inv_merc_y(y):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))


# Normalised mercator extent (0..1 world units)
MX0, MX1 = merc_x(LON_W), merc_x(LON_E)
MY0, MY1 = merc_y(LAT_N), merc_y(LAT_S)
GRID_H = int(round(GRID_W * (MY1 - MY0) / (MX1 - MX0)))


def lonlat_to_grid(lon, lat):
    """Continuous grid coordinates (cell units, origin top-left)."""
    gx = (merc_x(lon) - MX0) / (MX1 - MX0) * GRID_W
    gy = (merc_y(lat) - MY0) / (MY1 - MY0) * GRID_H
    return gx, gy


def grid_to_lonlat(gx, gy):
    x = MX0 + gx / GRID_W * (MX1 - MX0)
    y = MY0 + gy / GRID_H * (MY1 - MY0)
    return inv_merc_x(x), inv_merc_y(y)


def tile_range(z):
    n = 2 ** z
    x0 = int(math.floor(MX0 * n))
    x1 = int(math.floor((MX1 - 1e-12) * n))
    y0 = int(math.floor(MY0 * n))
    y1 = int(math.floor((MY1 - 1e-12) * n))
    return x0, x1, y0, y1


if __name__ == "__main__":
    print("grid", GRID_W, GRID_H)
    for z in range(TILE_ZMIN, TILE_ZMAX + 1):
        x0, x1, y0, y1 = tile_range(z)
        print(z, x0, x1, y0, y1, (x1 - x0 + 1) * (y1 - y0 + 1))
