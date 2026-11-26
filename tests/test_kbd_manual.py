"""2.11.0: CLI `kbd-level N` (2.12.0: no longer in the popup; the hardware key
does the same). The level is written like a key press and the daemon is not
told, so the popup help says: auto keeps your level until the room changes
enough for another level (or the screen wakes). This checks exactly that against the real loop:
fake sysfs files in a temp dir, stubbed D-Bus/hyprctl, fake clock."""
import atexit, contextlib, importlib.machinery, importlib.util, io, json, os, shutil, tempfile
tmp = tempfile.mkdtemp(prefix="ab-kbd-")
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
level = lambda: int(open(kb + "/brightness").read())
s0 = tmp + "/als0"
def room(lux):
    open(s0, "w").write(f"{lux}\n")
writes = []
def dev_set(self, raw):
    writes.append((self.name, int(raw), clock["t"] if "clock" in globals() else 0)); open(self.path + "/brightness", "w").write(f"{int(raw)}\n")
ab.sensor = lambda: (s0, 1.0)
ab.find_dev = lambda cls, pat: bl if cls == "backlight" else kb
ab.Dev.set = dev_set
ab.lid_closed = lambda: False
ab.screen_off = lambda: False
ab.fullscreen_video = lambda: False

def cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = ab.main(["omarchy-auto-brightness", *args])
    return rc, out.getvalue()

# CLI: sets the level now, clamps to the hardware range, status reports it
rc, out = cli("kbd-level", "1"); assert rc == 0 and level() == 1 and json.loads(out)["kbdLevel"] == 1, out
rc, out = cli("kbd-level", "5"); assert level() == 2 and json.loads(out)["kbdMax"] == 2
with contextlib.redirect_stderr(io.StringIO()): rc, out = cli("kbd-level", "x")
assert rc == 2 and level() == 2
cli("kbd-level", "0"); assert level() == 0
print("kbd-level CLI: sets 1, clamps 5 to 2, rejects x, status shows the level")

# daemon: dark room, auto turns it to 1 (2.16.0 default max); a manual Off sticks while the room
# stays dark; lights on (off anyway) and off again: auto lights it again
room(0)
clock = {"t": 1000.0}
events = {1040: "manual off", 1070: "lights on", 1090: "lights off"}
def sleep(dt):
    before = clock["t"]; clock["t"] += dt
    for at, what in events.items():
        if before < at <= clock["t"]:
            if what == "manual off": writes.append(("manual", 0, clock["t"])); cli("kbd-level", "0")
            if what == "lights on": room(300)
            if what == "lights off": room(0)
    if clock["t"] > 1090 + ab.DEFAULTS["zeroDropoutSeconds"] + 20: raise KeyboardInterrupt  # 2.16.2: zeros alone wait zeroDropoutSeconds
ab.time.sleep = sleep
ab.time.monotonic = lambda: clock["t"]
ab.time.time = lambda: clock["t"] + 1e9
try:
    ab.run()
except KeyboardInterrupt:
    pass
k = [(n, v, round(t - 1000, 1)) for n, v, t in writes if n != "intel_backlight" and t]
print("keyboard writes (name, level, s):", k)
i = [w[0] for w in k].index("manual")
assert ("dell::kbd_backlight", 1) in [w[:2] for w in k[:i]], "auto set level 1 in the dark first"
assert all(w[1] != 2 for w in k if w[0] == "dell::kbd_backlight"), "auto never sets level 2 by default"
assert k[i + 1][:2] == ("dell::kbd_backlight", 0), "the manual Off itself"
auto_after = k[i + 2:]
assert auto_after and min(w[2] for w in auto_after) >= 70, f"no auto write while the dark room did not change: {auto_after}"
st = json.load(open(ab.STATE))
assert auto_after[-1][:2] == ("dell::kbd_backlight", 1) and st["kbdLevel"] == 1, (auto_after, st)
print("manual Off stuck in the unchanged dark room; auto lit it again after the room got bright and dark again")
print("ok")
