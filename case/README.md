# Flightscope enclosure

Parametric CadQuery model: `flightscope_case.py`. STLs and renders are in `out/`. Landscape handheld, **125.7 × 98.6 × 75.4 mm** (127.7 mm wide across the grip ribs), three printed parts: front shell, mid-frame, rear cover.

## Layout

Front to back: bezel · 4.3" display · mid-frame (clamps the display) · Raspberry Pi 4 (components toward the display) · Waveshare UPS HAT (D) with two 21700 cells · rear cover. Everything behind the mid-frame is mounted on the rear cover, which is fitted turned 180° in its own plane (`COVER_ROT = 180`; the model draws the cover's contents in the cover's frame and turns them with `on_cover()` / `cover_pt()`).

As fitted:

| Part | Position |
|---|---|
| FlightAware Pro Stick Plus | bottom edge, centred, in a snap-fit cradle |
| GPS (Adafruit Ultimate GPS) | top-left corner, standing on its short edge, ceramic patch facing out through the top wall |
| USB-C charge socket | top right of the back face |
| Power switch (12 mm latching) | top wall, right-hand end |
| SMA bulkhead | top wall, directly behind the power switch |
| Pi GPIO header | bottom edge |
| Pi USB-C power / micro-HDMI, HAT ports | top edge |
| Pi USB / Ethernet | right wall |
| Pi SD card end, DSI socket | left wall |

The SMA pigtail runs up the right-hand side from a right-angle adapter on the stick's antenna jack. The stick's USB lead goes into the upper port of the Pi's blue USB3 pair.

## Estimated dimensions

These constants are estimates (`MEASURE` in the script). Measure them with calipers and rebuild if your parts differ:

| Constant | What to measure | Estimate |
|---|---|---|
| `PANEL_USBC_FLANGE`, `PANEL_USBC_HOLES` | charge socket flange, and its two holes either side of the port (dx, dy from centre) | 24 × 14, (±8.75, 0); M3 |
| `BTN_HEAD_OD`, `BTN_BODY_D`, `BTN_BODY_L` | power switch head ring, body diameter, body length | 18, 14, 17 |
| `ANT_RA_X`, `ANT_RA_LEG`, `ANT_PIG_PLUG`, `SMA_BH_IN` | right-angle SMA adapter, pigtail plug, bulkhead depth inside the wall | 15, 16, 20, 12 |
| `USB_FEMALE_H`, `USB_FEMALE_T` | USB extension's right-angle female block | 20 × 14 |

`measure.html` is a caliper sheet for entering these.

## Building

