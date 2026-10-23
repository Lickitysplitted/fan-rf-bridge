"""Generate the wESP32 RF hat KiCad project (schematic + placed PCB) and check it.

Run with KiCad's python so pcbnew is available:
  & "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe" make_board.py

Board coords below are hat mm, origin = top-left corner, y down, same top view
as the wESP32 product brief photo (RJ45 at left, JP1 at right).  All positions
that matter are relative to the mounting holes, which the hat shares.
"""
import os, re, json, uuid, subprocess, sys
import pcbnew
from pcbnew import VECTOR2I_MM as MM

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "fan-hat"
KICAD = os.path.dirname(os.path.dirname(sys.executable))          # ...\KiCad\10.0
FPLIB = os.path.join(KICAD, "share", "kicad", "footprints")
SYMLIB = os.path.join(KICAD, "share", "kicad", "symbols")
CLI = os.path.join(KICAD, "bin", "kicad-cli.exe")

# ---- measured / datasheet geometry ------------------------------------------
W, H = 75.0, 40.0
HOLES = [(3.5, 3.5), (71.5, 3.5), (3.5, 36.5), (71.5, 36.5)]     # brief: 3.5 mm from edges
# JP1 pin 1 (user-confirmed on the board): OUTER column, 1.8 mm from the right
# edge, 5.0 mm up from the bottom-right (non-plated) hole; pin 2 is inboard,
# pin 3 above pin 1.  Header is centred on the 40 mm axis.
JP1_PIN1 = (75 - 1.81, 40 - 8.57)
SRX_GAP = 18.22          # SRX882 pin2 -> pin3 centre distance (measured; datasheet says 18.86) - outline only
OX, OY = 100.0, 100.0    # board origin on the KiCad canvas

# ---- netlist ------------------------------------------------------------------
# JP1 (wESP32 GPIO header): odd = 1 GND,3 IO23,5 IO39,7 IO32,9 GND,11 IO18,13 IO13,
# 15 IO4,17 IO15,19 GND; even = 2 3.3V,4 IO36,6 IO34,8 IO35,10 IO33,12 IO5,14 IO14,
# 16 IO12,18 IO2,20 V+ (=5 V, jumper bridged).
J1_PINS = {1: "GND", 3: "IO23", 6: "IO34", 8: "IO35", 12: "IO5",   # pin 9 GND left NC: boxed in by the column-gap traces
           15: "IO4", 19: "GND", 20: "+5V"}
J1_NC = [2, 4, 5, 7, 9, 10, 11, 13, 14, 16, 17, 18]

