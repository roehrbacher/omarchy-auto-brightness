#!/usr/bin/env bash
# Installs the service (and the bar plugin if this checkout is not already it).
# No sudo. Does not touch shell.json: add "timon.auto-brightness" to the bar yourself
# (or via your config repo). ./install.sh --no-start installs without starting.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -Dm755 "$ROOT/bin/omarchy-auto-brightness" "$HOME/.local/bin/omarchy-auto-brightness"
install -Dm644 "$ROOT/systemd/omarchy-auto-brightness.service" "$HOME/.config/systemd/user/omarchy-auto-brightness.service"
P="$HOME/.config/omarchy/plugins/timon.auto-brightness"
if [[ $(readlink -f "$ROOT") != $(readlink -f "$P" 2>/dev/null || true) ]]; then
  mkdir -p "$P" && cp "$ROOT"/{manifest.json,Panel.qml,HeroLines.js,LICENSE,README.md,CHANGELOG.md} "$P/"
fi
command -v brightnessctl >/dev/null || echo "brightnessctl is missing (pacman -S brightnessctl)" >&2
systemctl --user daemon-reload
[[ ${1:-} == --no-start ]] || systemctl --user enable --now omarchy-auto-brightness.service
echo "Installed. Status: omarchy-auto-brightness status   Undo: $ROOT/uninstall.sh"
