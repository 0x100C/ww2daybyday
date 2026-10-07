// Mirror of build/geo.py: projection, grid and tile extents.
const LON_W = -25.0, LON_E = 60.0, LAT_S = 24.0, LAT_N = 71.5;

export const mercX = (lon) => (lon + 180) / 360;
export const mercY = (lat) => {
  const s = Math.sin(Math.max(-85, Math.min(85, lat)) * Math.PI / 180);
  return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI);
};
export const invMercX = (x) => x * 360 - 180;

// Display projection: Miller cylindrical, normalised like mercY so that x and
// y share one scale. The reference video uses this projection (fitted on
// landmarks: vertical/horizontal scale ratio 1.02, Mercator would need 1.16).
// The data grids and tiles stay in Web Mercator and are resampled on the GPU.
export const millerY = (lat) => {
  const f = lat * Math.PI / 180;
  return 0.5 - 1.25 * Math.log(Math.tan(Math.PI / 4 + 0.4 * f)) / (2 * Math.PI);
};
export const invMillerY = (y) => {
  const Y = (0.5 - y) * 2 * Math.PI / 1.25;
  return (Math.atan(Math.exp(Y)) - Math.PI / 4) / 0.4 * 180 / Math.PI;
};
export const invMercY = (y) => Math.atan(Math.sinh(Math.PI * (1 - 2 * y))) * 180 / Math.PI;

export const GEO = {
  LON_W, LON_E, LAT_S, LAT_N,
  MX0: mercX(LON_W), MX1: mercX(LON_E), MY0: mercY(LAT_N), MY1: mercY(LAT_S),
  NY0: millerY(LAT_N), NY1: millerY(LAT_S),
  zmin: 3, zmax: 7,
  tileRange(z) {
    const n = 2 ** z;
    return {
      x0: Math.floor(this.MX0 * n), x1: Math.floor((this.MX1 - 1e-12) * n),
      y0: Math.floor(this.MY0 * n), y1: Math.floor((this.MY1 - 1e-12) * n),
    };
  },
};
