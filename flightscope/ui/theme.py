"""One palette, one type scale. Instrument-panel dark; amber is the only accent."""
from __future__ import annotations
import pygame

GROUND      = (11, 18, 25)
SURFACE     = (20, 29, 38)
SUNK        = (16, 24, 32)
INK         = (230, 236, 241)
INK2        = (195, 206, 216)
MUTED       = (139, 155, 169)
RULE        = (36, 52, 65)
RULE_STRONG = (53, 74, 90)
SIGNAL      = (240, 162, 74)
DATA        = (95, 182, 214)
OK          = (79, 183, 132)
WARN        = (214, 163, 46)
RISK        = (226, 112, 95)
COAST       = (58, 84, 104)
GROUND_AC   = (120, 130, 140)

_FONTS: dict[tuple, pygame.font.Font] = {}
_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "fonts"
_NUNITO = {"regular": "Nunito-Regular.ttf", "bold": "Nunito-Bold.ttf", "extrabold": "Nunito-ExtraBold.ttf", "black": "Nunito-Black.ttf"}
_DEJAVU = {"regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "monobold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"}

def font(size: int, bold=False, mono=False, weight: str | None = None) -> pygame.font.Font:
    """Nunito (rounded, friendly) for everything a child reads; DejaVu Mono for the odd code."""
    import os
    w = weight or ("bold" if bold else "regular")
    key = (size, w, mono)
    if key not in _FONTS:
        if mono:
            path = _DEJAVU["monobold" if bold else "mono"]
        else:
            path = str(_DIR / _NUNITO[w])
            if not os.path.exists(path): path = _DEJAVU["bold" if w != "regular" else "regular"]
        try: _FONTS[key] = pygame.font.Font(path if os.path.exists(path) else None, size)
        except Exception: _FONTS[key] = pygame.font.Font(None, size)
    return _FONTS[key]

# altitude -> colour, low warm to high cool (like a real scope, and like tar1090)
_STOPS = [(0, (226, 112, 95)), (2000, (240, 162, 74)), (6000, (214, 190, 60)), (12000, (120, 200, 120)),
          (20000, (80, 190, 190)), (30000, (95, 150, 230)), (42000, (170, 120, 230))]

def alt_color(alt: int | None, on_ground=False) -> tuple:
    if on_ground: return GROUND_AC
    if alt is None: return MUTED
    if alt <= _STOPS[0][0]: return _STOPS[0][1]
    for (a0, c0), (a1, c1) in zip(_STOPS, _STOPS[1:]):
        if alt <= a1:
            t = (alt - a0) / (a1 - a0)
            return tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
    return _STOPS[-1][1]
