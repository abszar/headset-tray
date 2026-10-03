"""Talks to the headset through the HeadsetControl command-line program.

Nothing else in the application knows that HeadsetControl exists: the rest
works with HeadsetState, so a different backend would only replace this file.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

PROGRAM = "headsetcontrol"
# Long enough for a dongle that is slow to answer, short enough that a hung
# call never freezes the top-bar menu for long.
TIMEOUT_SECONDS = 10

NOT_INSTALLED = "HeadsetControl is not installed"
NOT_RESPONDING = "HeadsetControl did not respond"
UNEXPECTED_OUTPUT = "Unexpected output from HeadsetControl"
NO_DONGLE = "Dongle not found (check the udev rule)"
HEADSET_OFF = "Headset is off or out of range"
NO_ANSWER = "Headset did not answer"


@dataclass(frozen=True)
class HeadsetState:
    connected: bool
    # Percent, or None when the headset is on but has not said how full it is.
    battery: Optional[int] = None
    charging: bool = False
    # Why the headset is not connected; None while it is.
    error: Optional[str] = None


def find_program() -> Optional[str]:
    """The HeadsetControl executable, looking in ~/.local/bin as well.

    A systemd user service does not always have ~/.local/bin on its PATH,
    and that is where scripts/build-headsetcontrol.sh puts the program.
    """
    found = shutil.which(PROGRAM)
    if found:
        return found
    local = Path.home() / ".local" / "bin" / PROGRAM
    return str(local) if local.is_file() else None


def parse_status(text: str) -> HeadsetState:
    """Reads the output of `headsetcontrol -b -o json`."""
    try:
        document = json.loads(text)
        devices = document.get("devices") or []
    except (ValueError, AttributeError):
        return HeadsetState(connected=False, error=UNEXPECTED_OUTPUT)
    if not devices:
        return HeadsetState(connected=False, error=NO_DONGLE)

    device = devices[0]
    battery = device.get("battery")
    if not isinstance(battery, dict):
        errors = device.get("errors") or {}
        message = next(iter(errors.values()), None) if isinstance(errors, dict) else None
        return HeadsetState(connected=False, error=message or UNEXPECTED_OUTPUT)

    status = battery.get("status")
    level = battery.get("level")
    level = level if isinstance(level, int) and 0 <= level <= 100 else None
    if status == "BATTERY_AVAILABLE":
        return HeadsetState(connected=True, battery=level)
    if status == "BATTERY_CHARGING":
        return HeadsetState(connected=True, battery=level, charging=True)
    if status == "BATTERY_UNAVAILABLE":
        return HeadsetState(connected=False, error=HEADSET_OFF)
    return HeadsetState(connected=False, error=NO_ANSWER)


class HeadsetControl:
    def __init__(
        self,
        program: Optional[str],
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> None:
        self.program = program
        self._run = runner

    def read(self) -> HeadsetState:
        if self.program is None:
            return HeadsetState(connected=False, error=NOT_INSTALLED)
        try:
            # The exit code is not checked: HeadsetControl exits 1 when no
            # device is found and still prints a report saying so.
            result = self._run(
                [self.program, "-b", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return HeadsetState(connected=False, error=NOT_RESPONDING)
        except OSError:
            return HeadsetState(connected=False, error=NOT_INSTALLED)
        return parse_status(result.stdout)

    def set_auto_off(self, minutes: int) -> bool:
        """Sets the inactive time; 0 means the headset never turns itself off."""
        if self.program is None:
            return False
        try:
            result = self._run(
                [self.program, "-i", str(minutes)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        return result.returncode == 0
