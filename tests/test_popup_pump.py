"""2.15.1: the popup's setting writes (Panel.qml merged/apply/setSetting/pump,
the real function text) against a fake CLI process, with node. A click must
reach the CLI even when it repeats the value sent last time and the setting
was changed elsewhere meanwhile (terminal CLI, another monitor's popup); a
drag still sends only the newest value, one call at a time."""
import os, shutil, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
if not shutil.which("node"):
    print("node not installed: skipped"); sys.exit(0)
prog = r"""
const src = require("fs").readFileSync(process.argv[1], "utf8");
function grab(name) {
  const i = src.indexOf("function " + name + "(");
  let d = 0;
  for (let k = src.indexOf("{", i); k < src.length; k++) {
    if (src[k] === "{") d++;
    if (src[k] === "}" && --d === 0) return src.slice(i, k + 1);
  }
}
const root = { local: {}, localUntil: 0, wanted: {}, sent: {}, st: { enabled: true, min: 8, mode: "auto" }, tool: "ab" };
const actionProc = { running: false, command: null };
const api = new Function("root", "actionProc", "with (root) { " + ["merged", "apply", "setSetting", "pump"].map(grab).join("\n") +
  "\n return { setSetting, pump } }")(root, actionProc);
const calls = [];
function finish() { calls.push(actionProc.command.slice(1).join(" ")); actionProc.running = false; api.pump() }
function fileSays(s) { root.st = s; root.local = {} }
api.setSetting("enabled", false); finish();
fileSays({ enabled: true, min: 8, mode: "auto" });       // `omarchy-auto-brightness on` elsewhere
api.setSetting("enabled", false); if (actionProc.running) finish();
for (const v of [10, 14, 19, 23]) api.setSetting("min", v);  // a drag while the first call runs
while (actionProc.running) finish();
console.log(JSON.stringify(calls));
"""
out = subprocess.run(["node", "-e", prog, os.path.join(here, "..", "Panel.qml")], capture_output=True, text=True, check=True).stdout
calls = __import__("json").loads(out)
print(calls)
assert calls[:2] == ["off", "off"], "the second off click reached the CLI"
assert calls[2:] == ["set min 10", "set min 23"], "drag: first value, then only the newest"
print("ok")
