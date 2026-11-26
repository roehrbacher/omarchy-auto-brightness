"""2.16.3: the service can no longer grow into swap. A run of 2.16.1 kept
its RAM under the 64 MB cap but grew to 960 MB with 796 MB in swap: the
cap only limited RAM. Checks: the unit allows no swap and caps RAM; every
decision line logs the daemon's and the service's memory (memKB), so growth
is visible with its time and trigger; and a stuck brightnessctl fallback
gives up after 5 s instead of stalling the loop."""
import os, re, stat, tempfile, time
import loop_harness

here = os.path.dirname(os.path.abspath(__file__))
unit = open(os.path.join(here, "..", "systemd", "omarchy-auto-brightness.service")).read()
keys = dict(re.findall(r"^(\w+)=(.*)$", unit, re.M))
assert keys.get("MemorySwapMax") == "0", keys
assert keys.get("MemoryMax") == "64M" and keys.get("MemoryHigh") == "48M", keys
assert keys.get("OOMPolicy") == "continue" and keys.get("Restart") == "on-failure", keys

lp = loop_harness.Loop(lux=300, screen=500, conf={"debugLog": True})
lp.run(70)
lines = lp.log()
mem = [l["memKB"] for l in lines if "memKB" in l]
assert mem and len(mem) == len([l for l in lines if l.get("event") not in ("start", "stop")]), "a decision line without memKB"
assert all(isinstance(m["rss"], int) and m["rss"] > 1000 for m in mem), mem[-1]
print("memKB on every decision line, last:", mem[-1])

# brightnessctl fallback: D-Bus fails, brightnessctl hangs
d = tempfile.mkdtemp(prefix="ab-mem-")
ab = loop_harness.load(d)
fake = os.path.join(d, "bin"); os.makedirs(fake)
p = os.path.join(fake, "brightnessctl")
open(p, "w").write("#!/bin/sh\nsleep 60\n"); os.chmod(p, stat.S_IRWXU)
os.environ["PATH"] = fake + os.pathsep + os.environ["PATH"]
dev = os.path.join(d, "intel_backlight"); os.makedirs(dev)
open(dev + "/max_brightness", "w").write("1000\n"); open(dev + "/brightness", "w").write("500\n")
class Broken:
    def call_sync(self, *a):
        raise RuntimeError("no logind")
ab.Dev._bus = (Broken(), None)
t0 = time.monotonic()
ab.Dev(dev).set(400)
took = time.monotonic() - t0
print(f"stuck fallback returned after {took:.1f} s")
assert 4 <= took <= 8, took
print("ok")
