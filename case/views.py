"""Check renders of the loaded cover (out/v7_*.svg) and the viewer's data files: viewer_layout.js (the model's
constants, for viewer.html's extras and cable runs) and viewer_parts.js (base64 STLs from out/parts/, which
exploded.py writes). Run after exploded.py."""
import sys, json, base64, cadquery as cq
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flightscope_case as C, exploded as X, check as K
out = C.OUT
def box(w, h, d, x, y, z): return cq.Workplane("XY").box(w, h, d, centered=False).translate((x, y, z))
cover = C.rear_cover(); shell = C.front_shell()
loaded = cover.union(X.gps).union(X.dongle).union(X.panel_socket).union(K.bodies["dongle_sma_jack"]).union(K.bodies["ant_plug"]).union(K.bodies["usb_female_end"]).union(K.bodies["dongle_usb_plug"])
def svg(name, obj, d, w=1100, h=800):
    cq.exporters.export(obj, str(out / f"{name}.svg"), opt={"width": w, "height": h, "projectionDir": d, "showHidden": False, "strokeWidth": 0.5})
svg("v7_cover_loaded", loaded, (0.6, -0.8, 0.5))
svg("v7_cover_plan", loaded.union(X.pi), (0.0, 0.0, -1.0))
corner = C.on_cover(box(62, 24, 40, 0, 0, C.Z_COVER - 36))   # crops in the cover's frame, turned with it
svg("v7_gps_stand", cover.intersect(corner), (0.45, 0.8, -0.5))
svg("v7_gps_loaded", cover.union(X.gps).union(K.bodies["usb_c_elbow"]).union(K.bodies["usb_c_plug"]).union(shell).intersect(C.on_cover(box(62, 24, 60, 0, 0, C.Z_COVER - 56))), (0.45, 0.8, -0.5))
svg("v7_gps_back", cover.union(X.gps).intersect(corner), (0.3, -0.85, -0.4))

# every constant viewer.html reads (its layout test fails on a missing one)
keys = """WALL BEZEL_T OUT_W OUT_H OUT_D IN_W IN_H Z_GLASS Z_PCB Z_MID MID_T Z_PI_TOP Z_HAT_TOP Z_HAT_BOT Z_STANDOFF Z_COVER DISP_X DISP_Y DISPLAY_W DISPLAY_H
DISPLAY_PCB_T STACK_X STACK_Y PI_W PI_H PI_T PI_COMP_H PI_HOLES PILLARS RIM_BOSSES DONGLE_X DONGLE_Y DONGLE_L DONGLE_W DONGLE_T PANEL_USBC_XY
PANEL_USBC_FLANGE PANEL_USBC_BODY PANEL_USBC_PAD PANEL_USBC_HOLES PANEL_USBC_ROT HAT_USBC_X HAT_BTN_X PLUG_ROOM SMA_HOLE_D SMA_Y SMA_Z SMA_END_L
ANT_PLUG ANT_PLUG_L ANT_LEAD_D RIBBON_ROOM BTN_X BTN_Z BTN_D GPS_W GPS_H GPS_T GPS_PATCH_T GPS_BACK_T GPS_SLOT GPS_X GPS_Y GPS_PCB_Y GPS_Z_BOT
GPS_HOLES DSI_X DSI_Y DSI_LEN DSI_H USB_FPC_PLUG USB_SOCKET_L USB_SOCKET_W USB_SOCKET_T POCKET_L USB_LINK USB_ELBOW USB_ELBOW_W USB_FEMALE
USB_FEMALE_H USB_FEMALE_T USB_CABLE_ROOM DONGLE_PLUG ANT_RA_X ANT_RA_LEG ANT_PIG_PLUG SMA_BH_IN SMA_TOP_X SMA_TOP_Z BTN_HEAD_OD SMA_JACK ACTIVE_LEFT
ACTIVE_TOP COVER_ROT USB_PORT_Y BTN_BODY_L""".split()
L = {k: getattr(C, k) for k in keys}
(HERE / "viewer_layout.js").write_text("window.FLIGHTSCOPE_LAYOUT = " + json.dumps(L) + ";\n")
parts = {p.stem: base64.b64encode(p.read_bytes()).decode() for p in sorted((out / "parts").glob("*.stl"))}
(HERE / "viewer_parts.js").write_text("window.FLIGHTSCOPE_PARTS = " + json.dumps(parts) + ";\n")
print("views + viewer data done", len(parts), "parts")
