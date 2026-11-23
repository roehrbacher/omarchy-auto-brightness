# Changelog

Newest first. The version is `manifest.json` `version`; each commit subject starts with it.

## 2.12.0

Popup round 2: a live status line, a simpler keyboard section, live sliders and live lux.

- Status line under the title works like stock Bluetooth/Tailscale. In normal operation it cycles every 2.8 s with the same fade: "Following the light · N lx", "Screen at N %" or "Your +N % held", "Dark room · Keyboard light N" when the light is on, and "Reading the room". Special states show one line: "Dimming to N %", "Brightening to N %", "Holding for video", "Ignoring a sensor glitch", "Awake · matching the room", "Held by walk-away", "Paused · screen off", "Paused · lid closed", "Waiting for the sensor", "Turned off", "Service not running". The state file has the new fields for this: `luxNow`, `fadeTo`, `glitch`, `videoHold`, `waking`, `dark`.
- Keyboard section: the Off/1/2 buttons are gone (the laptop has a key for that; `kbd-level` stays in the CLI). One switch, "Follow the room light", for the existing `keyboard` setting, with help text on what auto does.
- Sliders are live. Before, the value label only moved after release, the knob jumped back to the old value on release until the CLI answered, and the screen only changed after the daemon's next 0.5 s pass plus a normal 1.5 to 10 s fade. Measured offscreen (drag min 8 -> 40 % in 2 s): label never moved during the drag, screen first changed 2.3 s after the drag started and reached 40 % 1.76 s after release. Now the label follows every move (median 0 ms, max 20 ms), the knob never jumps back, the screen starts moving after 134 ms, trails the finger by about 5 points (0.3 s) and reaches 40 % 135 ms after release. The popup sends the newest value, one CLI call at a time. The daemon follows a min/max change with 0.15 s fades for 2 s (`previewSeconds`, `previewFadeSeconds`). Reads of the state file never override a value you just set until the daemon reports it.
- Live lux. The popup showed the settled lux the screen follows, 4 to 5 s behind the room, and on a big drop first a part-way value (200 -> 40 lx showed 89.8 lx after 4.7 s). It now shows `luxNow`: the current sample with the glitch rules (range, quarantine, 0 lx drop-outs, sensors disagreeing, glitch episode) but without the 4 s median. Measured: 4 to 61 ms after the sensor change (14 changes). Test: `tests/test_popup_state.py`.
- With the popup open the daemon samples at 10 Hz (popup touches `$XDG_RUNTIME_DIR/omarchy-auto-brightness.watch` every second; stale after 2.5 s). The popup re-reads the state file on change (inotify) instead of every 0.25 s; closed, every 10 s, no process started.
- Popup font is `Style.font.menuFamily`; "NOW N %" is `Style.font.bodySmall` instead of caption.

## 2.11.0

New popup layout, manual keyboard light levels, and the popup no longer lags.

