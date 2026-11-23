"""2.10.1: lights off in an already dim room (3-5 lx, keyboard at level 1).
The part-way dim lands at ~1.2 lx and the real 0 lx is then inside the 2 lx
deadband, so up to 2.10.0 the controller stayed at the made-up part-way value
and the keyboard never went to level 2 (below 1 lx). The staged dim must end
at the real reading. The screen is at the floor either way (0-2 lx is dark)."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(before, secs=60):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    t, cur, levels = 0.0, 50.0, []
    while t < secs:
        v = before if t < 20 else 0.0
        ctl.feed_lux(t, filt.feed(t, [v, v]))
        pct = ctl.step(t, cur)
        if pct is not None: cur = pct
        k = ctl.kbd_level(2, t)
        if k is not None and k != ctl.kbd_want: ctl.kbd_want = k; levels.append((round(t - 20, 1), k))
        t = round(t + 0.5, 3)
    return levels, cur, ctl

for before in (3.0, 4.0, 5.0):
    levels, cur, ctl = sim(before)
    print(f"{before:.0f} -> 0 lx: keyboard {levels}, screen {cur:.0f}%, lux {ctl.stable}")
    assert levels and levels[-1][1] == 2, f"{before} -> 0 lx must end at keyboard level 2"
    assert cur <= 1.5, cur
print("ok")
