# Runs the real loop against a fake sysfs: dark -> bright, then a manual change.
import importlib.machinery, importlib.util, os, sys, tempfile, threading, time, json
p = os.path.join(os.path.dirname(__file__), "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
t = tempfile.mkdtemp()
def w(n, v): open(os.path.join(t, n), "w").write(str(v))
os.makedirs(t + "/bl"); os.makedirs(t + "/kbd")
for n, v in [("lux", 0), ("bl/brightness", 500), ("kbd/brightness", 0)]: w(n, v)
for d, m in (("bl", 1000), ("kbd", 2)): w(d + "/max_brightness", m)
class FakeDev(ab.Dev):
    def set(self, raw): w(self.name + "/brightness", int(raw))
ab.Dev = FakeDev
ab.sensors = lambda: [(t + "/lux", 1.0)]
ab.find_dev = lambda cls, pat: t + ("/kbd" if "kbd" in pat else "/bl")
ab.lid_closed = lambda: False
ab.locked = lambda: False
ab.STATE = t + "/state.json"; ab.CONF = t + "/conf.json"
json.dump({"min": 10, "max": 90, "pollSeconds": 0.2, "manualPauseMinutes": 1}, open(ab.CONF, "w"))
threading.Thread(target=ab.run, daemon=True).start()
def st(): return json.load(open(ab.STATE))
time.sleep(2.5); s = st(); print("dark  ", s, "kbd", open(t+"/kbd/brightness").read())
assert s["screen"] == 10 and open(t + "/kbd/brightness").read() == "1"
w("lux", 2000); time.sleep(4); s = st(); print("bright", s, "kbd", open(t+"/kbd/brightness").read())
assert s["screen"] >= 75 and open(t + "/kbd/brightness").read() == "0"
w("lux", 2100); time.sleep(1); assert st()["screen"] == s["screen"], "hysteresis"
w("bl/brightness", 300); time.sleep(1); s = st(); print("manual", s)
assert s["mode"] == "manual pause" and s["screen"] == 30
print("loop ok")
