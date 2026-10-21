"""Simulation of the v2 controller (no hardware). Prints a timeline log and
asserts the MacBook-style behaviour. Run: python3 tests/simulate.py"""
import importlib.machinery, importlib.util, os
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
c = dict(ab.DEFAULTS); c.update(min=1, max=100)
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

s = run(3, 200, label="office 200 lx")
assert abs(s - ab.curve_pct(200, c)) < 1
t0 = state["t"]; s = run(3, lambda t: 2 if t - t0 < 1.5 else 200, label="hand over sensor for 1.5 s (ignored)")
assert abs(s - ab.curve_pct(200, c)) < 1
s = run(6, 215, label="+7.5% lux (under 12% deadband, ignored)")
assert abs(s - ab.curve_pct(200, c)) < 1
# brighten fast
t0 = state["t"]; run(2.0, 5000, label="walk to window 5000 lx")
up_at = None
before = state["screen"]; run(1.6, 5000)
assert abs(state["screen"] - ab.curve_pct(5000, c)) < 1, "brightened within ~2 s settle + 1.5 s fade"
# dim slowly
run(2.0, 20, label="dark room 20 lx")
mid = run(3.5, 20)
assert mid > ab.curve_pct(20, c) + 3, "still fading after 3.5 s (slow dim)"
s = run(4, 20)
assert abs(s - ab.curve_pct(20, c)) < 1
# manual offset
s = run(3, 20, manual=s + 15, label="he raises brightness +15")
assert abs(s - (ab.curve_pct(20, c) + 15)) < 1 and abs(ctl.offset - 15) < 1
s = run(4, 40, label="20 -> 40 lx (2x, offset kept)")
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
kb(15); assert k.kbd_want == 0, "8-30 lx dead zone keeps off"
kb(6); assert k.kbd_want == 1, "dim -> 1"
kb(2); assert k.kbd_want == 2, "very dark -> 2"
kb(4); assert k.kbd_want == 2, "3-5 lx keeps 2 (hysteresis)"
kb(7); assert k.kbd_want == 1, "above 5 lx -> 1"
kb(4); assert k.kbd_want == 1, "4 lx from level 1 stays 1"
before = len(seen); kb(6.5); assert len(seen) == before, "no write without a threshold crossing (his key press sticks)"
kb(40); assert k.kbd_want == 0, "bright -> off"
print("simulation ok")
