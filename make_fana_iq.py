# Generate a HackRF cs8 IQ file replaying one Fan A (FT0317A) button press.
# Usage: python make_fana_iq.py <cmd_hex> [prefix_hex]
#   e.g. 08 for speed 3, 05 for power toggle; prefix defaults to remote A1 (00CE17), A2 is 114017
# Transmit: hackrf_transfer -t fanA_cmd.cs8 -f 433820000 -s 2000000 -x 30 -a 1
#   (tuned 100 kHz low; the tone is generated at +100 kHz so it lands on 433.92 MHz)
import math, struct, sys

FS = 2_000_000          # sample rate
TONE = 100_000          # baseband offset, Hz
AMP = 110               # int8 amplitude
cmd = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x08
PREFIX = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x00CE17  # remote ID; A1=00CE17, A2=114017

def bits(frame_cmd):
    v = (PREFIX << 16) | (frame_cmd << 8) | frame_cmd   # 40 bits
    return [(v >> (39 - i)) & 1 for i in range(40)]

# ponytail: pulse widths straight from the rtl_433 capture; tweak here if the
# fan ignores it (real receivers tolerate ~10%, but the knob stays visible)
SHORT, LONG, SYNC_LOW = 300e-6, 890e-6, 5100e-6

def frame_pulses(frame_cmd):
    p = []
    for b in bits(frame_cmd):
        p += [(LONG, 1), (SHORT, 0)] if b else [(SHORT, 1), (LONG, 0)]
    p += [(SHORT, 1), (SYNC_LOW, 0)]                    # sync
    return p

pulses = []
for _ in range(5): pulses += frame_pulses(cmd)          # B frames
pulses += [(33e-3, 0)]
for _ in range(5): pulses += frame_pulses(cmd | 0x40)   # C frames
pulses += [(50e-3, 0)]

out = bytearray()
phase = 0.0
dp = 2 * math.pi * TONE / FS
for dur, on in pulses:
    n = round(dur * FS)
    if on:
        for _ in range(n):
            out += struct.pack('bb', int(AMP * math.cos(phase)), int(AMP * math.sin(phase)))
            phase += dp
    else:
        out += b'\x00\x00' * n

fn = 'fanA_cmd.cs8'
open(fn, 'wb').write(out)
print(f'cmd 0x{cmd:02x} -> {fn}: {len(out)} bytes, {len(out)/2/FS*1000:.0f} ms')
