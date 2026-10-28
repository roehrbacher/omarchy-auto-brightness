# Auto Brightness for Omarchy

Screen brightness and keyboard light follow the laptop's **built-in ambient
light sensors** (Linux iio `als` devices). No camera, no habit learning, no sudo.

Version 2 works like a MacBook (no habit learning):

- 2.5.0: faster dimming. A big drop (sensor covered, lights off) now dims part-way after ~5 s (`dimQuickSeconds` 2.5 s after the 4 s sensor median: half the drop, counted in log-lux) and fully after ~10 s (`dimHoldSeconds` 8, was 12); fades down take 4 s (`dimSeconds`, was 7). Covering the sensor at 300 lx: first dim after 5 s, fully dark after ~14 s (was 14.5 s / ~21 s). Cost: train dips of 4-7 s now dim part-way (in the 23 Oct replay down to ~37 % instead of staying at ~65 %) and come back within ~1.5 s; 2 s dips still do nothing. Brightening and the spike/burst protection are unchanged. The keyboard light waits for the full dim (on after ~13 s of darkness).
- 2.4.0: the screen gets the same wait: a drop to under half the light (`dimBigRatio`) must hold for 12 s (`dimHoldSeconds`, every sample) before the screen dims, so 2-7 s train dips (250 -> 0 lx) no longer fade it 67% -> 1%. Smaller dims and all brightening stay quick. The keyboard wait (`kbdOnSeconds`) is now 3 s on top of that, so a real dark tunnel or room still lights the keys after ~15-17 s.
- 2.3.0: keyboard light like a MacBook: it only turns on (or goes to level 2) after the darkness has lasted 15 s (`kbdOnSeconds`), and turns off as soon as it is bright again. Short 0 lx dips on a train (shadows, tunnels, sensor dropouts of 2-7 s in a 200-400 lx cabin) no longer switch it on.
- 2.2.2: implausible jumps (from under 50 lx to over 5x+500 lx, or over 20000 lx) must hold for 10 s with every sample high, so the XPS sensors' bogus 6 s bursts (0 -> 41008 lx in a dark room) no longer flash the screen to 100%. Normal brightening stays fast.
- 2.2.1: dark-end hysteresis: lux changes under 2 lx are ignored and the curve treats 0-2 lx as dark, so the sensor's 0 <-> 1 lx wobble no longer fades the screen 1% <-> 13%.
- 2.2.0: keeps adjusting on the lock screen (only pauses while the screen is DPMS-off) and re-applies the keyboard level after a pause; a 4 s per-sensor median drops the XPS 14 light sensors' bogus 1-2 s bursts (dark room suddenly reading ~40000 lx).


- **Curve:** log-lux with gamma 0.8 between your min (default 8 %, the slider is the real floor) and max.
- **Your change is an offset, not a pause.** Brightness keys move the curve up
  or down by that amount. The offset is dropped when the room light moves more
  than 2.5x from where you set it, after resume / lid open, or the next day.
- **Fades:** brightens in ~1.5 s, dims over ~7 s (smoothstep). Light changes
  under 12 % and spikes or shadows shorter than 2 s are ignored. With two
  sensors (XPS 14) the brighter one wins, so a hand over one does nothing.
- **Never dims during a fullscreen video** (fullscreen window + an MPRIS player Playing).
- **Fresh reading** on resume and when the lid opens.
- **Keyboard light (Apple-style, native levels only):** level 2 below 1 lx
  (back to 1 only above 2 lx), level 1 below 4 lx, off above 12 lx; on/up only after 15 s of darkness, off at once; 4-12 lx
  keeps whatever it is. Calibrated on the XPS 14 sensors (a lit room reads
  ~16-35 lx, a covered sensor 0-3 lx). Only switched when the room crosses those lines, so
  your own key presses stick. `kbdLevel2Below: 0` disables level 2. The inactivity timeout is the Dell firmware's own
  (`/sys/class/leds/dell::kbd_backlight/stop_timeout`, 1 min): off when idle,
  back on at the next key press; changing it needs root.
- Holds while the lid is closed, the screen is locked, or the walk-away lock has dimmed it.
- Writes through `brightnessctl` (logind), so the user service needs no root.

`omarchy-auto-brightness sensors` shows what the light sensors expose (on the
XPS 14 the second one also reports colour temperature and chromaticity x/y).

Tests: `python3 tests/test_curve.py && python3 tests/simulate.py` (timeline log).

## Install / uninstall

    ./install.sh          # script, user service, plugin copy; enables the service
    ./uninstall.sh

Then add `{ "id": "timon.auto-brightness" }` to your bar. Click: popup with
on/off, min, max and the keyboard switch. Right-click: on/off.

CLI: `omarchy-auto-brightness status|on|off|lux|set min 10|set max 90|set keyboard off`.
Settings: `~/.config/omarchy/auto-brightness.json` (also `curve`, `kbdOnBelow`,
`kbdOffAbove`, `kbdLevel2Below`, `kbdLevel2Exit`, `gamma`, `floor`, `brightenSeconds`, `dimSeconds`, `luxDeadband`, `settleSeconds`, `offsetResetRatio`).

## Credits

Idea and survey of the problem from
[ziouf/omarchy-adaptive-brightness](https://github.com/ziouf/omarchy-adaptive-brightness)
(reviewed at 2dd87df). No code was copied: that plugin samples the webcam,
this one only uses the light sensors. MIT, see LICENSE.

## 2.6.0: Apple-style timing

Copied from Apple's patents (no habit learning, light sensor only):

- Fade length follows the size of the change (US 2012/0019493): dimming 1.5x or 3x takes
  ~5 s, 10x or more ~10 s; brightening 1.5x takes ~5 s, 2x or more 1.5 s. Eyes adapt
  slower to darkness, so the screen never dims faster than it brightens.
- In the dark it waits longer before dimming further (US 10,235,970): the settle wait
  doubles at 0 lx and is normal from 10 lx up. Brightening back stays quick.
- Already in place: a change must last (settle, spike median, jump rule) and be big
  enough (12 % / 2 lx deadband); readings outside 0-60000 lx are ignored; keyboard light
  only in low light; the keyboard's own firmware idle-off is left alone.

Not 1:1: Apple's actual lux curve is unpublished; True Tone and per-frame ramps don't
exist here; Apple's curve learning is left out on purpose. `omarchy-auto-brightness`
with `"appleRamps": false` in the config goes back to the 2.5.0 fades.
