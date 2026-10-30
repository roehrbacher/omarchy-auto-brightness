"""2.8.1: replay of Oct 30 22:29-22:32 (dark room, screen to 100 % at 22:31:18).
sensor1 sends impossible values (172051 lx) from 22:29:07, sensor0 from 22:30:38
(170063 lx) while sensor0 otherwise reads 0-1 lx. sensor1's quarantine ends first,
then it reports an in-range 43021 lx for >10 s while sensor0 (still quarantined)
reads 1 lx. 2.8.0 used sensor1 alone and accepted the 'sustained jump'."""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(seq, secs, dt=0.5):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    cur, t, peak = 1.0, 0.0, 0.0
    while t < secs:
        ctl.feed_lux(t, filt.feed(t, list(seq(t))))
        pct = ctl.step(t, cur)
        if pct is not None:
            cur = pct
        peak = max(peak, cur)
        t = round(t + dt, 3)
    return peak, ctl

T = lambda hh, mm, ss: (hh * 3600 + mm * 60 + ss) - (22 * 3600 + 29 * 60)
def oct30(t):
    s0, s1 = 1.0, 1.0
    if T(22, 29, 4) <= t < T(22, 29, 7): s1 = 43022.0
    if T(22, 29, 7) <= t < T(22, 30, 37) and int(t) % 20 == 0: s1 = 172051.0   # keeps sensor1 quarantined
    if T(22, 30, 38) <= t < T(22, 31, 0) and int(t) % 10 == 0: s0 = 170063.0   # sensor0 quarantined to ~22:31:30
    if T(22, 31, 3) <= t < T(22, 31, 24): s1 = 43021.0
    if T(22, 31, 27) <= t < T(22, 31, 28): s0 = s1 = 85969.0
    if T(22, 31, 36) <= t < T(22, 31, 37): s0 = 41937.0
    return (s0, s1)

peak, _ = sim(oct30, T(22, 33, 0))
assert peak <= 2, peak
print("Oct 30 22:29-22:33 replay (staggered quarantines, 43021 lx on one sensor): no change (peak %.1f%%)" % peak)
# both sensors reading the same burst inside a glitch episode
peak, _ = sim(lambda t: (170000.0, 1.0) if 10 <= t < 11 else ((43000.0, 43000.0) if 20 <= t < 40 else (1.0, 1.0)), 80)
assert peak <= 2, peak
print("both sensors 43000 lx for 20 s right after an impossible value: ignored")
# real sunlight, no glitch: still accepted
peak, ctl = sim(lambda t: (30000.0, 28000.0) if t >= 20 else (2.0, 2.0), 60)
assert peak > 90, peak
print("real 2 -> 30000 lx on both sensors: accepted (peak %.0f%%)" % peak)
# real sunlight after the episode is over: accepted
peak, ctl = sim(lambda t: (170000.0, 1.0) if 5 <= t < 6 else ((30000.0, 28000.0) if t >= 120 else (2.0, 2.0)), 160)
assert peak > 90, peak
print("real sunlight 2 min after a glitch: accepted (peak %.0f%%)" % peak)
