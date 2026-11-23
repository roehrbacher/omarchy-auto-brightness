import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Auto Brightness bar control. The work is done by the user service
// omarchy-auto-brightness; this shows its state and edits the settings.
// Layout follows the stock Bluetooth popup: PanelHero with the on/off
// switch, PanelSeparator, sections with PanelSectionHeader, 14 px apart.
Panel {
  id: root
  moduleName: "timon.auto-brightness"
  ipcTarget: "timon.auto-brightness"

  readonly property string tool: Quickshell.env("HOME") + "/.local/bin/omarchy-auto-brightness"
  readonly property string runDir: Quickshell.env("XDG_RUNTIME_DIR") || "/tmp"
  // The daemon rewrites the state file on every pass. While the popup is
  // open it is re-read on each change (inotify), and the popup touches the
  // watch file every second so the daemon samples at 10 Hz instead of 2 Hz.
  readonly property string stateFile: runDir + "/omarchy-auto-brightness.json"
  readonly property string watchFile: runDir + "/omarchy-auto-brightness.watch"
  property var st: ({ enabled: false, min: 8, max: 100, keyboard: true, mode: "not running" })
  property bool stateMissing: false

  // Settings the user just changed, shown at once. They win over every read
  // until the state file reports the same value (or 3 s pass with nothing in
  // flight), so a read never pulls a slider back mid-drag or after release.
  property var local: ({})
  property real localUntil: 0
  property var wanted: ({})
  property var sent: ({})

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.4)
  readonly property string fontFamily: Style.font.menuFamily
  readonly property bool hasKeyboard: st.kbdMax !== undefined && st.kbdMax > 0

  function merged(s) {
    var out = {}
    for (var k in s) out[k] = s[k]
    for (var l in local) out[l] = local[l]
    return out
  }
  function apply(text, fromFile) {
    var s
    try { s = JSON.parse(text) } catch (e) { return }
    if (fromFile) {
      var left = {}
      var keep = Date.now() < localUntil || actionProc.running
      for (var k in local) if (s[k] !== local[k] && keep) left[k] = local[k]
      local = left
    }
    st = merged(s)
  }
  function setSetting(key, value) {
    var l = {}
    for (var k in local) l[k] = local[k]
    l[key] = value
    local = l
    localUntil = Date.now() + 3000
    st = merged(st)
    wanted[key] = value
    pump()
  }
  // One CLI call at a time, always with the newest value: during a drag
  // that is a write about every 60 ms, as fast as the CLI starts.
  function pump() {
    if (actionProc.running) return
    for (var k in wanted) {
      var v = wanted[k]
      if (sent[k] === v) continue
      sent[k] = v
      if (k === "enabled") actionProc.command = [tool, v ? "on" : "off"]
      else if (k === "keyboard") actionProc.command = [tool, "set", "keyboard", v ? "on" : "off"]
      else actionProc.command = [tool, "set", k, String(v)]
      actionProc.running = true
      return
    }
  }
  function toggleEnabled() { setSetting("enabled", !st.enabled) }

  function luxValue() {
    var l = st.luxNow !== undefined && st.luxNow !== null ? st.luxNow : st.lux
    if (l === undefined || l === null) return null
    return l < 10 ? Math.round(l * 10) / 10 : Math.round(l)
  }
  function luxText() {
    var l = luxValue()
    return l === null ? "" : " · " + l + " lx"
  }
  function statusLine() {
    var m = st.mode || ""
    if (m === "not running") return "Service not running"
    if (m === "off" || !st.enabled) return "Off" + luxText()
    if (m === "auto") return "Following the light sensor" + luxText() + " · screen " + st.screen + "%"
    if (m === "walk-away dim") return "Held by the walk-away lock" + luxText()
    return "Paused (" + m + ")" + luxText()
  }

  // Hero status line. Like stock Bluetooth/Tailscale: one fixed line for a
  // special state, otherwise a few lines that cycle every 2.8 s with a fade.
  readonly property var heroLines: {
    var s = st, m = s.mode || ""
    if (m === "not running") return ["Service not running"]
    if (!s.enabled || m === "off") return ["Turned off"]
    if (m === "lid closed") return ["Paused · lid closed"]
    if (m === "walk-away dim") return ["Held by walk-away"]
    if (m === "screen off") return ["Paused · screen off"]
    if (m === "no reading") return ["Waiting for the sensor"]
    if (m !== "auto") return ["Paused · " + m]
    if (s.waking) return ["Awake · matching the room"]
    if (s.fadeTo !== undefined && s.fadeTo !== null && s.fadeTo !== s.screen)
      return [(s.fadeTo < s.screen ? "Dimming to " : "Brightening to ") + s.fadeTo + "%"]
    if (s.videoHold) return ["Holding for video"]
    if (s.glitch) return ["Ignoring a sensor glitch"]
    var lines = ["Following the light" + luxText()]
    lines.push(s.offset ? "Your " + (s.offset > 0 ? "+" : "") + s.offset + "% held" : "Screen at " + s.screen + "%")
    if (s.keyboard && s.kbdLevel > 0)
      lines.push((s.dark ? "Dark room · " : "") + "Keyboard light " + (s.kbdMax > 1 ? s.kbdLevel : "on"))
    lines.push("Reading the room")
    return lines
  }
  property int phraseIndex: 0
  readonly property bool rotatingPhrases: heroLines.length > 1
  readonly property string heroMeta: heroLines[phraseIndex % heroLines.length]
  Timer {
    id: phraseTimer
    interval: 2800
    running: root.opened && root.rotatingPhrases
    repeat: true
    onTriggered: phraseSwap.restart()
  }
  SequentialAnimation {
    id: phraseSwap
    PropertyAnimation { target: hero; property: "metaOpacity"; to: 0.0; duration: Style.duration(180); easing.type: Easing.OutQuad }
    ScriptAction { script: root.phraseIndex = (root.phraseIndex + 1) % Math.max(1, root.heroLines.length) }
    PropertyAnimation { target: hero; property: "metaOpacity"; to: 1.0; duration: Style.duration(260); easing.type: Easing.InQuad }
  }
  onRotatingPhrasesChanged: if (!rotatingPhrases) { phraseSwap.stop(); phraseIndex = 0; hero.metaOpacity = 1.0 }

  FileView {
    id: stateView
    path: root.stateFile
    blockLoading: true
    printErrors: false
    watchChanges: root.opened
    onFileChanged: reload()
    onLoaded: { root.stateMissing = false; root.apply(text(), true) }
    onLoadFailed: root.stateMissing = true
  }
  // Only when the state file is missing (service never ran this session):
  // the CLI also reads the saved settings. Once on load and on each open.
  Process { id: statusProc; command: [root.tool, "status"]; stdout: StdioCollector { onStreamFinished: root.apply(text, false) } }
  Process {
    id: actionProc
    stdout: StdioCollector { onStreamFinished: root.apply(text, false) }
    onExited: root.pump()
  }
  FileView { id: watchView; path: root.watchFile; printErrors: false }
  Timer {
    interval: 1000; running: root.opened; repeat: true; triggeredOnStart: true
    onTriggered: watchView.setText(String(Date.now()))
  }
  Timer {
    // Closed: the bar tooltip's state, a file read every 10 s. Open: retry
    // the file once a second only while it is missing.
    interval: root.opened ? 1000 : 10000; running: true; repeat: true
    onTriggered: if (!root.opened || root.stateMissing) stateView.reload()
  }
  function refreshOnOpen() {
    stateView.reload()
    if (stateMissing && !statusProc.running) statusProc.running = true
  }
  onOpenedChanged: if (opened) refreshOnOpen()
  Component.onCompleted: if (stateMissing) statusProc.running = true

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    bar: root.bar
    text: "󰃡"
    tooltipText: "Auto brightness " + (root.st.enabled ? "on" : "off") + "\n" + root.statusLine() + "\nRight-click: on/off"
    foreground: root.st.enabled ? (root.bar ? root.bar.barForeground : Color.foreground) : root.dim
    onPressed: function(b) {
      if (b === Qt.RightButton) root.toggleEnabled()
      else root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(380))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onActivateRequested: root.toggleEnabled()

      Column {
        id: column
        objectName: "abColumn"
        anchors.fill: parent
        spacing: Style.space(14)

        PanelHero {
          id: hero
          objectName: "abHero"
          title: "Auto Brightness"
          meta: root.heroMeta
          foreground: root.foreground
          fontFamily: root.fontFamily
          iconOpacity: root.st.enabled ? 1.0 : 0.5
          iconComponent: Component {
            Text {
              objectName: "abHeroIcon"
              textFormat: Text.PlainText
              text: "󰃡"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.display
            }
          }
          trailingControl: Component {
            ToggleSwitch {
              id: powerSwitch
              objectName: "abPower"
              checked: !!root.st.enabled
              foreground: root.foreground
              onToggled: root.toggleEnabled()

              PanelToolTip {
                visible: powerSwitch.containsMouse
                text: root.st.enabled ? "Turn auto brightness off" : "Turn auto brightness on"
                fontFamily: root.fontFamily
              }
            }
          }
        }

        PanelSeparator { objectName: "abRule1"; foreground: root.foreground }

        // ---------- Screen: min and max of the curve ----------
        Column {
          objectName: "abScreen"
          width: parent.width
          spacing: Style.space(10)

          Item {
            width: parent.width
            implicitHeight: Math.max(screenHeader.implicitHeight, screenNow.implicitHeight)
            PanelSectionHeader {
              id: screenHeader
              objectName: "abScreenHeader"
              text: "SCREEN"
              foreground: root.foreground
              fontFamily: root.fontFamily
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
            }
            Text {
              id: screenNow
              objectName: "abScreenNow"
              textFormat: Text.PlainText
              visible: root.st.screen !== undefined
              text: "NOW " + root.st.screen + "%"
              color: root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              font.bold: true
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)
            Item {
              width: parent.width
              implicitHeight: minLabel.implicitHeight
              Text { id: minLabel; objectName: "abMinLabel"; textFormat: Text.PlainText; text: "Minimum"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
              Text { objectName: "abMinValue"; anchors.right: parent.right; textFormat: Text.PlainText; text: root.st.min + "%"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.body }
            }
            PanelSlider {
              objectName: "abMinSlider"
              width: parent.width; bar: root.bar
              minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.min
              onMoved: function(v) { root.setSetting("min", Math.min(v, root.st.max)) }
              onReleased: function(v) { root.setSetting("min", Math.min(v, root.st.max)) }
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)
            Item {
              width: parent.width
              implicitHeight: maxLabel.implicitHeight
              Text { id: maxLabel; textFormat: Text.PlainText; text: "Maximum"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
              Text { objectName: "abMaxValue"; anchors.right: parent.right; textFormat: Text.PlainText; text: root.st.max + "%"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.body }
            }
            PanelSlider {
              objectName: "abMaxSlider"
              width: parent.width; bar: root.bar
              minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.max
              onMoved: function(v) { root.setSetting("max", Math.max(v, root.st.min)) }
              onReleased: function(v) { root.setSetting("max", Math.max(v, root.st.min)) }
            }
          }
        }

        PanelSeparator { visible: root.hasKeyboard; foreground: root.foreground }

        // ---------- Keyboard light: does auto drive it ----------
        Column {
          objectName: "abKeyboard"
          visible: root.hasKeyboard
          width: parent.width
          spacing: Style.space(10)

          PanelSectionHeader {
            objectName: "abKbdHeader"
            text: "KEYBOARD LIGHT"
            foreground: root.foreground
            fontFamily: root.fontFamily
          }

          Item {
            width: parent.width
            implicitHeight: Math.max(kbdLabel.implicitHeight, kbdSw.implicitHeight)
            Text {
              id: kbdLabel
              objectName: "abKbdAutoLabel"
              textFormat: Text.PlainText
              anchors.left: parent.left; anchors.right: kbdSw.left; anchors.rightMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              text: "Follow the room light"
              elide: Text.ElideRight
              color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body
            }
            ToggleSwitch {
              id: kbdSw
              objectName: "abKbdAuto"
              anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
              checked: !!root.st.keyboard; foreground: root.foreground
              onToggled: root.setSetting("keyboard", !root.st.keyboard)
            }
          }

          Text {
            objectName: "abKbdHelp"
            width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: "On: the light comes on about 15 s after the room goes dark" + (root.st.kbdMax > 1 ? " (level 2 when very dark)" : "")
              + ", goes off when it gets bright, and is set to match the room when the screen comes back on, the lid opens or the laptop wakes."
              + " Your keyboard key still works; auto keeps your level until the room changes enough for another level."
              + " Off: auto leaves the keyboard light alone."
            color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
          }
        }
      }
    }
  }
}
