import importlib.machinery, importlib.util, os, sys
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
c = dict(ab.DEFAULTS); c.update(min=10, max=90)
vals = [ab.curve_pct(l, c) for l in (0, 1, 5, 30, 150, 600, 2500, 10000, 50000)]
assert abs(vals[0] - 10) < 1e-6 and abs(vals[-1] - 90) < 1e-6, vals
assert all(a <= b for a, b in zip(vals, vals[1:])), vals
print("curve ok:", [round(v) for v in vals])
