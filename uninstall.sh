#!/usr/bin/env bash
# Removes the service, the script and the plugin copy. Keeps your settings file
# (~/.config/omarchy/auto-brightness.json); delete it by hand if you want.
set -uo pipefail
systemctl --user disable --now omarchy-auto-brightness.service 2>/dev/null
rm -f "$HOME/.config/systemd/user/omarchy-auto-brightness.service" "$HOME/.local/bin/omarchy-auto-brightness"
P="$HOME/.config/omarchy/plugins/timon.auto-brightness"
[[ -L $P || -f $P/manifest.json ]] && rm -rf "$P"
systemctl --user daemon-reload
echo "Removed. Also drop \"timon.auto-brightness\" from your bar config if you added it."
