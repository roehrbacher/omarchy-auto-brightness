"""2.6.0: Apple-style ramps (patent US 2012/0019493) and slower settling in the
dark (US 10,235,970)."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
c = dict(ab.DEFAULTS); ctl = ab.Controller(c)
R = ctl.ramp_seconds
cases = [(60, 40, 5.0), (60, 20, 5.0), (100, 10, 10.0), (100, 1, 10.0),
         (40, 60, 5.0), (30, 60, 1.5), (10, 90, 1.5)]
for a, b, want in cases:
    got = R(a, b); print(f"{a}% -> {b}%: {got:.1f} s (patent ~{want:g} s)")
    assert abs(got - want) < 0.05, (a, b, got)
assert 5.0 < R(100, 20) < 10.0                  # 5x dim in between
assert R(50, 40) > R(40, 50) - 1e-9             # never dims faster than it brightens
ctl.stable = 300; assert ctl.settle_seconds() == c["settleSeconds"]
ctl.stable = 0; assert abs(ctl.settle_seconds() - 2 * c["settleSeconds"]) < 1e-9
ctl.stable = 5; assert abs(ctl.settle_seconds() - 1.5 * c["settleSeconds"]) < 1e-9
c2 = dict(c, appleRamps=False); assert ab.Controller(c2).ramp_seconds(60, 20) == c["dimSeconds"]
print("ok")
