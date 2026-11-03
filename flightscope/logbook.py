"""His collection. One entry per AIRFRAME (ICAO hex), each holding a short list of sightings.
Nothing here is written by the map loop - only by a press of the LOG button."""
from __future__ import annotations
import json, time
from pathlib import Path
from . import safefile

AGAIN_AFTER_S = 2 * 3600      # a repeat press counts as a new sighting only after this, or on a new callsign
MAX_SIGHTINGS = 20
MAX_PLANES = 100              # a full book: LOG greys out; a book loaded over this keeps its newest

class Logbook:
    def __init__(self, cfg):
        self.dir = Path(cfg.cache_dir).parent / "flightscope-logbook"
        (self.dir / "photos").mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "logbook.json"
        self.by_hex: dict[str, dict] = {}
        if self.path.exists():
            try:
                for e in json.load(open(self.path)):
                    if "sightings" in e:
                        if e.get("kind"):
                            from .names import tidy_type
                            e["kind"] = tidy_type(e["kind"])            # older catches were stored as 'Beluga Xl'
                        self.by_hex[e["hex"]] = e
            except ValueError: pass
        if len(self.by_hex) > MAX_PLANES: self._trim()

    # ---- reads (cheap; safe to call every frame) ----
    def has(self, hex: str) -> bool: return hex in self.by_hex
    def get(self, hex: str) -> dict | None: return self.by_hex.get(hex)
    @property
    def full(self) -> bool: return len(self.by_hex) >= MAX_PLANES

    @property
    def entries(self) -> list[dict]:
        return sorted(self.by_hex.values(), key=lambda e: -e["last_seen"])

    def state(self, a) -> str:
        """'new' (never caught), 'again' (a press would count), 'same' (already counted this flight), or 'full'
        (a new plane, but the book has no room)."""
        e = self.by_hex.get(a.hex)
        if e is None: return "full" if self.full else "new"
        last = e["sightings"][0] if e["sightings"] else None
        if last is None: return "again"
        if (a.flight or "") != (last.get("flight") or "") or time.time() - last["at"] > AGAIN_AFTER_S: return "again"
        return "same"

    # ---- the one write path ----
    def press(self, a, route, photo_src: Path | None, credit: str = "") -> str:
        from . import names
        st = self.state(a)
        if st in ("same", "full"): return st
        sight = {"at": time.time(), "flight": a.flight or "",
                 "origin": names.place(route.origin) if route and route.origin else None,
                 "dest": names.place(route.dest) if route and route.dest else None}
        e = self.by_hex.get(a.hex)
        if e is None:
            e = {"hex": a.hex, "reg": a.reg, "type": a.type, "kind": names.plane_type(a.type, a.desc) if a.type else names.kind(a),
                 "name": names.label_for(a, route), "photo": None, "credit": "",
                 "first_seen": sight["at"], "last_seen": sight["at"], "times_seen": 0, "sightings": []}
            self.by_hex[a.hex] = e
        e["sightings"].insert(0, sight); del e["sightings"][MAX_SIGHTINGS:]
        e["last_seen"] = sight["at"]; e["times_seen"] += 1
        if not e.get("photo") and photo_src and Path(photo_src).exists():
            dst = self.dir / "photos" / f"{a.hex}.jpg"; safefile.copy_file(photo_src, dst); e["photo"], e["credit"] = str(dst), credit
        self._save()
        return st

    def remove(self, hex: str):
        e = self.by_hex.pop(hex, None)
        if e is None: return
        if e.get("photo"):
            try: safefile.remove(e["photo"])
            except OSError: pass
        self._save()

    def _trim(self):
        """Over the limit (an older build had none): drop the planes seen longest ago, with their photos."""
        for e in sorted(self.by_hex.values(), key=lambda e: e["last_seen"])[: len(self.by_hex) - MAX_PLANES]:
            print(f"logbook: full, dropping {e['hex']} (last seen {time.strftime('%Y-%m-%d', time.localtime(e['last_seen']))})", flush=True)
            self.remove(e["hex"])

    def _save(self):
        safefile.write_text(self.path, json.dumps(list(self.by_hex.values())))
