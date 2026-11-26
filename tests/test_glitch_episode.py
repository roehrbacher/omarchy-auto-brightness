"""2.8.1: replay of a logged glitch (dark room, screen to 100 % at 138 s).
Times are seconds since the recording started. The sensor sends impossible
values (170063 lx) while otherwise reading 0-1 lx, then an in-range 43021 lx
for >10 s. 2.8.0 accepted the 'sustained jump'. 2.16.4 reads one sensor (the
logged recording had two; the second one's part is dropped): for 90 s after an
impossible value a dark -> sunlight jump is not believed at all."""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(seq, secs, dt=0.5):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(c["sensorMedianSeconds"], c)
    cur, t, peak = 1.0, 0.0, 0.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, seq(t)))
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        peak = max(peak, cur)
        t = round(t + dt, 3)
    return peak, ctl

def replay(t):
    v = 1.0
    if 98 <= t < 120 and int(t) % 10 == 0: v = 170063.0   # quarantined to ~150 s
    if 123 <= t < 144: v = 43021.0                        # in range, for 21 s, inside the episode
    if 147 <= t < 148: v = 85969.0
    if 156 <= t < 157: v = 41937.0
    return v

peak, _ = sim(replay, 240)
assert peak <= 2, peak
print("4 min glitch replay (impossible values, 43021 lx for 21 s inside the episode): no change (peak %.1f%%)" % peak)
# an in-range burst right after an impossible value
peak, _ = sim(lambda t: 170000.0 if 10 <= t < 11 else (43000.0 if 20 <= t < 40 else 1.0), 80)
assert peak <= 2, peak
print("43000 lx for 20 s right after an impossible value: ignored")
# real sunlight, no glitch: still accepted
peak, ctl = sim(lambda t: 30000.0 if t >= 20 else 2.0, 60)
assert peak > 90, peak
print("real 2 -> 30000 lx: accepted (peak %.0f%%)" % peak)
# real sunlight after the episode is over: accepted
peak, ctl = sim(lambda t: 170000.0 if 5 <= t < 6 else (30000.0 if t >= 120 else 2.0), 160)
assert peak > 90, peak
print("real sunlight 2 min after a glitch: accepted (peak %.0f%%)" % peak)
