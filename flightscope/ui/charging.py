"""Plugged in and left alone: a big battery filling up, readable at a glance by a young child.
Shown by App after a minute without a touch while the HAT says it's charging; a tap (or unplugging) goes back.
The screen stays on, dim, while it charges, and is allowed to go dark once it has been full for a while."""
from __future__ import annotations
import math, time, pygame
from .widgets import text
from .kid import PAPER, ORANGE, GREEN, RED

W, H = 800, 480
NIGHT, NIGHT2, SOFT = (18, 28, 46), (30, 44, 68), (150, 166, 190)
BOLT = [(8, -36), (-20, 6), (-2, 6), (-10, 36), (20, -8), (2, -8), (12, -36)]

class ChargingScreen:
    FULL_DARK_S = 600            # full for this long: let the backlight go off as usual

    def __init__(self, app):
        self.app = app; self.t0 = time.time(); self.full_since = None
        self.sky = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            self.sky.fill(tuple(int(NIGHT[i] + (NIGHT2[i] - NIGHT[i]) * t) for i in range(3)), (0, y, W, 1))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN: self.app.pop()

    def update(self, dt):
        b = self.app.battery
        if not b.charging: return self.app.pop()                       # unplugged: back to whatever was there
        if b.state == "full": self.full_since = self.full_since or time.time()
        else: self.full_since = None

    @property
    def keep_lit(self) -> bool:
        return self.full_since is None or time.time() - self.full_since < self.FULL_DARK_S

    def draw(self, s):
        s.blit(self.sky, (0, 0))
        b = self.app.battery; full = b.state == "full"; pct = 100 if full else b.percent
        now = time.time()
        body = pygame.Rect(0, 0, 380, 180); body.center = (W // 2 - 14, 200)
        nub = pygame.Rect(body.right + 6, body.centery - 34, 26, 68)
        inner = body.inflate(-36, -36)
        pygame.draw.rect(s, (40, 56, 84), body, border_radius=34)
        if pct is not None:
            col = GREEN if full or pct >= 50 else ORANGE if pct >= 20 else RED
            fw = max(24, int(inner.w * pct / 100)); fill = pygame.Rect(inner.x, inner.y, fw, inner.h)
            pygame.draw.rect(s, col, fill, border_radius=18)
            if not full:                                                  # a glow sweeping into the battery: 'filling up'
                glow = pygame.Surface(fill.size, pygame.SRCALPHA)
                gx = int(((now - self.t0) % 2.0) / 2.0 * (fw + 120)) - 60
                for dx in range(-60, 61, 4):
                    a = int(90 * (1 - abs(dx) / 60))
                    pygame.draw.rect(glow, (255, 255, 255, a), (gx + dx, 0, 4, fill.h))
                mask = pygame.Surface(fill.size, pygame.SRCALPHA); pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=18)
                glow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                s.blit(glow, fill.topleft)
        pygame.draw.rect(s, PAPER, body, 10, border_radius=34)
        pygame.draw.rect(s, PAPER, nub, border_radius=10)
        if full:
            cx, cy = body.center                                          # a big tick: done
            tick = [(cx - 50, cy + 2), (cx - 14, cy + 38), (cx + 56, cy - 40)]
            pygame.draw.lines(s, PAPER, False, tick, 22)
            for p in tick: pygame.draw.circle(s, PAPER, p, 11)              # round ends and elbow
        else:
            sc = 1.6 + 0.08 * math.sin((now - self.t0) * 3)               # the bolt breathes gently
            pts = [(body.centerx + x * sc, body.centery + y * sc) for x, y in BOLT]
            pygame.draw.polygon(s, (255, 214, 64), pts); pygame.draw.polygon(s, NIGHT, pts, 5)
        label = "Full!" if full else (f"{pct}%" if pct is not None else "Charging")
        text(s, label, 64, PAPER, (W // 2, 360), "center", weight="black")
        small = "Tap to play" if full else (b.eta_text() if b.eta_text() else "Charging")
        text(s, small, 20, SOFT, (W // 2, 420), "center", weight="bold")
