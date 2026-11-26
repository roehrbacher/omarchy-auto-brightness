"""2.16.2: replay of the dims 2.16.1 still let through in a lit, unchanged
room (XPS 14), and of real lights-off events from the same log.
Recording: xps-glitch-dims-2.jsonl, the daemon's own decision-log lines (written
by two-sensor versions; 2.16.4 replays sensor0's column only, see two_sensor.py)
(times in seconds since each part started). The log only has a line when
something happened, so each part below lists what the sensors read between
the lines, as (from t, [sensor0, sensor1]); the comments say which logged
line proves each step. Zeros start 22.5 s before a logged quick dim (2.16.1:
20 s zeroDropoutSeconds + 2.5 s dimQuickSeconds); light is back 2 s
(settleSeconds) before the logged brighten. An impossible value is one
sample. Run with AB_DAEMON=<2.16.1 copy> to see the old dims come back at
the logged times (`--old` asserts that they do).

Glitches (room lit the whole time; sensor1 mostly reads 0.0 in a lit room):
  E1 ~107 lx: both sensors 0.0 for ~33 s, then again ~28 s: 58% -> 1%, kbd 1
  E2 ~135 lx: sensor0 impossible for ~28 s, sensor1 0.0: 60% -> 1%, kbd 1
  E3 ~256 lx: both 0.0 for ~27 s: 67% -> 38%
  E4 ~251 lx: one impossible on sensor0, then both 0.0 ~21 s, then the
     quarantined sensor0 reads 259 lx while sensor1 reads 0.0: 67% -> 37%
  E5 ~260 lx: both 0.0 for ~39 s: 67% -> 1%, kbd 1 (back in 19 s)
  E6 ~109 lx: both 0.0 for ~45 s: 59% -> 1%, kbd 1
None of them may move the screen or the keyboard now.

Real lights-off (the room stayed dark): faint 1-5 lx readings come first, so
they must dim exactly as fast as before:
  L1 ~35 lx -> 2 lx -> 1 lx, impossible bursts on both sensors
  L2 ~11 lx -> 7 lx -> 1 lx, impossible bursts
  L3 ~55 lx -> 2 lx -> 0 lx, sensor0 in-range 41008 lx burst, lights back on"""
import importlib.machinery, importlib.util, json, os, sys
import two_sensor
here = os.path.dirname(os.path.abspath(__file__))
p = os.environ.get("AB_DAEMON") or os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
REC = [json.loads(l) for l in open(os.path.join(here, "xps-glitch-dims-2.jsonl"))]
IMP = "imp"  # one impossible sample: the logged value is used

PARTS = {
    "E1": [(0, [107, 0]),
           (90.4, [0, 0]),          # quick dim at 112.9 (zeros since 90.4)
           (123.3, [105, 105]),     # brighten at 125.3, median [105, 105]
           (126.0, [106, 0]),
           (166.9, [0, 0]),         # quick dim at 189.4
           (195.0, [106, 0])],      # raw 106 at 195.3, brighten at 198.5
    "E2": [(0, [136, 0]),
           (32.9, [589945, 523714]),  # line at 32.9
           (33.4, [136, 645009]),     # line at 33.6
           (33.9, [136, 0]),
           (63.2, [556008, 0]),       # line at 63.2
           (63.7, [136, 0]),
           (72.5, [587275, 0]),       # quick dim at 95.0: no lit reading since 72.5
           (100.9, [134, 0]),         # raw 134 at 100.9; quarantine ends at 130.6
           (130.6, [137, 137]),
           (132.0, [138, 0]),
           (140.1, [138, 543230]),    # line at 140.1
           (140.6, [138, 0])],
    "E3": [(0, [257, 0]),
           (54.6, [0, 0]),          # heartbeat at 60.2 reads 0/0, quick dim at 77.1
           (79.8, [251, 0])],       # brighten at 83.8 (2 s median + 2 s settle), no full dim
    "E4": [(0, [256, 0]),
           (24.2, [-1744232, 0]),   # line at 24.2
           (24.7, [0, 0]),          # quick dim at 47.1, from sensor1's zeros
           (45.0, [259, 0]),        # line at 47.1: raw/median 259 on the quarantined sensor0
           (57.0, [255, 255]),      # brighten at 57.5 (quarantine over at 54.2)
           (59.0, [260, 0])],
    "E5": [(0, [260, 0]),
           (47.9, [0, 0]),          # heartbeat at 60.1 reads 0/0, quick dim at 70.4
           (87.2, [256, 0])],       # brighten at 89.2
    "E6": [(0, [109, 0]),
           (46.0, [0, 0]),          # heartbeat at 60.7 reads 0/0, quick dim at 68.5
           (90.8, [101, 0])],       # brighten at 92.8
    "L1": [(0, [30, 30]),
           (32.5, [35, 0]),
           (35.6, [2, 0]),          # quick dim to 2 lx at 40.1
           (45.3, [2, 2]),
           (50.9, [2, 76152]),      # line at 50.9
           (51.4, [2, 0]),
           (58.2, [39975, 0]),      # lines 58.2-62.2: in-range burst on sensor0
           (62.8, [39975, 67396]),
           (63.4, [67396, 0]),
           (68.7, [126130, 0]),
           (69.2, [1, 0]),
           (128.6, [1, 0])],
    "L2": [(0, [11, 11]),
           (36.0, [10, 10]),        # fade 12 -> 10 lx at 38.6
           (38.6, [9, 9]),
           (39.5, [7, 7]),          # median 7/7 at 41.3
           (44.4, [1, 1]),          # quick dim to 1 lx at 48.9
           (52.7, [31795, 129077]),
           (52.9, [129077, 129077]),
           (53.7, [1, 129077]),
           (54.2, [1, 0]),
           (98.0, [128313, 128313]),
           (98.5, [1, 1])],
    "L3": [(0, [56, 56]),
           (55.0, [2, 2]),          # quick dim to 3 lx at 59.5
           (63.7, [41008, 2]),      # lines 63.8-66.4: sensors disagree
           (66.5, [127115, 2]),
           (67.0, [0, 2]),
           (67.8, [67396, 2]),
           (68.3, [0, 2]),
           (75.0, [0, 0]),          # quick dim to 0 lx at 80.8
           (90.6, [161, 161])],     # lights back on, brighten at 92.6
}
ONE = {"E2": (32.9, 33.4, 63.2, 140.1), "E4": (24.2,), "L1": (50.9, 62.8, 63.4), "L2": (52.7, 52.9, 98.0), "L3": (66.5, 67.8)}