Needs [uv](https://docs.astral.sh/uv/) and ImageMagick. One-time setup:

```
uv venv case/.venv --python 3.12 && VIRTUAL_ENV=case/.venv uv pip install -r case/requirements.txt
```

`case/build.sh` rebuilds everything (about 4 minutes) and stops if the clash check finds anything. `case/build.sh --holes` adds a hole report.

| Script | What it does | Writes |
|---|---|---|
| `flightscope_case.py` | the model; every dimension is a constant at the top | `out/front_shell.stl`, `mid_frame.stl`, `rear_cover.stl`, `preview_*.png` |
| `check.py` | intersects every part and component stand-in pairwise and lists clashes | prints `clashes: 0` |
| `exploded.py` | stand-ins for the display, Pi, HAT, cells, stick, GPS, switch and socket in their assembled positions | `out/parts/*.stl`, `out/exploded.png` |
| `fit_test.py` | small test prints cut from the real parts | `out/fit/` |
| `views.py` | renders of the loaded cover, and the viewer's data | `out/v7_*.png`, `viewer_layout.js`, `viewer_parts.js` |
| `holes.py` | measures every screw and insert hole in the built solids | prints |

`viewer.html` is an interactive 3D assembly viewer (open it in a browser). `print/` holds Bambu Studio presets. `fonts/Nunito-Black-flat.ttf` is Nunito Black with overlapping outlines merged, used for the optional name on the back.

## Printing (Bambu P1S, PETG)

Import both presets in `print/` (Bambu Studio: **File → Import → Import Configs…**). With the printer set to *Bambu Lab P1S 0.4 nozzle*, select filament **Sunlu PETG Strong** and process **Flightscope PETG Strong** under *User presets*, plate type Textured PEI. They inherit from *Generic PETG* and *0.20mm Strength*; the differences are:

| Setting | Value |
|---|---|
| Dry the spool | 65 °C, 6 h |
| Nozzle | 245 °C, first layer 245 °C |
| Bed (textured PEI) | 75 °C (on smooth PEI, use glue stick as a release layer) |
| Layer height | 0.20 mm, first layer 0.20 mm |
| Wall loops | 6 (Arachne) |
| Top / bottom shell layers | 6 / 6 |
| Sparse infill | 40 % gyroid |
| Part cooling fan | min 10 %, max 40 %, off for the first 3 layers; overhang and bridge fan 70 % |
| Min layer time | 8 s |
| Speeds | outer wall 60, inner wall 100, infill and solid infill 150, gap fill 100, top surface 80, first layer 30 (its infill 50) mm/s |
| Max volumetric speed | 10 mm³/s |
| Flow ratio | 0.95, then Bambu's flow-rate calibration for the spool |
| Pressure advance | Flow Dynamics Calibration on |
| Retraction | 0.8 mm at 30 mm/s, Z-hop 0.4 mm |
| Seam | Aligned or Back |
| Elephant foot compensation | 0.15 mm |
| Supports / brim | none / none |

Orientation:
- `front_shell.stl`: face down (bezel on the plate).
- `rear_cover.stl`: inner face up.
- `mid_frame.stl`: flat.

If the 4.0 mm insert holes in `out/fit/hole_coupon.stl` print loose, set X-Y hole compensation to −0.05; if tight, +0.05.

## Fit-test prints (`out/fit/`)

| File | Size, time | Checks |
|---|---|---|
| `hole_coupon.stl` | 96 × 34 × 3 mm, ~10 min | every hole size: M3 insert 4.0 (with a boss stub), countersunk M3 3.4, countersunk M2.5 2.8, standoff 2.5, SMA bulkhead 6.6, switch 12.2 |
| `usb_corner.stl` | 51 × 22 × 35 mm, ~30 min | the cover corner at the stick's USB end, fused with the shell rim: the USB female block must clear the corner boss and its lead must get out |
| `bezel_tray.stl` + `mid_frame.stl` | 126 × 99 × 18 mm, ~1 h | display seats centred in the window, DSI socket clears the frame, pillars take the inserts |
| `rear_cover.stl` | ~2 h | GPS, stick, charge socket and Pi/HAT stack all fit |

Hole sizes are set by `INSERT_D` and `SCREW_D`.

## Hardware

- 8 × M3 brass heat-set inserts, 4.2–4.6 mm OD, 4–6 mm long: 4 in the bezel pillars, 4 in the rear corner bosses (4.0 mm holes). Set with a soldering iron at about 245 °C.
- Screws:

| Where | Qty | Screw |
|---|---|---|
| Mid-frame → bezel pillar inserts | 4 | M3 × 6 pan or button |
| Pi → 9 mm F-F hex standoffs on the HAT (kit) | 4 | M2.5 × 5 pan |
| 25 mm M-F hex studs (kit), male end through the HAT into the standoffs | 4 | kit part |
| Rear cover → female ends of the 25 mm studs | 4 | M2.5 × 8 countersunk |
| Rear cover → corner boss inserts | 4 | M3 × 8 countersunk |
| Back face → charge socket flange ears | 2 | M3 × 8 countersunk (M3 nuts behind if the ears aren't threaded) |
| GPS board | | slides into grooved posts; a dab of hot glue at the header end |

Countersunk screws: ISO 7046 or ISO 14581, 90° head.

- USB-C panel-mount extension with two screw holes ~17.5 mm apart (BTFO type), and a rigid right-angle USB-C adapter on the HAT's port.
- 12 mm latching metal push switch, two pins, no LED. Wired across the HAT's OFF/ON slide switch with the slide left at OFF: one lead to the slide switch's centre (EN) leg, one to the ON-side leg. Test first by bridging those two legs with a wire; if the Pi powers up, wire the switch there.
- SMA female bulkhead pigtail (~15 cm) and a right-angle SMA male → female adapter. 1090 MHz antenna with SMA male.
- USB-A right-angle extension (elbow 22 mm beyond the Pi, female block ~20 × 14 mm). `USB_LINK = "ribbon"` switches the model to a flat FPC extension, which makes the box 12 mm narrower.
- The display's own 12 cm DSI ribbon reaches; a 20 cm one gives slack.

## Assembly

1. Inserts into the 4 bezel pillars and the 4 corner bosses.
2. **Front shell**: display in from the back, glass against the bezel, corners between the four L-shaped guides. Mid-frame on, 4 screws into the pillars. Plug the DSI ribbon into the display and fold it back.
3. Power switch and SMA bulkhead into the top wall, nuts inside. Switch leads to the HAT slide switch's centre and ON legs.
4. **Rear cover**: Pi onto the HAT (9 mm standoffs, pogo pins), remove Waveshare's acrylic plate from the 25 mm studs, fit the cells. Bolt the stack to the cover: 4 countersunk screws from the back into the studs.
5. GPS: header end up, ceramic patch facing out toward the case edge; slide its long edges down the grooves in the two posts. Right-angle SMA adapter onto the stick's jack (leg toward the screen), clip the stick into its cradle, USB female block onto its plug. Charge socket flange onto its pad inside, 2 countersunk screws from the back, plug into the right-angle adapter on the HAT's USB-C.
6. **Close**: DSI ribbon into the Pi, pigtail onto the stick's adapter, USB lead into the upper blue USB3 port. Cover on with the GPS at the top and the stick at the bottom, 4 countersunk screws into the corner bosses.

## Features

- **Stick cradle**: 12 mm outer rail, three 2.4 mm snap hooks with a 1.2 mm lip, a 6 mm stiffening rail, and end stops of two 3 mm pillars either side of an 11.4 mm gap at each end (USB plug at one, the antenna plug's nut at the other).
- **GPS mount**: two 3.8 mm full-height posts with grooves (1.5 mm over the board's edge strip, 0.2 mm play), 2.0 mm between the patch and the wall.
- **Display guides**: four L-shaped guides inside the bezel, 4 mm tall, 0.5 mm clear of the glass.
- **Cell keepers**: two 2 mm ribs inside the cover across both cells, 1 mm short of them. Sand them if your cells are over 22 mm diameter.
- **Locating lip** on the cover: 1.2 mm thick, 2 mm tall, 0.3 mm inside the shell walls, with a 0.8 mm lead-in (`LIP_*`).
- **Screw bosses**: 3.8 mm radius, full-height web into the wall, 45° gusset beneath.
- **Grip ribs**: nine half-round ribs on each side wall, 1 mm proud, 2 mm wide, 8 mm pitch between the vent slots (`GRIP_*`).
- **Lanyard loop**: middle of the left edge, 28 mm wide, 15 mm out, 16 × 5 mm slot (`LANYARD_*`).
- **Finish**: flush countersunk screws on the back; 2 mm round-over on the front edge, 1.5 mm on the back; 1.5 mm 45° bevel round the screen window; 0.4 mm chamfer each side of the shell/cover seam; round-ended side vents.
- **Logo**: plane silhouette with a dotted trail, 0.6 mm deep in the top wall. `LOGO_NAME` adds a name in the bottom-right corner of the back (empty by default).
- **Interference check**: `check.py` reports 0 clashes for the current model.
