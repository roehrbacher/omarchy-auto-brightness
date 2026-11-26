"""2.10.0: replay of a logged ~4 min: both sensors read ~106 lx but keep
dropping to exactly 0 for 0.5-2.5 s, sometimes both at once. 2.9.0 dimmed
part-way (59% -> 32%) and came back. Real darkness must still dim.
2.16.4 reads one sensor (the first column of the capture) and an exact 0 never
beats a non-zero reading, at any light level."""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

# the captured 0.5 s pattern (sensor1 raw, sensor2 raw) / 1000 = lux
CAP = [(0,0),(112,0),(0,112),(112,0),(112,0),(112,0),(112,0),(112,116),(116,0),(106,106),(106,106),
       (106,0),(0,0),(106,0),(106,0),(106,0),(106,0),(106,0),(106,0),(0,0),(0,104),(104,0),(0,0),(0,0),
       (0,0),(0,0),(0,0),(102,0),(102,0),(102,0),(0,102),(102,0),(106,0),(106,0),(106,0),(0,106),(0,0),(0,106),(106,0),(106,0)]

def sim(seq, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(c["sensorMedianSeconds"], c)
    cur, t, lo = 60.0, 0.0, 100.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, float(seq(t)[0])))
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        if t > 30: lo = min(lo, cur)
        t = round(t + 0.5, 3)
    return lo, cur, ctl

def dropouts(t):
    if t < 30: return (106, 106)
    return CAP[int((t - 30) * 2) % len(CAP)]

lo0, _, _ = sim(lambda t: (106, 106), 200)
lo, cur, ctl = sim(dropouts, 200)
assert lo >= lo0 - 1, (lo, lo0)
print("Logged drop-out pattern for 170 s: no dim (lowest %.0f%%, steady %.0f%%)" % (lo, lo0))
lo, cur, ctl = sim(lambda t: (106, 106) if t < 30 else (0, 0), 30 + ab.DEFAULTS["zeroDropoutSeconds"] + 40)
assert cur < 10 and ctl.stable == 0, (cur, ctl.stable)
print("real 106 -> 0 lx on both sensors: still dims to %.0f%%" % cur)

# 2.16.4: at any light level, zeros alone wait zeroDropoutSeconds; after a faint
# reading (lights off) they count after zeroTrustSeconds
c = dict(ab.DEFAULTS)
def zeros_after(before, run=100.0):
    f, t, out = ab.SensorFilter(c["sensorMedianSeconds"], c), 0.0, None
    while t < 20:
        f.feed(t, before); t += 0.5
    start = t
    while t < start + run:
        if f.feed(t, 0.0) == 0 and out is None: out = t - start
        t += 0.5
    return out
for lux in (300.0, 20.0, 16.0, 7.0, 6.0):
    got = zeros_after(lux)
    assert got is not None and abs(got - c["zeroDropoutSeconds"]) <= 5, (lux, got)
for lux in (5.0, 2.0, 1.0):
    got = zeros_after(lux)
    assert got is not None and abs(got - c["zeroTrustSeconds"]) <= 1.5, (lux, got)
print("zeros count after %.0f s from 6-300 lx and after %.1f s right after a 1-5 lx reading" % (c["zeroDropoutSeconds"], c["zeroTrustSeconds"]))
# a zero with nothing before it (start, resume) is just the reading
f = ab.SensorFilter(c["sensorMedianSeconds"], c)
assert f.feed(0.0, 0.0) == 0.0
print("ok")
