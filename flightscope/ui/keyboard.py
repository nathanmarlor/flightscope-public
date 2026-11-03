"""On-screen keyboard: one field, big keys, Done. Used by the setup screen for names, passwords and the like."""
from __future__ import annotations
import time, pygame
from . import theme as T
from .widgets import text, fit_text
from .kid import Pill, draw_icon, PAPER, INK, INK_SOFT, CHIP, OUTLINE, ORANGE, GREEN, SHADOW

W, H = 800, 480
ROWS = [["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
        ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
        ["z", "x", "c", "v", "b", "n", "m"]]
SYMS = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["-", "_", "/", ":", ";", "(", ")", "£", "&", "@"],
        [".", ",", "?", "!", "'", "\"", "#", "%", "+", "="]]
KW, KH, GAP, TOP = 70, 58, 8, 122

class KeyboardScreen:
    def __init__(self, app, title, initial="", on_done=None, secret=False, hint=""):
        self.app = app; self.title = title; self.value = initial; self.on_done = on_done; self.secret = secret; self.hint = hint
        self.shift = False; self.caps = False; self.syms = False; self.show = not secret
        self.cancel = Pill((14, 14, 130, 50), "Back", size=19, icon="back")
        self.done = Pill((W - 154, 14, 140, 50), "Done", GREEN, PAPER, 19, icon="tick")
        self.keys: list[tuple[pygame.Rect, str]] = []; self._pressed = None; self._down = None
        self._repeat = None
        self._layout()

    def _layout(self):
        self.keys = []
        rows = SYMS if self.syms else ROWS
        for r, row in enumerate(rows):
            n = len(row); x0 = (W - (n * KW + (n - 1) * GAP)) // 2; y = TOP + r * (KH + GAP)
            for i, k in enumerate(row):
                self.keys.append((pygame.Rect(x0 + i * (KW + GAP), y, KW, KH), k))
            if r == 2 and not self.syms:                                   # shift sits left of z, same size as a key
                self.keys.append((pygame.Rect(x0 - GAP - KW - 14, y, KW + 14, KH), "shift"))
        y = TOP + 3 * (KH + GAP)
        self.keys.append((pygame.Rect(40, y, 110, KH), "123" if not self.syms else "abc"))
        self.keys.append((pygame.Rect(160, y, W - 160 - 10 - 96 - 10 - 110 - 40, KH), "space"))
        self.keys.append((pygame.Rect(W - 40 - 110 - 10 - 96, y, 96, KH), "bksp"))
        self.keys.append((pygame.Rect(W - 150, y, 110, KH), "done"))

    def _type(self, k):
        if k == "shift":
            if self.shift and time.time() - getattr(self, "_shift_at", 0) < 0.4: self.caps = not self.caps; self.shift = self.caps
            else: self.shift = not self.shift; self.caps = False
            self._shift_at = time.time(); return
        if k == "bksp": self.value = self.value[:-1]; return
        if k in ("123", "abc"): self.syms = not self.syms; self._layout(); return
        if k == "space": self.value += " "; return
        if k == "done": return self.finish()
        if len(self.value) >= 64: return
        ch = k.upper() if (self.shift or self.caps) and k.isalpha() else k
        self.value += ch
        if self.shift and not self.caps: self.shift = False

    def finish(self):
        self.app.pop()
        if self.on_done: self.on_done(self.value)

    def handle(self, e):
        if e.type == pygame.KEYDOWN:                                  # a real keyboard works too (dev)
            if e.key == pygame.K_ESCAPE: return self.app.pop()
            if e.key == pygame.K_RETURN: return self.finish()
            if e.key == pygame.K_BACKSPACE: self.value = self.value[:-1]; return
            if e.unicode and e.unicode.isprintable(): self.value += e.unicode
            return
        if e.type == pygame.MOUSEBUTTONDOWN:
            self._down = e.pos; self.cancel.pressed = self.cancel.hit(e.pos); self.done.pressed = self.done.hit(e.pos)
            self._pressed = next((k for r, k in self.keys if r.collidepoint(e.pos)), None)
            if self._pressed == "bksp": self._repeat = time.time() + 0.45
        elif e.type == pygame.MOUSEBUTTONUP:
            self.cancel.pressed = self.done.pressed = False; self._repeat = None
            if self._down is None: return
            p = e.pos; self._down = None; k = self._pressed; self._pressed = None
            if self.cancel.hit(p): return self.app.pop()
            if self.done.hit(p): return self.finish()
            if self.secret and pygame.Rect(W - 210, 74, 44, 44).collidepoint(p): self.show = not self.show; return
            if k is not None and any(r.collidepoint(p) and kk == k for r, kk in self.keys): self._type(k)

    def update(self, dt):
        if self._repeat and time.time() > self._repeat:            # held backspace
            self.value = self.value[:-1]; self._repeat = time.time() + 0.08

    def draw(self, s):
        s.fill(PAPER)
        self.cancel.draw(s); self.done.draw(s)
        text(s, self.title, 22, INK, (W / 2, 39), "center", weight="black")
        fr = pygame.Rect(40, 74, W - 80, 44)
        pygame.draw.rect(s, CHIP, fr, border_radius=12); pygame.draw.rect(s, OUTLINE, fr, 2, border_radius=12)
        shown = self.value if (self.show or not self.secret) else "•" * len(self.value)
        if shown: text(s, fit_text(shown, 22, fr.w - 90, weight="bold"), 22, INK, (fr.x + 16, fr.centery), "midleft", weight="bold")
        elif self.hint: text(s, self.hint, 18, INK_SOFT, (fr.x + 16, fr.centery), "midleft", weight="bold")
        cx = fr.x + 16 + T.font(22, weight="bold").size(shown)[0] + 2
        if int(time.time() * 2) % 2 == 0: pygame.draw.rect(s, ORANGE, (cx, fr.y + 9, 3, fr.h - 18))
        if self.secret: draw_icon(s, "eye", (W - 188, 96), INK if self.show else INK_SOFT)
        for r, k in self.keys:
            down = self._pressed == k and self._down is not None
            rr = r.move(0, 3) if down else r
            if not down: pygame.draw.rect(s, SHADOW, r.move(0, 3), border_radius=12)
            special = k in ("shift", "bksp", "123", "abc", "space", "done")
            fill = GREEN if k == "done" else (ORANGE if k == "shift" and (self.shift or self.caps) else (CHIP if special else PAPER))
            pygame.draw.rect(s, fill, rr, border_radius=12); pygame.draw.rect(s, OUTLINE, rr, 2, border_radius=12)
            if k == "bksp": draw_icon(s, "back", (rr.centerx, rr.centery), INK); pygame.draw.line(s, INK, (rr.centerx - 2, rr.centery), (rr.centerx + 9, rr.centery), 4)
            elif k == "shift":
                pygame.draw.polygon(s, PAPER if (self.shift or self.caps) else INK, [(rr.centerx, rr.centery - 12), (rr.centerx + 12, rr.centery), (rr.centerx + 5, rr.centery), (rr.centerx + 5, rr.centery + 10), (rr.centerx - 5, rr.centery + 10), (rr.centerx - 5, rr.centery), (rr.centerx - 12, rr.centery)])
            elif k == "space": pass
            elif k == "done": text(s, "Done", 20, PAPER, rr.center, "center", weight="extrabold")
            else:
                lab = k.upper() if (self.shift or self.caps) and k.isalpha() else k
                text(s, lab if len(k) == 1 else k, 24 if len(k) == 1 else 18, INK, rr.center, "center", weight="extrabold")
