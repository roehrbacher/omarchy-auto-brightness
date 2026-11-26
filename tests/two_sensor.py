"""2.16.4: the daemon reads one light sensor. The glitch replays rebuild what
both sensors read (the log was written by two-sensor versions) and feed the
filter sensor0's column, the plain light sensor. With AB_DAEMON set to an
older (two-sensor) copy they feed both columns, to see the old dims again."""
import os

OLD = bool(os.environ.get("AB_DAEMON"))


def make_filter(ab, c):
    return ab.SensorFilter(2, c["sensorMedianSeconds"], c) if OLD else ab.SensorFilter(c["sensorMedianSeconds"], c)


def feed(filt, t, v):
    return filt.feed(t, v if OLD else v[0])
