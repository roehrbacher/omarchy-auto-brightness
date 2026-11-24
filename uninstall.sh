#!/usr/bin/env bash
# Removes the service, the script and the plugin copy. Keeps your settings file
# (~/.config/omarchy/auto-brightness.json); delete it by hand if you want.
set -uo pipefail
systemctl --user disable --now omarchy-auto-brightness.service 2>/dev/null
# 2.16.0: start the other auto-brightness services it stopped (and turn
# Omarchy's automatic keyboard backlight back on if it turned it off)
[[ -x $HOME/.local/bin/omarchy-auto-brightness ]] && "$HOME/.local/bin/omarchy-auto-brightness" restore-replaced
rm -f "$HOME/.config/systemd/user/omarchy-auto-brightness.service" "$HOME/.local/bin/omarchy-auto-brightness"
P="$HOME/.config/omarchy/plugins/timon.auto-brightness"
[[ -L $P || -f $P/manifest.json ]] && rm -rf "$P"
systemctl --user daemon-reload
echo "Removed. Also drop \"timon.auto-brightness\" from your bar config if you added it."
