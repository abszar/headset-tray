#!/bin/sh
set -eu

# Builds HeadsetControl (https://github.com/Sapd/HeadsetControl) from source
# and installs the program in ~/.local/bin. Needs, once:
#   sudo apt install build-essential git cmake libhidapi-dev
#
# The revision is pinned to the one Headset Tray was written against; set
# HEADSETCONTROL_REVISION to build another (a tag, branch or commit).

repository=https://github.com/Sapd/HeadsetControl.git
revision=${HEADSETCONTROL_REVISION:-d0da29a09729307ba78cc0dfe69a439b95f068fd}
cache_root=${XDG_CACHE_HOME:-"$HOME/.cache"}
source_dir="$cache_root/headset-tray/HeadsetControl"

if [ ! -d "$source_dir/.git" ]; then
    install -d "$cache_root/headset-tray"
    git clone --quiet "$repository" "$source_dir"
fi
git -C "$source_dir" fetch --quiet --tags origin
git -C "$source_dir" checkout --quiet --detach "$revision"

cmake -S "$source_dir" -B "$source_dir/build" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_UNIT_TESTS=OFF >/dev/null
cmake --build "$source_dir/build" --parallel

install -d "$HOME/.local/bin"
install -m 0755 "$source_dir/build/headsetcontrol" "$HOME/.local/bin/headsetcontrol"
echo "Installed $("$HOME/.local/bin/headsetcontrol" --version) in ~/.local/bin."
echo "Next: scripts/install-udev-rule.sh (once, needs sudo)."
