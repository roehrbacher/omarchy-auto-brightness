"""2.16.0: Auto Brightness replaces other automatic brightness, the way Nice
Clipboard replaces the stock clipboard: while it runs, other auto-brightness
user services are stopped for the session (never disabled, masked or
edited: no sudo, no Omarchy files touched), and Omarchy's in-shell keyboard
auto (omacom/omarchy#13148) is switched off with its own user toggle flag.
`restore-replaced` (run by uninstall.sh) starts them again and removes the
flag, only if it was this plugin that set it. systemctl and omarchy-shell
are stubbed: nothing on this machine is touched."""
import os, tempfile, types
import loop_harness

tmp = tempfile.mkdtemp(prefix="ab-repl-")
os.makedirs(tmp + "/run")
ab = loop_harness.load(tmp, stub=False)
import importlib
calls, state = [], {"omarchy-brightness-auto.service": "active", "wluma.service": "inactive",
                     "omarchy-brightness-keyboard-auto.service": "active"}
enabled = {"omarchy-brightness-auto.service": "enabled", "omarchy-brightness-keyboard-auto.service": "disabled"}
def systemctl(*args, timeout=5):
    calls.append(args)
    if args[0] == "is-active":
        return types.SimpleNamespace(stdout="\n".join(state.get(u, "inactive") for u in args[1:]) + "\n")
    if args[0] == "is-enabled":
        return types.SimpleNamespace(stdout=enabled.get(args[1], "disabled") + "\n")
    if args[0] in ("stop", "start"):
        state[args[1]] = "inactive" if args[0] == "stop" else "active"
    return types.SimpleNamespace(stdout="")
shell = []
ab._systemctl = systemctl
ab.shutil.which = lambda name: "/usr/bin/" + name if name == "omarchy-toggle-keyboard-backlight-auto" else None
real_run = ab.subprocess.run
ab.subprocess.run = lambda cmd, **kw: (shell.append(cmd), types.SimpleNamespace(stdout="", returncode=0))[1]
# the daemon replaces them (keyboard on)
out = ab.replace_upstream(True)
print("replace:", out)
stops = [a for a in calls if a[0] == "stop"]
assert stops == [("stop", "omarchy-brightness-auto.service"), ("stop", "omarchy-brightness-keyboard-auto.service")], stops
assert not [a for a in calls if a[0] in ("disable", "mask", "edit")], calls
assert os.path.exists(ab.KBD_TOGGLE) and os.path.exists(ab.KBD_TOGGLE_MINE)
assert ab.KBD_TOGGLE.startswith(tmp + "/") and ["omarchy-shell", "-q", "omarchy.keyboard-backlight", "sync"] in shell
# again a minute later: nothing left to do
calls.clear(); assert ab.replace_upstream(True) == [] and not [a for a in calls if a[0] == "stop"]
# restore: only what it stopped and is still enabled starts again; its own flag goes
out = ab.restore_replaced()
print("restore:", out)
starts = [a for a in calls if a[0] == "start"]
assert starts == [("start", "omarchy-brightness-auto.service")], starts
assert not os.path.exists(ab.KBD_TOGGLE) and not os.path.exists(ab.REPLACED)
# a flag you set yourself (keyboard auto off by choice) is left alone
open(ab.KBD_TOGGLE, "w").close()
ab.replace_upstream(True); ab.restore_replaced()
assert os.path.exists(ab.KBD_TOGGLE), "your own toggle flag was removed"
# keyboard off in Auto Brightness: Omarchy's keyboard auto is not replaced
os.remove(ab.KBD_TOGGLE); state["omarchy-brightness-keyboard-auto.service"] = "active"; calls.clear()
ab.replace_upstream(False)
assert ("stop", "omarchy-brightness-keyboard-auto.service") not in calls and not os.path.exists(ab.KBD_TOGGLE)
# uninstall.sh runs restore-replaced before removing the script
sh = open(os.path.join(loop_harness.HERE, "..", "uninstall.sh")).read()
assert sh.index("restore-replaced") < sh.index("rm -f"), "uninstall.sh must restore first"
print("stopped for the session only, restored on uninstall, your own flag kept")
print("ok")