# ref: (lib, footprint, value, {pad: net}, (x, y) of pad 1, pin2 direction, on_back)
# pin2 direction (dx, dy) in hat mm picks the rotation; None = 0 deg.
DOWN, LEFT, RIGHT = (0, 2.54), (-2.54, 0), (2.54, 0)
# The unit is wall-mounted with the RJ45 end DOWN, so "up" = +x (the JP1 end).
# Radio modules lie FLAT in sockets with every ANT hole toward +x so the coils
# exit past the top (x = 75) edge.  Module bodies may overhang the JP1 pads and
# the screw heads: they sit 8.5 mm up on their sockets.
PARTS = {
    "J1": ("Connector_PinSocket_2.54mm", "PinSocket_2x10_P2.54mm_Vertical", "wESP32 JP1",
           J1_PINS, JP1_PIN1, LEFT, True),
    # SRX882: 1 ANT, 2 GND, 3 VCC, 4 CS, 5 DATA, 6 GND, 7 ANT(hole).  Pins 2/6 are
    # both GND and 1/7 both ANT (datasheet + RFLink), so the socket is a plain 1x4
    # on pins 3-6; pins 1-2 hang free (coil solders to pin 1 or the pin-7 hole).
    # Position = pad 3; rows along x, ANT end at +x (58.5, 3) and (58.5, 38.8).
    "U1": ("fan-hat", "SRX882_Socket", "SRX882-433",
           {3: "+5V", 4: "+5V", 5: "RX433_5V", 6: "GND"}, (36.24, 11.0), LEFT, False),
    "U2": ("fan-hat", "SRX882_Socket_BodyDown", "SRX882-315",
           {3: "+5V", 4: "+5V", 5: "RX315_5V", 6: "GND"}, (36.24, 28.4), LEFT, False),
    # STX882: socket 1 DATA, 2 VCC, 3 GND (ANT pad on the module); pins along y at
    # the top end, body toward +x (overhangs the JP1 pads), ANT holes at x ~ 73.7
    "U3": ("Connector_PinSocket_2.54mm", "PinSocket_1x03_P2.54mm_Vertical", "STX882-433",
           {1: "IO4", 2: "+5V", 3: "GND"}, (61.5, 14.0), DOWN, False),
    "U4": ("Connector_PinSocket_2.54mm", "PinSocket_1x03_P2.54mm_Vertical", "STX882-315",
           {1: "IO5", 2: "+5V", 3: "GND"}, (61.5, 27.4), DOWN, False),
    # 5 V -> 3.3 V dividers on the receiver data lines (replaces the Adafruit 757)
    "R1": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", "10k",
           {1: "RX433_5V", 2: "IO34"}, (24.0, 14.0), None, False),
    "R2": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", "20k",
           {1: "IO34", 2: "GND"}, (24.0, 17.0), None, False),
    "R3": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", "10k",
           {1: "RX315_5V", 2: "IO35"}, (24.0, 20.0), None, False),
    "R4": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", "20k",
           {1: "IO35", 2: "GND"}, (24.0, 23.0), None, False),
    # status LED on IO23
    "R5": ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", "330",
           {1: "IO23", 2: "LED_A"}, (44.0, 14.2), None, False),
    "D1": ("LED_THT", "LED_D3.0mm", "LED", {1: "GND", 2: "LED_A"}, (55.6, 14.2), DOWN, False),
    # decoupling: one 100n per module, 10u bulk on 5 V
    "C1": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P2.50mm", "100n", {1: "+5V", 2: "GND"}, (35.0, 18.0), None, False),
    "C2": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P2.50mm", "100n", {1: "+5V", 2: "GND"}, (41.0, 18.0), None, False),
    "C3": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P2.50mm", "100n", {1: "+5V", 2: "GND"}, (35.0, 24.0), None, False),
    "C4": ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P2.50mm", "100n", {1: "+5V", 2: "GND"}, (41.0, 24.0), None, False),
    "C5": ("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "10u", {1: "+5V", 2: "GND"}, (48.0, 19.6), None, False),
}
for i, h in enumerate(HOLES, 1):
    PARTS["H%d" % i] = ("MountingHole", "MountingHole_3.2mm_M3", "M2.5", {}, h, None, False)

# ---- routing: (net, layer, width, [points in hat mm]) ----------------------
# Every layer change happens at a THT pad, so no vias.  GND is the pours.
# J1 odd column (x 73.19) is reached through the 0.84 mm gap between the two
# header columns at x 71.92 (0.27 mm to each pad with 0.3 mm traces).
F, B = "F.Cu", "B.Cu"
TRACKS = [
    # receiver data -> divider tops
    ("RX433_5V", F, 0.3, [(31.16, 11), (31.16, 12.4), (25.7, 12.4), (24, 14)]),
    ("RX315_5V", F, 0.3, [(31.16, 28.4), (31.16, 27), (22.5, 27), (22.5, 21.5), (24, 20)]),
    # divider mid-points: R1.2-R2.1, R3.2-R4.1 on top, then off to J1 on the back
    ("IO34", F, 0.3, [(31.62, 14), (31.62, 15.5), (25.5, 15.5), (24, 17)]),
    ("IO34", B, 0.3, [(24, 17), (22.6, 18.4), (22.6, 34.6), (24, 36), (67.1, 36), (68.5, 34.6),
                      (68.5, 27.5), (69.65, 26.35), (70.65, 26.35)]),
    ("IO35", F, 0.3, [(31.62, 20), (31.62, 21.5), (25.5, 21.5), (24, 23)]),
    ("IO35", B, 0.3, [(31.62, 20), (33.4, 21.8), (68.6, 21.8), (70.65, 23.81)]),
    # transmitter data
    ("IO4", B, 0.3, [(61.5, 14), (62.4, 14.92), (71.92, 14.92), (71.92, 13.65), (73.19, 13.65)]),
    ("IO5", F, 0.3, [(61.5, 27.4), (64, 24.9), (64, 20.3), (65.6, 18.73), (70.65, 18.73)]),
    # status LED
    ("IO23", F, 0.3, [(44, 14.2), (45.6, 12.6), (64, 12.6), (66.76, 9.84), (71.92, 9.84),
                      (71.92, 28.89), (73.19, 28.89)]),
    ("LED_A", F, 0.3, [(51.62, 14.2), (54.2, 16.74), (55.6, 16.74)]),
    # 5 V: J1.20 up and over on the back to U3, then a top-side trunk at y 21.2
    ("+5V", B, 0.5, [(70.65, 8.57), (69.2, 7.1), (60, 7.1), (60, 15.04), (61.5, 16.54)]),
    ("+5V", F, 0.5, [(61.5, 16.54), (60, 18), (60, 28.4), (61.5, 29.94)]),
    ("+5V", F, 0.5, [(60, 21.2), (35, 21.2)]),
    ("+5V", F, 0.5, [(48, 19.6), (48, 21.2)]),
    ("+5V", F, 0.5, [(41, 18), (41, 24)]),
    ("+5V", F, 0.5, [(35, 18), (35, 24)]),
    ("+5V", F, 0.5, [(35, 18), (35, 12.4), (33.7, 11), (36.24, 11)]),
    ("+5V", F, 0.5, [(35, 24), (35, 27.1), (33.7, 28.4), (36.24, 28.4)]),
    # GND stitches where the pour can't reach a pad on its own
    ("GND", F, 0.3, [(73.19, 31.43), (71.9, 32.72), (62.5, 32.72), (61.5, 32.48)]),   # J1.1 -> U4.3
    ("GND", F, 0.3, [(55.6, 14.2), (57.0, 15.6), (57.0, 17.3), (54.7, 19.6), (50, 19.6)]),  # D1.1 -> C5.2
]

