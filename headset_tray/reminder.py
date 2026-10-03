"""When to remind the user to put the headset on charge for the night.

Pure logic, no GTK. The reminder runs in an evening window rather than at
suspend: the system only lets an application delay suspend by a few seconds,
too late for anyone to get up and plug a cable in.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from typing import Optional

from .headset import HeadsetState

REMIND_EVERY = timedelta(minutes=30)
# The night's window closes at this hour of the morning.
MORNING_HOUR = 5


@dataclass(frozen=True)
class ReminderState:
    # The evening the window opened on, or None outside the window.
    night: Optional[date] = None
    # The headset has been seen charging tonight. Once it has, the reminder
    # stays quiet until the next evening: a full headset left on the charger
    # may stop reporting that it is charging.
    charged: bool = False
    last: Optional[datetime] = None


def night_of(now: datetime, start: int) -> Optional[date]:
    """The evening `now` belongs to, if it falls in the reminder window.

    `start` is when the window opens, in minutes after midnight.
    """
    if now.hour * 60 + now.minute >= start:
        return now.date()
    if now.hour < MORNING_HOUR:
        return now.date() - timedelta(days=1)
    return None


def step(
    state: ReminderState, headset: HeadsetState, now: datetime, start: int
) -> tuple[ReminderState, bool]:
    """The new reminder state, and whether to remind the user now."""
    night = night_of(now, start)
    if night is None:
        return ReminderState(), False
    if state.night != night:
        state = ReminderState(night=night)

    if headset.connected and headset.charging:
        return replace(state, charged=True), False
    if not headset.connected or state.charged:
        return state, False
    if state.last is None or now - state.last >= REMIND_EVERY:
        return replace(state, last=now), True
    return state, False
