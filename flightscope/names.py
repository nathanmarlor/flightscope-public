"""Words a young child can read: airline names from callsigns, tidy aircraft types."""
from __future__ import annotations
import json, re
from pathlib import Path

_AIRLINES = json.load(open(Path(__file__).resolve().parent / "data" / "airlines.json"))
_TYPES = {"A20N": "Airbus A320neo", "A21N": "Airbus A321neo", "A319": "Airbus A319", "A320": "Airbus A320", "A321": "Airbus A321",
          "A332": "Airbus A330", "A333": "Airbus A330", "A339": "Airbus A330neo", "A343": "Airbus A340", "A346": "Airbus A340",
          "A359": "Airbus A350", "A35K": "Airbus A350", "A388": "Airbus A380 (double-decker!)",
          "B737": "Boeing 737", "B738": "Boeing 737", "B739": "Boeing 737", "B38M": "Boeing 737 MAX", "B39M": "Boeing 737 MAX",
          "B752": "Boeing 757", "B763": "Boeing 767", "B772": "Boeing 777", "B77W": "Boeing 777", "B77L": "Boeing 777",
          "B788": "Boeing 787 Dreamliner", "B789": "Boeing 787 Dreamliner", "B78X": "Boeing 787 Dreamliner", "B744": "Boeing 747 Jumbo Jet", "B748": "Boeing 747 Jumbo Jet",
          "E190": "Embraer 190", "E195": "Embraer 195", "E75L": "Embraer 175", "E290": "Embraer E2", "E295": "Embraer E2",
          "AT72": "ATR 72 (propellers)", "AT76": "ATR 72 (propellers)", "DH8D": "Dash 8 (propellers)", "SF34": "Saab 340 (propellers)",
          "C172": "Cessna (little plane)", "C152": "Cessna (little plane)", "PA28": "Piper (little plane)", "P28A": "Piper (little plane)",
          "EC35": "Helicopter", "EC45": "Helicopter", "EC55": "Helicopter", "H145": "Helicopter", "A139": "Helicopter", "AS55": "Helicopter", "R44": "Helicopter", "B06": "Helicopter",
          "A400": "RAF Atlas", "C17": "RAF Globemaster", "C130": "Hercules", "EUFI": "Typhoon fighter jet", "F35": "F-35 fighter jet", "HAWK": "Hawk jet", "TEX2": "Texan trainer"}

def airline(callsign: str) -> str | None:
    cs = (callsign or "").strip().upper()
    if len(cs) >= 4 and cs[:3].isalpha() and cs[3:4].isdigit():
        return _AIRLINES.get(cs[:3])
    return None

def tidy_type(d: str) -> str:
    """Undo .title() on the bits that are really letters: 'Beluga XL', '737 MAX', not 'Xl', 'Max'."""
    return re.sub(r"\b(Xl|Xlr|Lr|Er|Erj|Sp|Sr|Max|Atr|Crj)\b", lambda m: m.group(1).upper(), d)

def plane_type(t: str, desc: str = "") -> str:
    if t in _TYPES: return _TYPES[t]
    if desc:
        d = desc.title().replace("Airbus A-", "Airbus A").replace("Boeing ", "Boeing ")
        return tidy_type(re.sub(r"\s+", " ", d))[:28]
    return t or "a plane"

_BRAND = {   # what is painted on the plane, not the operating company
    "easyjet": "easyJet", "ryanair": "Ryanair", "buzz": "Ryanair", "malta air": "Ryanair", "lauda": "Lauda",
    "british airways": "British Airways", "ba cityflyer": "British Airways", "ba euroflyer": "British Airways",
    "klm": "KLM", "lufthansa": "Lufthansa", "tui": "TUI", "jet2": "Jet2", "wizz": "Wizz Air", "norwegian": "Norwegian",
    "swiss": "Swiss", "aer lingus": "Aer Lingus", "air france": "Air France", "eurowings": "Eurowings", "austrian": "Austrian",
    "tap": "TAP", "delta": "Delta", "united": "United", "air canada": "Air Canada", "etihad": "Etihad", "qatar": "Qatar Airways",
    "emirates": "Emirates", "virgin atlantic": "Virgin Atlantic", "vueling": "Vueling", "iberia": "Iberia", "loganair": "Loganair",
    "turkish": "Turkish Airlines", "pegasus": "Pegasus", "sunexpress": "SunExpress", "condor": "Condor", "finnair": "Finnair",
    "sas": "SAS", "scandinavian": "SAS", "icelandair": "Icelandair", "air transat": "Air Transat", "westjet": "WestJet",
    "american": "American Airlines", "fedex": "FedEx", "ups": "UPS", "dhl": "DHL", "cargolux": "Cargolux",
    "singapore": "Singapore Airlines", "cathay": "Cathay Pacific", "ethiopian": "Ethiopian", "hainan": "Hainan Airlines",
    "air india": "Air India", "royal air maroc": "Royal Air Maroc", "aegean": "Aegean", "brussels": "Brussels Airlines",
    "atlas air": "Atlas Air", "elite": "Elite Air", "blue islands": "Blue Islands", "aurigny": "Aurigny", "eastern": "Eastern Airways"}
