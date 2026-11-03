from __future__ import annotations
import pygame
from . import theme as T

def text(surf, s: str, size: int, color=T.INK, pos=(0, 0), anchor="topleft", bold=False, mono=False, weight=None) -> pygame.Rect:
    img = T.font(size, bold, mono, weight).render(s, True, color)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r

def fit_text(s: str, size: int, max_w: int, bold=False, mono=False, weight=None) -> str:
    f = T.font(size, bold, mono, weight)
    if f.size(s)[0] <= max_w: return s
    while s and f.size(s + "…")[0] > max_w: s = s[:-1]
    return s + "…"

class Button:
    def __init__(self, rect, label, size=15, bold=True, accent=False):
        self.rect = pygame.Rect(rect); self.label = label; self.size = size; self.bold = bold
        self.accent = accent; self.down = False

    def draw(self, surf):
        bg = T.SIGNAL if self.accent else (T.RULE_STRONG if self.down else T.SUNK)
        pygame.draw.rect(surf, bg, self.rect, border_radius=3)
        pygame.draw.rect(surf, T.RULE_STRONG if not self.accent else T.SIGNAL, self.rect, 1, border_radius=3)
        text(surf, self.label, self.size, T.GROUND if self.accent else T.INK, self.rect.center, "center", self.bold)

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

def pill(surf, s: str, pos, color, size=11) -> pygame.Rect:
    f = T.font(size, True, True)
    img = f.render(s, True, color)
    r = img.get_rect(topleft=pos).inflate(10, 4)
    pygame.draw.rect(surf, color, r, 1, border_radius=2)
    surf.blit(img, img.get_rect(center=r.center))
    return r

def badge(surf, s: str, pos, size=10) -> pygame.Rect:
    f = T.font(size, True, True)
    img = f.render(s, True, T.GROUND)
    r = img.get_rect(topleft=pos).inflate(8, 3)
    pygame.draw.rect(surf, T.SIGNAL, r, border_radius=2)
    surf.blit(img, img.get_rect(center=r.center))
    return r

_SCALED: dict[tuple, tuple] = {}
def vscale(surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
    """Scale to cover w×h, centre-cropped. Cached: smoothscale is far too slow to redo every frame on the Pi."""
    key = (id(surf), w, h); hit = _SCALED.get(key)
    if hit and hit[0] is surf: return hit[1]
    out = _vscale(surf, w, h)
    if len(_SCALED) >= 48: _SCALED.pop(next(iter(_SCALED)))
    _SCALED[key] = (surf, out)
    return out

def _vscale(surf, w, h):
    sw, sh = surf.get_size()
    k = max(w / sw, h / sh)
    s = pygame.transform.smoothscale(surf, (int(sw * k) + 1, int(sh * k) + 1))
    out = pygame.Surface((w, h))
    out.blit(s, ((w - s.get_width()) // 2, (h - s.get_height()) // 2))
    return out
