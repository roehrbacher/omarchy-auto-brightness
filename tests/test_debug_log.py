"""2.16.6: by default the decision log has no per-reading lux or heartbeats,
only faults and state changes. With debug-log on, the detailed lines are
written. The size cap rotates either way."""
import json, os, tempfile
import loop_harness
import importlib.machinery, importlib.util

here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab_cli", p)
spec = importlib.util.spec_from_loader("ab_cli", loader)
ab_cli = importlib.util.module_from_spec(spec)
loader.exec_module(ab_cli)


def lines(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def events(rows):
    return [r["event"] for r in rows]


# CLI: debug-log on|off persists and prints
tmp = tempfile.mkdtemp(prefix="ab-dlog-cli-")
os.environ.update(HOME=tmp, XDG_CONFIG_HOME=tmp + "/config", XDG_RUNTIME_DIR=tmp + "/run",
                  XDG_STATE_HOME=tmp + "/state")
# reload paths... the already-imported ab_cli used env at import. Re-load after env:
loader = importlib.machinery.SourceFileLoader("ab_cli2", p)
spec = importlib.util.spec_from_loader("ab_cli2", loader)
cli = importlib.util.module_from_spec(spec)
loader.exec_module(cli)
import io, contextlib, sys
def run_cmd(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["omarchy-auto-brightness", *args])
    return rc, buf.getvalue().strip()

rc, out = run_cmd("debug-log")
assert rc == 0 and out == "off", (rc, out)
rc, out = run_cmd("debug-log", "on")
assert rc == 0 and out == "debug-log on", (rc, out)
rc, out = run_cmd("debug-log")
assert rc == 0 and out == "on", (rc, out)
conf = json.load(open(cli.CONF))
assert conf["debugLog"] is True
rc, out = run_cmd("debug-log", "off")
assert rc == 0 and out == "debug-log off"
assert json.load(open(cli.CONF))["debugLog"] is False
print("CLI: debug-log off, on, off")

# default: start, mode, no heartbeat, no lux, no raw fields; faults are kept
lp = loop_harness.Loop(lux=40, screen=500)
# 70 s idle so a debug log would have heartbeats; then an impossible value; then zeros
def boom(lp):
    lp.room(-1832673)
def zeros(lp):
    lp.room(0)
def back(lp):
    lp.room(40)
lp.run(90, {70: boom, 71: zeros, 86: back})
rows = lines(lp.ab.DLOG)
ev = events(rows)
print("default events:", ev)
assert ev[0] == "start" and ev[-1] == "stop", ev
assert any(e.startswith("mode ") for e in ev), ev
assert "heartbeat" not in ev, ev
assert not any(e.startswith("lux ") or e.startswith("fade ") or e.startswith("keyboard") for e in ev), ev
assert any("impossible" in e and "quarantined" in e for e in ev), ev
assert any("stuck at 0 lx" in e for e in ev), ev
assert any("0 lx ended after" in e for e in ev), ev
for r in rows:
    if r["event"] not in ("start", "stop"):
        assert "raw" not in r and "stable" not in r and "memKB" not in r, r
        assert "heartbeat" != r["event"]
print(f"default: {len(rows)} lines, no per-reading fields")

# debug on: heartbeats and lux lines, with raw
lp = loop_harness.Loop(lux=40, screen=500, conf={"debugLog": True})
lp.run(90, {20: lambda lp: lp.room(80)})
rows = lines(lp.ab.DLOG)
ev = events(rows)
print("debug events (sample):", ev[:8], "...", ev[-3:])
assert ev[0] == "start" and ev[-1] == "stop", ev
assert "heartbeat" in ev, ev
assert any(e.startswith("lux ") for e in ev), ev
assert any("raw" in r and r.get("event") == "heartbeat" for r in rows), rows
print(f"debug-on: {len(rows)} lines, heartbeats and lux present")

# size cap still rotates (debug writes and default writes)
d = tempfile.mkdtemp(prefix="ab-dlog-cap-")
for label, payload in (("debug", {"event": "lux 40.0 -> 41.0", "raw": 41.0, "stable": 41.0}),
                       ("default", {"event": "sensor stuck at 0 lx for 10s", "mode": "auto"})):
    path = os.path.join(d, label + ".jsonl")
    lg = lp.ab.DecisionLog(path, 2000)
    for i in range(100):
        lg.write(**payload)
    assert os.path.exists(path + ".1") and os.path.getsize(path) <= 2200, label
    json.loads(open(path).readline())
    print(f"size cap rotates ({label})")
print("ok")
