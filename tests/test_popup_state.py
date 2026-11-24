"""2.12.0: what the popup reads from the state file, checked against the real
loop (fake sysfs in a temp dir, stubbed D-Bus/hyprctl, fake clock):
- luxNow follows the room on the next sample while lux (what the screen
  follows) still waits for the median and settle time; glitch values never
  reach luxNow (2.13.0: and are not reported to the popup at all)
- with the popup open (watch file fresh) the daemon samples at 10 Hz
- a min change is followed at once (short preview fade, "fadeTo" set),
  while a room change afterwards still fades slowly"""
import atexit, contextlib, importlib.machinery, importlib.util, io, json, os, shutil, tempfile
tmp = tempfile.mkdtemp(prefix="ab-popup-")
atexit.register(shutil.rmtree, tmp, True)
os.environ.update(HOME=tmp, XDG_CONFIG_HOME=tmp + "/config", XDG_RUNTIME_DIR=tmp + "/run", XDG_STATE_HOME=tmp + "/state")
os.makedirs(tmp + "/run")
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
ab.READER_THREAD = False  # 2.16.0: read the fake sensors inline, on the fake clock
ab.replace_upstream = lambda keyboard: []  # 2.16.0: never touch the real systemd units

def dev(name, maxv, cur):
    d = os.path.join(tmp, "sys", name); os.makedirs(d)
    open(d + "/max_brightness", "w").write(f"{maxv}\n"); open(d + "/brightness", "w").write(f"{cur}\n")
    return d
bl, kb = dev("intel_backlight", 1000, 600), dev("dell::kbd_backlight", 2, 0)
s0, s1 = tmp + "/als0", tmp + "/als1"
def sensor(f, lux): open(f, "w").write(f"{lux}\n")
def room(lux): sensor(s0, lux); sensor(s1, lux)
ab.sensors = lambda: [(s0, 1.0), (s1, 1.0)]
ab.find_dev = lambda cls, pat: bl if cls == "backlight" else kb
ab.Dev.set = lambda self, raw: open(self.path + "/brightness", "w").write(f"{int(raw)}\n")
ab.lid_closed = lambda: False
ab.screen_off = lambda: False
ab.fullscreen_video = lambda: False
states, sleeps = [], []
real_write = ab.write_state
def write_state(d):
    states.append((round(clock["t"] - 1000, 3), d)); real_write(d)
ab.write_state = write_state
def cli(*args):
    with contextlib.redirect_stdout(io.StringIO()):
        return ab.main(["omarchy-auto-brightness", *args])

room(200)
clock = {"t": 1000.0}
popup = {"open": False}
events = [(20, lambda: room(40)),
          (40, lambda: sensor(s0, 170063)), (41, lambda: sensor(s0, 40)),          # impossible value
          (80, lambda: sensor(s0, 43000)), (81, lambda: sensor(s0, 40)),           # in-range one-sensor burst
          (90, lambda: popup.update(open=True)),
          (100, lambda: room(1)), (101, lambda: room(0)),  # lights off (a faint 1 lx first, like a real room)
          (140, lambda: cli("set", "min", "40")),
          (150, lambda: room(300)),
]
def sleep(dt):
    before = clock["t"]; clock["t"] += dt
    sleeps.append((round(before - 1000, 3), dt))
    for at, fn in events:
        if before < 1000 + at <= clock["t"]:
            fn()
    if popup["open"]:
        open(ab.WATCH_FLAG, "w").write("1")
        os.utime(ab.WATCH_FLAG, (clock["t"] + 1e9, clock["t"] + 1e9))
    if clock["t"] > 1170: raise KeyboardInterrupt
ab.time.sleep = sleep
ab.time.monotonic = lambda: clock["t"]
ab.time.time = lambda: clock["t"] + 1e9
try:
    ab.run()
except KeyboardInterrupt:
    pass

def at(t0, t1): return [(t, d) for t, d in states if t0 < t <= t1]  # states written after the event at t0
# live lux: next sample after the room change; the settled lux still 200 for 2 s
first = at(20, 30)[0]
assert first[0] - 20 <= 0.5 and first[1]["luxNow"] == 40, first
assert all(d["lux"] == 200 for t, d in at(20, 22)), at(20, 22)[-1]
settled = next(t for t, d in at(20, 40) if d["lux"] != 200)
print(f"room 200 -> 40 lx: luxNow 40 after {first[0] - 20:.2f} s, settled lux moves after {settled - 20:.1f} s")
# glitches: never shown as luxNow, flagged while dropped
g1 = at(40, 41); g2 = at(80, 81)
assert all(d["luxNow"] == 40 for t, d in g1 + g2), [d["luxNow"] for t, d in g1 + g2]
assert all("glitch" not in d and "restless" not in d for t, d in states)
print("170063 lx (impossible) and a 43000 lx one-sensor burst: luxNow stays 40, nothing about it in the state")
# cadence: 2 Hz closed, 4 Hz with the popup open (not fading)
idle_closed = {dt for t, dt in sleeps if 60 <= t < 79}
idle_open = {dt for t, dt in sleeps if 125 <= t < 139}
assert idle_closed == {0.5} and idle_open == {0.25}, (idle_closed, idle_open)
print("sampling: 0.5 s closed, 0.25 s with the popup open (2.16.0: sensors at most 4 Hz)")
# preview: min 8 -> 40 in the dark room is on screen within 0.5 s, fadeTo shows it
screen_at = lambda t: next(d["screen"] for tt, d in states if tt >= t)
assert screen_at(139.9) <= 9, screen_at(139.9)
reach = next(t for t, d in at(140, 150) if d["screen"] >= 40)
assert reach - 140 <= 0.5, reach
assert any(d["fadeTo"] == 40 for t, d in at(140, 141))
print(f"min 8 -> 40: screen at 40 % after {reach - 140:.2f} s")
# a room change afterwards is still a normal slow fade
fading = [t for t, d in at(150, 165) if d["fadeTo"] is not None]
assert fading and fading[-1] - fading[0] >= 1.4, (fading[:1], fading[-1:])
print(f"room 0 -> 300 lx afterwards: normal fade of {fading[-1] - fading[0]:.1f} s")
print("ok")
