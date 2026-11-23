"""2.13.0: the popup's status line (HeroLines.js) for every state, as a
table. Runs the real JS file with node (skipped if node is missing; the
offscreen render harness shows the same lines in Quickshell)."""
import json, os, shutil, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
js = open(os.path.join(here, "..", "HeroLines.js")).read().replace(".pragma library", "")
if not shutil.which("node"):
    print("node not installed: skipped"); sys.exit(0)
base = {"enabled": True, "min": 8, "max": 100, "keyboard": True, "lux": 120, "luxNow": 126.4, "screen": 64,
        "target": 64, "offset": 0, "mode": "auto", "fadeTo": None, "videoHold": False, "waking": False,
        "dark": False, "lowBattery": False, "kbdLevel": 0, "kbdMax": 2}
dark = {"lux": 0.5, "luxNow": 0.4, "dark": True, "screen": 8, "target": 8}
cases = [  # (state, local hour, expected lines)
    ("following the light", {}, 14, ["Following the light · 126 lx", "Screen at 64%", "Reading the room"]),
    ("brightness key offset", {"offset": 10, "target": 74}, 14, ["Following the light · 126 lx", "Your +10% held", "Reading the room"]),
    ("keys pinned it to 100 %", {"offset": 40, "target": 100}, 14, ["Following the light · 126 lx", "Your keys maxed it out", "Reading the room"]),
    ("keys pinned it to 1 %", {"offset": -70, "target": 1}, 14, ["Following the light · 126 lx", "Your keys dimmed it all the way", "Reading the room"]),
    ("dark room, keyboard light 2, evening", {**dark, "kbdLevel": 2}, 20, ["Following the light · 0.4 lx", "Screen at 8%", "Dark room · Keyboard backlight 2", "Pitch black in here"]),
    ("dark room at night", {**dark, "kbdLevel": 2}, 23, ["Following the light · 0.4 lx", "Screen at 8%", "Dark room · Keyboard backlight 2", "Pitch black · night owl hours"]),
    ("dark, keyboard follow off", {**dark, "lux": 2.5, "luxNow": 2.5, "keyboard": False}, 20, ["Following the light · 2.5 lx", "Screen at 8%", "Dark in here · keyboard is yours", "Reading the room"]),
    ("dark room on low battery", {**dark, "kbdLevel": 1, "lowBattery": True}, 20, ["Following the light · 0.4 lx", "Screen at 8%", "Low battery · Keyboard backlight 1", "Pitch black in here"]),
    ("key pressed in a lit room", {"kbdLevel": 1}, 14, ["Following the light · 126 lx", "Screen at 64%", "Keyboard backlight 1", "Reading the room"]),
    ("direct sunlight", {"lux": 31000, "luxNow": 32000, "screen": 100, "target": 100}, 13, ["Following the light · 32000 lx", "Screen at 100%", "Direct sunlight · shades on"]),
    ("min = max = 100", {"min": 100, "max": 100, "screen": 100, "target": 100}, 14, ["Always full blast"]),
    ("min = max = 1", {"min": 1, "max": 1, "screen": 1, "target": 1}, 14, ["Max 1% · vampire mode"]),
    ("min = max = 40", {"min": 40, "max": 40, "screen": 40, "target": 40}, 14, ["Locked at 40% · sensor on a break"]),
    ("min > max (state file edited by hand)", {"min": 60, "max": 40, "screen": 40, "target": 40}, 14, ["Locked at 40% · sensor on a break"]),
    ("min = max with a key offset", {"min": 40, "max": 40, "offset": 10, "screen": 50, "target": 50}, 14, ["Following the light · 126 lx", "Your +10% held", "Reading the room"]),
    ("dimming", {"fadeTo": 40}, 14, ["Dimming to 40%"]),
    ("brightening", {"fadeTo": 80}, 14, ["Brightening to 80%"]),
    ("fullscreen video", {"videoHold": True}, 14, ["Holding for video"]),
    ("woke up", {"waking": True}, 14, ["Awake · matching the room"]),
    ("lid opened in a dark room", {**dark, "waking": True}, 23, ["Woke up in the dark · going easy"]),
    ("walk-away flag hold", {"mode": "walk-away dim"}, 14, ["Room at 126 lx", "Screen at 64%"]),
    ("screen blanked", {"mode": "screen off"}, 14, ["Room at 126 lx", "Screen at 64%"]),
    ("lid closed", {"mode": "lid closed"}, 14, ["Paused · lid closed"]),
    ("no reading yet", {"mode": "no reading", "lux": None, "luxNow": None}, 14, ["Screen at 64%"]),
    ("no reading, no screen value", {"mode": "no reading", "lux": None, "luxNow": None, "screen": None}, 14, ["Reading the room"]),
    ("turned off", {"enabled": False, "mode": "off"}, 14, ["Turned off"]),
    ("service not running", {"mode": "not running"}, 14, ["Service not running"]),
]
prog = js + "\nconst cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n" \
       "console.log(JSON.stringify(cases.map(c => lines(c[0], c[1]))));"
inp = json.dumps([[{**base, **st}, hour] for _, st, hour, _ in cases])
got = json.loads(subprocess.run(["node", "-e", prog], input=inp, capture_output=True, text=True, check=True).stdout)
bad = 0
for (name, _, hour, want), lines in zip(cases, got):
    print(f"{name:40} {' | '.join(l.upper() for l in lines)}")
    assert len(lines) <= 4, (name, lines)
    if lines != want:
        bad += 1; print(f"  expected {' | '.join(want)}")
assert not bad, f"{bad} case(s) differ"
print("ok")
