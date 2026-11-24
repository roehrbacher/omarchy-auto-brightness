"""2.16.0: the light sensors are read at most twice a second (4 Hz with
the popup open), also while fading; brightness writes during a fade stay at
60 Hz. Up to 2.15 every 60 Hz fade pass read both sensors (each XPS HID read
is a round trip to the sensor hub), and the logged impossible values came
about 11x more often per hour while fading. Real loop on a fake clock
(inline reads), plus the background reader on the real clock."""
import os, tempfile, time
import loop_harness

lp = loop_harness.Loop(lux=50, screen=100)
lp.run(40, {10: lambda lp: lp.room(5000)})
writes = [t for v, t in lp.screen_writes()]
fade = [t for t in writes if t > 10]
assert fade, "no fade"
t0, t1 = fade[0], fade[-1]
reads = [t for t in lp.reads if t0 <= t <= t1]  # one entry per sensor read
per_s = len(reads) / 2 / max(t1 - t0, 1e-9)
wps = len(fade) / max(t1 - t0, 1e-9)
print(f"fade {t1 - t0:.1f} s: {len(fade)} brightness writes ({wps:.0f}/s), {len(reads) // 2} reads per sensor ({per_s:.1f}/s)")
assert wps >= 30 and per_s <= 2.2, (wps, per_s)
idle = [t for t in lp.reads if 30 <= t <= 40]
assert len(idle) / 2 <= 21, len(idle)

# background reader: real thread, real clock, fake files
d = tempfile.mkdtemp(prefix="ab-reader-")
fs = [os.path.join(d, n) for n in ("a", "b")]
for f in fs: open(f, "w").write("123\n")
ab = loop_harness.load(d)
r = ab.SensorReader([(f, 1.0) for f in fs], threaded=True)
r.interval = 0.25
seen, end = [], time.monotonic() + 1.3
while time.monotonic() < end:
    got = r.take(time.monotonic())
    if got: seen.append(got)
    time.sleep(1 / 60)
assert 4 <= len(seen) <= 7 and all(g[1] == [123.0, 123.0] for g in seen), seen
assert all(len(g[2]) == 2 for g in seen), "read time per sensor is kept for the log"
open(fs[0] + ".tmp", "w").write("7\n"); os.replace(fs[0] + ".tmp", fs[0])
r.flush(time.monotonic())
for _ in range(50):
    got = r.take(time.monotonic())
    if got: break
    time.sleep(0.01)
assert got and got[1][0] == 7.0, got
print(f"background reader at 4 Hz: {len(seen)} samples in 1.3 s; flush reads again at once")
print("ok")
