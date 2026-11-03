"""The whole-world map (tools/build_world.py -> data/world.npz + world_labels.json), loaded in the background
and drawn with numpy so a layer of a few thousand pieces still builds in a fraction of a second on the Pi."""
from __future__ import annotations
import json, math, threading
from pathlib import Path
import numpy as np
import pygame

DATA = Path(__file__).resolve().parent / "data"
LAYERS = ("land", "lakes", "urban", "coast", "border")

def lod_for(zoom_nm: float) -> str:
    return "f" if zoom_nm <= 250 else "m" if zoom_nm <= 1200 else "c"

class World:
    def __init__(self):
        self.ready = False; self.sets = {}; self.labels = {"places": [], "airports": [], "countries": []}
        threading.Thread(target=self._load, name="world-map", daemon=True).start()

    def _load(self):
        try:
            z = np.load(DATA / "world.npz")
            for lod in "fmc":
                for name in LAYERS:
                    if f"{name}_{lod}_q" not in z: continue
                    q, off, bb = z[f"{name}_{lod}_q"], z[f"{name}_{lod}_off"], z[f"{name}_{lod}_bb"]
                    n = np.diff(off)
                    lo = np.repeat(bb[:, [0, 2]], n, axis=0); span = np.repeat(bb[:, [1, 3]] - bb[:, [0, 2]], n, axis=0)
                    ll = lo + (q.astype(np.float32) + 32768) / 65535 * span       # back to lat, lon
                    self.sets[(name, lod)] = (ll[:, 0].copy(), ll[:, 1].copy(), off, bb)
            self.labels = json.load(open(DATA / "world_labels.json"))
            self.ready = True
            print(f"world map loaded ({sum(len(v[0]) for v in self.sets.values())} points)", flush=True)
        except Exception as e:
            print(f"world map: {type(e).__name__}: {e}", flush=True)

    def draw(self, s, name, lod, center, org, k, color, lines=False, width=1, min_px=1.5):
        """Draw one layer onto s; center/org/k as MapScreen.to_px (flat NM projection about center)."""
        d = self.sets.get((name, lod))
        if d is None: return
        lat, lon, off, bb = d; lat0, lon0 = center; ox, oy = org
        kx = 60.0 * math.cos(math.radians(lat0)) * k; ky = 60.0 * k; LW, LH = s.get_size()
        sh = np.round(((bb[:, 2] + bb[:, 3]) / 2 - lon0) / 360.0) * 360.0          # the copy of each piece nearest the view
        x0 = ox + (bb[:, 2] - sh - lon0) * kx; x1 = ox + (bb[:, 3] - sh - lon0) * kx
        y0 = oy - (bb[:, 1] - lat0) * ky; y1 = oy - (bb[:, 0] - lat0) * ky
        vis = (x1 >= 0) & (x0 <= LW) & (y1 >= 0) & (y0 <= LH)
        if not lines: vis &= np.maximum(x1 - x0, y1 - y0) >= min_px                     # specks: skip
        for i in np.nonzero(vis)[0]:
            a, b = off[i], off[i + 1]
            pts = np.column_stack((ox + (lon[a:b] - sh[i] - lon0) * kx, oy - (lat[a:b] - lat0) * ky)).tolist()
            if lines: pygame.draw.lines(s, color, False, pts, width)
            elif len(pts) > 2: pygame.draw.polygon(s, color, pts)
