import unittest
from datetime import date, datetime, timedelta

from headset_tray.headset import HeadsetState
from headset_tray.reminder import ReminderState, night_of, step

ON = HeadsetState(connected=True, battery=75)
CHARGING = HeadsetState(connected=True, battery=75, charging=True)
OFF = HeadsetState(connected=False, error="Headset is off or out of range")


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


class NightOfTest(unittest.TestCase):
    def test_before_the_start_hour_is_not_night(self):
        self.assertIsNone(night_of(at(3, 20, 59), 21))
        self.assertIsNone(night_of(at(3, 12), 21))

    def test_evening_belongs_to_that_day(self):
        self.assertEqual(night_of(at(3, 21), 21), date(2026, 10, 3))
        self.assertEqual(night_of(at(3, 23, 59), 21), date(2026, 10, 3))

    def test_small_hours_belong_to_the_day_before(self):
        self.assertEqual(night_of(at(4, 2), 21), date(2026, 10, 3))

    def test_night_ends_in_the_morning(self):
        self.assertIsNone(night_of(at(4, 5), 21))


class StepTest(unittest.TestCase):
    def test_reminds_in_the_evening_when_not_charging(self):
        state, remind = step(ReminderState(), ON, at(3, 21), 21)
        self.assertTrue(remind)
        self.assertEqual(state.last, at(3, 21))

    def test_quiet_during_the_day(self):
        self.assertFalse(step(ReminderState(), ON, at(3, 15), 21)[1])

    def test_quiet_when_headset_is_off(self):
        self.assertFalse(step(ReminderState(), OFF, at(3, 22), 21)[1])

    def test_quiet_while_charging(self):
        self.assertFalse(step(ReminderState(), CHARGING, at(3, 22), 21)[1])

    def test_repeats_every_thirty_minutes(self):
        state, _ = step(ReminderState(), ON, at(3, 21), 21)
        state, remind = step(state, ON, at(3, 21, 29), 21)
        self.assertFalse(remind)
        state, remind = step(state, ON, at(3, 21, 30), 21)
        self.assertTrue(remind)

    def test_charging_once_silences_the_rest_of_the_night(self):
        # A full headset left on the charger may stop reporting "charging".
        state, _ = step(ReminderState(), CHARGING, at(3, 21), 21)
        self.assertFalse(step(state, ON, at(3, 23), 21)[1])

    def test_a_new_night_starts_afresh(self):
        state, _ = step(ReminderState(), CHARGING, at(3, 21), 21)
        state, _ = step(state, ON, at(4, 12), 21)
        state, remind = step(state, ON, at(4, 21), 21)
        self.assertTrue(remind)
        self.assertEqual(state.night, date(2026, 10, 4))

    def test_reminder_window_follows_the_chosen_hour(self):
        self.assertFalse(step(ReminderState(), ON, at(3, 21), 22)[1])
        self.assertTrue(step(ReminderState(), ON, at(3, 22) + timedelta(minutes=1), 22)[1])


if __name__ == "__main__":
    unittest.main()