# STX882 body outline relative to its socket pin 1 when pins run down (+y) and the
# body lies toward +x: pins 1.8 mm from the module edge, 3.4 mm from its end.
STX_BODY = (-1.8, -3.4, -1.8 + 14.8, -3.4 + 12.0)      # x0, y0, x1, y1 (x1 trimmed 0.4 to stay inside the edge)
# ANT pad: 1.2 mm from the far edge, 1.2 mm from the module end nearest the DATA
# pin (socket pad 1) - confirmed from the module photo (DATA VCC GND, ANT above DATA).
STX_ANT = (-1.8 + 15.2 - 1.2, -3.4 + 1.2)


# ---- PCB ---------------------------------------------------------------------
def srx_socket_footprint(board, name):
    """1x4 socket on SRX882 pins 3-6 (pad numbers 3..6, pad 3 at the origin);
    the module outline (35 x 10.4) and the free pins 1-2 / ANT hole are drawn on silk.
    Body on the +y side of the pad row (footprint frame), or -y for *_BodyDown."""
    side = -1 if name.endswith("BodyDown") else 1
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("fan-hat", name))
    tht_layers = pcbnew.FootprintLoad(os.path.join(FPLIB, "Connector_PinSocket_2.54mm.pretty"),
                                      "PinSocket_1x02_P2.54mm_Vertical").FindPadByNumber("1").GetLayerSet()
    for n, x in zip((3, 4, 5, 6), (0, 2.54, 5.08, 7.62)):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(n))
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetShape(pcbnew.PAD_SHAPE_RECT if n == 3 else pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(MM(1.7, 1.7))
        p.SetDrillSize(MM(1.0, 1.0))
        p.SetLayerSet(tht_layers)
        p.SetPosition(MM(x, 0))
        fp.Add(p)
    # module lies flat: 35 x 10.4 mm, pins 1.2 mm from one long edge; pin 1 is
    # 2.5 mm from the ANT end, pin 2 at +2.54, pin 3 a further SRX_GAP.
    x_ant_end = -(2.54 + SRX_GAP + 2.5)
    for layer, w in ((pcbnew.F_SilkS, 0.12), (pcbnew.F_CrtYd, 0.05)):
        r = pcbnew.PCB_SHAPE(fp)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(MM(x_ant_end, -1.2 * side)); r.SetEnd(MM(x_ant_end + 35.0, (-1.2 + 10.4) * side))
        r.SetLayer(layer); r.SetWidth(pcbnew.FromMM(w))
        fp.Add(r)
    for cx, cy, r_ in ((x_ant_end + 1.5, (-1.2 + 10.4 - 1.2) * side, 0.8),   # ANT hole (pin 7)
                       (-(2.54 + SRX_GAP), 0, 0.5), (-SRX_GAP, 0, 0.5)):    # free pins 1, 2
        c = pcbnew.PCB_SHAPE(fp)
        c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(MM(cx, cy)); c.SetEnd(MM(cx + r_, cy))
        c.SetLayer(pcbnew.F_SilkS); c.SetWidth(pcbnew.FromMM(0.15))
        fp.Add(c)
    fp.Reference().SetPosition(MM(-6, 4.5 * side))
    fp.Value().SetPosition(MM(-6, 7.0 * side))
    fp.SetLibDescription("SRX882 receiver module lying flat on a 1x4 female header (pins 3-6); pins 1-2 free")
    return fp


def build_pcb():
    board = pcbnew.BOARD()
    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    outline = pcbnew.PCB_SHAPE(board)
    outline.SetShape(pcbnew.SHAPE_T_RECT)
    outline.SetStart(MM(OX, OY)); outline.SetEnd(MM(OX + W, OY + H))
    outline.SetLayer(pcbnew.Edge_Cuts); outline.SetWidth(pcbnew.FromMM(0.1))
    board.Add(outline)

    for ref, (lib, name, value, pins, (x, y), p2dir, back) in PARTS.items():
        fp = srx_socket_footprint(board, name) if lib == "fan-hat" else pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)
        fp.SetReference(ref); fp.SetValue(value)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        if lib == "MountingHole":
            fp.SetExcludedFromBOM(True)
        board.Add(fp)
        fp.SetPosition(MM(OX + x, OY + y))
        if back:
            fp.Flip(fp.GetPosition(), False)
        want = (OX + x + p2dir[0], OY + y + p2dir[1]) if p2dir else None
        pads = sorted((q for q in fp.Pads() if q.GetNumber().isdigit()), key=lambda q: int(q.GetNumber()))
        for r in ([0] if p2dir is None else [0, 90, 180, 270]):
            fp.SetOrientationDegrees(r)
            p2 = pads[1] if p2dir else None
            if want is None or (abs(p2.GetPosition().x - pcbnew.FromMM(want[0])) < 1000 and abs(p2.GetPosition().y - pcbnew.FromMM(want[1])) < 1000):
                break
        else:
            raise SystemExit("no rotation puts %s pin 2 at %r" % (ref, p2dir))
        for pad in fp.Pads():
            n = pins.get(int(pad.GetNumber())) if pad.GetNumber().isdigit() else None
            if not n and ref == "J1":       # KiCad names no-connect pads like the schematic does
                n = "unconnected-(J1-Pin_%s-Pad%s)" % (pad.GetNumber(), pad.GetNumber())
            pad.SetNet(net(n) if n else board.GetNetInfo().GetNetItem(0))
        if lib == "fan-hat":
            try:
                io = pcbnew.PCB_IO_KICAD_SEXPR()
                libdir = os.path.join(HERE, "fan-hat.pretty")
                os.makedirs(libdir, exist_ok=True)
                io.FootprintSave(libdir, fp)
            except Exception as e:
                print("footprint lib not written:", e)

    # J1: pin 1 must be at JP1_PIN1, pin 3 straight above it (photo: square pad bottom-inner)
    j1 = board.FindFootprintByReference("J1")
    p1, p3 = j1.FindPadByNumber("1").GetPosition(), j1.FindPadByNumber("3").GetPosition()
    assert abs(p1.x - pcbnew.FromMM(OX + JP1_PIN1[0])) < 1000 and abs(p1.y - pcbnew.FromMM(OY + JP1_PIN1[1])) < 1000
    assert abs(p3.x - p1.x) < 1000 and abs((p1.y - p3.y) - pcbnew.FromMM(2.54)) < 1000, "J1 pin 3 not above pin 1"
    # SRX bodies: U1 above its pin row (-y), U2 below (+y); ANT ends at +x
    for ref, sign in (("U1", -1), ("U2", 1)):
        f = board.FindFootprintByReference(ref)
        assert sign * (f.GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter().y - f.GetPosition().y) > 0, ref + " body on wrong side"
        assert f.FindPadByNumber("6").GetPosition().x < f.GetPosition().x, ref + " ANT end not at +x"

    # STX882 bodies + ANT holes (the 1x3 socket footprint only shows the socket)
    for ref in ("U3", "U4"):
        px, py = PARTS[ref][4]
        r = pcbnew.PCB_SHAPE(board); r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(MM(OX + px + STX_BODY[0], OY + py + STX_BODY[1])); r.SetEnd(MM(OX + px + STX_BODY[2], OY + py + STX_BODY[3]))
        r.SetLayer(pcbnew.F_SilkS); r.SetWidth(pcbnew.FromMM(0.12)); board.Add(r)
        c = pcbnew.PCB_SHAPE(board); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(MM(OX + px + STX_ANT[0], OY + py + STX_ANT[1])); c.SetEnd(MM(OX + px + STX_ANT[0] + 0.8, OY + py + STX_ANT[1]))
        c.SetLayer(pcbnew.F_SilkS); c.SetWidth(pcbnew.FromMM(0.15)); board.Add(c)

    # bottom side: nothing over the RJ45 (x < 22) -- rule area
    try:
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowFootprints(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetLayer(pcbnew.B_Cu)
        z.SetZoneName("RJ45_below")
        o = z.Outline(); o.NewOutline()
        for px, py in ((7, 0), (22, 0), (22, H), (7, H)):    # x<7 = mounting holes
            o.Append(pcbnew.FromMM(OX + px), pcbnew.FromMM(OY + py))
        board.Add(z)
    except Exception as e:
        print("rule area skipped:", e)

    # GND pours both sides (unfilled; press B in pcbnew)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(net("GND")); z.SetZoneName("GND_" + ("F" if layer == pcbnew.F_Cu else "B"))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # THT pads reach GND on the other side
        o = z.Outline(); o.NewOutline()
        for px, py in ((0, 0), (W, 0), (W, H), (0, H)):
            o.Append(pcbnew.FromMM(OX + px), pcbnew.FromMM(OY + py))
        board.Add(z)

    for text, (x, y), layer in (
        ("wESP32 RF HAT 433/315", (10, 20), pcbnew.F_SilkS),
        ("RJ45 below - keep clear", (11, 20), pcbnew.B_SilkS),
        ("to wESP32 JP1 - pin 1 at edge", (50, 38.4), pcbnew.B_SilkS),
    ):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text); t.SetPosition(MM(OX + x, OY + y)); t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
        if layer == pcbnew.B_SilkS:
            t.SetMirrored(True)
        if x == 10:
            t.SetTextAngleDegrees(90)
        board.Add(t)

    for netname, layer, width, pts in TRACKS:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(MM(OX + x0, OY + y0)); t.SetEnd(MM(OX + x1, OY + y1))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(pcbnew.F_Cu if layer == F else pcbnew.B_Cu)
            t.SetNet(net(netname))
            board.Add(t)
    board.GetDesignSettings().m_MinResolvedSpokes = 1      # one thermal spoke is fine at hobby currents
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    path = os.path.join(HERE, NAME + ".kicad_pcb")
    pcbnew.SaveBoard(path, board)
    return path


