"""Measure every screw and insert hole in the built parts: the hole's width at depths below the cover's back face,
the insert holes in the shell, the pillars' radius and the mid-frame's holes. Probes the solids themselves, so it
shows what will print, not what the constants say."""
import io, sys, contextlib, cadquery as cq
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
with contextlib.redirect_stdout(io.StringIO()):
    import flightscope_case as C
cov, shell, mid = C.rear_cover().val(), C.front_shell().val(), C.mid_frame().val()

def hole(solid, x, y, z):
    """Diameter of the empty space round (x, y) at height z."""
    r = 0.0
    while r < 8 and not solid.isInside(cq.Vector(x + r, y, z), 1e-4): r += 0.02
    return round(2 * r, 2)

def outer(solid, x, y, z, start):
    """Where the solid ends going out from the axis (toward -y)."""
    r = start
    while r < 8 and solid.isInside(cq.Vector(x, y - r, z), 1e-4): r += 0.02
    return round(r, 2)

D = [0.05, 0.8, 1.6, 2.35]
print(f"cover holes: width at {D} mm below the back face")
for kind, pts in (("rim M3    ", C.RIM_BOSSES),                     # the socket and stack holes are in the cover's frame: cover_pt() turns them with it
                  ("socket M3 ", [C.cover_pt(C.PANEL_USBC_XY[0] + dx, C.PANEL_USBC_XY[1] + dy) for dx, dy in C.PANEL_USBC_HOLES]),
                  ("stack M2.5", [C.cover_pt(C.pi_x(a), C.pi_y(b)) for a, b in C.PI_HOLES])):
    for x, y in pts: print(f"  {kind} ({x:5.1f},{y:5.1f})", [hole(cov, x, y, C.OUT_D - d) for d in D])
for x, y in C.RIM_BOSSES: print(f"shell rim insert ({x:5.1f},{y:5.1f})  d {hole(shell, x, y, C.Z_COVER - 3)}")
for x, y in C.PILLARS: print(f"pillar           ({x:5.1f},{y:5.1f})  insert d {hole(shell, x, y, C.Z_MID - 3)}  radius {outer(shell, x, y, C.Z_MID - 1, 2.5)} (more where it merges into a wall)")
for x, y in C.PILLARS: print(f"mid-frame hole   ({x:5.1f},{y:5.1f})  d {hole(mid, x, y, C.Z_MID + 1)}")
print("valid:", {n: (f().val().isValid(), len(f().solids().vals())) for n, f in (("rear_cover", C.rear_cover), ("front_shell", C.front_shell), ("mid_frame", C.mid_frame))}, "(valid, solids)")
