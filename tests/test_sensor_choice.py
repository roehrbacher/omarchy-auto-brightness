"""2.16.4: the daemon reads one light sensor, the plain illuminance one. The
XPS lists the same chip twice (plain, and a colour view with colour
temperature and chromaticity): reading both doubled the traffic to the sensor
hub and the 0 lx dropouts, and the second view mostly read 0. Fake sysfs: the
colour view is never read, whatever order the devices come in."""
import os, shutil, tempfile, time
import loop_harness

d = tempfile.mkdtemp(prefix="ab-choice-")
ab = loop_harness.load(d)
root = ab.IIO = os.path.join(d, "iio")

def dev(n, name, chans, value="64000"):
    p = os.path.join(root, f"iio:device{n}"); os.makedirs(p, exist_ok=True)
    open(p + "/name", "w").write(name + "\n")
    for ch in chans:
        open(f"{p}/in_{ch}", "w").write(value + "\n")
    return p

def sensor_for(layout):
    shutil.rmtree(root, ignore_errors=True)
    for n, name, chans in layout:
        dev(n, name, chans)
    return ab.sensor()

PLAIN = ("illuminance_raw", "illuminance_scale")
COLOUR = ("illuminance_raw", "illuminance_scale", "colortemp_raw", "chromaticity_x_raw", "chromaticity_y_raw")
xps = [(0, "prox", ("proximity0_raw",)), (1, "als", PLAIN), (2, "als", COLOUR), (3, "hinge", ())]
got = sensor_for(xps)
assert got and got[0].endswith("iio:device1/in_illuminance_raw"), got
# the colour view first: still the plain one
got = sensor_for([(1, "als", COLOUR), (2, "als", PLAIN)])
assert got and got[0].endswith("iio:device2/in_illuminance_raw"), got
# only a colour sensor (another laptop): that one
got = sensor_for([(1, "als", COLOUR)])
assert got and got[0].endswith("iio:device1/in_illuminance_raw"), got
assert sensor_for([(0, "prox", ("proximity0_raw",))]) is None
print("plain sensor chosen:", os.path.basename(os.path.dirname(sensor_for(xps)[0])))

# one reader reads one file
plain = os.path.join(root, "iio:device1"); colour = os.path.join(root, "iio:device2")
sensor_for(xps)
open(plain + "/in_illuminance_raw", "w").write("64000\n"); open(plain + "/in_illuminance_scale", "w").write("0.001\n")
opened = []
real_read = ab.read
ab.read = lambda p, default=None: (opened.append(p), real_read(p, default))[1]
r = ab.SensorReader((plain + "/in_illuminance_raw", 0.001), threaded=True); r.interval = 0.1
seen, end = [], time.monotonic() + 1.0
while time.monotonic() < end:
    got = r.take(time.monotonic())
    if got: seen.append(got)
    time.sleep(0.02)
assert seen and all(abs(g[1] - 64.0) < 1e-6 for g in seen), seen
assert set(opened) == {plain + "/in_illuminance_raw"}, set(opened)
print(f"{len(seen)} samples of 64 lx, all from one file")
print("ok")
