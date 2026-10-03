#!/bin/sh
set -eu

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
user_data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
user_config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
app_install_root="$user_data_root/headset-tray"
app_id=io.github.abdelali.HeadsetTray

install -d "$app_install_root/headset_tray" "$HOME/.local/bin"
install -d "$user_data_root/applications"
install -d "$user_config_root/autostart" "$user_config_root/systemd/user"

# Replace the package wholesale, so no module from an older revision lingers.
rm -rf "$app_install_root/headset_tray"
install -d "$app_install_root/headset_tray"
for app_source in "$project_root"/headset_tray/*.py; do
    install -m 0644 "$app_source" "$app_install_root/headset_tray/"
done

install -m 0755 "$project_root/data/headset-tray-launcher" \
    "$HOME/.local/bin/headset-tray"
# The launcher file is named after the application id so that GNOME
# attributes the low-battery notification to it.
install -m 0644 "$project_root/data/headset-tray.desktop" \
    "$user_data_root/applications/$app_id.desktop"
install -m 0644 "$project_root/data/headset-tray-autostart.desktop" \
    "$user_config_root/autostart/headset-tray.desktop"
install -m 0644 "$project_root/data/headset-tray.service" \
    "$user_config_root/systemd/user/headset-tray.service"

update-desktop-database "$user_data_root/applications" >/dev/null 2>&1 || true
systemctl --user daemon-reload
timeout 60 systemctl --user restart headset-tray.service

if ! command -v headsetcontrol >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/headsetcontrol" ]; then
    echo "Headset Tray is installed, but HeadsetControl is not:" >&2
    echo "run scripts/build-headsetcontrol.sh, then scripts/install-udev-rule.sh." >&2
fi
