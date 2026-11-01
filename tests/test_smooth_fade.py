"""2.9.0: fades write at 60 Hz and move in log (perceived) space, so each
write is a tiny step. Prints the biggest single-write steps."""
import importlib.machinery, importlib.util, math, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
ld = importlib.machinery.SourceFileLoader("ab", p)
ab = importlib.util.module_from_spec(importlib.util.spec_from_loader("ab", ld)); ld.exec_module(ab)
c = dict(ab.DEFAULTS)
for a, b in [(5, 80), (80, 5), (95, 75), (77, 76), (1, 30)]:
    ctl = ab.Controller(c)
    ctl.target = lambda b=b: float(b)
    ctl.waking = lambda t: False
    cur, t, vals = float(a), 1000.0, [float(a)]
    while True:
        v = ctl.step(t, cur)
        if v is None: break
        cur = v; vals.append(v); t += 1 / 60
        if ctl.ramp is None: break
    d = [abs(y - x) for x, y in zip(vals, vals[1:])]
    lr = [abs(math.log(y / x)) * 100 for x, y in zip(vals, vals[1:])]
    print(f"{a:>3}% -> {b:>3}%: {len(d)} writes over {len(d)/60:.1f}s, max step {max(d):.2f} points, max {max(lr):.2f}% relative")
    assert abs(vals[-1] - b) < 0.01
    assert max(lr) < 6.0, "every write under 6% relative change (old 10 Hz linear: up to 56%)"
print("ok")
