"""2.7.0: a logged resume in a dark room. The sensor first reported a stale
4 lx, then 0 lx. 2.6.1 faded 63% -> 19% -> 1% over ~18 s and never lit the
keyboard (the part-way dim 4 -> 1.2 lx stayed "staged" because 1.2 -> 0 lx is
inside the 2 lx deadband). Now: dark within ~3 s, keyboard on at once."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(lux_at, wake=True, secs=30):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100, kbdMaxLevel=2)  # level 2 is opt-in since 2.16.0
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"])
    if wake: ctl.reset(0.0, "resume")
    t, cur, kbd, dark_at, kbd_at = 0.0, 63.0, None, None, None
    while t < secs:
        v = lux_at(t); ctl.feed_lux(t, filt.feed(t, [v, v]))
        pct = ctl.step(t, cur)
        if pct is not None: cur = pct
        k = ctl.kbd_level(3, t)
        if k is not None and k != ctl.kbd_want: ctl.kbd_want = k; kbd = k; kbd_at = kbd_at or t
        if dark_at is None and cur <= 1.5: dark_at = t
        t = round(t + 0.1, 3)
    return dark_at, kbd, kbd_at, ctl

dark_at, kbd, kbd_at, ctl = sim(lambda t: 4.0 if t < 1.5 else 0.0)
print(f"wake in the dark (stale 4 lx first): screen 1% after {dark_at:.1f}s, keyboard level {kbd} after {kbd_at:.1f}s")
assert dark_at is not None and dark_at <= 4.0, dark_at
assert kbd and kbd >= 1 and kbd_at <= 4.0, (kbd, kbd_at)
# deadband regression without wake: 4 lx -> 0 lx steady must end the staged dim and light the keyboard
c = dict(ab.DEFAULTS); c.update(kbdMaxLevel=2); ctl = ab.Controller(c); filt = ab.SensorFilter(2, 4.0); t = 0.0; kb = None
while t < 60:
    v = 4.0 if t < 10 else 0.0; ctl.feed_lux(t, filt.feed(t, [v, v])); ctl.step(t, 50)
    k = ctl.kbd_level(3, t)
    if k is not None and k != ctl.kbd_want: ctl.kbd_want = k; kb = (k, t)
    t = round(t + 0.25, 3)
print(f"no wake, 4 -> 0 lx: keyboard level {kb[0]} at {kb[1]-10:.1f}s after the drop")
assert kb and kb[0] == 2 and not ctl.dim_staged  # 0 lx is below kbdLevel2Below (2.10.1)
