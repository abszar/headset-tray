import unittest

from headset_tray.headset import HeadsetState
from headset_tray.monitor import Decision, decide

OFF = HeadsetState(connected=False, error="Headset is off or out of range")


def on(battery, charging=False):
    return HeadsetState(connected=True, battery=battery, charging=charging)


class DecideTest(unittest.TestCase):
    def test_first_sighting_applies_auto_off(self):
        self.assertTrue(decide(None, on(80), alert_armed=True).apply_auto_off)

    def test_reconnection_applies_auto_off(self):
        self.assertTrue(decide(OFF, on(80), alert_armed=True).apply_auto_off)

    def test_staying_connected_does_not_reapply(self):
        self.assertFalse(decide(on(80), on(75), alert_armed=True).apply_auto_off)

    def test_staying_off_does_nothing(self):
        self.assertEqual(decide(OFF, OFF, alert_armed=True), Decision(False, False, True))

    def test_low_battery_alerts_once(self):
        first = decide(on(50), on(25), alert_armed=True)
        self.assertTrue(first.alert_low_battery)
        self.assertFalse(first.alert_armed)
        second = decide(on(25), on(25), alert_armed=first.alert_armed)
        self.assertFalse(second.alert_low_battery)

    def test_no_alert_while_charging(self):
        decision = decide(on(50), on(25, charging=True), alert_armed=True)
        self.assertFalse(decision.alert_low_battery)

    def test_charging_rearms_the_alert(self):
        self.assertTrue(decide(on(25), on(25, charging=True), alert_armed=False).alert_armed)

    def test_level_above_threshold_rearms_the_alert(self):
        self.assertTrue(decide(on(25), on(50), alert_armed=False).alert_armed)

    def test_unknown_level_never_alerts(self):
        decision = decide(on(None), on(None), alert_armed=True)
        self.assertFalse(decision.alert_low_battery)
        self.assertTrue(decision.alert_armed)


if __name__ == "__main__":
    unittest.main()
