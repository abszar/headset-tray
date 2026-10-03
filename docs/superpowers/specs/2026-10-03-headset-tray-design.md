# Headset Tray — design

Date: 2026-10-03

## Goal

A GNOME top-bar indicator for the SteelSeries Arctis Nova 7P (USB dongle
`1038:220a`) that starts at login, shows the headset's battery level beside
its icon, and lets the user choose how long the headset waits before turning
itself off — or stop it turning off at all.

Success: after a reboot the icon is in the top bar with the right percentage,
and the headset no longer turns off sooner than the chosen time.

## Approach

Python 3, GTK 3 and Ayatana AppIndicator — the same stack, installation layout
and service model as Stand Up Reminder. The headset is driven through the
[HeadsetControl](https://github.com/Sapd/HeadsetControl) CLI, which already
implements the Nova 7P's HID protocol:

- `headsetcontrol -b -o json` reads the battery;
- `headsetcontrol -i N` sets the inactive time (0 = never, 1–90 minutes).

Rejected: speaking HID directly over `/dev/hidraw` (re-implements and must
maintain a vendor protocol), and a GNOME Shell extension (breaks with GNOME
upgrades and departs from Stand Up Reminder).

## Components

| Module | Responsibility |
| --- | --- |
| `headset.py` | Runs HeadsetControl and parses its JSON into a `HeadsetState` (connected, battery %, charging, error message); sets the inactive time. The only module that knows about the CLI. |
| `settings.py` | `Settings(auto_off_minutes=30, low_battery_alert=True)`, stored as `~/.config/headset-tray/settings.json`. Unknown or invalid values fall back to defaults. |
| `monitor.py` | Pure logic, no GTK. Given the previous and new `HeadsetState`, decides whether to re-apply the auto-off time (headset just appeared), raise a low-battery alert (≤ 25 %, once), or re-arm the alert (charging or back above 25 %). |
| `application.py` | The indicator: `audio-headset-symbolic` icon, label `75%` or `—`, and the menu below. |

Menu:

```
Battery: 75% (charging)        (insensitive status line)
Turn off after ▸  Never / 5 / 10 / 15 / 30 / 60 / 90 min   (radio)
☑ Low-battery alert (at 25%)
Refresh now
Quit
```

## Data flow

- Poll every 60 seconds, and on demand from a "Refresh now" menu item.
- Every call to HeadsetControl runs on one worker thread, so the menu never
  waits on the dongle and a read never overlaps a write.
- Choosing a time saves it, then applies it at once if the headset is on;
  otherwise it is applied when the headset is next seen. A rejected write
  is retried on the next poll, and the menu says so meanwhile.
- The headset forgetting the setting (power cycle, dongle replug) is covered
  by re-applying it on every disconnected → connected transition.

## Error handling

HeadsetControl missing, no permission on the dongle, no device, or headset
off: the label shows `—` and the status line says why. Nothing raises out of
the poll loop. The systemd user service restarts the process on failure.

## Installation

- `scripts/build-headsetcontrol.sh` clones and builds HeadsetControl into
  `~/.local/bin` (needs `build-essential cmake libhidapi-dev`).
- `scripts/install-udev-rule.sh` installs HeadsetControl's udev rules with
  `sudo`, once, so the dongle is reachable without root.
- `scripts/install.sh` installs the app user-locally (package under
  `~/.local/share/headset-tray`, launcher in `~/.local/bin`, `.desktop`,
  autostart entry, systemd user service) and restarts the service.

## Testing

`unittest`: JSON parsing (charging, discharging, headset off, no device,
garbage output, missing binary), settings round trip and validation, and
every monitor decision.
