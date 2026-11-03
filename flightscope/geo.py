"""Flat-earth helpers. Good to well under a pixel at the ranges this device uses."""
import math

NM_PER_DEG = 60.0

def nm_xy(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Offset of (lat,lon) from (lat0,lon0) in nautical miles: +x east, +y north."""
    x = ((lon - lon0 + 540.0) % 360.0 - 180.0) * NM_PER_DEG * math.cos(math.radians(lat0))     # the short way round
    y = (lat - lat0) * NM_PER_DEG
    return x, y

def dist_bearing(lat0, lon0, lat, lon) -> tuple[float, float]:
    x, y = nm_xy(lat, lon, lat0, lon0)
    d = math.hypot(x, y)
    b = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0
    return d, b

def gc_nm(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in NM (fine for 'how far to Alicante')."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3440.065 * 2 * math.asin(math.sqrt(a))

def compass(bearing: float) -> str:
    pts = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return pts[int((bearing + 11.25) // 22.5) % 16]
