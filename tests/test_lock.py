"""2.6.1: the lock screen is not a hold. Only DPMS-off, walk-away, lid or off hold."""
import importlib.machinery, importlib.util, os, inspect
here = os.path.dirname(__file__)
p = os.path.join(here, "..", "bin", "omarchy-auto-brightness")
loader = importlib.machinery.SourceFileLoader("ab", p)
spec = importlib.util.spec_from_loader("ab", loader); ab = importlib.util.module_from_spec(spec); loader.exec_module(ab)
on, off = (lambda: True), (lambda: False)
# locked but lit: the daemon has no lock input at all, so it keeps adjusting
assert ab.hold_reason(True, False, False, off, True) == "auto"
assert ab.hold_reason(True, False, False, on, True) == "screen off"   # lock screen blanked
assert ab.hold_reason(True, False, True, off, True) == "walk-away dim"
assert ab.hold_reason(True, True, False, off, True) == "lid closed"
assert ab.hold_reason(False, False, False, off, True) == "off"
assert not hasattr(ab, "locked"), "no lock check left"
assert "isLocked" not in inspect.getsource(ab)
print("lock screen: keeps adjusting (holds only when DPMS-off, walk-away, lid closed or off)")
