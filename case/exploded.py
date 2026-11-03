#!/usr/bin/env python3
"""Exploded assembly drawing: printed parts + component stand-ins, spread along the build axis (z)."""
import sys, cadquery as cq
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flightscope_case as C

def box(w, h, d, x, y, z): return cq.Workplane("XY").box(w, h, d, centered=False).translate((x, y, z))

# ---- component stand-ins, in their assembled positions ----
display = box(C.DISPLAY_W, C.DISPLAY_H, C.DISPLAY_GLASS_T + C.DISPLAY_PCB_T, C.DISP_X, C.DISP_Y, C.Z_GLASS)
for hx in (C.DISPLAY_HOLE_IN, C.DISPLAY_W - C.DISPLAY_HOLE_IN):
    for hy in (C.DISPLAY_HOLE_IN, C.DISPLAY_H - C.DISPLAY_HOLE_IN):
        display = display.union(cq.Workplane("XY").workplane(offset=C.Z_PCB + C.DISPLAY_PCB_T).center(C.DISP_X + hx, C.DISP_Y + hy).circle(2.5).extrude(C.DISPLAY_REAR_H))
pi = box(C.PI_W, C.PI_H, C.PI_T, C.STACK_X, C.STACK_Y, C.Z_PI_TOP)
for (py, ph) in ((2, 14), (20, 14), (39, 14)):                                              # USB2, USB3, Ethernet stacks (Pi frame: from the edge opposite the GPIO)
    pi = pi.union(box(17, ph, C.PI_COMP_H, C.pi_x(C.PI_W - 15, 17), C.pi_y(py, ph), C.Z_PI_TOP - C.PI_COMP_H))
pi = pi.union(box(51, 5, 8.5, C.pi_x(7, 51), C.pi_y(C.PI_H - 6, 5), C.Z_PI_TOP - 8.5))       # GPIO header
for (cx, cw, ch) in ((3.5 + 7.7, 9.0, 3.3), (3.5 + 7.7 + 14.8, 7.5, 3.0), (3.5 + 7.7 + 28.3, 7.5, 3.0), (53.5, 7.0, 6.0)):   # USB-C power, micro-HDMI x2, audio: on the edge opposite the GPIO, 1 mm proud
    pi = pi.union(box(cw, 8.5, ch, C.pi_x(cx - cw / 2, cw), C.pi_y(-1.0, 8.5), C.Z_PI_TOP - ch))
hat = box(C.PI_W, C.PI_H, C.HAT_T, C.STACK_X, C.STACK_Y, C.Z_HAT_TOP)
hat = hat.union(box(9.6, 7.5, 4.2, C.pi_x(C.HAT_USBC_X[0], 9.6), C.STACK_Y - 0.1, C.Z_HAT_TOP - 3.3))   # USB-C, flush with the edge (STEP)
hat = hat.union(box(9.0, 11.7, 3.9, C.pi_x(9.5, 9.0), C.STACK_Y - 6.5, C.Z_HAT_TOP - 6.1))            # the part that overhangs the edge by 6.5 at 9.5-18.5 (STEP)
standoffs = None
for hx, hy in C.PI_HOLES:
    s = cq.Workplane("XY").workplane(offset=C.Z_PI_TOP + C.PI_T).center(C.pi_x(hx), C.pi_y(hy)).circle(2.5).extrude(C.HAT_PI_GAP)
    standoffs = s if standoffs is None else standoffs.union(s)
studs = None                                                                                   # kit's M2.5 x 25 M-F hex studs under the HAT (male end up through the HAT into the 9 mm standoffs); their female ends take the cover screws
for hx, hy in C.PI_HOLES:
    s = cq.Workplane("XY").workplane(offset=C.Z_HAT_BOT).center(C.pi_x(hx), C.pi_y(hy)).polygon(6, 4.5).extrude(C.HAT_STANDOFF_END)   # 4.5 across corners (STEP)
    studs = s if studs is None else studs.union(s)
cells = None
for cy in (C.pi_y(6.8 + 10.5), C.pi_y(28.2 + 10.5)):
    cell = cq.Workplane("YZ").workplane(offset=C.pi_x(7.5, 70)).center(cy, C.Z_CELLS - 10.5).circle(10.5).extrude(70)
    cells = cell if cells is None else cells.union(cell)
for hx in (1.0, 82.2):                                                                         # the holder's end walls (contacts), the only part of it as deep as the cells (STEP)
    cells = cells.union(box(1.8, 44.6, C.Z_CELLS - 0.2 - C.Z_HAT_BOT, C.pi_x(hx, 1.8), C.pi_y(C.PI_H - 50.3), C.Z_HAT_BOT))   # 5.7..50.3 across
