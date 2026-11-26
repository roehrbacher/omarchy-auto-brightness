"""2.16.0: replay of three logged dims in an unchanged, lit room (XPS 14,
2.15.1). Recording: xps-glitch-dims.jsonl, the daemon's own decision-log
lines (times in seconds since each part started, nothing else changed).
  A  ~1100 lx: both sensors impossible (2078488 / -908297 lx), then exact
     0.0 readings: 2.15 dimmed 81% -> 46% -> 1%, keyboard -> 2, and waited
     10 s at 1% ("sustained jump") before coming back.
  B  ~570 lx: sensor0 impossible while sensor1 (quarantined) read 0.0; the
     "all sensors quarantined" fallback used that 0: 74% -> 42%.
  C  ~550 lx, two minutes later: both sensors exactly 0.0 for ~6 s: 100% -> 68%.
The log only has a line when something happened, so the samples between
lines (2 Hz, the daemon's idle rate) are rebuilt from what the lines prove:
- a logged `raw` holds until the next line;
- an impossible raw holds only while the next line's `median` for that
  sensor is still empty (no in-range reading for 4 s); otherwise it was one
  sample, and the sensor reads that next median (or its last in-range raw);
- before each logged quick dim the sensors read that line's `median` for the
  6 s 2.15 needed to dim (3.5 s zero check + 2.5 s quick dim).
The logged manual key presses are replayed too.
None of the three may move the screen or the keyboard now.
AB_DAEMON=<path> runs it against another version (to see the old dims)."""
import importlib.machinery, importlib.util, json, os
import two_sensor
here = os.path.dirname(os.path.abspath(__file__))
p = os.environ.get("AB_DAEMON") or os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
REC = [json.loads(l) for l in open(os.path.join(here, "xps-glitch-dims.jsonl"))]
BACK = 6.0

def samples(lines):
    """[(t, [s0, s1])] at 2 Hz from the logged lines (see the docstring)."""
    bad = lambda v: v is not None and not (0 <= v <= ab.MAX_LUX)
    after, valid = [], [None, None]   # per line: what each sensor reads after its first sample
    for k, r in enumerate(lines):
        nxt = lines[k + 1]["median"] if k + 1 < len(lines) else r["median"]
        row = []
        for i, v in enumerate(r["raw"]):
            if not bad(v):
                valid[i] = v; row.append(v)
            elif k + 1 < len(lines) and nxt[i] is None:
                row.append(v)
            else:
                row.append(nxt[i] if nxt[i] is not None else valid[i])
        after.append(row)
    end = lines[-1]["t"] + 20
    out, t = [], -10.0
    while t <= end:
        k = max([j for j, r in enumerate(lines) if r["t"] <= t] or [0])
        first = lines[k]["t"] <= t < lines[k]["t"] + 0.5
        v = list(lines[k]["raw"] if first or t < lines[0]["t"] else after[k])
        for r in lines:
            if "quick dim" in r["event"] and r["t"] - BACK <= t < r["t"]:
                v = [m if m is not None else x for m, x in zip(r["median"], v)]
        out.append((round(t, 3), v))
        t += 0.5
    return out

def replay(part):
    lines = [r for r in REC if r["part"] == part]
    c = dict(ab.DEFAULTS); c.update(min=1, max=100)
    ctl, filt = ab.Controller(c), two_sensor.make_filter(ab, c)
    cur, kbd = lines[0]["current"], 0
    ctl.kbd_want = 0
    manual = [(r["t"], r["current"]) for r in lines if r["event"].startswith("manual change")]
    trace = []
    for t, v in samples(lines):
        ctl.feed_lux(t, two_sensor.feed(filt, t, v))
        while manual and manual[0][0] <= t:
            cur = manual.pop(0)[1]; ctl.manual(t, cur, "day")
        # 60 Hz fade writes between the 2 Hz samples
        for k in range(30):
            pct = ctl.step(t + k / 60, cur)
            if pct is not None: cur = pct
        if ctl.stable is not None:
            k2 = ctl.kbd_level(2, t)
            if k2 is not None and k2 != ctl.kbd_want:
                ctl.kbd_want = kbd = k2
        trace.append((t, cur, kbd))
    return trace

def window(trace, t0, t1):
    w = [(t, s, k) for t, s, k in trace if t0 <= t <= t1]
    return min(s for _, s, _ in w), max(k for _, _, k in w)

ok = True
for name, part, t0, t1, level in (("A ~1100 lx, both impossible, then 0.0", 0, 75, 140, 80.8),
                                  ("B ~570 lx, all-quarantined fallback", 1, 55, 100, 74.5),
                                  ("C ~550 lx, both 0.0 for ~6 s", 1, 175, 215, 100.0)):
    lo, kmax = window(replay(part), t0, t1)
    good = lo >= level - 2 and kmax == 0
    ok &= good
    print(f"{name}: screen lowest {lo:.0f}% (was at {level:.0f}%), keyboard max {kmax} -> {'held' if good else 'MOVED'}")
assert ok, "a glitch moved the screen or the keyboard"
# the replays end where they started: the room did not change
for part, want in ((0, 80.5), (1, 99.9)):
    end = replay(part)[-1][1]
    assert abs(end - want) <= 2, (part, end, want)
print("ok")
