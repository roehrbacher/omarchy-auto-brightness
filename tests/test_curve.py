import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
c = dict(ab.DEFAULTS); c.update(min=1, max=100)
vals = [ab.curve_pct(l, c) for l in (0, 1, 5, 30, 150, 600, 2500, 10000, 50000)]
assert abs(vals[0] - 8) < 1e-6, "8% floor even with min 1"
assert abs(vals[-1] - 100) < 1e-6
assert all(a <= b for a, b in zip(vals, vals[1:])), vals
print("curve ok:", [round(v) for v in vals])