dongle = box(C.DONGLE_L, C.DONGLE_T, C.DONGLE_W, C.DONGLE_X, C.DONGLE_Y, C.Z_COVER - C.DONGLE_W)
button = (cq.Workplane("XZ").workplane(offset=-(C.OUT_H + 3)).center(C.BTN_X, C.BTN_Z).circle(C.BTN_HEAD_OD / 2).extrude(3)                 # head ring outside
          .union(cq.Workplane("XZ").workplane(offset=-(C.OUT_H - C.WALL)).center(C.BTN_X, C.BTN_Z).circle(C.BTN_BODY_D / 2).extrude(C.BTN_BODY_L))       # body behind the panel
          .union(box(8, C.BTN_DEPTH - C.BTN_BODY_L, 4, C.BTN_X - 4, C.OUT_H - C.WALL - C.BTN_DEPTH, C.BTN_Z - 2)))                                     # solder terminals
gz0 = C.GPS_Z_BOT - C.GPS_H                                                                                       # header (top) end, toward the screen
gps = (box(C.GPS_W, C.GPS_T, C.GPS_H, C.GPS_X, C.GPS_PCB_Y, gz0)                                                   # PCB standing upright on its short edge in the bottom band
       .union(box(15, C.GPS_PATCH_T, 15, C.GPS_X + (C.GPS_W - 15) / 2, C.GPS_Y, gz0 + 12))                       # 15 x 15 patch: 12..27 from the header end, centred across, facing the wall
       .union(box(16, C.GPS_BACK_T, 20, C.GPS_X + (C.GPS_W - 16) / 2, C.GPS_PCB_Y + C.GPS_T, gz0 + 9))           # coin-cell holder on the back
       .union(box(10, 6, 3, C.GPS_X + (C.GPS_W - 10) / 2, C.GPS_PCB_Y - 2.2, gz0 - 3)))                           # leads leaving the header end
px, py = C.PANEL_USBC_XY
panel_socket = box(C.PANEL_USBC_FLANGE[0], C.PANEL_USBC_FLANGE[1], 3, px - C.PANEL_USBC_FLANGE[0] / 2, py - C.PANEL_USBC_FLANGE[1] / 2, C.Z_COVER - C.PANEL_USBC_PAD + C.WALL - 3).union(
         box(12, 8, 14, px - 6, py - 4, C.Z_COVER - C.PANEL_USBC_PAD + C.WALL - 14))
# everything above that rides on the cover, turned with it into the box (COVER_ROT); the display and the switch belong to the shell
pi, standoffs, hat, studs, cells, dongle, gps, panel_socket = (C.on_cover(w) for w in (pi, standoffs, hat, studs, cells, dongle, gps, panel_socket))

# ---- explode along z (toward the back); offsets must clear the 71 mm-deep shell ----
items = [("front_shell", C.front_shell(), 0), ("button", button, 0), ("display", display, 95), ("mid_frame", C.mid_frame(), 130),
         ("pi", pi, 175), ("standoffs", standoffs, 205), ("hat", hat, 230), ("studs", studs, 250), ("cells", cells, 265), ("dongle", dongle, 300),
         ("rear_cover", C.rear_cover(), 345), ("panel_socket", panel_socket, 345), ("gps", gps, 345)]
asm = None
for name, part, k in items:
    p = part.translate((0, 0, k))
    asm = p if asm is None else asm.union(p, clean=False)
out = C.OUT / "exploded.svg"
cq.exporters.export(asm, str(out), opt={"width": 1200, "height": 1700, "projectionDir": (0.55, -0.75, -0.45), "showHidden": False, "strokeWidth": 0.5})
print("exploded ->", out)


# ---- individual parts in ASSEMBLED position, for the interactive viewer ----
PARTS = C.OUT / "parts"; PARTS.mkdir(exist_ok=True)
for name, part in [("front_shell", C.front_shell()), ("mid_frame", C.mid_frame()), ("rear_cover", C.rear_cover()),
                   ("button", button), ("panel_socket", panel_socket), ("gps", gps), ("display", display), ("pi", pi), ("standoffs", standoffs), ("hat", hat),
                   ("studs", studs), ("cells", cells), ("dongle", dongle)]:
    cq.exporters.export(part, str(PARTS / f"{name}.stl"), tolerance=0.08, angularTolerance=0.15)
print("parts ->", PARTS)
