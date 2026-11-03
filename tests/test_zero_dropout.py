"""2.10.0: replay of Nov 3 12:01-12:05: both sensors read ~106 lx but keep
dropping to exactly 0 for 0.5-2.5 s, sometimes both at once. 2.9.0 dimmed
part-way (59% -> 32%) and came back. Real darkness must still dim."""
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
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    cur, t, lo = 60.0, 0.0, 100.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, [float(x) for x in seq(t)]))
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
print("Nov 3 drop-out pattern for 170 s: no dim (lowest %.0f%%, steady %.0f%%)" % (lo, lo0))
lo, cur, ctl = sim(lambda t: (106, 106) if t < 30 else (0, 0), 90)
assert cur < 10 and ctl.stable == 0, (cur, ctl.stable)
print("real 106 -> 0 lx on both sensors: still dims to %.0f%%" % cur)
