# Auto Brightness for Omarchy

Screen brightness and keyboard light follow the laptop's **built-in ambient
light sensors** (Linux iio `als` devices). No camera, no habit learning, no sudo.
The goal is to behave like a MacBook: slow, smooth fades and no visible jumps,
even when the XPS 14's HID light sensors send garbage.

Changes per version: [CHANGELOG.md](CHANGELOG.md).

## How it behaves

- **Curve:** log-lux with gamma 0.8 between your min (default 8 %) and max. Your min slider is the real floor. 0 to 2 lx counts as dark, 10000 lx gives the max.
- **Your change is an offset, not a pause.** Brightness keys move the curve up
  or down by that amount. The offset is dropped when the room light moves more
  than 2.5x from where you set it, after resume or lid open, or the next day.
  A key press while the screen is only part-way dimmed accepts the darkness
  it was heading for, so the full dim does not undo your change.
- **Reaction:** a light change must last 2 s (up to 4 s when dimming in the dark) after a 4 s per-sensor median. Changes under 12 % or under 2 lx are ignored. A drop to under half the light dims part-way first and fully only after it held 8 s, so short train tunnels and shadows do little. Covering the sensor at 300 lx: first dim after about 6.5 s, fully dark after about 20 s.
- **Fades:** the length follows the size of the change, as in Apple's patent US 2012/0019493. Brightening 2x or more takes 1.5 s, 1.5x takes 5 s. Dimming up to 3x takes 5 s, 10x or more takes 10 s. Brightness is written 60 times a second in even perceived (log) steps.
- **Sensor glitches:** each sensor's readings go through a 4 s median weighted by time, and the brighter sensor wins, so a hand over one sensor does nothing. An exact 0 lx from a lit sensor counts only after it held 3.5 s. A reading above 60000 lx ignores that sensor for 30 s. When one sensor says sunlight and the other says dark, the lower one is used. A jump from dark to sunlight must hold 10 s, and is not believed at all for 90 s after an impossible reading.
- **Resume and lid open:** the sensor is read fresh and followed at once for 3 s, with 0.4 s fades.
- **Never dims during a fullscreen video** (fullscreen window and an MPRIS player playing).
- **Keyboard light (Apple-style, native levels only):** level 2 below 1 lx
  (back to 1 only above 2 lx), level 1 below 4 lx, off above 12 lx; 4 to 12 lx
  keeps whatever it is. It goes on or up 3 s after the screen accepted the darkness (about 15 s after the lights go off) and off at once. Calibrated on the XPS 14 sensors (a lit room reads
  about 16 to 35 lx, a covered sensor 0 to 3 lx). It is only switched when the room crosses those lines, so
  your own key presses stick. `kbdLevel2Below: 0` disables level 2. The inactivity timeout is the Dell firmware's own
  (`/sys/class/leds/dell::kbd_backlight/stop_timeout`, 1 min): off when idle,
  back on at the next key press; changing it needs root.
- Keeps adjusting on the lock screen. Holds only while the lid is closed, the screen is blanked (DPMS off), or the walk-away lock has dimmed it.
- Writes through logind's SetBrightness (D-Bus, `brightnessctl` as fallback), so the user service needs no root.
- Every decision (raw and filtered lux, target, current, mode, trigger) goes to `~/.local/state/omarchy-auto-brightness/decisions.jsonl`, capped at 1 MB with one older copy.

`omarchy-auto-brightness sensors` shows what the light sensors expose (on the
XPS 14 the second one also reports colour temperature and chromaticity x/y).

Tests (no hardware, temp state only): `for f in tests/test_*.py; do python3 "$f" || break; done`.

## Install / uninstall

    ./install.sh          # script, user service, plugin copy; enables the service
    ./uninstall.sh

Then add `{ "id": "timon.auto-brightness" }` to your bar. Right-click: on/off.
Click: a popup laid out like Omarchy's Bluetooth popup (same 380 px width).
- **Header:** the on/off switch and a status line. In normal operation it
  cycles every 2.8 s like the stock Bluetooth and Tailscale popups: the live
  lux, the screen level or your held offset, the keyboard light when it is on,
  and "Reading the room". Special states show one fixed line instead:
  dimming or brightening to N %, holding for video, ignoring a sensor glitch,
  awake and matching the room, held by walk-away, paused (screen off, lid
  closed), waiting for the sensor, turned off, service not running.
- **Screen:** min and max sliders. The value and the screen follow the drag
  live (the daemon follows a min/max change with 0.15 s fades for 2 s).
- **Keyboard light** (only with a keyboard backlight): one switch, whether
  auto also drives the keyboard light. The hardware key keeps working;
  auto keeps your level until the room changes enough for another level.

The lux in the popup is the live reading (`luxNow`: this sample, with the
glitch rules but without the 4 s median). The screen still follows the
smoothed value (`lux`). While the popup is open it re-reads the state file
on every change and touches `$XDG_RUNTIME_DIR/omarchy-auto-brightness.watch`,
so the daemon samples at 10 Hz instead of 2 Hz; closed, it reads the file every 10 s.

CLI: `omarchy-auto-brightness status|on|off|lux|set min 10|set max 90|set keyboard off|kbd-level 0`.
Settings: `~/.config/omarchy/auto-brightness.json`. Besides `enabled`, `min`,
`max` and `keyboard` it takes any key of `DEFAULTS` at the top of
`bin/omarchy-auto-brightness`, for example `gamma`, `fullLux`, `kbdOnBelow`,
`kbdOffAbove`, `kbdLevel2Below`, `kbdLevel2Exit`, `kbdOnSeconds`, `dimHoldSeconds`,
`dimQuickSeconds`, `brightenSeconds`, `luxDeadband`, `settleSeconds` and
`offsetResetRatio`. `"appleRamps": false` goes back to fixed fades
(`brightenSeconds` up, `dimSeconds` down).

## Credits

Idea and survey of the problem from
[ziouf/omarchy-adaptive-brightness](https://github.com/ziouf/omarchy-adaptive-brightness)
(reviewed at 2dd87df). No code was copied: that plugin samples the webcam,
this one only uses the light sensors. MIT, see LICENSE.