- The popup uses Omarchy's own building blocks, like the stock Bluetooth popup: `PanelHero` header (big icon, bold title, caps status line, on/off switch on the right), `PanelSeparator`, and sections with `PanelSectionHeader` 14 px apart, all flush left, 380 px wide. Body text is `Style.font.body`, help text `Style.font.bodySmall`, dim text `Qt.darker(foreground, 1.4)`.
- Keyboard light buttons Off, 1 and 2 under "Keyboard light (manual)". The selected button is the current level. A manual level works like a key press: the daemon is not told, so it changes the light again only when the room gets dark or bright enough for another level, the screen comes back on after a hold, the lid opens or the laptop wakes. The section is hidden on machines without a keyboard backlight. New CLI command `kbd-level N` (clamped to the keyboard's levels).
- The state file and `status` now include `kbdLevel` and `kbdMax`.
- Popup lag fixed. The popup ran `omarchy-auto-brightness status` (a Python start) every 1.5 s while open, so a change showed up to 1.5 s late (measured offscreen: median 743 ms, max 1483 ms after the daemon wrote it). Before 2.11.0 the keyboard level was not shown at all, and after a click the switches waited for the next poll. The popup now reads the state file directly every 0.25 s while open (median 226 ms, max 257 ms) and every 10 s while closed, with no process started. After a click, the new settings and keyboard level show at once.
- Note: the lux shown is the settled value the screen follows, so it still moves only after the 4 s sensor median and 2 s settle time. That delay is part of the filtering, not the popup.

## 2.10.2

Pre-release checks (security audit and implicit state machines review). One bug fix.

- Pressing brightness up while the screen was only part-way dimmed no longer gets undone. Your offset was anchored to the part-way value (about 13 lx after lights off at 200 lx). When the full dim reached 0 lx about 6 s later, that looked like the light moving 14x, so the offset was cleared and the screen faded to the minimum. The README says the offset stays until the room light moves more than 2.5x from where you set it, and the room had not changed after the press. A key press during the part-way dim now accepts the darkness the dim was heading for, so your level stays. When the lights come back on, the 2.5x rule still clears the offset. Test: `tests/test_manual_during_dim.py`.
- The part-way dim is now one explicit state, the lux it is heading for (`staged_to`), instead of a separate on/off flag.

## 2.10.1

Quality pass. Two bug fixes, no other behaviour change.

- A 2 s burst of garbage from one light sensor no longer brightens the screen when it arrives during a fade. The daemon reads the sensors 60 times a second while fading and twice a second otherwise. The per-sensor median counted readings, so the burst outvoted the calm readings before it. In a 300 lx room the screen went from 66 % to 91 % and took about 9 s to come back. The median now weighs each reading by how long it lasted. Test: `tests/test_fade_cadence_burst.py`.
- Turning the lights off in an already dim room (3 to 5 lx) now takes the keyboard light to level 2. The part-way dim stopped at about 1.2 lx, the real 0 lx reading was inside the 2 lx deadband, and the keyboard stayed at level 1. The part-way dim now finishes at the real reading. The screen was already at its minimum, so it does not change. Test: `tests/test_dim_room_to_dark.py`.
- `tests/simulate.py` is now `tests/test_simulate.py` and passes again. Its timings were from before 2.6.0, and its keyboard level 2 check had caught the bug above.
- Code cleanup: config values are read from `DEFAULTS` without second fallback values that disagreed with them (`zeroTrustSeconds` 8 s against 3.5 s, for example). State that was created on first use is set up in the constructors. A leftover `if True:` block is gone. The module docstring and the comment on `dimSeconds` describe the current behaviour.
- The version history moved from the README to this file. The README lists only current behaviour and settings that exist (`curve` and `floor` never did).

## 2.10.0

Ignores the light sensors' short drop-outs to exactly 0 lx (seen Nov 3: the screen dimmed and came back in an unchanged room). An exact 0 from a lit sensor only counts once it holds 3.5 s, so real darkness still dims.

## 2.9.0

Smoother fades. Brightness now changes about 60 times a second during a fade (was 10) and moves in even perceived steps (log scale, like macOS) instead of straight lines, so no step is visible: brightening 5% -> 80% used to jump up to 39% at once, now at most ~5% (relative) per 1/60 s. Writes go to logind over one kept D-Bus connection (brightnessctl as fallback).

## 2.8.1

Fixes another full-brightness jump (Oct 30 22:31): when the two sensors glitched one after the other, the sensor still reading the real dark room was ignored and the other one's 43000 lx won. The sensor cross-check now always includes every sensor, and for 90 s after any impossible reading a dark -> sunlight jump is not believed at all.

## 2.8.0

One light sensor alone sending garbage (~43000 lx or impossible 170000 lx in a dark room, for 10+ s) no longer maxes the screen: a sensor that reports an impossible value is ignored for 30 s, and when one sensor says sunlight while the other says dark, the lower one is used. Every brightness decision is now logged (raw and filtered lux, target, current, mode, trigger) to `~/.local/state/omarchy-auto-brightness/decisions.jsonl`, capped at 1 MB with one older copy.

## 2.7.0

Waking from suspend or opening the lid reads the sensor fresh and follows it at once for 3 s (0.4 s fades, keyboard light without the 3 s wait), so a dark room is dark within ~3 s. Fixes the keyboard light never turning on when the dark reading landed inside the 2 lx deadband after a part-way dim.

## 2.6.1

No behaviour change. Confirms (with a test) that brightness keeps following the light on the lock screen; the README wrongly said it held while locked. Removed the unused lock check.

## 2.6.0

Apple-style timing, copied from Apple's patents (no habit learning, light sensor only).

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

## 2.5.0

Faster dimming. A big drop (sensor covered, lights off) now dims part-way after ~5 s (`dimQuickSeconds` 2.5 s after the 4 s sensor median: half the drop, counted in log-lux) and fully after ~10 s (`dimHoldSeconds` 8, was 12); fades down take 4 s (`dimSeconds`, was 7). Covering the sensor at 300 lx: first dim after 5 s, fully dark after ~14 s (was 14.5 s / ~21 s). Cost: train dips of 4-7 s now dim part-way (in the 23 Oct replay down to ~37 % instead of staying at ~65 %) and come back within ~1.5 s; 2 s dips still do nothing. Brightening and the spike/burst protection are unchanged. The keyboard light waits for the full dim (on after ~13 s of darkness).

## 2.4.0

The screen gets the same wait: a drop to under half the light (`dimBigRatio`) must hold for 12 s (`dimHoldSeconds`, every sample) before the screen dims, so 2-7 s train dips (250 -> 0 lx) no longer fade it 67% -> 1%. Smaller dims and all brightening stay quick. The keyboard wait (`kbdOnSeconds`) is now 3 s on top of that, so a real dark tunnel or room still lights the keys after ~15-17 s.

## 2.3.0

Keyboard light like a MacBook: it only turns on (or goes to level 2) after the darkness has lasted 15 s (`kbdOnSeconds`), and turns off as soon as it is bright again. Short 0 lx dips on a train (shadows, tunnels, sensor dropouts of 2-7 s in a 200-400 lx cabin) no longer switch it on.

## 2.2.2

Implausible jumps (from under 50 lx to over 5x+500 lx, or over 20000 lx) must hold for 10 s with every sample high, so the XPS sensors' bogus 6 s bursts (0 -> 41008 lx in a dark room) no longer flash the screen to 100%. Normal brightening stays fast.

## 2.2.1

Dark-end hysteresis: lux changes under 2 lx are ignored and the curve treats 0-2 lx as dark, so the sensor's 0 <-> 1 lx wobble no longer fades the screen 1% <-> 13%.

## 2.2.0

Keeps adjusting on the lock screen (only pauses while the screen is DPMS-off) and re-applies the keyboard level after a pause; a 4 s per-sensor median drops the XPS 14 light sensors' bogus 1-2 s bursts (dark room suddenly reading ~40000 lx).

## 2.1.1 and earlier

- 2.1.1: your min is the real floor (no hard 8 %); keyboard thresholds calibrated to the XPS 14 sensors.
- 2.1.0: Apple-style keyboard levels with hysteresis.
- 2.0.0: MacBook-style offset instead of a pause, log-lux curve, fast brighten and slow dim, 2 s spike filter, no dimming during fullscreen video, fresh reading on resume and lid open.
- 1.0.0: ambient light sensors drive the screen and keyboard light; user service; bar control.
