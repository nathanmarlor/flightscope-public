"""Minimum prints to prove the fit before the full case: a shallow bezel tray (front shell cut off just
behind the mid-frame), a hole coupon for every hole size, the USB corner (cover and shell fused), plus the real mid-frame and rear cover."""
import cadquery as cq
import flightscope_case as C

OUT = C.OUT / "fit"; OUT.mkdir(exist_ok=True)

# 1. bezel tray: the front shell, kept only to 1.5 mm behind the mid-frame. Tests: window position over the
#    picture, display pocket, pillar height, mid-frame fit, and whether the display drops in from behind.
tray_depth = C.Z_MID + C.MID_T + 1.5
tray = C.front_shell().intersect(cq.Workplane("XY").box(C.OUT_W + 2, C.OUT_H + 2, tray_depth, centered=False).translate((-1, -1, 0)))

# 2. hole coupon: every hole in the design at its real size, in one 3 mm plate, labelled by position.
coupon = cq.Workplane("XY").box(96, 34, 3, centered=False).edges("|Z").fillet(3)
holes = [(10, C.INSERT_D, "M3 insert 4.0"), (22, C.SCREW_D, "M3 clear 3.4, countersunk (cover rim, charge socket)"), (33, C.M25_D, "M2.5 clear 2.8, countersunk (stack studs)"),
         (45, 2.5, "GPS/display std 2.5"), (60, C.SMA_HOLE_D, "SMA 6.6 (antenna lead neck / stick jack)"), (80, C.BTN_D, "switch 12.2")]
for x, d, _ in holes:
    coupon = coupon.cut(cq.Workplane("XY").workplane(offset=-1).center(x, 17).circle(d / 2).extrude(5))
# countersinks on the bed face exactly as on the cover's back: a countersunk M3 at 22 and M2.5 at 33 should sit flush
for x, sd, cd in ((22, C.SCREW_D, C.CSK_D), (33, C.M25_D, C.M25_CSK_D)):
    d = (cd - sd) / 2
    coupon = coupon.cut(cq.Workplane("XY").add(cq.Solid.makeCone(sd / 2, cd / 2 + 0.5, d + 0.5, cq.Vector(x, 17, d), cq.Vector(0, 0, -1))))
# an 8 mm stub of a cover boss with its insert hole, so the heat-set is tested in the vertical
coupon = coupon.union(cq.Workplane("XY").workplane(offset=3).center(10, 17).circle(C.BOSS_R).extrude(8)
                      .cut(cq.Workplane("XY").workplane(offset=2).center(10, 17).circle(C.INSERT_D / 2).extrude(10)))

# 3. USB corner: the top-right of the rear cover and the front shell's rim there, fused into one piece. Only the stick cradle's
#    USB end (the last hook, both rails, the plug-end stop) and the shell's last 20 mm (the corner boss, its gusset, both walls). Snap the real
#    stick in with the lead's female block on its plug: does the block clear the boss, and does the lead get out past it?
ux0, uy0 = C.DONGLE_X + C.DONGLE_L - 22, C.DONGLE_Y - 3.0                  # 2 mm short of the last hook; just below the cradle's inner rail (clear of the stack boss)
uz0 = C.Z_COVER - C.BOSS_H - C.GUSSET_H - 1                                 # the shell from 1 mm in front of the gusset's tip
keep = lambda z0: cq.Workplane("XY").box(C.OUT_W + 2 - ux0, C.OUT_H - 0.2 - uy0, C.OUT_D + 1 - z0, centered=False).translate((ux0, uy0, z0))   # 0.2 under the top: no lanyard tab
corner = C.front_shell().intersect(C.on_cover(keep(uz0))).union(C.rear_cover().intersect(C.on_cover(keep(0))))   # the region is the cover's; turned with it
corner = corner.rotate((0, 0, 0), (1, 0, 0), 180)                           # cover face down, ready to print
bb = corner.val().BoundingBox(); corner = corner.translate((-bb.xmin, -bb.ymin, -bb.zmin))

for name, part in (("bezel_tray", tray), ("hole_coupon", coupon), ("usb_corner", corner), ("mid_frame", C.mid_frame()), ("rear_cover", C.rear_cover())):
    cq.exporters.export(part, str(OUT / f"{name}.stl"), tolerance=0.05, angularTolerance=0.1)
    bb = part.val().BoundingBox(); v = part.val().Volume() / 1000
    print(f"{name:12s} {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:5.1f} mm   {v:5.1f} cm3 solid" + ("" if len(part.solids().vals()) == 1 else "   NOT ONE PIECE"))
print("fit prints ->", OUT)
