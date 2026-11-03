#!/usr/bin/env python3
"""The whole-world map behind the detailed home map (build_map.py): Natural Earth land, lakes, towns, coastline
and country borders at three levels of detail, cut into pieces with bounding boxes so the app only draws what
is on screen; plus world towns, airports and country names for labels. Needs numpy.

  python3 tools/build_world.py          (reads data/, writes flightscope/data/world.npz + world_labels.json)

Detail levels (the app picks by zoom, NM across the screen): f <= 250, m <= 1200, c beyond.
Coordinates are stored as int16 inside each piece's box (~0.0002 deg on a 10 deg piece), compressed."""
import csv, json, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data"
OUT = ROOT / "flightscope" / "data"
LODS = {"f": dict(tol=0.0008, tile=5.0, chunk=400), "m": dict(tol=0.02, tile=15.0, chunk=400), "c": dict(tol=0.12, tile=45.0, chunk=400)}

def dp(pts, tol):
    """Douglas-Peucker on an (n, 2) array, iterative."""
    n = len(pts)
    if n < 4 or tol <= 0: return pts
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        a, b = pts[i], pts[j]; seg = pts[i + 1:j]
        d = b - a; L = math.hypot(*d)
        if L == 0: dist = np.hypot(*(seg - a).T)
        else: dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(dist))
        if dist[k] > tol:
            k += i + 1; keep[k] = True; stack += [(i, k), (k, j)]
    return pts[keep]

