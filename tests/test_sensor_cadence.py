"""2.16.0 / 2.16.5: the light sensor is read at most once a second, also
while fading; brightness writes during a fade stay at 60 Hz. The 0.9 s
end-to-start gap is in test_sensor_read_gap.py. Up to 2.15 every 60 Hz fade
pass read the sensor (each XPS HID read is a round trip to the sensor hub).
Real loop on a fake clock (inline reads), plus the background reader on the
real clock."""
import os, tempfile, time
import loop_harness

lp = loop_harness.Loop(lux=50, screen=100)
lp.run(40, {10: lambda lp: lp.room(5000)})
writes = [t for v, t in lp.screen_writes()]
fade = [t for t in writes if t > 10]
assert fade, "no fade"
t0, t1 = fade[0], fade[-1]
reads = [t for t in lp.reads if t0 <= t <= t1]  # one entry per sensor read (one sensor since 2.16.4)
per_s = len(reads) / max(t1 - t0, 1e-9)
wps = len(fade) / max(t1 - t0, 1e-9)
print(f"fade {t1 - t0:.1f} s: {len(fade)} brightness writes ({wps:.0f}/s), {len(reads)} sensor reads ({per_s:.1f}/s)")
assert wps >= 30 and per_s <= 1.2, (wps, per_s)
idle = [t for t in lp.reads if 30 <= t <= 40]
assert 9 <= len(idle) <= 12, len(idle)

# background reader: real thread, real clock, fake files
d = tempfile.mkdtemp(prefix="ab-reader-")
f = os.path.join(d, "a")
open(f, "w").write("123\n")
ab = loop_harness.load(d)
r = ab.SensorReader((f, 1.0), threaded=True)
r.interval, r.min_gap = 1.0, 0.9
seen, end = [], time.monotonic() + 3.2
while time.monotonic() < end:
    got = r.take(time.monotonic())
    if got: seen.append(got)
    time.sleep(1 / 60)
assert 3 <= len(seen) <= 5 and all(g[1] == 123.0 for g in seen), seen
assert all(isinstance(g[2], int) for g in seen), "read time is kept for the log"
open(f + ".tmp", "w").write("7\n"); os.replace(f + ".tmp", f)
r.flush(time.monotonic())
got = None
for _ in range(200):
    got = r.take(time.monotonic())
    if got: break
    time.sleep(0.01)
assert got and got[1] == 7.0, got
print(f"background reader at 1 Hz: {len(seen)} samples in 3.2 s; flush reads again after the 0.9 s gap")
print("ok")
