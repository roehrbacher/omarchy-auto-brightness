"""2.16.0: the screen coming back from a blank (lock screen idle, DPMS off)
behaves like a MacBook display waking: the light sensor kept reading while
it was off, and the screen goes straight to the level for the room
(0.4 s instead of a 1.5-10 s fade). Waking in a dark room it never jumps
up: brightening there takes the normal fade (Apple's "luminescence shock
avoidance", US 8,743,161 / US 11,755,143). Real loop, fake sysfs and clock."""
import loop_harness

def blank(lp): lp.off = True
def wake(lp): lp.off = False

def after_wake(lp, t0=100):
    w = [(v, t) for v, t in lp.screen_writes() if t >= t0]
    return w, (w[-1][1] - w[0][1] if w else None)

C = dict(min=1, max=100)
# lit room got much brighter while blanked: there at once on wake
lp = loop_harness.Loop(lux=100, screen=500, conf=C).run(110, {40: blank, 60: lambda lp: lp.room(3000), 100: wake})
w, dur = after_wake(lp)
want = round(lp.ab.curve_pct(3000, dict(lp.ab.DEFAULTS, **C)) / 100 * 1000)
print(f"100 -> 3000 lx while blanked: {w[0][0]}..{w[-1][0]} raw in {dur:.2f} s after wake (curve {want})")
assert not [x for x in lp.screen_writes() if 40 < x[1] < 100], "nothing written while blanked"
assert abs(w[-1][0] - want) <= 2 and dur <= 0.6, (w[-1], dur)
# room got darker while blanked: also at once
lp = loop_harness.Loop(lux=3000, screen=900, conf=C).run(110, {40: blank, 60: lambda lp: lp.room(100), 100: wake})
w, dur = after_wake(lp)
print(f"3000 -> 100 lx while blanked: down in {dur:.2f} s after wake")
assert dur <= 0.6, dur
# dark room (1 lx -> 8 lx while blanked, still under wakeDarkLux): brightens slowly
lp = loop_harness.Loop(lux=1, screen=10, conf=C).run(115, {40: blank, 60: lambda lp: lp.room(8), 100: wake})
w, dur = after_wake(lp)
print(f"dark room 1 -> 8 lx while blanked: brightening over {dur:.2f} s after wake")
assert w and dur >= 1.0, (w[:2], dur)  # the normal 1.5 s brighten, not the 0.4 s wake jump
# the same in the light without a blank: normal Apple fade (unchanged)
lp = loop_harness.Loop(lux=100, screen=500, conf=C).run(70, {40: lambda lp: lp.room(3000)})
w, dur = after_wake(lp, 40)
print(f"100 -> 3000 lx with the screen on: normal fade {dur:.2f} s")
assert dur >= 1.4, dur
print("ok")
