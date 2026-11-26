"""2.15.1: a state file left behind by a dead daemon is not shown as live.
The real loop (fake sysfs, stubbed hyprctl/D-Bus) runs a few passes and
dies; a bad settings file then makes the restart crash before its first
write. `status` and the popup's status line (HeroLines.js, with node) must
say "not running" once the stamp is older than 30 s, and not before."""
import atexit, contextlib, importlib.machinery, importlib.util, io, json, os, shutil, subprocess, tempfile
tmp = tempfile.mkdtemp(prefix="ab-stale-")
atexit.register(shutil.rmtree, tmp, True)
os.environ.update(HOME=tmp, XDG_CONFIG_HOME=tmp + "/config", XDG_RUNTIME_DIR=tmp + "/run", XDG_STATE_HOME=tmp + "/state")
os.makedirs(tmp + "/run")
here = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
ab.READER_THREAD = False  # 2.16.0: read the fake sensors inline, on the fake clock
ab.replace_upstream = lambda keyboard: []  # 2.16.0: never touch the real systemd units
d = tmp + "/intel_backlight"; os.makedirs(d)
open(d + "/max_brightness", "w").write("1000\n"); open(d + "/brightness", "w").write("500\n")
s0 = tmp + "/als0"; open(s0, "w").write("300\n")
ab.sensor = lambda: (s0, 1.0)
ab.find_dev = lambda cls, pat: d if cls == "backlight" else None
ab.Dev.set = lambda self, raw: open(self.path + "/brightness", "w").write(f"{int(raw)}\n")
ab.lid_closed = lambda: False; ab.screen_off = lambda: False; ab.fullscreen_video = lambda: False
clock = {"t": 5000.0, "passes": 0}
real_time = ab.time.time
def sleep(dt):
    clock["t"] += dt; clock["passes"] += 1
    if clock["passes"] > 5: raise KeyboardInterrupt  # the daemon dies
ab.time.sleep = sleep
ab.time.monotonic = lambda: clock["t"]
ab.time.time = lambda: clock["t"]
with contextlib.redirect_stdout(io.StringIO()):
    try: ab.run()
    except KeyboardInterrupt: pass
st = json.load(open(ab.STATE))
assert st["mode"] == "auto" and abs(st["ts"] - clock["t"]) < 1, st

os.makedirs(os.path.dirname(ab.CONF), exist_ok=True)
open(ab.CONF, "w").write('{"min": "abc"}')
try:
    with contextlib.redirect_stdout(io.StringIO()): ab.run()
    raise AssertionError("expected the restart to crash on the bad settings file")
except ValueError:
    pass
open(ab.CONF, "w").write("{}")

def status(at):
    ab.time.time = lambda: at
    out = io.StringIO()
    with contextlib.redirect_stdout(out): ab.main(["x", "status"])
    return json.loads(out.getvalue())
assert status(st["ts"] + 5)["mode"] == "auto", "5 s old: still running"
assert status(st["ts"] + 31)["mode"] == "not running", "31 s old: left over"
legacy = dict(st); del legacy["ts"]
json.dump(legacy, open(ab.STATE, "w"))
assert status(st["ts"] + 999)["mode"] == "auto", "a file without a stamp (older daemon) is not flagged"
print("status: fresh -> auto, 31 s old -> not running, unstamped -> auto")

if shutil.which("node"):
    js = open(os.path.join(here, "..", "HeroLines.js")).read().replace(".pragma library", "")
    prog = js + "\nconst [s, t] = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n" \
           "console.log(JSON.stringify([lines(s, 14, t + 5)[0], lines(s, 14, t + 31)[0], lines(s, 14)[0]]));"
    got = json.loads(subprocess.run(["node", "-e", prog], input=json.dumps([st, st["ts"]]),
                                    capture_output=True, text=True, check=True).stdout)
    print("popup:", got)
    # it died mid-fade: before 2.15.1 the popup said "Brightening to 71%" forever
    assert got[0] != "Service not running" and got[0] == got[2], got
    assert got[1] == "Service not running", got
else:
    print("node not installed: popup part skipped")
print("ok")
