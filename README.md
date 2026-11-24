# Auto Brightness for Omarchy

Screen brightness and keyboard backlight follow the laptop's **built-in ambient
light sensors** (Linux iio `als` devices). No camera, no habit learning, no sudo.
The goal is to behave like a MacBook: slow, smooth fades and no visible jumps.

Tuned for, and only tested on, the Dell XPS 14. Other laptops with a standard
Linux light sensor will likely run, but the lux thresholds may need adjusting
(see Hardware).

Changes per version: [CHANGELOG.md](CHANGELOG.md).

## How it behaves

- **Curve:** log-lux with gamma 0.8 between your min (default 8 %) and max. Your min slider is the real floor. 0 to 2 lx counts as dark, 10000 lx gives the max.
- **Your change is an offset, not a pause.** Brightness keys move the curve up
  or down by that amount. The offset is dropped when the room light moves more
  than 2.5x from where you set it, after resume or lid open, or the next day.
  A key press while the screen is only part-way dimmed accepts the darkness
  it was heading for, so the full dim does not undo your change.
- **Reaction:** a light change must last 2 s (up to 4 s when dimming in the dark) after a 4 s per-sensor median. Changes under 12 % or under 2 lx are ignored. A drop to under half the light dims part-way first and fully only after it held 8 s, so short dips and shadows do little. Covering the sensor at 300 lx: first dim after about 6.5 s, fully dark after about 20 s.
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
- **Low battery:** on battery below 15 % (`kbdLowBatteryPercent`, 0 = off) auto sets the keyboard backlight to level 1 at most, and lowers its own level 2 to 1. A key press to 2 still sticks; the charger lifts the cap. The battery is read from `/sys/class/power_supply` every 10 s (peripheral batteries are ignored). 15 % because Omarchy has no percentage-based power saver: it switches power profiles on plugging in or unplugging, and only warns at 10 %.
- Keeps adjusting on the lock screen. Holds only while the lid is closed, the screen is blanked (DPMS off), or a walk-away lock has dimmed it (any tool that creates `$XDG_RUNTIME_DIR/omarchy-walk-away.dimmed`; none ships with this plugin).
- Writes through logind's SetBrightness (D-Bus, `brightnessctl` as fallback), so the user service needs no root.
- Every decision (raw and filtered lux, target, current, mode, trigger) goes to `~/.local/state/omarchy-auto-brightness/decisions.jsonl`, capped at 1 MB with one older copy.

## Hardware

It runs on any laptop with a standard Linux iio light sensor (`als`) and a
backlight written through logind. No root, no camera.

It is only tested on the Dell XPS 14, and several parts are tuned for that
machine:

- The glitch filters exist because its HID sensors send garbage bursts.
- The keyboard thresholds (`kbdOnBelow`, `kbdLevel2Below`, `kbdLevel2Exit`,
  `kbdOffAbove`) were calibrated on its sensors (a lit room reads about
  16 to 35 lx). `darkLux` and `fullLux` set the dark and bright ends of the
  screen curve.
- The keyboard inactivity timeout is the Dell firmware's own
  (`/sys/class/leds/dell::kbd_backlight/stop_timeout`).

Other laptops will likely run, but may need those lux thresholds adjusted
in `~/.config/omarchy/auto-brightness.json` (any key of `DEFAULTS` in
`bin/omarchy-auto-brightness`). `omarchy-auto-brightness sensors` shows
what a sensor reports (on the XPS 14 the second one also reports colour
temperature and chromaticity x/y).

Tests (no hardware, temp state only): `for f in tests/test_*.py; do python3 "$f" || break; done`.

## Install / uninstall

Needs: Omarchy's Quickshell shell (plugin manifest `schemaVersion` 1), Python 3,
a laptop with an iio ambient light sensor (`/sys/bus/iio/devices/*/name` is
`als`), and `python-gobject` for logind writes. Without `python-gobject`
every write falls back to `brightnessctl`.

    ./install.sh          # script, user service, plugin copy; enables the service
    ./uninstall.sh

Then add `{ "id": "timon.auto-brightness" }` to the bar in `~/.config/omarchy/shell.json`. Right-click: on/off.
Click: a popup laid out like Omarchy's Bluetooth popup (same 380 px width).
- **Header:** the on/off switch and a status line (`HeroLines.js`). A state
  that changes what the screen does shows one fixed line (turned off, lid
  closed, dimming/brightening to N %, holding for video, min = max "Always
  full blast" / "Locked at N %"). Otherwise up to four lines cycle every 2.8 s
  like the stock Bluetooth and Tailscale popups: the live lux, the screen
  level or your key offset, the keyboard backlight, and one fun fact about the
  room (sunlight, pitch black). Internal holds (blanked screen, walk-away
  flag, no reading yet) and sensor glitch handling never show; the popup then
  shows plain facts ("Room at N lx", "Screen at N%"). Full table:
  `python3 tests/test_hero_lines.py`.
- **Screen:** min and max sliders. The value and the screen follow the drag
  live (the daemon follows a min/max change with 0.15 s fades for 2 s).
- **Keyboard backlight** (only on laptops that have one): one row with a
  switch, "Turns on automatically in the dark", for whether auto also drives
  it. The hardware key keeps working. There is no section title above it:
  a single row is deliberate, so this differs from the design rule that
  every section has a PanelSectionHeader.

The lux in the popup is the live reading (`luxNow`: this sample, with the
glitch rules but without the 4 s median). The screen still follows the
smoothed value (`lux`). While the popup is open it re-reads the state file
on every change and touches `$XDG_RUNTIME_DIR/omarchy-auto-brightness.watch`,
so the daemon samples at 10 Hz instead of 2 Hz; closed, it reads the file every 10 s.

CLI: `omarchy-auto-brightness status|on|off|lux|set min 10|set max 90|set keyboard off|kbd-level 0`.
Settings: `~/.config/omarchy/auto-brightness.json`. Besides `enabled`, `min`,
`max` and `keyboard` it takes any key of `DEFAULTS` at the top of
`bin/omarchy-auto-brightness`, for example `gamma`, `fullLux`, `kbdOnBelow`,
`kbdOffAbove`, `kbdLevel2Below`, `kbdLowBatteryPercent`, `kbdLevel2Exit`, `kbdOnSeconds`, `dimHoldSeconds`,
`dimQuickSeconds`, `brightenSeconds`, `luxDeadband`, `settleSeconds` and
`offsetResetRatio`. `"appleRamps": false` goes back to fixed fades
(`brightenSeconds` up, `dimSeconds` down).

## Credits

Idea and survey of the problem from
[ziouf/omarchy-adaptive-brightness](https://github.com/ziouf/omarchy-adaptive-brightness)
(reviewed at 2dd87df). No code was copied: that plugin samples the webcam,
this one only uses the light sensors. MIT, see LICENSE.
