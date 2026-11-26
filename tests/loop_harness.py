"""Shared fake-sysfs harness for tests that run the real daemon loop (2.16.0).
Fresh temp dir and module per call; fake clock; D-Bus, hyprctl and systemd
stubbed. Nothing touches the real machine."""
import atexit, contextlib, importlib.machinery, importlib.util, io, os, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load(tmp, stub=True):
    os.environ.update(HOME=tmp, XDG_CONFIG_HOME=tmp + "/config", XDG_RUNTIME_DIR=tmp + "/run", XDG_STATE_HOME=tmp + "/state")
    p = os.environ.get("AB_DAEMON") or os.path.join(HERE, "..", "bin", "omarchy-auto-brightness")
    loader = importlib.machinery.SourceFileLoader("ab", p)
    spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
    ab.READER_THREAD = False
    if stub:
        ab.replace_upstream = lambda keyboard: []
    return ab


class Loop:
    """events: {seconds: fn(loop)}. Records screen/keyboard writes, sensor
    reads and states with times in seconds since the start."""

    def __init__(self, lux=300, screen=500, kbd=0, conf=None):
        self.tmp = tempfile.mkdtemp(prefix="ab-loop-")
        atexit.register(shutil.rmtree, self.tmp, True)
        os.makedirs(self.tmp + "/run")
        self.ab = ab = load(self.tmp)
        self.t0, self.clock = 1000.0, 1000.0
        self.bl, self.kb = self.dev("intel_backlight", 1000, screen), self.dev("dell::kbd_backlight", 2, kbd)
        self.s = [self.tmp + "/als0"]
        self.room(lux)
        self.off = False
        self.writes, self.reads, self.states, self.sleeps = [], [], [], []
        if conf:
            import json
            os.makedirs(os.path.dirname(ab.CONF), exist_ok=True)
            json.dump(conf, open(ab.CONF, "w"))
        loop = self
        def dev_set(dev, raw):
            loop.writes.append((dev.name, int(raw), loop.now()))
            open(dev.path + "/brightness", "w").write(f"{int(raw)}\n")
        ab.sensor = lambda: (self.s[0], 1.0)
        ab.find_dev = lambda cls, pat: self.bl if cls == "backlight" else self.kb
        ab.Dev.set = dev_set
        ab.lid_closed = lambda: False
        ab.screen_off = lambda: loop.off
        ab.fullscreen_video = lambda: False
        real_raw = ab.lux_raw
        ab.lux_raw = lambda sens: (loop.reads.append(loop.now()), real_raw(sens))[1]
        real_ws = ab.write_state
        ab.write_state = lambda d: (loop.states.append((loop.now(), d)), real_ws(d))

    def dev(self, name, maxv, cur):
        d = os.path.join(self.tmp, "sys", name); os.makedirs(d)
        open(d + "/max_brightness", "w").write(f"{maxv}\n"); open(d + "/brightness", "w").write(f"{cur}\n")
        return d

    def now(self):
        return round(self.clock - self.t0, 4)

    def room(self, lux):
        for f in self.s:
            open(f, "w").write(f"{lux}\n")

    def level(self, path=None):
        return int(open((path or self.kb) + "/brightness").read())

    def set_level(self, path, v):
        open(path + "/brightness", "w").write(f"{int(v)}\n")

    def run(self, until, events=None):
        ab, events = self.ab, dict(events or {})
        def sleep(dt):
            before = self.clock; self.clock += dt
            self.sleeps.append((round(before - self.t0, 4), dt))
            for at in sorted(events):
                if before < self.t0 + at <= self.clock:
                    events[at](self)
            if self.clock - self.t0 > until:
                raise KeyboardInterrupt
        real = ab.time.sleep, ab.time.monotonic, ab.time.time  # the time module is shared
        ab.time.sleep = sleep
        ab.time.monotonic = lambda: self.clock
        ab.time.time = lambda: self.clock + 1e9
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                ab.run()
            except KeyboardInterrupt:
                pass
            finally:
                ab.time.sleep, ab.time.monotonic, ab.time.time = real
        return self

    def kbd_writes(self):
        return [(v, t) for n, v, t in self.writes if n == "dell::kbd_backlight"]

    def screen_writes(self):
        return [(v, t) for n, v, t in self.writes if n == "intel_backlight"]

    def screen(self):
        return int(open(self.bl + "/brightness").read())

    def log(self):
        import json
        return [json.loads(l) for l in open(self.ab.DLOG)]
