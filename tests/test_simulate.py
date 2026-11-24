"""Simulation of the controller (no hardware): spikes, deadband, fades, the
manual offset, fullscreen video, new day / resume, keyboard levels, HID
bursts and the dark-end wobble. Prints a timeline log. Timings as of 2.6.0+
(Apple ramps: 1.5-5 s up, 5-10 s down; big drops wait dimHoldSeconds)."""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
c = dict(ab.DEFAULTS); c.update(min=1, max=100, kbdMaxLevel=2)  # level 2 is opt-in since 2.16.0
ctl = ab.Controller(c)
dt = 0.1
state = {"t": 0.0, "screen": 50.0, "kbd": 0}
def run(secs, lux, no_dim=False, manual=None, label=""):
    if label: print(f"--- {label}")
    if manual is not None:
        state["screen"] = manual; ctl.manual(state["t"], manual, "d1")
    end = state["t"] + secs
    while state["t"] < end - 1e-9:
        t = state["t"]
        ctl.feed_lux(t, lux(t) if callable(lux) else lux)
        v = ctl.step(t, state["screen"], no_dim=no_dim)
        if v is not None: state["screen"] = v
        k = ctl.kbd_level(2)
        if k is not None and k != ctl.kbd_want: ctl.kbd_want = k; state["kbd"] = k; ctl.ev(t, f"keyboard -> {k}")
        for et, m in ctl.events: print(f"t={et:6.1f}s  {m}")
        ctl.events.clear()
        state["t"] += dt
    print(f"t={state['t']:6.1f}s  screen={state['screen']:.0f}% target={ctl.target():.0f}% kbd={state['kbd']}")
    return state["screen"]

s = run(6, 200, label="lit room 200 lx")
assert abs(s - ab.curve_pct(200, c)) < 1
t0 = state["t"]; s = run(3, lambda t: 2 if t - t0 < 1.5 else 200, label="hand over sensor for 1.5 s (ignored)")
assert abs(s - ab.curve_pct(200, c)) < 1
s = run(6, 215, label="+7.5% lux (under 12% deadband, ignored)")
assert abs(s - ab.curve_pct(200, c)) < 1
# brighten fast
run(2.0, 5000, label="walk to window 5000 lx")
run(5.1, 5000)
assert abs(state["screen"] - ab.curve_pct(5000, c)) < 1, "brightened within ~2 s settle + 5 s fade (65% -> 94% is under 1.5x)"
# dim slowly
bright = run(2.0, 20, label="dark room 20 lx (big drop: part-way first, fully after dimHoldSeconds)")
assert abs(bright - ab.curve_pct(5000, c)) < 1, "no reaction to a big drop within 2 s"
mid = run(6.0, 20)
assert ab.curve_pct(20, c) + 3 < mid < bright - 3, "part-way dim first"
s = run(3.5, 20)
assert s > ab.curve_pct(20, c) + 1, "still fading 3.5 s into the full dim (slow dim)"
s = run(2.5, 20)
assert abs(s - ab.curve_pct(20, c)) < 1
# manual offset
s = run(3, 20, manual=s + 15, label="he raises brightness +15")
assert abs(s - (ab.curve_pct(20, c) + 15)) < 1 and abs(ctl.offset - 15) < 1
s = run(7.1, 40, label="20 -> 40 lx (2x, offset kept)")
assert abs(ctl.offset - 15) < 1 and abs(s - min(100, ab.curve_pct(40, c) + 15)) < 1
s = run(12, 300, label="20 -> 300 lx (15x, offset cleared)")
assert ctl.offset == 0 and abs(s - ab.curve_pct(300, c)) < 1
# fullscreen video never dims
s0 = state["screen"]; s = run(10, 3, no_dim=True, label="fullscreen video, room goes dark")
assert s >= s0 - 0.01
s = run(10, 3, label="video ends")
assert abs(s - ab.curve_pct(3, c)) < 1 and state["kbd"] == 1
ctl.manual(state["t"], s + 10, "d1"); ctl.new_day(state["t"], "d2")
assert ctl.offset == 0, "offset cleared next day"
ctl.manual(state["t"], s + 10, "d2"); ctl.reset(state["t"], "resume")
assert ctl.offset == 0 and ctl.stable is None, "fresh reading after resume"
for et, m in ctl.events: print(f"t={et:6.1f}s  {m}")
print("--- keyboard: Apple-style levels with hysteresis")
k = ab.Controller(dict(c)); seen = []
def kb(lux, secs=3):
    global t
    for i in range(int(secs / dt)):
        k.feed_lux(t, lux); w = k.kbd_level(2)
        if w is not None and w != k.kbd_want:
            k.kbd_want = w; seen.append((lux, w)); print(f"lux {lux:>5} -> keyboard {w}")
        t += dt