def samples(part, end):
    seg, out, t = PARTS[part], [], 0.0
    while t <= end:
        k = max(j for j, s in enumerate(seg) if s[0] <= t + 1e-9)
        out.append((round(t, 3), [float(v) for v in seg[k][1]]))
        t = round(t + 0.5, 3)
    return out


def replay(part):
    lines = [r for r in REC if r["part"] == part]
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), two_sensor.make_filter(ab, c)
    cur = lines[0]["current"]
    ctl.kbd_want = kbd = 0
    trace = []
    for t, v in samples(part, lines[-1]["t"] + 20):
        ctl.feed_lux(t, two_sensor.feed(filt, t, v))
        for k in range(30):  # 60 Hz fade writes between the 2 Hz samples
            pct = ctl.step(t + k / 60, cur)
            if pct is not None: cur = pct
        if ctl.stable is not None:
            k2 = ctl.kbd_level(2, t)
            if k2 is not None and k2 != ctl.kbd_want:
                ctl.kbd_want = kbd = k2
        trace.append((t, cur, kbd, ctl.stable))
    return lines, trace


def first_dim(trace, start, below):
    return next((t for t, s, _, _ in trace if t >= start and s < below), None)


old = "--old" in sys.argv
ok = True
for part in ("E1", "E2", "E3", "E4", "E5", "E6"):
    lines, trace = replay(part)
    level = lines[0]["current"]
    lo = min(s for _, s, _, _ in trace)
    kmax = max(k for _, _, k, _ in trace)
    dips = [r["t"] for r in lines if "quick dim" in r["event"]]
    held = lo >= level - 2 and kmax == 0
    print(f"{part}: logged dims at {dips} s; screen lowest {lo:.0f}% (was {level:.0f}%), keyboard max {kmax} -> {'held' if held else 'MOVED'}")
    if old:
        # the reconstruction reproduces the logged dims within a second
        for d in dips:
            got = first_dim(trace, d - 3, level - 0.5)
            print(f"   logged dim at {d} s, replay dims at {got} s")
            ok &= got is not None and abs(got - d) <= 1.5
    else:
        ok &= held
    end = trace[-1][1]
    ok &= abs(end - level) <= 3  # it ends where it started: the room did not change
for part in ("L1", "L2", "L3"):
    # real lights-off: no slower than the log (2.16.1 and older, same rules for faint light)
    lines, trace = replay(part)
    quick = next(r["t"] for r in lines if "quick dim" in r["event"])
    floor = next(r["t"] for r in lines if r.get("current") is not None and r["current"] <= 1.5)
    kbd_on = next(r["t"] for r in lines if r["event"].startswith("keyboard -> 1") or "keyboard -> 1;" in r["event"])
    level = next(s for t, s, _, _ in trace if t >= 10)  # settled on the replayed room
    got = first_dim(trace, 10, level - 0.5)
    dark = next((t for t, s, k, _ in trace if s <= 1.5), None)
    kb = next((t for t, s, k, _ in trace if k >= 1), None)
    print(f"{part}: logged quick dim {quick} s, 1% by {floor} s, keyboard on {kbd_on} s;"
          f" replay first dim {got} s, 1% at {dark} s, keyboard on {kb} s")
    ok &= got is not None and got <= quick + 1.5
    ok &= dark is not None and dark <= floor + 1.5
    ok &= kb is not None and kb <= kbd_on + 1.5
    if part == "L3":
        back = [t for t, s, _, _ in trace if t > 90.6 and s > 50]
        # lights back on: 2 s median + 2 s settle + 1.5 s fade. 2.16.4 reads one
        # sensor: it was quarantined for 30 s by the 67396 lx sample at 67.8 s
        # (the log's other sensor carried the room then), so it waits for that
        ok &= bool(back) and back[0] - 90.6 <= 6 if two_sensor.OLD else bool(back) and back[0] <= 67.8 + 30 + 6
assert ok, "see above"
print("ok")
