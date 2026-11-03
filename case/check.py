#!/usr/bin/env python3
"""Interference check: every part and connector body as a solid, pairwise intersections."""
import sys, itertools, cadquery as cq
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flightscope_case as C
import exploded as X          # reuses the component stand-ins (assembled positions)

def box(w, h, d, x, y, z): return cq.Workplane("XY").box(w, h, d, centered=False).translate((x, y, z))
def box2(x0, y0, z0, x1, y1, z1): return box(x1 - x0, y1 - y0, z1 - z0, x0, y0, z0)

def pig_route():
    """The bulkhead pigtail (box frame), 4 mm square: from its plug on the right-angle adapter (on the cover) to the bulkhead's inner end (shell)."""
    px, py = C.cover_pt(C.DONGLE_X - C.ANT_RA_X, C.SMA_Y); pz = C.SMA_Z - C.ANT_RA_LEG - C.ANT_PIG_PLUG   # the plug's cable end, toward the screen
    if not C.COVER_ROT:                                                  # along the band in front of the stick
        return box(C.SMA_TOP_X - px, 4, 4, px - 2, py - 2, pz - 3)
    # cover turned: the plug is at the bottom of the right-hand end. Out of the plug, a jog to a lane by the right wall, up it in front of the
    # USB elbow, then back to the bulkhead's depth just under the switch body, and up into the bulkhead behind the switch
    lx, yb = C.OUT_W - C.WALL - 5.3, C.OUT_H - C.WALL - C.SMA_BH_IN    # lane centre; the bulkhead's inner end
    yc0, yc1 = C.OUT_H - C.WALL - C.BTN_BODY_L - 2.7, C.OUT_H - C.WALL - C.BTN_BODY_L - 0.2   # the climb, between the elbow and the switch body
    z0, sz = pz - 4, C.SMA_TOP_Z
    return (box2(min(px, lx) - 2, py - 2, z0, max(px, lx) + 2, py + 2, pz)                 # jog
            .union(box2(lx - 2, py - 2, z0, lx + 2, yc1, pz))                                # up the lane
            .union(box2(lx - 2, yc0, z0, lx + 2, yc1, sz + 2))                                # back to the bulkhead's depth
            .union(box2(C.SMA_TOP_X - 2, yc0, sz - 2, lx + 2, yc1, sz + 2))                  # across under the switch body
            .union(box2(C.SMA_TOP_X - 2, yc0, sz - 2, C.SMA_TOP_X + 2, yb, sz + 2)))         # up into the bulkhead