# ---- schematic ----------------------------------------------------------------
def sexpr_block(text, header):
    i = text.index(header)
    depth, j, instr = 0, i, False
    while True:
        c = text[j]
        if c == '"' and text[j - 1] != '\\':
            instr = not instr
        elif not instr:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return text[i:j + 1]
        j += 1


PIN_RE = re.compile(r'\(pin\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+[\d.]+\)(?:(?!\(pin\s).)*?\(number\s+"([^"]+)"', re.S)

CUSTOM_SYMS = """
  (symbol "SRX882" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
    (property "Value" "SRX882" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "fan-hat:SRX882_Socket" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "SRX882_0_1" (rectangle (start -7.62 8.89) (end 7.62 -8.89) (stroke (width 0.254) (type default)) (fill (type background))))
    (symbol "SRX882_1_1"
      (pin passive line (at -10.16 1.27 0) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin input line (at -10.16 -1.27 0) (length 2.54) (name "CS" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      (pin output line (at -10.16 -3.81 0) (length 2.54) (name "DATA" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -10.16 -6.35 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
    )
  )
  (symbol "STX882" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 6.35 0) (effects (font (size 1.27 1.27))))
    (property "Value" "STX882" (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "Connector_PinSocket_2.54mm:PinSocket_1x03_P2.54mm_Vertical" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "STX882_0_1" (rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0.254) (type default)) (fill (type background))))
    (symbol "STX882_1_1"
      (pin input line (at -10.16 2.54 0) (length 2.54) (name "DATA" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -10.16 0 0) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -10.16 -2.54 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    )
  )
"""

