# Case

Remix of [wESP32 Case by notjj](https://www.thingiverse.com/thing:5901543)
("No Tabs With Port" base + top), licensed
[CC BY-NC-SA](https://creativecommons.org/licenses/by-nc-sa/4.0/). These
derived files are shared under the same licence: credit notjj, non-commercial
use only, and share changes alike.

The stock base was measured and rebuilt 20 mm taller to fit the HAT stack, with
an antenna/LED slot, low side vents, and a magnetic lid. Mount on the wall with
the RJ45 end down.

## wESP32_Case_Base_Tall_HAT.stl  (58 x 42.5 x 85)

Base with walls 20 mm taller than stock (cavity 40.5 deep) for the fan-control HAT
(75 x 40 on M2.5 x 18 standoffs, SRX882 modules 14.5 mm above HAT top).
Stack from floor: 3 posts + 1.2 PCB + 18 standoff + 1.6 HAT + 14.5 modules = 38.3
-> 2.2 mm clearance. Stock screw tubes are omitted (lid is magnetic).

- Antenna/LED slot: 38.8 x 8.5 mm (x -28.89..10.11, y 28.5..37.0) in the end wall
  opposite the RJ45 (top wall when wall-mounted RJ45-down), sitting exactly between
  the two antenna-end magnet blocks and level with their tops. Coil clearance: 4 mm
  coils clear at attach heights up to 11 mm above the HAT top in both board
  orientations; at 12 mm they clip the slot's top edge by ~0.8 mm.
- Vents: 3 x (14 x 6 mm) per side wall at 9-15 mm, in the board-to-HAT air gap.
- Magnet blocks: 7.5 x 9 mm corner ledges, top at 37 mm, 6.2 x 3.2 mm pockets opening
  up. RJ45-end blocks span 29-37; antenna-end blocks span 28.3-37 so they frame the
  slot. Undersides are small unsupported overhangs; enable supports if the slicer flags.

## wESP32_Case_Top_Magnetic.stl  (58 x 5.5 x 85)

Same outline and lip as the stock lid plus four 3.5 mm corner bosses (inside the lip)
with 6.2 x 3.2 pockets opening down. 8 x 6x3 mm disc magnets total, glued; faces meet
37 mm above the floor. Glue base magnets first, snap lid magnets on to set polarity.