bodies = {
  "front_shell": C.front_shell(), "mid_frame": C.mid_frame(), "rear_cover": C.rear_cover(),
  "display": X.display, "pi": X.pi, "standoffs": X.standoffs, "hat": X.hat, "studs": X.studs, "cells": X.cells, "dongle": X.dongle, "button": X.button, "panel_socket": X.panel_socket, "gps": X.gps,
  # connector bodies the harness needs
  "dongle_sma_jack": cq.Workplane("YZ").workplane(offset=C.DONGLE_X - 10).center(C.DONGLE_Y + C.DONGLE_T / 2, C.Z_COVER - C.DONGLE_W / 2).circle(3.2).extrude(10),
  "dongle_usb_plug": box(C.DONGLE_PLUG, 4.5, 12, C.DONGLE_X + C.DONGLE_L, C.DONGLE_Y + 4.2, C.Z_COVER - C.DONGLE_W / 2 - 6),
  **({"usb_socket":  box(C.USB_SOCKET_L, C.USB_SOCKET_T, C.USB_SOCKET_W, C.DONGLE_X + C.DONGLE_L + 1.0, C.DONGLE_Y + C.DONGLE_T / 2 - C.USB_SOCKET_T / 2, C.Z_COVER - C.DONGLE_W / 2 - C.USB_SOCKET_W / 2),
  "usb_fpc_plug":    box(C.USB_FPC_PLUG, 13, 5.5, C.STACK_X - 2 - C.USB_FPC_PLUG, C.pi_y(2.5, 13), C.Z_PI_TOP - 14.5)} if C.USB_LINK == "ribbon" else   # ribbon plug in the Pi's top USB2 port
     {"usb_female_end": box(C.USB_FEMALE + 8, C.USB_FEMALE_T, C.USB_FEMALE_H, C.DONGLE_X + C.DONGLE_L + C.DONGLE_PLUG - 8, C.DONGLE_Y + C.DONGLE_T / 2 - C.USB_FEMALE_T / 2, C.Z_COVER - C.DONGLE_W / 2 - C.USB_FEMALE_H / 2),   # right-angle block over the last 8 mm of the plug
      "usb_a_elbow":    box(C.USB_ELBOW - 2, C.USB_ELBOW_W, 7, C.STACK_X - C.USB_ELBOW, C.pi_y(C.USB_PORT_Y), C.Z_PI_TOP - 11.5),
      # the lead leaves the block's bezel-side face, drops 8 mm, runs left in front of the stick (over the switch), then down to the Pi's ports
      "usb_cable_drop": box(6, 6, 8, C.DONGLE_X + C.DONGLE_L + C.DONGLE_PLUG - 2, C.DONGLE_Y + C.DONGLE_T / 2 - 3, C.Z_COVER - C.DONGLE_W / 2 - C.USB_FEMALE_H / 2 - 8),
      "usb_cable_run":  box(C.DONGLE_X + C.DONGLE_L + C.DONGLE_PLUG + 4 - (C.STACK_X - 9.5), 6, 6, C.STACK_X - 9.5, C.DONGLE_Y + C.DONGLE_T / 2 - 3, C.Z_COVER - C.DONGLE_W / 2 - C.USB_FEMALE_H / 2 - 13),
      "usb_cable_down": box(6, C.DONGLE_Y + C.DONGLE_T / 2 + 3 - (C.pi_y(C.USB_PORT_Y) + 1), 6, C.STACK_X - 9.5, C.pi_y(C.USB_PORT_Y) + 1, C.Z_COVER - C.DONGLE_W / 2 - C.USB_FEMALE_H / 2 - 13)}),
  "usb_c_elbow":     box(13, 9, 9, C.pi_x(C.HAT_USBC_X[0] - 0.5, 13), C.STACK_Y - 15.5, C.Z_HAT_TOP - 9),
  "usb_c_plug":      box(28, 7, 6.5, C.pi_x(C.HAT_USBC_X[0] + 13, 28), C.STACK_Y - 14.5, C.Z_HAT_TOP - 8),   # the charge extension's male plug, sideways out of the adapter
  # the charge lead from the socket to that plug, passing behind the upright GPS (between its coin cell and the stack)
  "charge_lead":     box(C.pi_x(C.HAT_USBC_X[0] + 13 + 28) - C.PANEL_USBC_XY[0], 4.5, 4.5, C.PANEL_USBC_XY[0], C.GPS_PCB_Y + C.GPS_T + C.GPS_BACK_T + 1.0, C.Z_HAT_BOT + 3),
  # the charge socket's two screws, M3 x 8 countersunk, in from the back face through the cover and the flange's ears
  "socket_screws":   cq.Workplane("XY").pushPoints([(C.PANEL_USBC_XY[0] + dx, C.PANEL_USBC_XY[1] + dy) for dx, dy in C.PANEL_USBC_HOLES]).circle(1.5).extrude(8.0).translate((0, 0, C.OUT_D - 8.0)),
  # antenna: the lead's SMA plug on the stick's jack (inside variant) and the lead's neck out through the wall slot;
  # bulkhead: a right-angle adapter on the jack, its leg and the pigtail's plug toward the screen, the bulkhead in the top wall
  **({"ant_plug": cq.Workplane("YZ").workplane(offset=C.DONGLE_X - C.ANT_RA_X - 4.5).center(C.SMA_Y, C.SMA_Z).circle(4.25).extrude(C.ANT_RA_X + 4.5 - 0.3),
      "ant_leg": cq.Workplane("XY").workplane(offset=C.SMA_Z - C.ANT_RA_LEG).center(C.DONGLE_X - C.ANT_RA_X, C.SMA_Y).circle(4.25).extrude(C.ANT_RA_LEG),
      "ant_pig_plug": cq.Workplane("XY").workplane(offset=C.SMA_Z - C.ANT_RA_LEG - C.ANT_PIG_PLUG).center(C.DONGLE_X - C.ANT_RA_X, C.SMA_Y).circle(4.0).extrude(C.ANT_PIG_PLUG),
      "pig_run": pig_route(),
      "sma_bulkhead": cq.Workplane("XZ").workplane(offset=-(C.OUT_H - C.WALL)).center(C.SMA_TOP_X, C.SMA_TOP_Z).circle(4.5).extrude(C.SMA_BH_IN)} if C.ANT_PLUG == "bulkhead" else
     {"ant_plug": cq.Workplane("YZ").workplane(offset=C.DONGLE_X - C.ANT_PLUG_L).center(C.SMA_Y, C.SMA_Z).circle(4.25).extrude(C.ANT_PLUG_L - 0.3),
      "ant_lead": cq.Workplane("YZ").workplane(offset=C.DONGLE_X - C.ANT_PLUG_L - 25).center(C.SMA_Y, C.SMA_Z).circle(C.ANT_LEAD_D / 2).extrude(25.5)} if C.ANT_PLUG != "outside" else {}),
}
allowed = {("rear_cover", "panel_socket"), ("rear_cover", "studs"), ("hat", "studs"), ("front_shell", "button"), ("hat", "usb_c_elbow"),
           ("dongle", "dongle_usb_plug"), ("dongle_usb_plug", "usb_socket"), ("pi", "usb_fpc_plug"), ("dongle_usb_plug", "usb_female_end"), ("pi", "usb_a_elbow"), ("usb_female_end", "usb_cable_drop"), ("usb_cable_drop", "usb_cable_run"), ("usb_cable_run", "usb_cable_down"), ("usb_cable_down", "usb_a_elbow"), ("dongle", "dongle_sma_jack"), ("dongle_sma_jack", "ant_plug"), ("ant_plug", "ant_lead"), ("ant_plug", "ant_leg"), ("ant_leg", "ant_pig_plug"), ("front_shell", "sma_bulkhead"), ("ant_pig_plug", "pig_run"), ("pig_run", "sma_bulkhead"), ("usb_c_elbow", "usb_c_plug"), ("charge_lead", "usb_c_plug"), ("charge_lead", "panel_socket"), 
           ("hat", "standoffs"), ("pi", "standoffs"), ("hat", "cells"), ("rear_cover", "standoffs"), ("rear_cover", "socket_screws"), ("panel_socket", "socket_screws")}  # things that are meant to touch
