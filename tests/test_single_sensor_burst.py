"""2.8.0: replay of a logged ~50 min (dark room, 5x screen to 100 %).
Sensor 0 alone sends HID garbage for >10 s (in-range ~43000 lx mixed with
impossible 170063 / 24318 lx) while sensor 1 keeps reading 2 lx. 2.7.0 took
the brighter median and accepted the 'sustained jump' after 10 s."""
import importlib.machinery, importlib.util, os, tempfile, json
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(seq, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    cur, t, peak = 1.0, 0.0, 0.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, list(seq(t))))
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        peak = max(peak, cur)
        t = round(t + 0.5, 3)
    return peak, ctl

def burst(t, impossible):
    if 60 <= t < 80:  # 20 s burst on sensor 0 only
        if impossible and int(t * 2) % 7 == 0:
            return (170063.0, 2.0)
        return (42915.0, 2.0)
    return (2.0, 2.0)

peak, _ = sim(lambda t: burst(t, True), 140)
assert peak <= 2, peak
print("sensor-0 burst with impossible values (20 s): no change (peak %.1f%%)" % peak)
peak, _ = sim(lambda t: burst(t, False), 140)
assert peak <= 2, peak
print("sensor-0 in-range burst 42915 lx vs 2 lx (20 s): no change (peak %.1f%%)" % peak)

# real sunlight on both sensors is still accepted
peak, ctl = sim(lambda t: (30000.0, 28000.0) if t >= 60 else (2.0, 2.0), 100)
assert peak > 90 and ctl.stable > 20000, (peak, ctl.stable)
print("real 2 -> 30000 lx on both sensors: accepted (peak %.0f%%)" % peak)
# covering one sensor in a lit room: the uncovered one still wins
peak, ctl = sim(lambda t: (300.0, 0.0 if t >= 30 else 300.0), 60)
assert abs(ctl.stable - 300) < 1, ctl.stable
print("one sensor covered at 300 lx: the brighter still wins")

# decision log rotates at its cap
d = tempfile.mkdtemp(); lg = ab.DecisionLog(os.path.join(d, "decisions.jsonl"), 2000)
for i in range(100):
    lg.write(event="x", raw=[1.0, 2.0], target=1.0)
assert os.path.exists(lg.path + ".1") and os.path.getsize(lg.path) <= 2200
json.loads(open(lg.path).readline())
print("decision log rotates at its size cap")
