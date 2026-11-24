"""2.16.0: a small brightness change of your own sticks. Omarchy's fine step
(Alt + brightness key) is 1 %; up to 2.15 only changes over 1.5 % counted
as yours, so a 1 % step faded back. Now 2 raw steps or 0.5 % count. Real loop,
fake sysfs and clock (tests/loop_harness.py)."""
import loop_harness

def bump(pct):
    def fn(lp):
        lp.set_level(lp.bl, lp.screen() + round(pct / 100 * 1000))
    return fn

for pct in (1, -1, 5):
    lp = loop_harness.Loop(lux=300, screen=500)
    lp.run(70, {20: lambda lp: lp.__setattr__("before", lp.screen()), 30: bump(pct)})
    want = lp.before + round(pct / 100 * 1000)
    after = [v for v, t in lp.screen_writes() if t > 30]
    manual = [r for r in lp.log() if "manual change" in r.get("event", "")]
    print(f"{pct:+d}% at 300 lx: {lp.before} -> {want} raw, writes after it {after}, end {lp.screen()}, logged: {manual[0]['event'] if manual else None}")
    assert manual and lp.screen() == want and not after, (pct, lp.screen(), after)
# our own fade writes are never taken for a key press
lp = loop_harness.Loop(lux=300, screen=200).run(40, {10: lambda lp: lp.room(3000)})
assert not [r for r in lp.log() if "manual change" in r.get("event", "")], "own fade counted as manual"
print("a 1 % step sticks (both ways); the daemon's own fades never count as a key press")
print("ok")