# the connector stand-ins above are in the cover's frame: turn the ones that ride on the cover into the box (COVER_ROT). exploded.py's
# stand-ins and the rear cover come already turned; the shell's (switch, bulkhead, display) never turn, and pig_route() is drawn in the box
COVER_SIDE = {"dongle_sma_jack", "dongle_usb_plug", "usb_socket", "usb_fpc_plug", "usb_female_end", "usb_a_elbow", "usb_cable_drop", "usb_cable_run",
              "usb_cable_down", "usb_c_elbow", "usb_c_plug", "charge_lead", "socket_screws", "ant_plug", "ant_leg", "ant_pig_plug", "ant_lead"}
for n in COVER_SIDE & bodies.keys(): bodies[n] = C.on_cover(bodies[n])
# unmeasured: reported, not counted. The female block's 20 x 14 section is a guess (USB_FEMALE_H/_T) and, drawn, it reaches the top-right
# corner boss: fit_test's usb_corner print with the real block settles it. Move a pair back out of here once it is measured
unmeasured = {("front_shell", "usb_female_end")}
bad = 0
for a, b in itertools.combinations(bodies, 2):
    if (a, b) in allowed or (b, a) in allowed: continue
    try:
        v = bodies[a].intersect(bodies[b]).val().Volume()
    except Exception:
        v = 0.0
    if v > 1.0:
        bb = bodies[a].intersect(bodies[b]).val().BoundingBox()
        if (a, b) in unmeasured or (b, a) in unmeasured:
            print(f"CHECK {a:16s} x {b:16s}  {v:8.0f} mm3   x {bb.xmin:.1f}..{bb.xmax:.1f}  y {bb.ymin:.1f}..{bb.ymax:.1f}  z {bb.zmin:.1f}..{bb.zmax:.1f}   (unmeasured part: test print)"); continue
        bad += 1; print(f"FOUL  {a:16s} x {b:16s}  {v:8.0f} mm3   x {bb.xmin:.1f}..{bb.xmax:.1f}  y {bb.ymin:.1f}..{bb.ymax:.1f}  z {bb.zmin:.1f}..{bb.zmax:.1f}")
print("clashes:", bad)
