"""2.16.0: the keyboard backlight around Omarchy's lock blank. The lock runs
`omarchy-brightness-keyboard off` (saves the level in
$XDG_RUNTIME_DIR/omarchy-brightness-keyboard-<dev>, sets 0) and on wake
`dpms on` then `... restore` (puts the saved level back, deletes the file),
under a flock on <file>.lock. Up to 2.15 the daemon re-applied its own level
right after the screen came on: a key press to off was undone, and in
daylight it could write 0 before the restore put the old 1 back (lit all day).
Now it waits for the restore and keeps the level unless the room crossed a
keyboard threshold during the hold. Real loop, fake sysfs and clock."""
import os
import loop_harness

def rec(lp): return os.path.join(lp.ab.RUN, "omarchy-brightness-keyboard-dell::kbd_backlight")
def blank(lp):
    if not os.path.exists(rec(lp)): open(rec(lp), "w").write(f"{lp.level()}\n")
    lp.set_level(lp.kb, 0); lp.off = True
def wake(lp): lp.off = False
def restore(lp):
    if os.path.exists(rec(lp)):
        lp.set_level(lp.kb, int(open(rec(lp)).read())); os.remove(rec(lp))
def key(v): return lambda lp: lp.set_level(lp.kb, v)
def room(v): return lambda lp: lp.room(v)

def scenario(events, until=160):
    lp = loop_harness.Loop(lux=1, screen=100)
    return lp.run(until, events)

# 1. dark room, auto lights it (level 1), you switch it off, the screen blanks and wakes
lp = scenario({30: key(0), 40: blank, 100: wake, 100.4: restore})
auto = lp.kbd_writes()
print("1 key off, blank, wake:", auto, "end", lp.level())
assert auto and auto[0][0] == 1 and auto[0][1] < 30, auto
assert not [w for w in auto if w[1] > 30] and lp.level() == 0, auto
# 2. the room got bright during the blank: off after the restore, nothing before it
lp = scenario({40: blank, 60: room(300), 100: wake, 100.4: restore})
auto = lp.kbd_writes()
print("2 bright during the blank:", auto, "end", lp.level())
assert not [w for w in auto if 40 <= w[1] < 100.4], auto
assert [w for w in auto if w[1] >= 100.4][-1:] and auto[-1][0] == 0 and lp.level() == 0, auto
# 3. the same with a slow restore (3 s after dpms on): still no write before it
lp = scenario({40: blank, 60: room(300), 100: wake, 103: restore})
auto = lp.kbd_writes()
print("3 slow restore:", auto, "end", lp.level())
assert not [w for w in auto if 40 <= w[1] < 103] and lp.level() == 0, auto
# 4. dark the whole time: the restore brings back 1, no extra write
lp = scenario({40: blank, 100: wake, 100.4: restore})
auto = lp.kbd_writes()
print("4 dark throughout:", auto, "end", lp.level())
assert not [w for w in auto if w[1] > 40] and lp.level() == 1, auto
# 5. a key press to 2 is never undone (auto's own maximum is 1)
lp = scenario({30: key(2), 40: blank, 100: wake, 100.4: restore})
assert not [w for w in lp.kbd_writes() if w[1] > 30] and lp.level() == 2, lp.kbd_writes()
print("5 key press to 2 kept through the blank")
# 6. no restore at all (never blanked by the lock): auto decides after kbdRestoreMaxSeconds
lp = scenario({40: lambda lp: setattr(lp, "off", True), 60: room(300), 100: wake})
auto = lp.kbd_writes()
assert auto[-1][0] == 0 and 100 < auto[-1][1] <= 100 + lp.ab.DEFAULTS["kbdRestoreSeconds"] + 1.5, auto
print("6 blank without the lock's record: off %.1f s after wake" % (auto[-1][1] - 100))
print("ok")
