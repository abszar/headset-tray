#!/bin/sh
set -eu

# Removes Headset Tray. Leaves HeadsetControl, its udev rule and the saved
# settings in place; remove those by hand if wanted.

user_data_root=${XDG_DATA_HOME:-"$HOME/.local/share"}
user_config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
app_id=io.github.abdelali.HeadsetTray

systemctl --user stop headset-tray.service >/dev/null 2>&1 || true
rm -f "$user_config_root/autostart/headset-tray.desktop"
rm -f "$user_config_root/systemd/user/headset-tray.service"
rm -f "$user_data_root/applications/$app_id.desktop"
rm -f "$HOME/.local/bin/headset-tray"
rm -rf "$user_data_root/headset-tray"
update-desktop-database "$user_data_root/applications" >/dev/null 2>&1 || true
systemctl --user daemon-reload
