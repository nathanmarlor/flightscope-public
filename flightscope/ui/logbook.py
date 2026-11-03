"""My Logbook: one card per plane he has caught, and a page listing where he's seen it go."""
from __future__ import annotations
import time, pygame
from . import theme as T
from .widgets import text, fit_text, vscale
from .kid import plane_art, Pill, route_line, draw_icon, PAPER, INK, INK_SOFT, CHIP, OUTLINE, ORANGE, GREEN
from .mapview import ROUTE, halo_text
from .. import names

def brand(e):
    """Stored airline name, passed through today's brand rule so old catches match new ones."""
    return names.short_airline(e["name"], e["name"])

def has_airline(e) -> bool:
    """The stored name is an airline only if it isn't just the kind of plane again."""
    k = e.get("kind") or ""
    return bool(e["name"]) and e["name"] not in (k, k.split(" (")[0]) and not names.is_kind_word(e["name"])

W, H = 800, 480
COLS, TW, TH, GAP, TOP = 2, 376, 140, 16, 76

def day(ts: float) -> str:
    t = time.localtime(ts); today = time.localtime()
    if t[:3] == today[:3]: return "Today"
    if t[:3] == time.localtime(time.time() - 86400)[:3]: return "Yesterday"
    return time.strftime("%a %-d %b", t)

def when(ts: float) -> str: return f"{day(ts)} at {time.strftime('%H:%M', time.localtime(ts))}"

_PHOTOS: dict[str, pygame.Surface | None] = {}
def photo(e):
    p = e.get("photo")
    if not p: return None
    if p not in _PHOTOS:
        try: _PHOTOS[p] = pygame.image.load(p).convert()
        except Exception: _PHOTOS[p] = None
    return _PHOTOS[p]

def trip_text(sight) -> tuple[str | None, str | None]:
    return sight.get("origin"), sight.get("dest")

