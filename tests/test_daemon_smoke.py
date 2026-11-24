"""The daemon loop itself (run()) against fake sysfs files in a temp dir:
two light sensors, a backlight and a keyboard light. No D-Bus, hyprctl or
real hardware: those helpers are stubbed. Catches crashes in the loop that the
Controller tests cannot see (2.8.0 shipped one). Fake clock, 2 Hz idle and
60 Hz fades like the real loop."""
import atexit, importlib.machinery, importlib.util, json, os, shutil, tempfile
tmp = tempfile.mkdtemp(prefix="ab-smoke-")
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
bl, kb = dev("intel_backlight", 1000, 500), dev("dell::kbd_backlight", 2, 0)
s0, s1 = tmp + "/als0", tmp + "/als1"
def room(lux):
    for f in (s0, s1): open(f, "w").write(f"{lux}\n")
room(300)

clock = {"t": 1000.0, "sleeps": 0}
def sleep(dt):
    clock["t"] += dt; clock["sleeps"] += 1
    if abs(clock["t"] - 1030) < 0.3: room(0)          # lights off at 30 s
    if clock["t"] > 1070: raise KeyboardInterrupt
writes = []
def dev_set(self, raw):
    writes.append((self.name, int(raw))); open(self.path + "/brightness", "w").write(f"{int(raw)}\n")

ab.sensors = lambda: [(s0, 1.0), (s1, 1.0)]
ab.find_dev = lambda cls, pat: bl if cls == "backlight" else kb
ab.Dev.set = dev_set
ab.lid_closed = lambda: False
ab.screen_off = lambda: False
ab.fullscreen_video = lambda: False
ab.time.sleep = sleep
ab.time.monotonic = lambda: clock["t"]
ab.time.time = lambda: clock["t"] + 1e9
try:
    ab.run()
except KeyboardInterrupt:
    pass

c = dict(ab.DEFAULTS)
st = json.load(open(ab.STATE))
log = [json.loads(l) for l in open(ab.DLOG)]
scr = [r for n, r in writes if n == "intel_backlight"]
kbd = [r for n, r in writes if n == "dell::kbd_backlight"]
lit = round(ab.curve_pct(300, c) / 100 * 1000)
print(f"{clock['sleeps']} loop passes, {len(scr)} screen writes, lit {max(scr)} (curve {lit}), end {scr[-1]}, keyboard {kbd}, mode {st['mode']}, log {len(log)} lines")
assert log[0]["event"] == "start" and log[0]["version"] == ab.VERSION
assert st["mode"] == "auto" and st["lux"] == 0.0
assert abs(max(scr) - lit) <= 1, "faded to the 300 lx level"
assert scr[-1] == round(c["min"] / 100 * 1000), "dark room ends at the min"
assert kbd and kbd[-1] == 1, "keyboard level 1 in the dark (2.16.0: kbdMaxLevel 1 by default)"
assert 2 not in kbd, "auto never sets level 2 by default"
print("ok")