t = 1000.0
kb(200); assert k.kbd_want == 0
kb(8); assert k.kbd_want == 0, "4-12 lx dead zone keeps off"
kb(3, 13); assert k.kbd_want == 1, "dim -> 1 (big drop: after dimHoldSeconds)"
kb(0, 13); assert k.kbd_want == 2, "very dark -> 2"
kb(1.5); assert k.kbd_want == 2, "1-2 lx keeps 2 (hysteresis)"
kb(3); assert k.kbd_want == 1, "above 2 lx -> 1"
kb(1.5); assert k.kbd_want == 1, "1.5 lx from level 1 stays 1"
before = len(seen); kb(3.5); assert len(seen) == before, "no write without a threshold crossing (his key press sticks)"
kb(0); kb(19); assert k.kbd_want == 0, "covered (2) then lit room 19 lx -> off (a real session)"
print("simulation ok")

# XPS HID sensor bursts (from a real log): dark room, two sensors alternately
# report ~40000 lx for 0.5-1.5 s, overlapping to >2 s of max(). Must be ignored.
f = ab.SensorFilter(2, c["sensorMedianSeconds"])
ctl2 = ab.Controller(c); scr = 1.0; peak = 0
def burst(t):
    a = 41008.0 if 10.0 <= t < 11.5 else 0.0
    b = 41008.0 if 11.0 <= t < 12.5 else 0.0
    return [a, b]
for i in range(300):
    t = i * 0.1
    ctl2.feed_lux(t, f.feed(t, burst(t)))
    v = ctl2.step(t, scr)
    if v is not None: scr = v
    peak = max(peak, scr)
print(f"--- HID burst: peak screen {peak:.0f}% stable={ctl2.stable}")
assert peak < 5 and ctl2.stable == 0.0, "sensor burst must not brighten"
# but a real lamp switched on is followed within ~4.5 s
f = ab.SensorFilter(2, c["sensorMedianSeconds"]); ctl3 = ab.Controller(c)
for i in range(100):
    t = i * 0.1
    ctl3.feed_lux(t, f.feed(t, [0.0 if t < 2 else 300.0, 0.0 if t < 2 else 250.0]))
    if ctl3.stable == 300.0: print(f"--- lamp on at 2 s followed at {t:.1f} s"); break
assert ctl3.stable == 300.0 and t < 7
print("sensor filter OK")

# Dark-end wobble (from a real XPS log): sensor flips 0 <-> 1 lx every few s.
assert abs(ab.curve_pct(1, c) - ab.curve_pct(0, c)) < 1, "no step between 0 and 1 lx"
f = ab.SensorFilter(2, c["sensorMedianSeconds"]); ctl4 = ab.Controller(c); scr = 1.0; lo = hi = None
for i in range(1200):
    t = i * 0.1
    w = 1.0 if int(t / 3) % 2 else 0.0
    ctl4.feed_lux(t, f.feed(t, [w, w]))
    v = ctl4.step(t, scr)
    if v is not None: scr = v
    if t > 5: lo = scr if lo is None else min(lo, scr); hi = scr if hi is None else max(hi, scr)
print(f"--- 0/1 lx wobble 120 s: screen {lo:.1f}..{hi:.1f}%")
assert hi - lo < 0.5, "screen must stay steady"
print("dark wobble OK")
