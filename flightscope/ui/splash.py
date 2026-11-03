"""Loading screen: a plane flies across the sky for a few seconds, then the map. Finding planes happens on the map
(its 'Looking for planes' banner), so a slow feed never keeps a child staring at this. Its first frame, frozen, is
also the boot screen (App.save_boot_frame -> flightscope-bootsplash.service), so the boot picture comes alive."""
from __future__ import annotations
import math, time, pygame
from . import theme as T
from .widgets import text
from .kid import PAPER, INK, INK_SOFT, ORANGE

W, H = 800, 480
SKY_TOP, SKY_BOTTOM = (150, 205, 245), (214, 236, 252)
PLANE = [(0, -11), (2, -7), (2, -2), (11, 3), (11, 5), (2, 3), (2, 7), (5, 10), (5, 11), (0, 10),
         (-5, 11), (-5, 10), (-2, 7), (-2, 3), (-11, 5), (-11, 3), (-2, -2), (-2, -7)]

class SplashScreen:
    def __init__(self, app):
        self.app = app; self.t0 = time.time()
        self.sky = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            self.sky.fill(tuple(int(SKY_TOP[i] + (SKY_BOTTOM[i] - SKY_TOP[i]) * t) for i in range(3)), (0, y, W, 1))

    HOLD_S = 4.0                      # one good look at the plane, then the map

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and time.time() - self.t0 > 1.0: self.app.replace(self.app.make_main())

    def update(self, dt):
        if time.time() - self.t0 > self.HOLD_S: self.app.replace(self.app.make_main())

    def draw(self, s, up=None):
        s.blit(self.sky, (0, 0))
        if up is None: up = time.time() - self.t0
        # sun
        pygame.draw.circle(s, (255, 226, 120), (690, 90), 44); pygame.draw.circle(s, (255, 244, 190), (690, 90), 34)
        # the map's own plane shape, big, crossing the sky with a dotted trail behind it
        x = (up * 130 + 240) % (W + 400) - 200; y = 200 + 16 * math.sin(up * 1.2)
        for i in range(1, 50):
            px = x - 40 - i * 14
            if -20 < px < W + 20: pygame.draw.circle(s, (255, 255, 255), (px, y + 3 * math.sin((up - i * 0.1) * 1.2)), 3)
        sc = 4.6; t = math.radians(90); ct, st = math.cos(t), math.sin(t)
        poly = [(x + (px * ct - py * st) * sc, y + (px * st + py * ct) * sc) for px, py in PLANE]
        pygame.draw.polygon(s, (120, 170, 210), [(a + 5, b + 7) for a, b in poly])
        pygame.draw.polygon(s, PAPER, poly); pygame.draw.polygon(s, INK, poly, 3)
        text(s, self.app.cfg.splash_title, 62, INK, (W / 2, 330), "center", weight="black")
        for i in range(3):                                         # three hopping dots: 'getting ready', no reading needed
            hop = max(0.0, math.sin(up * 6 - i * 0.9)) * 10 if up > 0 else 0
            pygame.draw.circle(s, ORANGE, (W / 2 - 30 + i * 30, 405 - hop), 8)
