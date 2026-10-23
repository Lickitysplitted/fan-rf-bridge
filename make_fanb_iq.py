# Generate a HackRF cs8 IQ file for one Fan B (FA0188A, 315MHz) command.
# Usage: python make_fanb_iq.py <speed1|speed2|speed3|off|light>
# Transmit: hackrf_transfer -t fanB_cmd.cs8 -f 314900000 -s 2000000 -x 30 -a 1
#   (tuned 100 kHz low; tone at +100 kHz lands on 315.000 MHz)
import json, math, struct, sys

FS = 2_000_000
TONE = 100_000
AMP = 110
REPEATS = 8   # remote sends ~10 frames per press; 8 is plenty

name = sys.argv[1] if len(sys.argv) > 1 else 'speed1'
t = json.load(open('fanB_timings.json'))[name]['timings']

out = bytearray()
phase = 0.0
dp = 2 * math.pi * TONE / FS
for _ in range(REPEATS):
    for dur in t:
        n = round(abs(dur) * 1e-6 * FS)
        if dur > 0:
            for _ in range(n):
                out += struct.pack('bb', int(AMP * math.cos(phase)), int(AMP * math.sin(phase)))
                phase += dp
        else:
            out += b'\x00\x00' * n
out += b'\x00\x00' * (FS // 20)  # 50ms tail

open('fanB_cmd.cs8', 'wb').write(out)
print(f'{name} -> fanB_cmd.cs8: {len(out)} bytes, {len(out)/2/FS*1000:.0f} ms')
