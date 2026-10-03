"""Decides what a new headset reading calls for. Pure logic, no GTK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .headset import HeadsetState

# The Nova 7P reports its battery in 25 % steps, so this is its last step
# before empty.
LOW_BATTERY_PERCENT = 25


@dataclass(frozen=True)
class Decision:
    # Send the auto-off time to the headset: it has just appeared, and may
    # have come back from a power cycle that reset it.
    apply_auto_off: bool
    alert_low_battery: bool
    # Whether a later low reading may alert again. Disarmed by an alert,
    # re-armed by charging or by a reading back above the threshold.
    alert_armed: bool


def decide(
    previous: Optional[HeadsetState], current: HeadsetState, alert_armed: bool
) -> Decision:
    if not current.connected:
        return Decision(False, False, alert_armed)

    appeared = previous is None or not previous.connected
    level = current.battery
    if current.charging or (level is not None and level > LOW_BATTERY_PERCENT):
        return Decision(appeared, False, True)
    if level is not None and alert_armed:
        return Decision(appeared, True, False)
    return Decision(appeared, False, alert_armed)
