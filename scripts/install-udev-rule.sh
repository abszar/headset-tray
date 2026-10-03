#!/bin/sh
set -eu

# Installs HeadsetControl's udev rules so that the headset dongle can be
# used without root. Run once, after scripts/build-headsetcontrol.sh; asks
# for the sudo password.

program=$(command -v headsetcontrol || echo "$HOME/.local/bin/headsetcontrol")
if [ ! -x "$program" ]; then
    echo "HeadsetControl not found: run scripts/build-headsetcontrol.sh first." >&2
    exit 1
fi

rules=$(mktemp)
trap 'rm -f "$rules"' EXIT
"$program" -u >"$rules" 2>/dev/null

sudo install -m 0644 "$rules" /etc/udev/rules.d/70-headsets.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "udev rules installed. If the headset still is not found, unplug and"
echo "replug its USB dongle."