def clip(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of [(x, y)...] (x = lon) to a box."""
    def edge(pts, inside, inter):
        out = []
        if not pts: return out
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev): out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev): out.append(inter(prev, cur))
            prev = cur
        return out
    ix = lambda p, q, x: (x, p[1] + (x - p[0]) / (q[0] - p[0]) * (q[1] - p[1]))
    iy = lambda p, q, y: (p[0] + (y - p[1]) / (q[1] - p[1]) * (q[0] - p[0]), y)
    pts = edge(poly, lambda p: p[0] >= x0, lambda p, q: ix(p, q, x0))
    pts = edge(pts, lambda p: p[0] <= x1, lambda p, q: ix(p, q, x1))
    pts = edge(pts, lambda p: p[1] >= y0, lambda p, q: iy(p, q, y0))
    return edge(pts, lambda p: p[1] <= y1, lambda p, q: iy(p, q, y1))

def rings(path, holes=False, keep=lambda props: True):
    """Outer rings (and, with holes=True, the holes as a second list) of every polygon in a GeoJSON file."""
    outer, inner = [], []
    for f in json.load(open(path))["features"]:
        if not keep(f["properties"]): continue
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        for p in polys:
            outer.append(np.array(p[0], float)[:, :2])
            if holes: inner += [np.array(h, float)[:, :2] for h in p[1:]]
    return outer, inner

def lines(path):
    out = []
    for f in json.load(open(path))["features"]:
        g = f["geometry"]
        ls = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"] if g["type"] == "MultiLineString" else []
        out += [np.array(l, float)[:, :2] for l in ls if len(l) > 1]
    return out

def poly_pieces(rs, lod, min_span):
    """Simplify each ring, drop the ones too small to see at this level, cut the rest into tiles."""
    tol, T = LODS[lod]["tol"], LODS[lod]["tile"]; out = []
    for r in rs:
        x0, y0 = r.min(0); x1, y1 = r.max(0)
        if max(x1 - x0, y1 - y0) < min_span: continue
        s = dp(r, tol)
        if len(s) < 3: continue
        if x1 - x0 <= T and y1 - y0 <= T: out.append(s); continue
        for tx in np.arange(math.floor(x0 / T) * T, x1, T):
            for ty in np.arange(math.floor(y0 / T) * T, y1, T):
                c = clip([tuple(p) for p in s], tx, ty, tx + T, ty + T)
                if len(c) >= 3: out.append(np.array(c))
    return out

def line_pieces(ls, lod, min_span):
    tol, n = LODS[lod]["tol"], LODS[lod]["chunk"]; out = []
    for l in ls:
        if np.ptp(l, 0).max() < min_span: continue
        s = dp(l, tol)
        for i in range(0, len(s) - 1, n - 1):
            if len(s[i:i + n]) > 1: out.append(s[i:i + n])
    return out

def pack(pieces):
    """-> q (N, 2) int16 lat/lon inside each box, off (P+1), bb (P, 4) lat0 lat1 lon0 lon1."""
    qs, off, bb = [], [0], []
    for p in pieces:
        ll = p[:, ::-1]                                      # (lon, lat) -> (lat, lon)
        ll[:, 0] = np.clip(ll[:, 0], -85, 85)
        lo, hi = ll.min(0), ll.max(0); span = np.maximum(hi - lo, 1e-9)
        qs.append(np.round((ll - lo) / span * 65535 - 32768).astype(np.int16))
        off.append(off[-1] + len(p)); bb.append([lo[0], hi[0], lo[1], hi[1]])
    return (np.concatenate(qs) if qs else np.zeros((0, 2), np.int16)), np.array(off, np.int32), np.array(bb, np.float32)

def main():
    home = json.load(open(OUT / "map.json"))
    hl, hlo, rad = home["home"][0], home["home"][1], home["radius_nm"]
    dlat = rad / 60.0; dlon = rad / 60.0 / max(0.2, math.cos(math.radians(hl)))
    in_home = lambda lat, lon: hl - dlat <= lat <= hl + dlat and hlo - dlon <= lon <= hlo + dlon

    land, land_holes = rings(SRC / "ne_10m_land.geojson", holes=True)
    lakes, _ = rings(SRC / "ne_10m_lakes.geojson")
    big_lakes, _ = rings(SRC / "ne_10m_lakes.geojson", keep=lambda p: (p.get("scalerank") or 9) <= 3)
    urban, _ = rings(SRC / "ne_10m_urban_areas.geojson")
    coast = lines(SRC / "ne_10m_coastline.geojson")
    border = lines(SRC / "ne_10m_admin_0_boundary_lines_land.geojson")

    arrays = {}
    plan = {"f": dict(land=(land, 0.0), lakes=(lakes + land_holes, 0.0), urban=(urban, 0.0), coast=(coast, 0.0), border=(border, 0.0)),
            "m": dict(land=(land, 0.08), lakes=(lakes + land_holes, 0.15), coast=(coast, 0.08), border=(border, 0.0)),
            "c": dict(land=(land, 0.5), lakes=(big_lakes + land_holes, 0.8), coast=(coast, 0.5), border=(border, 0.0))}
    for lod, layers in plan.items():
        for name, (src, min_span) in layers.items():
            pieces = (line_pieces if name in ("coast", "border") else poly_pieces)(src, lod, min_span)
            q, off, bb = pack(pieces)
            arrays[f"{name}_{lod}_q"], arrays[f"{name}_{lod}_off"], arrays[f"{name}_{lod}_bb"] = q, off, bb
            print(f"{name:6s} {lod}: {len(pieces):6d} pieces {len(q):8d} pts")
    np.savez_compressed(OUT / "world.npz", **arrays)

    r4 = lambda v: round(v, 4)
    places = []
    for f in json.load(open(SRC / "ne_10m_populated_places_simple.geojson"))["features"]:
        p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
        pop = int(p.get("pop_max") or 0)
        if pop >= 100000 and not in_home(lat, lon): places.append({"name": p["name"], "lat": r4(lat), "lon": r4(lon), "pop": pop})
    places.sort(key=lambda p: -p["pop"])
    airports = []
    with open(SRC / "airports.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            big = r["type"] == "large_airport"; med = r["type"] == "medium_airport" and r["scheduled_service"] == "yes"
            if not (big or med): continue
            try: lat, lon = float(r["latitude_deg"]), float(r["longitude_deg"])
            except ValueError: continue
            if in_home(lat, lon): continue
            airports.append({"icao": r["icao_code"] or r["ident"], "iata": r["iata_code"], "name": r["name"],
                             "city": (r["municipality"] or "").split(",")[0].strip(), "lat": r4(lat), "lon": r4(lon), "rank": 3 if big else 2})
    countries = []
    for f in json.load(open(SRC / "ne_50m_admin_0_countries.geojson"))["features"]:
        p = f["properties"]
        countries.append({"name": p.get("NAME_EN") or p["NAME"], "lat": r4(p["LABEL_Y"]), "lon": r4(p["LABEL_X"]), "min": float(p.get("MIN_LABEL") or 5)})
    json.dump({"places": places, "airports": airports, "countries": countries}, open(OUT / "world_labels.json", "w"), separators=(",", ":"))
    for f in ("world.npz", "world_labels.json"): print(f, (OUT / f).stat().st_size // 1024, "KB")
    print(f"places={len(places)} airports={len(airports)} countries={len(countries)}")

if __name__ == "__main__":
    main()
