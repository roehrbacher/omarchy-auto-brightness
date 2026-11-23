"""2.10.2: lights go off, the screen dims part-way, and you press brightness
up because you want it brighter in the dark. Up to 2.10.1 your offset was
anchored to the made-up part-way lux (13 lx); the pending full dim then moved
the light "14x" from there, cleared the offset and faded the screen to the
minimum ~6 s after your key press. The README promises the offset stays until
the room light moves more than 2.5x from where you set it, and the room did
not change after the press. A press during the part-way dim now accepts the
darkness the dim was heading for, so your level sticks."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(lux_at, secs, press_after_dim=2.0, delta=20):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    t, cur, staged_at, pressed, after = 0.0, None, None, None, []
    while t < secs:
        v = lux_at(t)
        ctl.feed_lux(t, filt.feed(t, [v, v]))
        if cur is None: cur = ctl.target()
        if staged_at is None and ctl.dim_staged: staged_at = t
        if pressed is None and staged_at is not None and t - staged_at >= press_after_dim:
            cur = min(100, cur + delta); ctl.manual(t, cur, "d"); pressed = cur
        x = ctl.step(t, cur)
        if x is not None: cur = x
        if pressed is not None: after.append(cur)
        t = round(t + (1 / 60 if ctl.ramp is not None else 0.5), 4)
    return pressed, after, ctl, c

pressed, after, ctl, c = sim(lambda t: 200.0 if t < 20 else 0.0, 70)
print(f"lights off, pressed up to {pressed:.0f}% during the part-way dim: lowest after {min(after):.0f}%, end {after[-1]:.0f}%, offset {ctl.offset:+.0f}")
assert min(after) >= pressed - 1, "the screen must not dim below what you just set"
assert ctl.offset > 0

# the offset still goes when the light really comes back (2.5x rule)
pressed, after, ctl, c = sim(lambda t: 200.0 if t < 20 or t > 50 else 0.0, 80)
print(f"...and the lights come back on at 50 s: end {after[-1]:.0f}% (curve at 200 lx {ab.curve_pct(200, c):.0f}%), offset {ctl.offset:+.0f}")
assert ctl.offset == 0 and abs(after[-1] - ab.curve_pct(200, c)) < 1
print("ok")
