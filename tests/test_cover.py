"""2.5.0: covering the sensor (or the room going dark) dims quickly in two
stages: part-way after dimQuickSeconds, fully after dimHoldSeconds more.
Prints the time to the first dim and to the end of the dimming.
2.16.0: with any faint real reading on the way (a hand lets 1-5 lx through,
a dark room lit by the screen reads 1-4 lx) the timing is unchanged. Exact
0.0 on both sensors straight from a lit room is also what the XPS HID
dropouts look like (6-17 s runs), so on its own it waits zeroDropoutSeconds."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def run(lux_at, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"])
    t, cur, first, done, trace = 0.0, None, None, None, []
    while t < secs:
        v = lux_at(t)
        ctl.feed_lux(t, filt.feed(t, [v, v]))
        if cur is None and ctl.target() is not None: cur = ctl.target()
        if cur is not None:
            pct = ctl.step(t, cur)
            if pct is not None:
                if pct < cur - 0.5 and first is None and t >= 20: first = t - 20
                cur = pct
            if t >= 20 and first is not None and abs(cur - ctl.target()) < 0.5 and ctl.target() <= c["min"] + 0.5 and done is None: done = t - 20
        trace.append((t, cur)); t = round(t + 0.25, 3)
    return first, done, cur

first, done, end = run(lambda t: 300 if t < 20 else (2 if t < 21 else 0), 60)
print("cover at 300 lx (2 lx leak, then 0): first dim after %.1f s, fully dark after %s s, end %.0f%%" % (first, done, end))
assert first is not None and first <= 7.0, first  # 2.10.0: +3.5 s zero-dropout check (was 5 s)
assert done is not None and done <= 20.0, done  # 2.6.0: Apple dims 10x over ~10 s (was 14 s)
first, done, end = run(lambda t: 300 if t < 20 else 1, 60)
print("cover at 300 lx (1 lx): first dim after %.1f s, fully dark after %s s" % (first, done))
assert first is not None and first <= 5.0 and done is not None and done <= 20.0, (first, done)
Z = ab.DEFAULTS["zeroDropoutSeconds"]
first, done, end = run(lambda t: 300 if t < 20 else 0, 80)
print("300 lx -> exactly 0.0 on both sensors: first dim after %.1f s, fully dark after %s s, end %.0f%%" % (first, done, end))
assert first is not None and Z <= first <= Z + 3.5, first
assert done is not None and done <= Z + 20.0 and end <= 1.5, (done, end)