class LogbookScreen:
    def __init__(self, app):
        self.app = app; self.airline = None            # (field, name): ("airline", "TUI") or ("kind", "Boeing 737 MAX")
        self.back = Pill((14, 14, 130, 50), "Map", size=19, icon="back")
        self.totals = Pill((W - 174, 14, 160, 50), "", ORANGE, PAPER, 17)
        self.clear = Pill((W - 174, 14, 160, 50), "", size=16, icon="close")
        self.scroll = 0.0; self._down = None; self._moved = 0; self._last = 0
        self.entries = []; self._refresh()

    def _refresh(self):
        es = self.app.logbook.entries
        if not self.airline: self.entries = es; return
        field, name = self.airline
        self.entries = [e for e in es if (brand(e) if field == "airline" else (e.get("kind") or "Plane")) == name]

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): return self.app.pop()
        if e.type == pygame.MOUSEBUTTONDOWN:
            self._down = e.pos; self._last = e.pos[1]; self._moved = 0; self.back.pressed = self.back.hit(e.pos)
            self.totals.pressed = not self.airline and self.totals.hit(e.pos); self.clear.pressed = bool(self.airline) and self.clear.hit(e.pos)
        elif e.type == pygame.MOUSEMOTION and self._down is not None:
            dy = e.pos[1] - self._last; self._last = e.pos[1]; self._moved += abs(dy)
            self.scroll = max(0, self.scroll - dy)
        elif e.type == pygame.MOUSEBUTTONUP and self._down is not None:
            self.back.pressed = self.totals.pressed = self.clear.pressed = False
            if self._moved < 12:
                if self.back.hit(e.pos): self.app.pop()
                elif self.airline and self.clear.hit(e.pos): self.airline = None; self.scroll = 0; self._refresh()
                elif not self.airline and self.entries and self.totals.hit(e.pos): self.app.push(TotalsScreen(self.app, self))
                else:
                    i = self._tile_at(e.pos)
                    if i is not None: self.app.push(LogEntryScreen(self.app, self.entries[i]))
            self._down = None

    def _tile_at(self, p):
        if p[1] < TOP: return None
        x0 = (W - (COLS * TW + (COLS - 1) * GAP)) // 2
        col = (p[0] - x0) // (TW + GAP); row = int((p[1] - TOP + self.scroll) // (TH + GAP))
        if col < 0 or col >= COLS or (p[0] - x0) % (TW + GAP) > TW: return None
        i = row * COLS + col
        return i if 0 <= i < len(self.entries) else None

    def update(self, dt):
        self._refresh()                              # a removal or a new catch shows up as soon as we're back here
        rows = (len(self.entries) + COLS - 1) // COLS
        self.scroll = min(self.scroll, max(0, rows * (TH + GAP) - (H - TOP) + GAP))

    def draw(self, s):
        s.fill(PAPER)
        x0 = (W - (COLS * TW + (COLS - 1) * GAP)) // 2
        s.set_clip(pygame.Rect(0, TOP, W, H - TOP))
        for i, e in enumerate(self.entries):
            r = pygame.Rect(x0 + (i % COLS) * (TW + GAP), TOP + (i // COLS) * (TH + GAP) - self.scroll, TW, TH)
            if r.bottom < TOP or r.top > H: continue
            pygame.draw.rect(s, CHIP, r, border_radius=16)
            pr = pygame.Rect(r.x + 10, r.y + 10, 150, TH - 20)
            ph = photo(e)
            if ph: s.blit(vscale(ph, pr.w, pr.h), pr)
            else:
                s.blit(plane_art(pr.w, pr.h, "", e.get("kind") == "Helicopter"), pr)
            draw_icon(s, "star", (pr.x + 14, pr.y + 14), ORANGE)
            if e["times_seen"] > 1:
                br = pygame.Rect(pr.x + 26, pr.y + 4, 34, 20); pygame.draw.rect(s, ORANGE, br, border_radius=10); pygame.draw.rect(s, PAPER, br, 2, border_radius=10)
                text(s, f"×{e['times_seen']}", 12, PAPER, br.center, "center", weight="black")
            tx = pr.right + 14; tw = r.right - tx - 10
            text(s, e.get("reg") or e["hex"].upper(), 26, INK, (tx, r.y + 6), "topleft", weight="black")
            text(s, fit_text(e.get("kind") or "Plane", 16, tw, weight="bold"), 16, INK_SOFT, (tx, r.y + 44), "topleft", weight="bold")
            if has_airline(e):
                text(s, fit_text(brand(e), 16, tw, weight="bold"), 16, INK_SOFT, (tx, r.y + 66), "topleft", weight="bold")
            text(s, day(e["last_seen"]), 13, INK_SOFT, (tx, r.bottom - 12), "bottomleft", weight="bold")
        s.set_clip(None)
        pygame.draw.rect(s, PAPER, (0, 0, W, TOP)); pygame.draw.line(s, OUTLINE, (0, TOP - 2), (W, TOP - 2), 2)
        self.back.draw(s)
        n = len(self.entries); cfg = self.app.cfg
        text(s, f"{cfg.possessive} Logbook" if cfg.owner else "My Logbook", 28, INK, (166, 39), "midleft", weight="black")
        if self.airline:
            name = self.airline[1]
            w = min(330, T.font(16, weight="extrabold").size(name)[0] + 72)    # fit the name, never the title
            self.clear.rect = pygame.Rect(W - 14 - w, 14, w, 50)
            self.clear.draw(s, label=name)
        elif n: self.totals.draw(s, label=f"{n} plane{'' if n == 1 else 's'}")
        if not self.entries:
            text(s, "No planes yet!", 34, INK_SOFT, (W / 2, 230), "center", weight="black")
            text(s, "Tap a plane on the map, then tap  + LOG", 20, INK_SOFT, (W / 2, 280), "center", weight="bold")

class LogEntryScreen:
    def __init__(self, app, e):
        self.app = app; self.e = e
        self.back = Pill((14, 14, 150, 50), "Logbook", size=19, icon="back"); self._down = None
        self.remove = Pill((W - 150, H - 58, 136, 44), "Remove", size=15, color=INK_SOFT)
        self.yes = Pill((W - 330, H - 62, 170, 50), "Yes, remove", (226, 84, 70), PAPER, 16)
        self.no = Pill((W - 150, H - 62, 136, 50), "Keep it", GREEN, PAPER, 16)
        self.confirming = False

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): return self.app.pop()
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self._down = ev.pos; self.back.pressed = self.back.hit(ev.pos)
            for b in (self.remove, self.yes, self.no): b.pressed = b.hit(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONUP:
            for b in (self.back, self.remove, self.yes, self.no): b.pressed = False
            if not self._down: return
            p = ev.pos; self._down = None
            if self.confirming:
                if self.yes.hit(p): self.app.logbook.remove(self.e["hex"]); return self.app.pop()
                if self.no.hit(p): self.confirming = False; return
                return
            if self.remove.hit(p): self.confirming = True; return
            self.app.pop()

    def update(self, dt): pass

    def draw(self, s):
        s.fill(PAPER); e = self.e
        pr = pygame.Rect(0, 0, W, 210); ph = photo(e)
        if ph: s.blit(vscale(ph, pr.w, pr.h), pr)
        else:
            s.blit(plane_art(pr.w, pr.h, "", e.get("kind") == "Helicopter", radius=0), pr)
        if ph and e.get("credit"): halo_text(s, f"photo: {e['credit']}", 11, INK_SOFT, (W - 10, pr.bottom - 8), "bottomright", bold=False)
        self.back.draw(s)
        y = pr.bottom + 8
        text(s, e.get("reg") or e["hex"].upper(), 34, INK, (20, y), "topleft", weight="black")
        draw_icon(s, "star", (W - 30, y + 22), ORANGE)
        n = e["times_seen"]
        text(s, f"Seen {n} time{'' if n == 1 else 's'}", 18, ORANGE, (W - 48, y + 22), "midright", weight="extrabold")
        y += 44
        what = e.get("kind") or "Plane"
        if has_airline(e): what += f"   ·   {brand(e)}"
        text(s, fit_text(f"{what}   ·   first caught {day(e['first_seen'])}", 16, 760, weight="bold"), 16, INK_SOFT, (20, y), "topleft", weight="bold")
        y += 32
        text(s, "WHERE I'VE SEEN IT GO", 13, INK_SOFT, (20, y), "topleft", weight="extrabold"); y += 22
        rows = e["sightings"][:5]
        for si in rows:
            r = pygame.Rect(20, y, W - 40, 34)
            pygame.draw.rect(s, CHIP, r, border_radius=10)
            text(s, when(si["at"]), 15, INK_SOFT, (r.x + 14, r.centery), "midleft", weight="bold")
            o, d = trip_text(si)
            if o or d: route_line(s, o or "?", d or "?", 17, ROUTE, (r.x + 200, r.y + 6), r.w - 220)
            else: text(s, "just flying around", 16, INK_SOFT, (r.x + 200, r.centery), "midleft", weight="bold")
            y += 40
        if len(e["sightings"]) > 5:
            text(s, f"and {len(e['sightings']) - 5} more", 14, INK_SOFT, (W / 2, y + 2), "midtop", weight="bold")
        if self.confirming:
            text(s, "Take this plane out of the logbook?", 17, INK, (W - 350, H - 37), "midright", weight="extrabold")
            self.yes.draw(s); self.no.draw(s)
        else:
            self.remove.draw(s)


class TotalsScreen:
    """The report: how many of each airline, how many of each kind. Tap an airline to see just those.
    A filter is a state of the grid beneath us, never a new screen - so Map always means the map."""
    def __init__(self, app, grid):
        self.app = app; self.grid = grid
        self.back = Pill((14, 14, 150, 50), "Logbook", size=19, icon="back"); self._down = None
        from collections import Counter
        es = app.logbook.entries
        self.airlines = Counter(brand(e) for e in es if has_airline(e)).most_common()
        self.kinds = Counter(e.get("kind") or "Plane" for e in es).most_common()
        self.rows: list[tuple[pygame.Rect, tuple]] = []

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): return self.app.pop()
        if ev.type == pygame.MOUSEBUTTONDOWN: self._down = ev.pos; self.back.pressed = self.back.hit(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONUP and self._down:
            self.back.pressed = False; p = ev.pos; self._down = None
            if self.back.hit(p): return self.app.pop()
            for r, flt in self.rows:
                if r.collidepoint(p):
                    self.grid.airline = flt; self.grid.scroll = 0; self.grid._refresh()
                    return self.app.pop()

    def update(self, dt): pass

    def _section(self, s, title, items, x, y, w, field):
        text(s, title, 13, INK_SOFT, (x, y), "topleft", weight="extrabold"); y += 24
        top = max((n for _, n in items), default=1)
        for name, n in items[:7]:
            r = pygame.Rect(x, y, w, 38)
            pygame.draw.rect(s, CHIP, r, border_radius=10)
            bar = pygame.Rect(x + 4, y + 4, int((w - 8) * n / top), 30)
            pygame.draw.rect(s, (255, 214, 160) if field == "airline" else (205, 222, 236), bar, border_radius=8)
            text(s, fit_text(name, 17, w - 70, weight="extrabold"), 17, INK, (x + 14, r.centery), "midleft", weight="extrabold")
            text(s, str(n), 19, ORANGE if field == "airline" else (36, 120, 220), (r.right - 14, r.centery), "midright", weight="black")
            self.rows.append((r, (field, name)))
            y += 44
        if len(items) > 7: text(s, f"and {len(items) - 7} more", 13, INK_SOFT, (x, y), "topleft", weight="bold")

    def draw(self, s):
        s.fill(PAPER); self.rows = []
        self.back.draw(s)
        n = len(self.app.logbook.entries)
        text(s, f"{n} plane{'' if n == 1 else 's'} caught", 28, INK, (186, 39), "midleft", weight="black")
        pygame.draw.line(s, OUTLINE, (0, TOP - 2), (W, TOP - 2), 2)
        self._section(s, "BY AIRLINE  ·  tap one to see them", self.airlines, 20, TOP + 14, 370, "airline")
        self._section(s, "BY PLANE  ·  tap one to see them", self.kinds, 410, TOP + 14, 370, "kind")
