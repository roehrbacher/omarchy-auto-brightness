# Auto Brightness for Omarchy

Screen brightness and keyboard light follow the laptop's **built-in ambient
light sensors** (Linux iio `als` devices). No camera, no habit learning, no sudo.

- Fixed lux → brightness curve (log scale) between your **min** and **max**,
  4 % hysteresis and a smooth ~2 %/40 ms ramp (about 1 s from dark to bright). Polls every 1.5 s (tiny CPU).
- Two sensors (e.g. Dell XPS 14): the brighter reading wins, so a hand over one
  does not dim the screen. Reads `in_illuminance_input`, or `raw × scale`.
- Keyboard light (`*kbd_backlight`): on below 8 lx, off above 30 lx.
- Change brightness or the keyboard light yourself → auto pauses 15 min.
- Does nothing while the lid is closed or the screen is locked.
- Writes through `brightnessctl` (logind), so the user service needs no root.

## Install / uninstall

    ./install.sh          # script, user service, plugin copy; enables the service
    ./uninstall.sh

Then add `{ "id": "timon.auto-brightness" }` to your bar. Click: popup with
on/off, min, max and the keyboard switch. Right-click: on/off.

CLI: `omarchy-auto-brightness status|on|off|lux|set min 10|set max 90|set keyboard off`.
Settings: `~/.config/omarchy/auto-brightness.json` (also `curve`, `kbdOnBelow`,
`kbdOffAbove`, `pollSeconds`, `manualPauseMinutes`).

## Credits

Idea and survey of the problem from
[ziouf/omarchy-adaptive-brightness](https://github.com/ziouf/omarchy-adaptive-brightness)
(reviewed at 2dd87df). No code was copied: that plugin samples the webcam,
this one only uses the light sensors. MIT, see LICENSE.