_JUNK = (" Ltd", " Limited", " plc", " PLC", " Inc", " Inc.", " GmbH", " S.A.", " SA", " AG", " Co.", " Europe", " UK", " Malta",
         " Switzerland", " Cityhopper", " CityLine", " Air Shuttle", " International", " Discover", " Rouge", " Hop", ".com")

def short_airline(name: str | None, fallback: str) -> str:
    """The brand a child sees on the plane: subsidiaries and regional arms collapse to the parent."""
    if not name: return fallback
    low = name.lower()
    for key, brand in _BRAND.items():
        if low.startswith(key) or f" {key}" in low: return brand
    for junk in _JUNK:
        if name.endswith(junk): name = name[: -len(junk)]
    return name.strip() or fallback

def is_kind_word(name: str) -> bool:
    """True for our own words for a sort of plane ('Big jet', 'Helicopter') - never an airline."""
    return name in KIND_WORDS

_CATEGORY = {"A1": "Small plane", "A2": "Small plane", "A3": "Airliner", "A4": "Big jet", "A5": "Big jet", "A6": "Fast jet",
             "A7": "Helicopter", "B1": "Glider", "B2": "Balloon", "B4": "Microlight", "B6": "Drone"}
KIND_WORDS = set(_CATEGORY.values()) | {"Plane", "Helicopter", "Airliner", "Small plane", "a plane"}

_HELI = {"AS50", "AS55", "AS65", "AS32", "EC20", "EC30", "EC35", "EC45", "EC55", "EC75", "H135", "H145", "H160", "H175", "A109", "A119", "A139",
         "A169", "A189", "AW09", "B06", "B105", "B212", "B412", "B429", "B407", "B430", "B505", "S76", "S92", "R22", "R44", "R66", "G2CA", "MD52", "MD60",
         "EH10", "LYNX", "PUMA", "H60", "H64", "CH47", "WLWT", "A1NG", "S61"}

def kind(a) -> str:
    """What sort of flying thing this is, in a child's words. Never a raw code."""
    if a.type in _HELI: return "Helicopter"
    if a.type:
        t = plane_type(a.type, "")
        if t != a.type: return t.split(" (")[0]
    if a.category in _CATEGORY: return _CATEGORY[a.category]
    if a.type: return "Small plane" if a.type[0] in "CPDRSGBMTVZ" and len(a.type) <= 4 else "Plane"
    return "Plane"

def label_for(a, route=None) -> str:
    """Best child-readable name: airline (adsbdb first, then callsign prefix), else the kind of plane."""
    al = (route.airline if route and route.airline else None) or airline(a.flight)
    if al: return short_airline(al, kind(a))
    return kind(a)

def place(ap) -> str:
    """'Paisley, Renfrewshire' -> 'Paisley'. The bit before the comma is what a child says."""
    if not ap: return "?"
    import re
    c = (ap.get("city") or ap.get("name") or ap.get("iata") or "?")
    m = re.search(r"\(([^)]+)\)", c)            # "Zemunik (Zadar)" -> "Zadar"
    if m and len(m.group(1)) > 2: return m.group(1).strip()
    return c.split(",")[0].split("/")[0].strip()

def mins(m: float) -> str:
    m = int(round(m))
    if m < 1: return "less than a minute"
    if m < 60: return f"{m} min"
    return f"{m // 60} h {m % 60:02d} min"

def flight_times_short(a, route) -> tuple[str | None, str | None]:
    """Chip-length versions: 'took off 23 min ago', 'lands in 46 min'."""
    ago, eta = flight_times(a, route)
    return (ago.replace("about ", "") if ago else None, eta.replace("about ", "") if eta else None)

def flight_times(a, route) -> tuple[str | None, str | None]:
    """('took off about 40 min ago', 'lands in about 25 min') estimated from distances and speed."""
    from .geo import gc_nm
    if a.lat is None or a.on_ground or not route: return None, None
    gs = max(float(a.gs or 0), 120.0)
    # a climbing or descending plane is slow now but cruises at ~420 kt for most of a long leg
    v = lambda leg: gs if leg < 150 else max(gs, 420.0)
    ago = eta = None
    o, d = route.origin, route.dest
    if o and o.get("lat") is not None:
        flown = gc_nm(o["lat"], o["lon"], a.lat, a.lon)
        ago = "just taken off" if flown < 8 else f"took off about {mins(flown / v(flown) * 60 + 3)} ago"
    if d and d.get("lat") is not None:
        left = gc_nm(a.lat, a.lon, d["lat"], d["lon"])
        eta = "landing now!" if left < 6 else f"lands in about {mins(left / v(left) * 60 + 6)}"
    return ago, eta

def plausible_route(a, route):
    """adsbdb routes are keyed on callsign and go stale; keep one only if the plane sits roughly
    between its two airports. Otherwise return the airline name alone."""
    if route is None or a.lat is None: return route
    o, d = route.origin, route.dest
    if not (o and d and o.get("lat") is not None and d.get("lat") is not None): return route
    from .geo import gc_nm
    direct = gc_nm(o["lat"], o["lon"], d["lat"], d["lon"])
    via = gc_nm(o["lat"], o["lon"], a.lat, a.lon) + gc_nm(a.lat, a.lon, d["lat"], d["lon"])
    if via > direct * 1.25 + 120:
        from .routes import Route
        return Route(None, None, route.airline)
    return route
