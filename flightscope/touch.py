"""Touch input straight from the panel's evdev node. One finger becomes the pygame
mouse events the screens already use; two fingers become PINCH events."""
from __future__ import annotations
import math, threading
import pygame

PINCH = pygame.USEREVENT + 1      # attrs: phase in start/move/end, scale (vs start), center (x, y)

try:
    import evdev
    from evdev import ecodes as E
except ImportError:
    evdev = None

def find_device(hint="ft5x06"):
    if evdev is None: return None
    for p in evdev.list_devices():
        d = evdev.InputDevice(p)
        caps = d.capabilities()
        if hint in d.name.lower() or (E.EV_ABS in caps and E.ABS_MT_POSITION_X in dict(caps.get(E.EV_ABS, []))):
            return d
    return None

class Touch:
    def __init__(self, size=(800, 480), hint="ft5x06"):
        self.w, self.h = size
        self.hint = hint; self.dev = find_device(hint)
        self.ok = self.dev is not None
        if not self.ok:
            print("touch: no evdev touchscreen found yet - will keep looking", flush=True)
            threading.Thread(target=self._wait_for_panel, name="touch-find", daemon=True).start(); return
        self._start()

    def _wait_for_panel(self):
        """The panel's I2C sometimes isn't ready when the kernel probes it at boot (probe fails with -5),
        so the touchscreen never appears. Re-binding the driver later fixes it; keep trying."""
        import subprocess, time
        for i in range(120):
            time.sleep(3)
            self.dev = find_device(self.hint)
            if self.dev: self.ok = True; self._start(); return
            if i % 3 == 0:
                subprocess.run(["sudo", "-n", "sh", "-c", "echo 10-0038 > /sys/bus/i2c/drivers/edt_ft5x06/bind"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("touch: gave up looking for the touchscreen", flush=True)

    def _start(self):
        caps = dict(self.dev.capabilities(absinfo=True).get(E.EV_ABS, []))
        ax = caps.get(E.ABS_MT_POSITION_X) or caps.get(E.ABS_X)
        ay = caps.get(E.ABS_MT_POSITION_Y) or caps.get(E.ABS_Y)
        self.xr = (ax.min, ax.max) if ax else (0, self.w - 1)
        self.yr = (ay.min, ay.max) if ay else (0, self.h - 1)
        print(f"touch: {self.dev.path} '{self.dev.name}' x{self.xr} y{self.yr}")
        threading.Thread(target=self._run, name="touch", daemon=True).start()

    def _scale(self, x, y):
        sx = (x - self.xr[0]) / max(1, self.xr[1] - self.xr[0]) * (self.w - 1)
        sy = (y - self.yr[0]) / max(1, self.yr[1] - self.yr[0]) * (self.h - 1)
        return int(min(self.w - 1, max(0, sx))), int(min(self.h - 1, max(0, sy)))

    def _run(self):
        post = pygame.event.post; Ev = pygame.event.Event
        slots: dict[int, list] = {}; cur = 0
        single = False; multi = False; d0 = 1.0
        for ev in self.dev.read_loop():
            if ev.type == E.EV_ABS:
                if ev.code == E.ABS_MT_SLOT: cur = ev.value
                elif ev.code == E.ABS_MT_TRACKING_ID:
                    if ev.value == -1: slots.pop(cur, None)
                    else: slots.setdefault(cur, [None, None])
                elif ev.code == E.ABS_MT_POSITION_X: slots.setdefault(cur, [None, None])[0] = ev.value
                elif ev.code == E.ABS_MT_POSITION_Y: slots.setdefault(cur, [None, None])[1] = ev.value
            elif ev.type == E.EV_SYN and ev.code == E.SYN_REPORT:
                live = [self._scale(*v) for v in slots.values() if v[0] is not None and v[1] is not None]
                if len(live) >= 2:
                    (x1, y1), (x2, y2) = live[0], live[1]
                    d = max(1.0, math.hypot(x2 - x1, y2 - y1)); c = ((x1 + x2) // 2, (y1 + y2) // 2)
                    if not multi:
                        multi = True; d0 = d
                        post(Ev(PINCH, phase="start", scale=1.0, center=c))
                    else:
                        post(Ev(PINCH, phase="move", scale=d / d0, center=c))
                elif len(live) == 1:
                    if multi: continue                       # one finger lifted mid-pinch: wait for both
                    p = live[0]
                    if not single:
                        single = True; post(Ev(pygame.MOUSEBUTTONDOWN, pos=p, button=1))
                    else:
                        post(Ev(pygame.MOUSEMOTION, pos=p, rel=(0, 0), buttons=(1, 0, 0)))
                else:
                    if multi:
                        multi = False; post(Ev(PINCH, phase="end", scale=1.0, center=(0, 0)))
                    elif single:
                        post(Ev(pygame.MOUSEBUTTONUP, pos=self._last if hasattr(self, "_last") else (0, 0), button=1))
                    single = False
                if len(live) == 1: self._last = live[0]
