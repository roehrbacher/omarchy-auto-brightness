"""2.15.0: on battery under kbdLowBatteryPercent (15 %), auto sets the
keyboard backlight to level 1 at most. A key press to 2 still sticks, the
charger lifts the cap, 0 turns it off, and a peripheral battery (mouse at
5 %) is ignored. Real loop: fake sysfs and power_supply in a temp dir,
stubbed D-Bus/hyprctl, fake clock."""
import atexit, importlib.machinery, importlib.util, json, os, shutil, tempfile
tmp = tempfile.mkdtemp(prefix="ab-bat-")
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
bl, kb = dev("intel_backlight", 1000, 80), dev("dell::kbd_backlight", 2, 0)
level = lambda: int(open(kb + "/brightness").read())
ps = tmp + "/power_supply"
def supply(name, **files):
    d = os.path.join(ps, name); os.makedirs(d, exist_ok=True)
    for k, v in files.items(): open(f"{d}/{k}", "w").write(f"{v}\n")
supply("00-mouse", type="Battery", scope="Device", capacity=5, status="Discharging")  # sorts first
supply("AC", type="Mains", online=0)
supply("BAT0", type="Battery", capacity=50, status="Discharging")
ab.POWER_SUPPLY = ps
s0 = tmp + "/als0"
open(s0, "w").write("0\n")  # dark room the whole time
writes = []
def dev_set(self, raw):
    if self.name != "intel_backlight": writes.append((int(raw), round(clock["t"] - 1000, 1)))
    open(self.path + "/brightness", "w").write(f"{int(raw)}\n")
ab.sensor = lambda: (s0, 1.0)
ab.find_dev = lambda cls, pat: bl if cls == "backlight" else kb
ab.Dev.set = dev_set
ab.lid_closed = lambda: False
ab.screen_off = lambda: False
ab.fullscreen_video = lambda: False
states = []
real_write = ab.write_state
ab.write_state = lambda d: (states.append((round(clock["t"] - 1000, 1), d)), real_write(d))

clock = {"t": 1000.0}
def conf(**kv):
    kv.setdefault("kbdMaxLevel", 2)  # 2.16.0: the cap only matters when auto may use level 2
    os.makedirs(os.path.dirname(ab.CONF), exist_ok=True)
    json.dump(kv, open(ab.CONF, "w"))
    os.utime(ab.CONF, (clock["t"] + 1e9, clock["t"] + 1e9))
conf()
events = {1030: lambda: supply("BAT0", capacity=12),
          1060: lambda: (writes.append(("key", 2)), open(kb + "/brightness", "w").write("2\n")),
          1090: lambda: (supply("BAT0", status="Charging"), supply("AC", online=1)),
          1110: lambda: (supply("BAT0", status="Discharging"), supply("AC", online=0)),
          1130: lambda: conf(kbdLowBatteryPercent=0)}
def sleep(dt):
    before = clock["t"]; clock["t"] += dt
    for at, fn in events.items():
        if before < at <= clock["t"]: fn()
    if clock["t"] > 1150: raise KeyboardInterrupt
ab.time.sleep = sleep
ab.time.monotonic = lambda: clock["t"]
ab.time.time = lambda: clock["t"] + 1e9
try:
    ab.run()
except KeyboardInterrupt:
    pass
print("keyboard writes (level, s):", writes)
auto = [w for w in writes if w[0] != "key"]
def between(a, b): return [lv for lv, t in auto if a <= t < b]
assert between(0, 30)[-1:] == [2], "50 % battery (mouse at 5 % ignored): level 2 in the dark"
assert between(30, 42) == [1], "12 % on battery: auto lowers its own 2 to 1 within the 10 s battery read"
assert between(42, 90) == [], "a key press to 2 on low battery sticks"
assert level() == 2 or between(90, 110), "key press kept until the charger comes"
assert between(90, 105) == [2], "charger: cap lifted, level 2 again"
assert between(110, 122) == [1], "back on battery at 12 %: capped again"
assert between(130, 150) == [2], "kbdLowBatteryPercent 0: no cap"
low = lambda t0: next(d["lowBattery"] for t, d in states if t >= t0)
assert low(20) is False and low(45) is True and low(100) is False and low(125) is True and low(145) is False
print("cap at 12 %: 2 -> 1; key press to 2 stuck; charger lifts it; 0 disables it; lowBattery in the state")
# 2.16.0 default (kbdMaxLevel 1): auto never uses level 2, so the cap has
# nothing to do: level 1 in the dark at 12 % too, and no "Low battery" line
import loop_harness
lp = loop_harness.Loop(lux=0.5, screen=100)
lp.ab.POWER_SUPPLY = ps; supply("BAT0", capacity=12, status="Discharging"); supply("AC", online=0)
lp.run(40)
assert [v for v, t in lp.kbd_writes()] == [1] and lp.level() == 1, lp.kbd_writes()
assert not any(d.get("lowBattery") for t, d in lp.states)
print("default max level 1: dark room at 12 % battery -> level 1, no cap shown")
print("ok")
