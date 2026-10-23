"""2.4.0: the 23 Oct train dips (cabin ~210-400 lx, sensors at 0 lx for 2-7 s)
also faded the screen 67% -> 1%. Big drops must now hold dimHoldSeconds before
the screen dims; a real lasting darkness still dims, brightening stays quick."""
import ast, importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
SEQ = ast.literal_eval(open(os.path.join(here, "train-2026-10-23.txt")).read())

def sim(lux_at, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"])
    t, cur, lo, first_dim = 0.0, None, 100.0, None
    while t < secs:
        v = lux_at(t)
        ctl.feed_lux(t, filt.feed(t, [v, v]))
        if cur is None and ctl.target() is not None:
            cur = ctl.target()
        if cur is not None:
            pct = ctl.step(t, cur)
            if pct is not None:
                if pct < cur and ctl.ramp and first_dim is None and t > 5:
                    first_dim = t
                cur = pct
            if t > 5: lo = min(lo, cur)
        t = round(t + 0.5, 3)
    return lo, first_dim, cur

def replay(t):
    v = SEQ[0][1]
    for st, lux in SEQ:
        if st > t: break
        v = lux
    return v

lo, first, _ = sim(replay, SEQ[-1][0] + 30)
base = ab.curve_pct(200, dict(ab.DEFAULTS, min=1, max=100))
assert lo >= base - 1, (lo, base)
print("train replay: screen never below %.0f%% (curve at 200 lx = %.0f%%)" % (lo, base))
for d in (2, 4, 6, 7, 10):
    lo, first, _ = sim(lambda t: 0.0 if 30 <= t < 30 + d else 250.0, 90)
    assert first is None, (d, first)
print("0 lx dips of 2-10 s: screen does not dim")
lo, first, cur = sim(lambda t: 0.0 if t >= 30 else 250.0, 90)
assert first is not None and 30 + 12 <= first <= 30 + 18 and cur <= 2, (first, cur)
print("lasting darkness: dimming starts after %.1f s, ends at %.0f%%" % (first - 30, cur))
lo, first, cur = sim(lambda t: 150.0 if t >= 30 else 250.0, 60)
assert first is not None and first - 30 <= 5, first
print("small drop 250 -> 150 lx: dims after %.1f s (unchanged)" % (first - 30))
