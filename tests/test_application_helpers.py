import unittest

from headset_tray.application import battery_label, clock_label, preset_label, status_line
from headset_tray.headset import HeadsetState

OFF = HeadsetState(connected=False, error="Headset is off or out of range")


class LabelTest(unittest.TestCase):
    def test_battery_label(self):
        self.assertEqual(battery_label(HeadsetState(True, 75)), "75%")
        self.assertEqual(battery_label(HeadsetState(True, 50, charging=True)), "⚡50%")
        self.assertEqual(battery_label(HeadsetState(True, None)), "—")
        self.assertEqual(battery_label(OFF), "—")
        self.assertEqual(battery_label(None), "—")

    def test_status_line(self):
        self.assertEqual(status_line(HeadsetState(True, 75)), "Battery: 75%")
        self.assertEqual(
            status_line(HeadsetState(True, 50, charging=True)), "Battery: 50% (charging)"
        )
        self.assertEqual(
            status_line(HeadsetState(True, None, charging=True)),
            "Battery: unknown (charging)",
        )
        self.assertEqual(status_line(OFF), "Headset is off or out of range")
        self.assertEqual(status_line(None), "Looking for the headset…")

    def test_preset_label(self):
        self.assertEqual(preset_label(0), "Never")
        self.assertEqual(preset_label(30), "30 minutes")
        self.assertEqual(preset_label(60), "1 hour")
        self.assertEqual(preset_label(90), "1 hour 30 minutes")

    def test_clock_label(self):
        self.assertEqual(clock_label(21 * 60), "21:00")
        self.assertEqual(clock_label(22 * 60 + 30), "22:30")


if __name__ == "__main__":
    unittest.main()
