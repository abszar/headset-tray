# Headset Tray

A small GNOME top-bar indicator for SteelSeries wireless headsets. It shows
the headset's battery level beside its icon, and lets you choose how long the
headset waits before turning itself off — or stop it turning off at all —
without SteelSeries GG, which does not run on Linux.

```
🎧 75%
├─ Battery: 75%
├─ Turn off after ▸  Never · 5 · 10 · 15 · 30 · 60 · 90 minutes
├─ ☑ Low-battery alert (at 25%)
├─ Refresh now
└─ Quit
```

Written for and tested against the **Arctis Nova 7P** (USB dongle
`1038:220a`). It talks to the headset through
[HeadsetControl](https://github.com/Sapd/HeadsetControl), so other headsets
that HeadsetControl supports for battery and inactive time should work too.

## What it does

- Starts at login and lives in the top bar.
- Shows the battery as `75%`, `⚡50%` while charging, or `—` when the headset
  is off, out of range or unreachable; the first menu line says why.
- Saves the auto-off choice and sends it to the headset at once, and again
  every time the headset reconnects, so a power cycle never undoes it.
- Sends one notification when the battery drops to 25 %, and does not repeat
  it until the headset has been charged.

## Requirements

Ubuntu 24.04 or another GNOME desktop with the AppIndicator extension (on by
default on Ubuntu), plus:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
    build-essential git cmake libhidapi-dev
```

## Install

```sh
scripts/build-headsetcontrol.sh   # builds HeadsetControl into ~/.local/bin
scripts/install-udev-rule.sh      # once, asks for sudo: lets you use the dongle without root
scripts/install.sh                # installs and starts Headset Tray
```

If the headset is not found after the udev step, unplug and replug the dongle.

Everything installs for your user only: the application under
`~/.local/share/headset-tray`, a launcher in `~/.local/bin`, a systemd user
service (`headset-tray.service`) and an autostart entry. Settings are kept in
`~/.config/headset-tray/settings.json`.

After quitting from the menu, start it again from the application grid
(“Headset Tray”) or with `systemctl --user start headset-tray.service`.

## Uninstall

```sh
scripts/uninstall.sh
```

This leaves HeadsetControl, its udev rule and your settings in place.

## Development

```sh
scripts/run-tests.sh
```

The design is in [`docs/superpowers/specs`](docs/superpowers/specs).

## Licence

MIT