# ref -> (lib symbol id, sheet position)
SYMS = {
    "J1": ("Connector_Generic:Conn_02x10_Odd_Even", (60, 90)),
    "U1": ("fan-hat:SRX882", (120, 40)), "U2": ("fan-hat:SRX882", (120, 85)),
    "U3": ("fan-hat:STX882", (120, 125)), "U4": ("fan-hat:STX882", (120, 155)),
    "R1": ("Device:R", (175, 40)), "R2": ("Device:R", (175, 60)),
    "R3": ("Device:R", (175, 85)), "R4": ("Device:R", (175, 105)),
    "R5": ("Device:R", (175, 135)), "D1": ("Device:LED", (175, 160)),
    "C1": ("Device:C", (225, 40)), "C2": ("Device:C", (225, 60)), "C3": ("Device:C", (225, 80)),
    "C4": ("Device:C", (225, 100)), "C5": ("Device:C_Polarized", (225, 125)),
    "H1": ("Mechanical:MountingHole", (225, 160)), "H2": ("Mechanical:MountingHole", (245, 160)),
    "H3": ("Mechanical:MountingHole", (225, 175)), "H4": ("Mechanical:MountingHole", (245, 175)),
}


def build_sch():
    libs = {}
    for lib in ("Device", "Connector_Generic", "Mechanical"):
        libs[lib] = open(os.path.join(SYMLIB, lib + ".kicad_sym"), encoding="utf-8").read()
    custom = "(kicad_symbol_lib (version 20241209) (generator \"kicad_symbol_editor\") (generator_version \"9.0\")%s)\n" % CUSTOM_SYMS
    open(os.path.join(HERE, NAME + ".kicad_sym"), "w", encoding="utf-8").write(custom)
    libs["fan-hat"] = custom

    lib_symbols, defs = [], {}
    for lib_id in sorted({v[0] for v in SYMS.values()}):
        lib, name = lib_id.split(":")
        block = sexpr_block(libs[lib], '(symbol "%s"' % name)
        # KiCad's lib copies use "Device:R" as the name and "R_1_1" for units
        block = block.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)
        if "(extends " in block[:200]:
            raise SystemExit("derived symbol not supported: " + lib_id)
        lib_symbols.append(block)
        defs[lib_id] = [(float(x), float(y), int(a), num) for x, y, a, num in PIN_RE.findall(block)]

    root = str(uuid.uuid4())
    out = ['(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")',
           '  (uuid "%s")' % root, '  (paper "A4")', '  (lib_symbols', *lib_symbols, '  )']
    font = '(effects (font (size 1.27 1.27))'
    for ref, (lib_id, (sx, sy)) in SYMS.items():
        lib, fpname, value, pins = PARTS[ref][:4]
        out.append('  (symbol (lib_id "%s") (at %g %g 0) (unit 1) (exclude_from_sim no) (in_bom %s) (on_board yes) (dnp no)'
                   % (lib_id, sx, sy, "no" if ref.startswith("H") else "yes"))
        out.append('    (uuid "%s")' % uuid.uuid4())
        out.append('    (property "Reference" "%s" (at %g %g 0) %s (justify left)))' % (ref, sx + 10, sy - 2, font))
        out.append('    (property "Value" "%s" (at %g %g 0) %s (justify left)))' % (value, sx + 10, sy + 1, font))
        out.append('    (property "Footprint" "%s:%s" (at %g %g 0) %s (hide yes)))' % (lib, fpname, sx, sy, font))
        out.append('    (property "Datasheet" "" (at %g %g 0) %s (hide yes)))' % (sx, sy, font))
        for _, _, _, num in defs[lib_id]:
            out.append('    (pin "%s" (uuid "%s"))' % (num, uuid.uuid4()))
        out.append('    (instances (project "%s" (path "/%s" (reference "%s") (unit 1))))' % (NAME, root, ref))
        out.append('  )')
        # one global label (or no-connect) per pin, at the pin's connection point
        for px, py, ang, num in defs[lib_id]:
            x, y = sx + px, sy - py            # lib y is up, sheet y is down
            n = int(num) if num.isdigit() else None
            netname = pins.get(n)
            if ref == "J1" and n in J1_NC:
                out.append('  (no_connect (at %g %g) (uuid "%s"))' % (x, y, uuid.uuid4()))
                continue
            if not netname:
                continue
            la = (ang + 180) % 360
            just = "left" if la in (0, 90) else "right"
            out.append('  (global_label "%s" (shape input) (at %g %g %d) (fields_autoplaced yes) %s (justify %s)) (uuid "%s")'
                       ' (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 0 0 0) %s (hide yes))))'
                       % (netname, x, y, la, font, just, uuid.uuid4(), font))
    out.append('  (text "wESP32 RF hat: JP1 odd 1 GND 3 IO23 5 IO39 7 IO32 9 GND 11 IO18 13 IO13 15 IO4 17 IO15 19 GND / even 2 3V3 4 IO36 6 IO34 8 IO35 10 IO33 12 IO5 14 IO14 16 IO12 18 IO2 20 V+(5V)\\n'
               'RX data is 5 V: 10k/20k divider -> IO34/IO35.  RJ45 end down: modules lie flat, ANT holes at the +x end, coils exit past the x=75 edge.  SRX882 pins 1-2 (ANT, GND) left free: 2/6 both GND, 1/7 both ANT.  Pin 2-3 gap measured %.2f mm." (exclude_from_sim no) (at 20 20 0) %s (justify left)) (uuid "%s"))' % (SRX_GAP, font, uuid.uuid4()))
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    open(os.path.join(HERE, NAME + ".kicad_sch"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    open(os.path.join(HERE, NAME + ".kicad_pro"), "w").write(json.dumps({
        "meta": {"filename": NAME + ".kicad_pro", "version": 1},
        "board": {"design_settings": {"defaults": {}, "rules": {"min_resolved_spokes": 1}}},
        "sheets": [[root, "Root"]], "boards": [], "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    }, indent=2))
    open(os.path.join(HERE, "sym-lib-table"), "w").write('(sym_lib_table (version 7)\n  (lib (name "fan-hat")(type "KiCad")(uri "${KIPRJMOD}/fan-hat.kicad_sym")(options "")(descr ""))\n)\n')
    open(os.path.join(HERE, "fp-lib-table"), "w").write('(fp_lib_table (version 7)\n  (lib (name "fan-hat")(type "KiCad")(uri "${KIPRJMOD}/fan-hat.pretty")(options "")(descr ""))\n)\n')


# ---- check: schematic netlist == PCB pad nets, ERC, DRC ------------------------------
def check(pcb_path):
    sch = os.path.join(HERE, NAME + ".kicad_sch")
    nl = os.path.join(HERE, "check_netlist.xml")
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", nl, sch], check=True)
    xml = open(nl, encoding="utf-8").read()
    sch_nets = {}
    for netblock in re.findall(r"<net .*?</net>", xml, re.S):
        name = re.search(r'name="([^"]+)"', netblock).group(1)
        for ref, pin in re.findall(r'<node ref="([^"]+)" pin="([^"]+)"', netblock):
            if not name.startswith("unconnected-"):
                sch_nets[(ref, pin)] = name
    board = pcbnew.LoadBoard(pcb_path)
    pcb_nets = {(fp.GetReference(), p.GetNumber()): p.GetNetname() for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetname() and not p.GetNetname().startswith("unconnected-")}
    # the netlist exporter names nets after their global label; unlabeled = Net-(...)
    bad = {k: (sch_nets.get(k), pcb_nets.get(k)) for k in set(sch_nets) | set(pcb_nets) if sch_nets.get(k) != pcb_nets.get(k)}
    assert not bad, "schematic/PCB net mismatch: %r" % bad
    os.remove(nl)
    for cmd, rep in (("sch", "erc"), ("pcb", "drc")):
        r = subprocess.run([CLI, cmd, rep, "--severity-error", "--exit-code-violations", "-o", os.path.join(HERE, "check_%s.rpt" % rep)]
                           + (["--schematic-parity"] if cmd == "pcb" else []) + [
                            sch if cmd == "sch" else pcb_path], capture_output=True, text=True)
        txt = open(os.path.join(HERE, "check_%s.rpt" % rep)).read()
        print(rep.upper(), "exit", r.returncode, "-", " | ".join(l for l in txt.splitlines() if l.startswith("** Found") or "messages" in l))
    print("check OK: %d pads netted, nets match schematic" % len(pcb_nets))


if __name__ == "__main__":
    p = build_pcb()
    build_sch()
    check(p)
