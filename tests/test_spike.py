"""2.2.2: the logged 23:50 burst (dark room, 0 lx -> 41008 lx for 6 s -> 1 lx)
must not change the brightness; a real sustained 0 -> 500 lx change must."""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(seq, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"])
    cur, t, first, changed = 1.0, 0.0, None, []
    while t < secs:
        v = seq(t)
        ctl.feed_lux(t, filt.feed(t, [v, v]))  # both sensors report the burst
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        if cur > 2 and first is None:
            first = t
        changed.append(cur)
        t = round(t + 0.5, 3)
    return first, max(changed), ctl

# logged burst: 60 s at 0 lx, 6 s of 41008, then 1 lx
first, peak, _ = sim(lambda t: 41008.0 if 60 <= t < 66 else (0.0 if t < 60 else 1.0), 120)
assert first is None and peak <= 2, (first, peak)
print("burst 0 -> 41008 lx for 6 s: no brightness change (peak %.1f%%)" % peak)

# also a 9.5 s burst is ignored
first, peak, _ = sim(lambda t: 41008.0 if 60 <= t < 69.5 else 0.0, 120)
assert first is None, first
print("9.5 s burst ignored")

# real light: 0 -> 500 lx sustained
first, peak, ctl = sim(lambda t: 500.0 if t >= 60 else 0.0, 90)
assert first is not None and first - 60 <= 8, first
assert abs(ctl.stable - 500) < 1, ctl.stable
print("real 0 -> 500 lx: brightening started after %.1f s (peak %.0f%%)" % (first - 60, peak))

# real sunlight 0 -> 30000 sustained is accepted after ~10 s
first, peak, ctl = sim(lambda t: 30000.0 if t >= 60 else 0.0, 100)
assert first is not None and first - 60 <= 15 and ctl.stable > 20000, first
print("sustained 0 -> 30000 lx accepted after %.1f s" % (first - 60))
