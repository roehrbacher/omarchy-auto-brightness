"""2.8.0: replay of a logged ~50 min (dark room, 5x screen to 100 %).
The sensor sends HID garbage for >10 s (in-range ~43000 lx mixed with
impossible 170063 / 24318 lx). 2.7.0 took it and accepted the 'sustained jump'
after 10 s. 2.16.4 reads one sensor (the log had a second one reading 2 lx
that vetoed such bursts): the impossible values quarantine the sensor and the
glitch episode rule holds the screen; an in-range burst alone must last 10 s."""
import importlib.machinery, importlib.util, os, tempfile, json
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(seq, secs):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(c["sensorMedianSeconds"], c)
    cur, t, peak = 1.0, 0.0, 0.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, seq(t)))
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        peak = max(peak, cur)
        t = round(t + 0.5, 3)
    return peak, ctl

def burst(t, impossible):
    if 60 <= t < 80:  # 20 s of garbage
        if impossible and int(t * 2) % 7 == 0:
            return 170063.0
        return 42915.0
    return 2.0

peak, _ = sim(lambda t: burst(t, True), 140)
assert peak <= 2, peak
print("burst with impossible values (20 s): no change (peak %.1f%%)" % peak)
peak, _ = sim(lambda t: 42915.0 if 60 <= t < 69 else 2.0, 140)
assert peak <= 2, peak
print("in-range burst 42915 lx vs 2 lx (9 s): no change (peak %.1f%%)" % peak)

# real sunlight is still accepted
peak, ctl = sim(lambda t: 30000.0 if t >= 60 else 2.0, 100)
assert peak > 90 and ctl.stable > 20000, (peak, ctl.stable)
print("real 2 -> 30000 lx: accepted (peak %.0f%%)" % peak)
# covering the sensor in a lit room: exact zeros, held for the 60 s dropout wait, then believed
peak, ctl = sim(lambda t: 0.0 if t >= 30 else 300.0, 60)
assert abs(ctl.stable - 300) < 1, ctl.stable
peak, ctl = sim(lambda t: 0.0 if t >= 30 else 300.0, 100)
assert ctl.stable < 1, ctl.stable
print("sensor covered at 300 lx: held for 60 s, then dark")

# decision log rotates at its cap
d = tempfile.mkdtemp(); lg = ab.DecisionLog(os.path.join(d, "decisions.jsonl"), 2000)
for i in range(100):
    lg.write(event="x", raw=1.0, target=1.0)
assert os.path.exists(lg.path + ".1") and os.path.getsize(lg.path) <= 2200
json.loads(open(lg.path).readline())
print("decision log rotates at its size cap")
