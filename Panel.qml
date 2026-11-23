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
  // 2.11.0: the daemon rewrites this file on every loop pass (twice a
  // second, 60 times while fading). Reading it directly instead of spawning
  // `omarchy-auto-brightness status` every 1.5 s gets changes on screen
  // within ~0.25 s while the popup is open.
  readonly property string stateFile: (Quickshell.env("XDG_RUNTIME_DIR") || "/tmp") + "/omarchy-auto-brightness.json"
  property var st: ({ enabled: false, min: 8, max: 100, keyboard: true, mode: "not running" })
  property bool dragging: false
  // Settings and the keyboard level the last action wrote win over the state
  // file until the daemon has written its next pass (at most 0.5 s later).
  property var pending: ({})
  property real pendingUntil: 0
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.4)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property bool hasKeyboard: st.kbdMax !== undefined && st.kbdMax > 0

  function apply(text, fromAction) {
    var s
    try { s = JSON.parse(text) } catch (e) { return }
    if (fromAction) {
      pending = { enabled: s.enabled, min: s.min, max: s.max, keyboard: s.keyboard }
      if (s.kbdLevel !== undefined) pending.kbdLevel = s.kbdLevel
      pendingUntil = Date.now() + 1500
    } else if (Date.now() < pendingUntil) {
      for (var k in pending) {
        if (s[k] !== pending[k]) s[k] = pending[k]
      }
    }
    st = s
  }
  function run(args) {
    if (actionProc.running) return
    actionProc.command = [tool].concat(args)
    actionProc.running = true
  }
  function refresh() {
    if (dragging || actionProc.running) return
    stateView.reload()
  }
  function luxText() {
    return st.lux === null || st.lux === undefined ? "" : " · " + Math.round(st.lux) + " lx"
  }
  function statusLine() {
    var m = st.mode || ""
    var lux = luxText()
    if (m === "auto" && !st.offset) return "Following the light sensor" + lux + " · screen " + st.screen + "%"
    if (m === "auto" && st.offset) return "Following the light sensor" + lux + " · your offset " + (st.offset > 0 ? "+" : "") + st.offset + "%"
    if (m === "walk-away dim") return "Held by the walk-away lock" + lux
    if (m === "off") return "Off" + lux
    if (m === "not running") return "Service not running"
    return "Waiting (" + m + ")" + lux
  }
  // Short form for the hero's caps meta line.
  function heroMeta() {
    var m = st.mode || ""
    if (m === "auto") return "Following the light" + luxText()
    if (m === "walk-away dim") return "Held by walk-away" + luxText()
    if (m === "off") return "Turned off" + luxText()
    if (m === "not running") return "Service not running"
    return "Waiting · " + m
  }

  // The state file only exists while the daemon has run this session; when
  // it is missing, ask the CLI (it also reads the saved settings).
  FileView {
    id: stateView
    path: root.stateFile
    blockLoading: true
    printErrors: false
    onLoaded: root.apply(text(), false)
    onLoadFailed: if (!statusProc.running) statusProc.running = true
  }
  Process { id: statusProc; command: [root.tool, "status"]; stdout: StdioCollector { onStreamFinished: root.apply(text, false) } }
  Process { id: actionProc; stdout: StdioCollector { onStreamFinished: root.apply(text, true) } }
  Timer {
    // Open: a small file read every 0.25 s. Closed: every 10 s for the bar
    // icon and its tooltip, no process spawned.
    interval: root.opened ? 250 : 10000; running: true; repeat: true; triggeredOnStart: true
    onTriggered: root.refresh()
  }
  onOpenedChanged: if (opened) refresh()

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    bar: root.bar
    text: "󰃡"
    tooltipText: "Auto brightness " + (root.st.enabled ? "on" : "off") + "\n" + root.statusLine() + "\nRight-click: on/off"
    foreground: root.st.enabled ? (root.bar ? root.bar.barForeground : Color.foreground) : root.dim
    onPressed: function(b) {
      if (b === Qt.RightButton) root.run([root.st.enabled ? "off" : "on"])
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
      onActivateRequested: root.run([root.st.enabled ? "off" : "on"])

      Column {
        id: column
        objectName: "abColumn"
        anchors.fill: parent
        spacing: Style.space(14)

        PanelHero {
          id: hero
          objectName: "abHero"
          title: "Auto Brightness"
          meta: root.heroMeta()
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
              busy: actionProc.running
              foreground: root.foreground
              onToggled: root.run([root.st.enabled ? "off" : "on"])

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
              textFormat: Text.PlainText
              visible: root.st.screen !== undefined
              text: "NOW " + root.st.screen + "%"
              color: root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
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
              Text { anchors.right: parent.right; textFormat: Text.PlainText; text: root.st.min + "%"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.body }
            }
            PanelSlider {
              objectName: "abMinSlider"
              width: parent.width; bar: root.bar
              minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.min
              onDraggingChanged: root.dragging = dragging
              onReleased: function(v) { root.run(["set", "min", String(Math.min(v, root.st.max))]) }
            }
          }

          Column {
            width: parent.width
            spacing: Style.space(6)
            Item {
              width: parent.width
              implicitHeight: maxLabel.implicitHeight
              Text { id: maxLabel; textFormat: Text.PlainText; text: "Maximum"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
              Text { anchors.right: parent.right; textFormat: Text.PlainText; text: root.st.max + "%"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.body }
            }
            PanelSlider {
              width: parent.width; bar: root.bar
              minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.max
              onDraggingChanged: root.dragging = dragging
              onReleased: function(v) { root.run(["set", "max", String(Math.max(v, root.st.min))]) }
            }
          }

          Text {
            objectName: "abOffset"
            visible: root.st.mode === "auto" && !!root.st.offset
            width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: "Your brightness keys moved the curve " + (root.st.offset > 0 ? "+" : "") + root.st.offset + "%."
            color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
          }
        }

        PanelSeparator { visible: root.hasKeyboard; foreground: root.foreground }

        // ---------- Keyboard light ----------
        Column {
          objectName: "abKeyboard"
          visible: root.hasKeyboard
          width: parent.width
          spacing: Style.space(10)

          PanelSectionHeader {
            objectName: "abKbdHeader"
            text: "KEYBOARD LIGHT (MANUAL)"
            foreground: root.foreground
            fontFamily: root.fontFamily
          }

          ButtonGroup {
            id: levels
            objectName: "abKbdLevels"
            focusable: false
            options: root.st.kbdMax >= 2 ? [{ value: "0", label: "Off" }, { value: "1", label: "1" }, { value: "2", label: "2" }]
                                         : [{ value: "0", label: "Off" }, { value: "1", label: "On" }]
            value: root.st.kbdLevel === undefined ? "" : String(root.st.kbdLevel)
            foreground: root.foreground
            fontFamily: root.fontFamily
            onChanged: function(v) { root.run(["kbd-level", v]) }
          }

          Text {
            objectName: "abKbdHelp"
            width: parent.width; wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            text: !root.st.enabled
              ? "Sets the light now. Auto Brightness is off, so only you and the keyboard's own idle timeout change it."
              : root.st.keyboard
                ? "Sets the light now. Auto still changes it when the room gets dark or bright enough for another level, the screen comes back on, the lid opens or the laptop wakes."
                : "Sets the light now. With Auto in the dark off, only you and the keyboard's own idle timeout change it."
            color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
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
              text: "Auto in the dark"
              elide: Text.ElideRight
              color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body
            }
            ToggleSwitch {
              id: kbdSw
              objectName: "abKbdAuto"
              anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
              checked: !!root.st.keyboard; busy: actionProc.running; foreground: root.foreground
              onToggled: root.run(["set", "keyboard", root.st.keyboard ? "off" : "on"])
            }
          }
        }
      }
    }
  }
}
