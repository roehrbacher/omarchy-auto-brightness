.pragma library

// Status line under the popup title (2.13.0). `s` is the daemon's state
// file, `hour` the local hour. One line = a fixed special state; more =
// they cycle. Only facts the user cares about, never filter internals.

function luxLabel(s) {
  var l = s.luxNow !== undefined && s.luxNow !== null ? s.luxNow : s.lux
  if (l === undefined || l === null) return ""
  return (l < 10 ? Math.round(l * 10) / 10 : Math.round(l)) + " lx"
}

function lines(s, hour) {
  var m = s.mode || ""
  if (m === "not running") return ["Service not running"]
  if (!s.enabled || m === "off") return ["Turned off"]
  if (m === "lid closed") return ["Paused · lid closed"]
  // Holds that are internal (walk-away flag, blanked screen, no reading
  // yet) show plain facts that stay true while held, no explanation.
  if (m !== "auto") {
    var held = []
    if (luxLabel(s)) held.push("Room at " + luxLabel(s))
    if (s.screen !== undefined && s.screen !== null) held.push("Screen at " + s.screen + "%")
    return held.length ? held : ["Reading the room"]
  }
  if (s.waking) return [s.dark ? "Woke up in the dark · going easy" : "Awake · matching the room"]
  if (s.fadeTo !== undefined && s.fadeTo !== null && s.fadeTo !== s.screen)
    return [(s.fadeTo < s.screen ? "Dimming to " : "Brightening to ") + s.fadeTo + "%"]
  if (s.videoHold) return ["Holding for video"]
  if (s.min >= s.max && !s.offset) {
    if (s.max >= 100) return ["Always full blast"]
    if (s.max <= 1) return ["Max 1% · vampire mode"]
    return ["Locked at " + s.max + "% · sensor on a break"]
  }
  var lux = s.luxNow !== undefined && s.luxNow !== null ? s.luxNow : s.lux
  var out = ["Following the light" + (luxLabel(s) ? " · " + luxLabel(s) : "")]
  if (s.offset > 0 && s.target >= 100) out.push("Your keys maxed it out")
  else if (s.offset < 0 && s.target <= 1) out.push("Your keys dimmed it all the way")
  else if (s.offset) out.push("Your " + (s.offset > 0 ? "+" : "") + s.offset + "% held")
  else out.push("Screen at " + s.screen + "%")
  if (s.keyboard && s.kbdLevel > 0)
    out.push((s.lowBattery ? "Low battery · " : s.dark ? "Dark room · " : "") + "Keyboard backlight " + (s.kbdMax > 1 ? s.kbdLevel : "on"))
  else if (!s.keyboard && s.dark && s.kbdMax > 0)
    out.push("Dark in here · keyboard is yours")
  if (lux !== null && lux !== undefined && lux >= 20000) out.push("Direct sunlight · shades on")
  else if (lux !== null && lux !== undefined && lux < 1) out.push(hour >= 22 || hour < 6 ? "Pitch black · night owl hours" : "Pitch black in here")
  else out.push("Reading the room")
  return out
}
