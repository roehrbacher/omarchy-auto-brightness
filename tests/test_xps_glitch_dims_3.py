"""Replay of three dim-room dims 2.16.3 and older let through in a dim, unchanged room
(XPS 14, ~6-20 lx, room light falling slowly). Recording:
xps-glitch-dims-3.jsonl, the daemon's own decision-log lines (times in
seconds since each part started); each part lists what the sensors read
between the lines, as (from t, [sensor0, sensor1]). sensor1 reads 0.0 the
whole time (it is the second HID view of the same light sensor and mostly
reads 0.0).

  G1 ~20 lx: sensor0 reads 0.0 for ~3 s: quick dim 41% -> 27%, back in ~4 s.
     sensor0's median (20 lx) is not above the old 20 lx line, so its zeros are
     believed at once (2.16.3).
  G2 ~16 lx: sensor0 reads an impossible 66360 lx for ~10 s and is
     quarantined 30 s after the last one; only sensor1's 0.0 is left, and a
     16 lx room is not "lit" (zeroDropoutLux 20 then), so 0 lx wins: 39% -> 1%,
     keyboard on, back ~40 s later when the quarantine ends.

  G3 ~9 -> 6 lx (dusk, falling slowly): six minutes of bursts on both
     sensors (impossible values, then sensor0 stuck at an in-range 39019 lx).
     Each time sensor0 is quarantined, sensor1's 0.0 wins: 1% three times
     (28 s, 46 s, then 97 s), keyboard on. The long one lasts because the
     stuck 39019 lx "disagrees" with sensor1's 0.0 and the lower one wins.
     It ends with a real light change: lamps switched on, 6 -> 30 lx on
     sensor0 in one step, steady after (both sensors read 30 once the
     service restarted). That one must brighten within ~4 s, as logged.

Real light changes in these recordings are smooth (dusk: 1-2 lx steps a
minute) or one step to a new steady level (lamps on). The glitches are
exact 0.0 next to a reading of 6-20 lx a moment before, values over
60000 lx or negative, and in-range values far from both neighbours that
repeat exactly (39019, 66360, 67367, 83000 lx), often on both sensors at once.

Default: asserts none of the dims happens (screen within 3 points of the
room's level, keyboard off) and that the lamps-on change is followed within
~6 s. Real daemon: 2.16.4 reads one sensor and replays sensor0's column.
`--old` with AB_DAEMON=<2.16.3 copy> asserts that the old version dims at the
logged times (the replay is faithful)."""
import importlib.machinery, importlib.util, json, os, sys
import two_sensor
here = os.path.dirname(os.path.abspath(__file__))
p = os.environ.get("AB_DAEMON") or os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
REC = [json.loads(l) for l in open(os.path.join(here, "xps-glitch-dims-3.jsonl"))]

I = 666666  # one impossible sample the log did not show
PARTS = {
    "G1": [(0, [20, 0]),
           (29.0, [0, 0]),          # quick dim at 33.2 (median [0, 0], raw back to 20)
           (32.0, [20, 0])],        # brighten at 35.9
    "G2": [(0, [16, 0]),
           (46.6, [66360, 0]),      # line at 46.6; raw still 66360 at 49.4 and 55.7
           (57.0, [15, 0])],        # raw 15 at 59.0; quarantine ends ~30 s later, brighten at 88.3
    # impossible values are logged only when a quarantine starts; the
    # unlogged ones in between (I) are placed so the replay matches the log
    "G3": [(0, [8, 0]), (19.5, [7, 7]), (20.5, [7, 0]),
           (21.7, [7, I]), (22.1, [I, I]), (30.0, [7, 0]),
           (59.7, [67367, 0]), (60.2, [7, 0]),          # quick dim at 64.3
           (92.0, [6, 0]),                              # brighten at 92.5
           (93.5, [125097, 0]), (95.5, [125097, 67367]), (96.0, [67367, I]), (104.0, [7, 0]),
           (120.0, [I, 0]), (120.5, [7, 0]),            # dim at 137.1
           (141.6, [7, 84085]), (142.1, [7, 0]),
           (151.0, [I, 0]), (151.5, [6, 0]),            # brighten at 183.7
           (216.7, [6, 83000]), (217.2, [6, 0]),
           (265.8, [126052, 0]), (266.3, [6, 0]),       # quick dim at 268.7
           (273.8, [6, 169051]), (274.3, [6, 0]),
           (294.8, [83026, 0]), (295.3, [6, 0]),
           (325.0, [39019, 0]),                         # stuck in range, "disagree" from 328.9
           (360.9, [30, 0])],                           # lamps on; brighten at 365.1
}
LIGHTS_ON = {"G3": (360.9, 30.0)}  # real light change: (when, lux)

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
for part in ("G1", "G2", "G3"):
    lines, trace = replay(part)
    level = lines[0]["current"]
    on = LIGHTS_ON.get(part)
    before = [x for x in trace if on is None or x[0] < on[0]]
    lo = min(s for _, s, _, _ in before)
    kmax = max(k for _, _, k, _ in before)
    floor = min(r["current"] for r in lines if on is None or r["t"] < on[0])  # the logged room drifts too
    room = min(r["target"] for r in lines if r["event"].startswith("lux") and "->" in r["event"]
               and "quick dim" not in r["event"] and r["stable"] >= 5) if part == "G3" else level
    held = lo >= min(level, room) - 3 and kmax == 0
    dims = [r["t"] for r in lines if r["event"].startswith("lux") and r["stable"] is not None and r["stable"] < 4
            and "finished" not in r["event"]]
    print(f"{part}: logged dims at {dims} s; screen lowest {lo:.0f}% (room {min(level, room):.0f}%), keyboard max {kmax} -> {'held' if held else 'MOVED'}")
    if not old:
        ok &= held
    else:
        # brightened back: "lux X -> Y" from under 4 lx to a lit stable value
        backs = [r["t"] for r in lines if r["event"].startswith("lux ") and r["stable"] is not None and r["stable"] >= 5
                 and float(r["event"].split()[1]) < 4]
        for d in dims:
            got = first_dim(trace, d - 4, min(level, room) - 3)
            print(f"   logged dim at {d} s, replay dims at {got} s")
            ok &= got is not None and abs(got - d) <= 4
        for b in backs:
            since = max([d + 0.5 for d in dims if d < b] + [b - 4])  # after the replayed dim
            up = next((t for t, s, _, st in trace if t > since and st is not None and st >= 5), None)
            print(f"   logged back at {b} s, replay back at {up} s")
            ok &= up is not None and abs(up - b) <= 4
    if on:
        # the real light change is followed like the log: within ~4 s (2 s median + 2 s settle)
        up = next((t for t, s, _, st in trace if t >= on[0] and st is not None and abs(st - on[1]) <= 2), None)
        print(f"   lamps on at {on[0]} s: replay follows at {up} s")
        ok &= up is not None and up - on[0] <= 6
    ok &= abs(trace[-1][1] - lines[-1]["target"]) <= 3
assert ok, "see above"
print("ok" if not old else "ok (the old version dims at the logged times)")
