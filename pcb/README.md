# wESP32 RF hat (fan-hat)

75 × 40 mm board that stacks on top of the wESP32 on its four mounting holes and
plugs into JP1. Carries the two STX882 transmitters and two SRX882 receivers in
sockets, the 5 V → 3.3 V dividers for the receiver data lines, decoupling and a
status LED. Replaces the Perma-Proto + Adafruit 757.

Open `fan-hat.kicad_pro` in KiCad 10. `make_board.py` regenerates everything
(schematic, placed AND routed PCB with filled GND pours, custom footprint/symbol)
and checks that schematic nets == PCB pad nets, ERC and DRC (all clean):

    & "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe" make_board.py

Edit positions/nets/tracks in the script (`PARTS`, `TRACKS`), not in KiCad —
re-running overwrites the files. `fan-hat-gerbers.zip` is the fab upload
(2-layer, 1.6 mm, any finish; JLCPCB/PCBWay 5 pcs).

## Geometry (from the product brief)

- Holes ⌀3.2 at 3.5 mm from each edge (wESP32: ⌀3, same spots), M2.5 hardware.
- JP1 pin 1 = OUTER column (1.8 mm from the right edge), 5.0 mm up from the
  bottom-right (non-plated) hole, header centred on the 40 mm axis; pin 2
  inboard, pin 3 above pin 1. **Caliper-check on the real board:** pin 1 at
  1.8 mm from the right edge, 8.6 mm from the bottom edge.
- Left 22 mm of the underside is kept empty: RJ45 (15.2 mm tall) and 12 mm
  electrolytics are there. Right end underside is the 2×10.
- SRX882: pins 2 and 6 are both GND, pins 1 and 7 both ANT (NiceRF datasheet,
  RFLink wiring page), so the socket is a plain 1×4 on pins 3–6 (VCC, CS, DATA,
  GND). Pins 1–2 hang free above the board (measured pin 2 → 3 gap 18.22 mm is
  drawn on silk only). Coil solders to pin 1 or the pin-7 hole.
- Modules lie FLAT in their sockets (pins straight, not bent): the pin row is
  1.2 mm (SRX) / 1.8 mm (STX) from one long edge and the body lies over the
  board. The unit mounts on the wall with the RJ45 end DOWN, so "up" is the
  JP1 end (+x): the two SRX882 lie along the board with pin 1 (ANT end) toward
  +x, the two STX882 sit at the top with their bodies overhanging the JP1 pads
  (they are 8.5 mm up on their sockets — pads and screw heads are below them).
  All four ANT holes (silk circles) face +x, so the coils exit past the top edge.
  STX882 ANT pad is at the DATA end of the socket (confirmed from the module).

## Stack

Hat underside is 18 mm above the wESP32 top (M2.5 × 18 mm standoffs ×4).
JP1 ships as bare pads. Used: 3M 929836-04-10 2x10 header soldered into
JP1 UPSIDE DOWN (short 6 mm side in the board, 12.95 mm side pointing up; trim
the stubs underneath), mating a plain 2x10 female socket (8.5 mm body) on the
hat's underside. Socket opening sits ~9.5 mm above the wESP32, the pin tips at
~15.5 mm, so ~6 mm insertion. Ordinary 6 mm-pin headers won't reach.
Fallback: two Arduino-style stackable female headers plugged into each other
on JP1 and a plain male header on the hat - same footprint.

Above the hat: modules lie flat on 8.5 mm sockets, so ≈ 10–14 mm total; the
coil antennas solder to the ANT hole on each module and extend past the top
edge — the hat has no antenna pads.

## BOM

| Ref | Part | Qty |
|---|---|---|
| J1 | 2×10 female socket (hat) + 2×10 long-pin male header (wESP32 JP1) | 1 + 1 |
| U1, U2 | SRX882 (433, 315) on 1×4 female headers | 2 + 2 |
| U3, U4 | STX882 (433, 315) on 1×3 female header | 2 + 2 |
| R1, R3 | 10 kΩ axial | 2 |
| R2, R4 | 20 kΩ axial | 2 |
| R5 | 330 Ω axial | 1 |
| D1 | 3 mm LED | 1 |
| C1–C4 | 100 nF ceramic disc, 2.5 mm | 4 |
| C5 | 10 µF electrolytic, 5 mm ⌀, 2 mm pitch | 1 |
| H1–H4 | M2.5 × 18 mm standoff + screws | 4 |

Routing notes: JP1's odd column is reached through the 0.84 mm gap between the
header columns (IO23 on top, IO5 on the bottom), which boxes in pin 9 — so pin 9
is left NC and GND uses pins 1 and 19. GND is the pours on both sides plus two
short stitches (JP1.1→U4.3, D1.1→C5.2). No vias.

Nets: IO4 → STX-433 DATA, IO5 → STX-315 DATA, SRX-433 DATA → 10k/20k → IO34,
SRX-315 DATA → 10k/20k → IO35, IO23 → 330 Ω → LED. Everything runs on V+ (5 V,
jumper bridged); 3.3 V unused. Receiver CS tied to 5 V.

## Assembly note (case)

The printed case has magnet blocks in the corners at the antenna end that reach
up to 1 mm inside the HAT's long edges (x 69–75; the wESP32 sits 0.6 mm
off-centre in the case). Bend both SRX coils at least 2.5 mm inboard where they
pass that end: SRX-433 to y ≈ 5.5, SRX-315 to y ≈ 36.3. That clears the blocks
in either board orientation with ≥ 0.7 mm margin and passes over the STX
modules. The STX coils are already inboard.

Coil height: the case's antenna slot tops out 37 mm above the case floor, so
every coil must leave its module with its axis no more than 11 mm above the HAT
top. The module PCBs sit at 8.5–9.5 mm (socket + board), so solder each coil
with its lead bent so the coil runs level with the module board (axis ≈ 9.5–10
mm), not perched on top of it.

## Before ordering

1. Open the board in KiCad, run DRC once yourself, eyeball the 3D view.
2. Upload `fan-hat-gerbers.zip`.
3. Firmware already drives the LED (`status_led` light on GPIO23 in `fan-control.yaml`).
