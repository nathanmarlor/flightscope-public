#!/usr/bin/env python3
"""Clip Natural Earth + OurAirports around a home position into one compact JSON
the app draws with plain pygame calls. Polygons are clipped to the bounding box so
nothing off-screen is ever iterated at draw time.

  python3 tools/build_map.py 53.2333 -2.2333 --radius-nm 220
"""
import argparse, csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data"
OUT = ROOT / "flightscope" / "data" / "map.json"

def clip_poly(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a [(lon,lat)...] ring to a box."""
    def clip(pts, inside, inter):
        out = []
        if not pts: return out
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev): out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
            prev = cur
        return out
    def ix(p, q, x): t = (x - p[0]) / (q[0] - p[0]); return (x, p[1] + t * (q[1] - p[1]))
    def iy(p, q, y): t = (y - p[1]) / (q[1] - p[1]); return (p[0] + t * (q[0] - p[0]), y)
    pts = poly
    pts = clip(pts, lambda p: p[0] >= x0, lambda p, q: ix(p, q, x0))
    pts = clip(pts, lambda p: p[0] <= x1, lambda p, q: ix(p, q, x1))
    pts = clip(pts, lambda p: p[1] >= y0, lambda p, q: iy(p, q, y0))
    pts = clip(pts, lambda p: p[1] <= y1, lambda p, q: iy(p, q, y1))
    return pts

def geoms(feature):
    g = feature["geometry"]
    if g["type"] == "Polygon": return [g["coordinates"]]
    if g["type"] == "MultiPolygon": return g["coordinates"]
    if g["type"] == "LineString": return [[g["coordinates"]]]
    if g["type"] == "MultiLineString": return [[c] for c in g["coordinates"]]
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lat", type=float); ap.add_argument("lon", type=float)
    ap.add_argument("--radius-nm", type=float, default=220)
    a = ap.parse_args()
    dlat = a.radius_nm / 60.0
    dlon = a.radius_nm / 60.0 / max(0.2, math.cos(math.radians(a.lat)))
    lat0, lat1, lon0, lon1 = a.lat - dlat, a.lat + dlat, a.lon - dlon, a.lon + dlon
    inbox = lambda lat, lon: lat0 <= lat <= lat1 and lon0 <= lon <= lon1
    r4 = lambda v: round(v, 4)

    def polys_from(path, min_pts=3):
        out = []
        for f in json.load(open(path))["features"]:
            for poly in geoms(f):
                ring = poly[0]                     # outer ring only; holes are lakes we draw separately
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                if max(xs) < lon0 or min(xs) > lon1 or max(ys) < lat0 or min(ys) > lat1: continue
                c = clip_poly([(p[0], p[1]) for p in ring], lon0, lat0, lon1, lat1)
                if len(c) >= min_pts: out.append([[r4(p[1]), r4(p[0])] for p in c])
        return out

    def lines_from(path):
        out = []
        for f in json.load(open(path))["features"]:
            for line in geoms(f):
                run = []
                for lon, lat in line[0]:
                    if inbox(lat, lon): run.append([r4(lat), r4(lon)])
                    else:
                        if len(run) > 1: out.append(run)
                        run = []
                if len(run) > 1: out.append(run)
        return out

    land = polys_from(SRC / "ne_10m_land.geojson")
    lakes = polys_from(SRC / "ne_10m_lakes.geojson")
    urban = polys_from(SRC / "ne_10m_urban_areas.geojson")
    coast = lines_from(SRC / "ne_10m_coastline.geojson")
    rivers = lines_from(SRC / "ne_10m_rivers_europe.geojson")

    airports, runways = [], []
    by_ref = {}
    with open(SRC / "airports.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try: lat, lon = float(r["latitude_deg"]), float(r["longitude_deg"])
            except ValueError: continue
            if not inbox(lat, lon): continue
            d_nm = math.hypot((lon - a.lon) * 60 * math.cos(math.radians(a.lat)), (lat - a.lat) * 60)
            big = r["type"] == "large_airport"; med = r["type"] == "medium_airport"
            # small airfields only if they are real (have an ICAO code) and nearby - no hospital helipads
            small_near = r["type"] == "small_airport" and bool(r["icao_code"]) and (d_nm < 40 or r["scheduled_service"] == "yes")
            if not (big or med or small_near): continue
            city = (r["municipality"] or "").split(",")[0].strip()
            ap_ = {"icao": r["icao_code"] or r["ident"], "iata": r["iata_code"], "name": r["name"],
                   "city": city, "lat": r4(lat), "lon": r4(lon),
                   "rank": 3 if big else 2 if med else 1}
            airports.append(ap_); by_ref[r["id"]] = ap_
    with open(SRC / "runways.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["airport_ref"] not in by_ref or r["closed"] == "1": continue
            try:
                runways.append([r4(float(r["le_latitude_deg"])), r4(float(r["le_longitude_deg"])),
                                r4(float(r["he_latitude_deg"])), r4(float(r["he_longitude_deg"]))])
            except ValueError: continue

    places = []
    for f in json.load(open(SRC / "ne_10m_populated_places_simple.geojson"))["features"]:
        p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
        if not inbox(lat, lon): continue
        pop = int(p.get("pop_max") or 0)
        if pop < 15000: continue
        places.append({"name": p["name"], "lat": r4(lat), "lon": r4(lon), "pop": pop})
    places.sort(key=lambda p: -p["pop"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {"home": [a.lat, a.lon], "radius_nm": a.radius_nm, "land": land, "lakes": lakes, "urban": urban,
            "coast": coast, "rivers": rivers, "airports": airports, "runways": runways, "places": places}
    json.dump(data, open(OUT, "w"), separators=(",", ":"))
    kb = OUT.stat().st_size // 1024
    print(f"land={len(land)} lakes={len(lakes)} urban={len(urban)} coast={len(coast)} rivers={len(rivers)} "
          f"airports={len(airports)} runways={len(runways)} places={len(places)} -> {OUT} ({kb} KB)")

if __name__ == "__main__":
    main()
