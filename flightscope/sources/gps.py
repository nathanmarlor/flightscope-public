"""GPS on the Pi's UART: NMEA straight off /dev/serial0, no gpsd. Tells the map where 'here' is."""
from __future__ import annotations
import calendar, os, subprocess, threading, time

try:
    import serial
except ImportError:
    serial = None

def _deg(v: str, hemi: str) -> float | None:
    """NMEA ddmm.mmmm / dddmm.mmmm -> signed degrees."""
    if not v or "." not in v: return None
    i = v.index(".") - 2
    d = float(v[:i]) + float(v[i:]) / 60.0
    return -d if hemi in ("S", "W") else d

def _nmea_ok(line: str) -> bool:
    """'$...*hh' with the right XOR checksum. UART noise (boot, a loose wire) gives torn or garbled sentences."""
    body, star, cs = line[1:].rpartition("*")
    if not star or len(cs) < 2: return False
    x = 0
    for ch in body: x ^= ord(ch)
    try: return int(cs[:2], 16) == x
    except ValueError: return False

class GpsSource:
    name = "gps"

    def __init__(self, cfg, port="/dev/serial0", baud=9600):
        self.port, self.baud = port, baud
        self.present = False            # the port opened
        self.talking = False            # sentences are arriving (wired up right)
        self.fix = False; self.lat = None; self.lon = None; self.sats = 0; self.hdop = None
        self.speed_kt = 0.0; self.course = None
        self.updated = 0.0; self.sentences = 0; self.bad = 0; self.error = None
        self._sky: dict[tuple, tuple] = {}     # (system, sat) -> (snr or None, time) from GSV: what it can see/hear
        self._clock_set_at = 0.0
        self._stop = threading.Event()
        if serial is None: self.error = "pyserial missing"; return
        threading.Thread(target=self._run, name="gps", daemon=True).start()

    def stop(self): self._stop.set()

    def here(self):
        """(lat, lon) if we have a fix that's less than a minute old."""
        return (self.lat, self.lon) if self.fix and time.time() - self.updated < 60 else None

    def _run(self):
        while not self._stop.is_set():
            try:
                with serial.Serial(self.port, self.baud, timeout=2) as s:
                    self.present = True; self.error = None; last = time.time()
                    while not self._stop.is_set():
                        line = s.readline().decode("ascii", "ignore").strip()
                        if not line:
                            if time.time() - last > 10: self.talking = False; self.fix = False
                            continue
                        if not line.startswith("$"): continue
                        last = time.time(); self.talking = True
                        if not _nmea_ok(line): self.bad += 1; continue
                        self.sentences += 1
                        try: self._parse(line)
                        except (ValueError, IndexError): self.bad += 1
            except Exception as e:
                self.present = False; self.talking = False; self.fix = False; self.error = str(e)[:60]
                self._stop.wait(5)

    def _parse(self, line):
        body = line[1:].split("*")[0]; f = body.split(",")
        tag = f[0][2:]                                                  # GP/GN/GL prefix -> RMC, GGA
        if tag == "RMC" and len(f) >= 9:
            ok = f[2] == "A"; la, lo = _deg(f[3], f[4]), _deg(f[5], f[6])
            if ok and la is not None and lo is not None:
                self.lat, self.lon, self.fix, self.updated = la, lo, True, time.time()
                try: self.speed_kt = float(f[7] or 0); self.course = float(f[8]) if f[8] else None
                except ValueError: pass
                if len(f) >= 10: self._set_clock(f[1], f[9])
            elif not ok: self.fix = False
        elif tag == "GSV" and len(f) >= 4:
            now = time.time()
            for i in range(4, len(f) - 3, 4):                           # 4 per sentence: id, elevation, azimuth, SNR
                if f[i]:
                    try: self._sky[(f[0][:2], f[i])] = (int(f[i + 3]) if f[i + 3] else None, now)
                    except ValueError: pass
        elif tag == "GGA" and len(f) >= 9:
            try: self.sats = int(f[7] or 0); self.hdop = float(f[8]) if f[8] else None
            except ValueError: pass

    def _set_clock(self, hms: str, dmy: str):
        """The rootfs is read-only, so the saved clock is the same at every boot. With no Wi-Fi (no NTP) set the
        system clock from the GPS - otherwise logbook catches get the wrong time."""
        if os.path.exists("/run/systemd/timesync/synchronized") or time.time() - self._clock_set_at < 600: return
        try:
            gps = calendar.timegm((2000 + int(dmy[4:6]), int(dmy[2:4]), int(dmy[0:2]), int(hms[0:2]), int(hms[2:4]), int(float(hms[4:]))))
        except (ValueError, IndexError): return
        self._clock_set_at = time.time()
        if abs(gps - time.time()) > 30:
            r = subprocess.run(["sudo", "-n", "date", "-u", "-s", f"@{gps}"], capture_output=True, text=True)
            print(f"gps: clock set from GPS ({'ok' if r.returncode == 0 else r.stderr.strip()[:60]})", flush=True)

    def sky(self) -> tuple[int, int, int | None]:
        """(satellites in view, how many it actually hears, best signal in dB) over the last 10 s."""
        now = time.time(); items = list(self._sky.items())               # one atomic copy: the GPS thread writes it
        for k, (_, t) in items:
            if now - t > 10: self._sky.pop(k, None)
        live = [v for _, (v, t) in items if now - t <= 10]; snrs = [v for v in live if v]
        return len(live), len(snrs), max(snrs) if snrs else None

    def signal_text(self) -> str:
        if not self.talking: return "—"
        seen, heard, best = self.sky()
        if not heard: return f"hears none yet  ·  {seen} in view" if seen else "hears none yet"
        word = "good" if heard >= 6 and best >= 35 else "OK" if heard >= 4 and best >= 28 else "weak - needs sky"
        return f"hears {heard} of {seen}  ·  best {best} dB  ·  {word}"

    def status(self) -> str:
        if serial is None: return "no pyserial"
        if not self.present: return "no serial port" if self.error else "opening…"
        if not self.talking: return "nothing on the wire — check TX/RX"
        if not self.fix: return f"waiting for a fix · {self.sats} satellites"
        return f"{self.lat:.4f}, {self.lon:.4f} · {self.sats} satellites"
