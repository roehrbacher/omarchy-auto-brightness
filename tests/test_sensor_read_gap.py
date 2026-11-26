"""2.16.5: the gap between the end of one sensor read and the start of the
next is never under 0.9 s, at the 1 Hz rate, with the (old) popup interval,
and after a wake flush. The firmware sticks at 0 lx when that gap is short."""
import os, tempfile, time
import loop_harness

GAP = 0.9
SLOP = 0.02  # scheduler slop on a sleep; the floor itself is 0.9

def install_timer(r, delay=0.15):
    times = []
    real = r._read
    def timed():
        t0 = time.monotonic()
        if delay:
            time.sleep(delay)
        got = real()
        times.append((t0, time.monotonic()))
        return got
    r._read = timed
    return times

def gaps(times):
    return [b[0] - a[1] for a, b in zip(times, times[1:])]

def start_reader(path, interval, min_gap=GAP, delay=0.15):
    import threading
    ab = loop_harness.load(os.path.dirname(path))
    r = ab.SensorReader((path, 1.0), threaded=False)
    r.interval, r.min_gap = interval, min_gap
    times = install_timer(r, delay)
    r.lock, r.wake = threading.Lock(), threading.Event()
    r.threaded = True
    threading.Thread(target=r._loop, name="sensors", daemon=True).start()
    return r, times

d = tempfile.mkdtemp(prefix="ab-gap-")
f = os.path.join(d, "a")
open(f, "w").write("50\n")

# 1 Hz, with a 0.15 s read like the real sensor
r, times = start_reader(f, interval=1.0)
deadline = time.monotonic() + 3.6
while time.monotonic() < deadline and len(times) < 4:
    r.take(time.monotonic())
    time.sleep(0.02)
g = gaps(times)
print(f"1 Hz, {len(times)} reads, gaps {[round(x, 3) for x in g]}")
assert len(g) >= 2, times
assert all(x >= GAP - SLOP for x in g), g

# old popup rate (0.25 s): the 0.9 s floor still holds
r, times = start_reader(f, interval=0.25)
deadline = time.monotonic() + 3.2
while time.monotonic() < deadline and len(times) < 4:
    r.take(time.monotonic())
    time.sleep(0.02)
g = gaps(times)
print(f"popup interval 0.25 s, {len(times)} reads, gaps {[round(x, 3) for x in g]}")
assert len(g) >= 2, times
assert all(x >= GAP - SLOP for x in g), g

# wake flush right after a read still waits for the gap, then reads
r, times = start_reader(f, interval=1.0)
deadline = time.monotonic() + 1.0
while time.monotonic() < deadline and len(times) < 1:
    r.take(time.monotonic())
    time.sleep(0.01)
assert times, "no first read"
r.flush(time.monotonic())
t_flush = time.monotonic()
deadline = time.monotonic() + 1.5
while time.monotonic() < deadline and len(times) < 2:
    r.take(time.monotonic())
    time.sleep(0.01)
assert len(times) >= 2, times
g = times[1][0] - times[0][1]
lag = times[1][0] - t_flush
print(f"flush after first read: gap {g:.3f} s, next read {lag:.3f} s after flush")
assert g >= GAP - SLOP, g
assert lag < GAP + 0.2, lag  # fresh as soon as the gap allows, not a full extra interval

# inline (fake clock): same rules, including flush
ab = loop_harness.load(d)
r = ab.SensorReader((f, 1.0), threaded=False)
r.interval, r.min_gap = 1.0, GAP
assert r.take(0.0) and r.take(0.5) is None and r.take(1.0)
r.flush(1.05)
assert r.take(1.05) is None, "flush must still honour the gap"
assert r.take(1.95)
print("inline: 1 Hz; flush waits 0.9 s")
print("ok")
