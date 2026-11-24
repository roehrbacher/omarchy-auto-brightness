"""2.10.1: the daemon reads the sensors on every loop pass, 60 times a second
while a fade runs and twice a second otherwise. The per-sensor median used to
count samples, not time, so a 2 s single-sensor HID burst during a fade got
120 samples against the ~8 calm ones before it and won the 4 s median: in a
lit 300 lx room the screen faded 66 % -> 100 % (and took ~9 s to come back).
The same burst at the idle cadence is ignored (it fills only half the window). The median must weigh each reading by how long
it lasted. Replays the daemon's cadence (1/60 s while fading, else 0.5 s)."""
import importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)

def sim(lux_at, secs, sample=None):
    """sample=None: feed the sensors on every pass (the 2.10-2.15 cadence);
    sample=0.25: at most every 0.25 s like 2.16.0, while writes stay at 60 Hz."""
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"], c)
    t, cur, peak, fades, last = 0.0, None, 0.0, 0, None
    while t < secs:
        if sample is None or last is None or t - last >= sample - 1e-6:
            last = t
            ctl.feed_lux(t, filt.feed(t, lux_at(t)))
        if cur is None and ctl.target() is not None: cur = ctl.target()
        if cur is not None:
            if ctl.ramp is None and abs(ctl.target() - cur) >= 1: fades += 1
            v = ctl.step(t, cur)
            if v is not None: cur = v
            if t > 1: peak = max(peak, cur)
        t += 1 / 60 if ctl.ramp is not None else 0.5
    return peak, cur, c

# 150 lx room, a lamp at 20 s brings it to 300 lx (a fade up starts ~2-4 s
# later); 0.5 s into that fade sensor0 sends 41008 lx for 2 s.
def lamp_and_burst(t):
    room = 150.0 if t < 20 else 300.0
    a = room
    if 24.5 <= t < 26.5: a = 41008.0
    return [a, room * 0.9]
peak, end, c = sim(lamp_and_burst, 60)
want = ab.curve_pct(300, c)
print(f"burst during a fade at 300 lx: peak {peak:.0f}% (room level {want:.0f}%), end {end:.0f}%")
assert peak < want + 1, f"single-sensor burst during a fade must not brighten (peak {peak:.0f}%)"
assert abs(end - want) < 1, end

# the median still follows a real change at the 60 Hz cadence: a lamp to
# 3000 lx that starts during a fade is followed
def real(t):
    v = 150.0 if t < 20 else (300.0 if t < 23 else 3000.0)
    return [v, v * 0.9]
peak, end, c = sim(real, 60)
print(f"real 300 -> 3000 lx during a fade: end {end:.0f}% (want {ab.curve_pct(3000, c):.0f}%)")
assert abs(end - ab.curve_pct(3000, c)) < 1

# 2.16.0: the daemon reads the sensors at most 4 times a second, also while
# fading. The same burst and the same real change come out the same.
for name, fn, want in (("burst", lamp_and_burst, ab.curve_pct(300, c)), ("real", real, ab.curve_pct(3000, c))):
    peak, end, _ = sim(fn, 60, sample=0.25)
    print(f"4 Hz sensor reads, {name}: peak {peak:.0f}%, end {end:.0f}% (want {want:.0f}%)")
    assert abs(end - want) < 1 and (name == "real" or peak < want + 1)
print("ok")
