import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Auto Brightness bar control. The work is done by the user service
// omarchy-auto-brightness; this only shows its state and edits the settings.
Panel {
  id: root
  moduleName: "timon.auto-brightness"
  ipcTarget: "timon.auto-brightness"

  readonly property string tool: Quickshell.env("HOME") + "/.local/bin/omarchy-auto-brightness"
  property var st: ({ enabled: false, min: 8, max: 100, keyboard: true, mode: "not running" })
  property bool dragging: false
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.45)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family

  function apply(text) { try { st = JSON.parse(text) } catch (e) {} }
  function run(args) {
    if (actionProc.running) return
    actionProc.command = [tool].concat(args)
    actionProc.running = true
  }
  function statusLine() {
    var m = st.mode || ""
    var lux = st.lux === null || st.lux === undefined ? "" : " · " + Math.round(st.lux) + " lx"
    if (m === "auto") return "Following the light sensor" + lux + " · screen " + st.screen + "%"
    if (m === "manual pause") return "Paused after your change (" + Math.ceil(st.pausedFor / 60) + " min left)" + lux
    if (m === "off") return "Off" + lux
    if (m === "not running") return "Service not running"
    return "Waiting (" + m + ")" + lux
  }

  Process { id: statusProc; command: [root.tool, "status"]; stdout: StdioCollector { onStreamFinished: root.apply(text) } }
  Process { id: actionProc; stdout: StdioCollector { onStreamFinished: root.apply(text) } }
  Timer {
    interval: root.opened ? 1500 : 10000; running: true; repeat: true; triggeredOnStart: true
    onTriggered: if (!statusProc.running && !actionProc.running && !root.dragging) statusProc.running = true
  }

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
    contentWidth: Style.space(300)
    contentHeight: panel.fittedContentHeight(column.implicitHeight, Style.space(360))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onActivateRequested: root.run([root.st.enabled ? "off" : "on"])

      Column {
        id: column
        width: parent.width
        spacing: Style.space(8)

        Item {
          width: parent.width
          height: Math.max(title.implicitHeight, sw.implicitHeight)
          Text {
            id: title
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            text: "Auto brightness"
            color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.heading
          }
          ToggleSwitch {
            id: sw
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            checked: root.st.enabled; busy: actionProc.running; foreground: root.foreground
            onToggled: root.run([root.st.enabled ? "off" : "on"])
          }
        }

        Text {
          width: parent.width; wrapMode: Text.WordWrap
          text: root.statusLine()
          color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.caption
        }

        Text { text: "Minimum " + root.st.min + "%"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
        PanelSlider {
          width: parent.width; bar: root.bar
          minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.min
          onDraggingChanged: root.dragging = dragging
          onReleased: function(v) { root.run(["set", "min", String(Math.min(v, root.st.max))]) }
        }

        Text { text: "Maximum " + root.st.max + "%"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
        PanelSlider {
          width: parent.width; bar: root.bar
          minimum: 1; maximum: 100; step: 1; integer: true; value: root.st.max
          onDraggingChanged: root.dragging = dragging
          onReleased: function(v) { root.run(["set", "max", String(Math.max(v, root.st.min))]) }
        }

        Item {
          width: parent.width
          height: Math.max(kbdLabel.implicitHeight, kbdSw.implicitHeight)
          Text {
            id: kbdLabel
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            text: "Keyboard light in the dark"
            color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body
          }
          ToggleSwitch {
            id: kbdSw
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            checked: root.st.keyboard; busy: actionProc.running; foreground: root.foreground
            onToggled: root.run(["set", "keyboard", root.st.keyboard ? "off" : "on"])
          }
        }
      }
    }
  }
}
