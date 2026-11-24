"""2.3.0: a recorded session of about 17 min: the room read ~210-400 lx but the
sensors dropped to 0 lx for 2-7 s now and then (shadows/dropouts), and
the keyboard light went to level 2 each time. Replay of the logged stable lux
(seconds since the start of the recording, lux): the keyboard must stay off. A real
dark stretch must still turn it on within ~20 s and off at once when bright."""
import ast, importlib.machinery, importlib.util, os
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
SEQ = ast.literal_eval(open(os.path.join(here, "sensor-dips.txt")).read())

def sim(lux_at, secs, start_kbd=0):
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), ab.SensorFilter(2, c["sensorMedianSeconds"])
    ctl.kbd_want = start_kbd
    t, ons, offs = 0.0, [], []
    while t < secs:
        v = lux_at(t)
        ctl.feed_lux(t, filt.feed(t, [v, v]))
        w = ctl.kbd_level(2, t)
        if w is not None and w != ctl.kbd_want:
            (ons if w > (ctl.kbd_want or 0) else offs).append((t, w)); ctl.kbd_want = w
        t = round(t + 0.5, 3)
    return ons, offs

def replay(t):
    v = 300.0
    for st, lux in SEQ:
        if st > t: break
        v = lux
    return v

ons, _ = sim(replay, SEQ[-1][0] + 30)
assert not ons, ons
print("dip replay (%d lux changes, dips to 0 lx for 2-7 s): keyboard stayed off" % len(SEQ))

# the exact logged dips, real-time: 6 s and 7 s at 0 lx in a 250 lx room
# 2.5.0: the screen dims fully after 8 s (was 12), so a 12 s dip is real darkness now
for d in (2, 4, 6, 7):
    ons, _ = sim(lambda t: 0.0 if 30 <= t < 30 + d else 250.0, 90)
    assert not ons, (d, ons)
print("0 lx dips of 2-7 s: keyboard stays off")

# a real lasting darkness: on after ~15 s of darkness, off at once after
ons, offs = sim(lambda t: (1.0 if t < 31 else 0.0) if 30 <= t < 120 else 250.0, 150)
assert ons and 30 + 10 <= ons[0][0] <= 30 + 16, ons
assert offs and offs[-1][1] == 0 and offs[-1][0] - 120 <= 4, offs
print("90 s darkness (1 lx, then 0): on after %.1f s, off %.1f s after the light returned" % (ons[0][0] - 30, offs[-1][0] - 120))
# 2.16.0: exactly 0.0 on both sensors alone first waits zeroDropoutSeconds
Z = ab.DEFAULTS["zeroDropoutSeconds"]
ons, offs = sim(lambda t: 0.0 if 30 <= t < 120 else 250.0, 150)
assert ons and 30 + Z <= ons[0][0] <= 30 + Z + 16, ons
print("90 s of exact 0.0 lx: on after %.1f s" % (ons[0][0] - 30))

# flicker: alternating 0 / 250 lx every 5 s for 2 min never turns it on
ons, _ = sim(lambda t: 0.0 if int(t / 5) % 2 else 250.0, 150)
assert not ons, ons
print("5 s light/dark flicker: keyboard stays off")
