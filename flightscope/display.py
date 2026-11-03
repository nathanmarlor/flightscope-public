"""Output backends. The Pi path renders into an ordinary pygame Surface and copies
it to /dev/fb0 each frame - the same route the boot console takes, so it works
wherever the console does. No GL, no compositor, no DRM master."""
from __future__ import annotations
import os
from pathlib import Path
import pygame

class FbDisplay:
    def __init__(self, dev="/dev/fb0", size=(800, 480)):
        sysfs = Path("/sys/class/graphics") / Path(dev).name
        self.bpp = int((sysfs / "bits_per_pixel").read_text())
        self.stride = int((sysfs / "stride").read_text())
        vw, vh = map(int, (sysfs / "virtual_size").read_text().split(","))
        self.w, self.h = size
        if (vw, vh) != size:
            print(f"display: fb is {vw}x{vh}, app is {self.w}x{self.h} - drawing top-left")
        # write(), not mmap: on DRM fbdev emulation a write() marks the region damaged
        # and gets it flushed to the scanout; mmap writes can sit in a shadow buffer.
        self.fd = os.open(dev, os.O_WRONLY)
        assert pygame.display.get_driver() == "dummy", f"SDL driver is {pygame.display.get_driver()}, expected dummy"
        pygame.display.set_mode((1, 1))            # dummy driver needs a window to exist
        self.surface = pygame.Surface(size)
        if self.bpp == 16:
            self._conv = pygame.Surface(size, 0, 16, (0xF800, 0x07E0, 0x001F, 0))
        elif self.bpp == 32:
            self._conv = pygame.Surface(size, 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
        else:
            raise RuntimeError(f"unsupported framebuffer depth {self.bpp}")
        self.row_bytes = self.w * self.bpp // 8

    def raw(self, surf) -> bytes:
        """surf as the framebuffer's own bytes (format and row padding) - `cat file > /dev/fb0` shows it."""
        self._conv.blit(surf, (0, 0)); buf = self._conv.get_buffer().raw
        if self.stride == self.row_bytes: return buf
        pad = b"\0" * (self.stride - self.row_bytes); rb = self.row_bytes
        return b"".join(buf[y * rb:(y + 1) * rb] + pad for y in range(self.h))

    def flip(self):
        self._conv.blit(self.surface, (0, 0))
        buf = self._conv.get_buffer().raw
        if self.stride == self.row_bytes:
            os.pwrite(self.fd, buf, 0)
        else:                                       # padded rows: one write per line
            rb, st = self.row_bytes, self.stride
            for y in range(self.h):
                os.pwrite(self.fd, buf[y * rb:(y + 1) * rb], y * st)

    def close(self):
        os.close(self.fd)

class SdlDisplay:
    """Desktop window or SDL kmsdrm - whatever SDL can present."""
    def __init__(self, size=(800, 480), windowed=False):
        if not windowed: os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")
        pygame.display.init()
        self.surface = pygame.display.set_mode(size, 0 if windowed else pygame.FULLSCREEN)
        pygame.display.set_caption("Flightscope")
        pygame.mouse.set_visible(windowed)
    def flip(self): pygame.display.flip()
    def close(self): pass

def _mode(cfg) -> str:
    m = os.environ.get("FLIGHTSCOPE_DISPLAY") or ("window" if cfg.windowed else "fb")
    return m if not (m == "fb" and not os.path.exists("/dev/fb0")) else "kmsdrm"

def select_driver(cfg):
    """Set SDL's video driver before pygame.init(). For the fb path SDL must NOT open
    the DRM device: a DRM master in this process stops the kernel flushing /dev/fb0."""
    m = _mode(cfg)
    if m == "fb": os.environ["SDL_VIDEODRIVER"] = "dummy"
    elif m == "kmsdrm": os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    else: os.environ.pop("SDL_VIDEODRIVER", None)

def make(cfg):
    m = _mode(cfg)
    if m == "fb": return FbDisplay()
    return SdlDisplay(windowed=(m == "window"))
