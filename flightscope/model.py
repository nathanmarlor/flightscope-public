"""Aircraft state shared between data sources and the UI."""
from __future__ import annotations
import math, time
from collections import deque
from dataclasses import dataclass, field
from .geo import dist_bearing

TRAIL_S = 90.0      # seconds of breadcrumb to keep
STALE_S = 75.0      # drop an aircraft not heard for this long (a wide view asks each of up to 9 spots every 45 s)

@dataclass
class Aircraft:
    hex: str
    flight: str = ""
    reg: str = ""
    type: str = ""
    desc: str = ""
    lat: float | None = None
    lon: float | None = None
    alt: int | None = None          # feet; None if unknown
    on_ground: bool = False
    gs: float | None = None         # knots
    track: float | None = None      # degrees
    vr: int | None = None           # ft/min
    squawk: str = ""
    category: str = ""
    military: bool = False          # tar1090-db flag (dbFlags bit 0), set by the feed
    interesting: bool = False       # tar1090-db flag (dbFlags bit 1): notable or unusual aircraft
    dst: float | None = None        # NM from home
    dir: float | None = None        # bearing from home
    sources: set = field(default_factory=set)
    first_seen: float = 0.0
    last_seen: float = 0.0
    last_pos: float = 0.0
    trail: deque = field(default_factory=lambda: deque(maxlen=120))

    def heading(self) -> float | None:
        """Reported track, else the direction of the last bit of breadcrumb, else None."""
        if self.track is not None: return self.track
        if len(self.trail) >= 2:
            (la0, lo0, _), (la1, lo1, _) = self.trail[-2], self.trail[-1]
            dx = (lo1 - lo0) * math.cos(math.radians(la1)); dy = la1 - la0
            if abs(dx) + abs(dy) > 1e-5: return (math.degrees(math.atan2(dx, dy)) + 360) % 360
        return None

    def est_pos(self, now: float) -> tuple[float, float]:
        """Dead-reckoned position: last fix advanced along track at ground speed (capped 15 s)."""
        if self.lat is None: return (None, None)
        if self.on_ground or not self.gs or self.track is None: return (self.lat, self.lon)
        dt = max(0.0, min(15.0, now - self.last_pos))
        d = self.gs / 3600.0 * dt                      # NM travelled
        t = math.radians(self.track)
        lat = self.lat + d * math.cos(t) / 60.0
        lon = self.lon + d * math.sin(t) / (60.0 * max(0.2, math.cos(math.radians(self.lat))))
        return (lat, lon)

    @property
    def label(self) -> str:
        return self.flight or self.reg or self.hex.upper()

    @property
    def alt_text(self) -> str:
        if self.on_ground: return "GND"
        if self.alt is None: return "----"
        return f"FL{self.alt//100:03d}" if self.alt >= 18000 else f"{self.alt:,} ft"

class Fleet:
    """Merges snapshots from any number of sources into one live picture."""
    def __init__(self, home_lat: float, home_lon: float):
        self.home = (home_lat, home_lon)
        self.by_hex: dict[str, Aircraft] = {}
        self.new_hexes: set[str] = set()

    def set_home(self, lat, lon):
        self.home = (lat, lon)
        for a in self.by_hex.values():
            if a.lat is not None:
                a.dst, a.dir = dist_bearing(lat, lon, a.lat, a.lon)

    def update(self, rows: list[dict], source: str, now: float | None = None):
        now = now or time.time()
        for r in rows:
            h = (r.get("hex") or "").lower()
            if len(h) != 6 or h.startswith("~"): continue        # non-ICAO / TIS-B targets
            if r.get("type") == "adsb_icao_nt": continue           # ground equipment (tower test sets)
            if r.get("r") == "TWR" or r.get("t") == "TWR": continue
            if str(r.get("category") or "").startswith("C"): continue   # surface vehicles, obstructions
            a = self.by_hex.get(h)
            if a is None:
                a = Aircraft(hex=h, first_seen=now)
                self.by_hex[h] = a
                self.new_hexes.add(h)
            a.sources.add(source)
            a.last_seen = now - float(r.get("seen", 0) or 0)
            if r.get("flight"): a.flight = r["flight"].strip()
            if r.get("r"): a.reg = r["r"].strip()
            if r.get("t"): a.type = r["t"].strip()
            if r.get("desc"): a.desc = r["desc"].strip()
            ab = r.get("alt_baro")
            if ab == "ground": a.on_ground, a.alt = True, 0
            elif isinstance(ab, (int, float)): a.on_ground, a.alt = False, int(ab)
            if r.get("gs") is not None: a.gs = float(r["gs"])
            hdg = r.get("track")
            if hdg is None: hdg = r.get("true_heading")
            if hdg is None: hdg = r.get("mag_heading")
            if hdg is not None: a.track = float(hdg)
            if r.get("baro_rate") is not None: a.vr = int(r["baro_rate"])
            if r.get("squawk"): a.squawk = str(r["squawk"])
            if r.get("category"): a.category = str(r["category"])
            if "dbFlags" in r:                                     # bitmask: 1 military, 2 interesting (4 PIA and 8 LADD are privacy flags, never shown)
                try: fl = int(r["dbFlags"])
                except (TypeError, ValueError): fl = 0
                a.military, a.interesting = bool(fl & 1), bool(fl & 2)
            lat, lon = r.get("lat"), r.get("lon")
            if lat is not None and lon is not None:
                tpos = now - float(r.get("seen_pos", 0) or 0)
                if (lat, lon) != (a.lat, a.lon):
                    a.trail.append((lat, lon, tpos))
                a.lat, a.lon, a.last_pos = lat, lon, tpos
                a.dst, a.dir = dist_bearing(self.home[0], self.home[1], lat, lon)
        # expire
        for h in [h for h, a in self.by_hex.items() if now - a.last_seen > STALE_S]:
            del self.by_hex[h]
        for a in self.by_hex.values():
            while a.trail and now - a.trail[0][2] > TRAIL_S:
                a.trail.popleft()

    def positioned(self) -> list[Aircraft]:
        return [a for a in self.by_hex.values() if a.lat is not None]

    def by_distance(self) -> list[Aircraft]:
        return sorted(self.positioned(), key=lambda a: a.dst if a.dst is not None else 9e9)

    def take_new(self) -> set[str]:
        n, self.new_hexes = self.new_hexes, set()
        return n
