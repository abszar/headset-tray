import json
import subprocess
import unittest

from headset_tray.headset import HeadsetControl, HeadsetState, parse_status


def report(battery=None, errors=None, devices=True):
    """A HeadsetControl JSON report shaped like `headsetcontrol -b -o json`."""
    device = {
        "status": "success",
        "device": "SteelSeries Arctis Nova 7P",
        "vendor": "SteelSeries ",
        "product": "Arctis Nova 7P",
        "id_vendor": "0x1038",
        "id_product": "0x220a",
        "capabilities": ["CAP_BATTERY_STATUS", "CAP_INACTIVE_TIME"],
        "capabilities_str": ["battery", "inactive time"],
    }
    if battery is not None:
        device["battery"] = battery
    if errors is not None:
        device["errors"] = errors
    listed = [device] if devices else []
    return json.dumps(
        {
            "name": "HeadsetControl",
            "version": "4.0.0",
            "api_version": "1.4",
            "hidapi_version": "0.14.0",
            "device_count": len(listed),
            "devices": listed,
        }
    )


class ParseStatusTest(unittest.TestCase):
    def test_discharging_headset_reports_its_level(self):
        state = parse_status(report({"status": "BATTERY_AVAILABLE", "level": 75}))
        self.assertEqual(state, HeadsetState(connected=True, battery=75))

    def test_charging_headset_is_flagged(self):
        state = parse_status(report({"status": "BATTERY_CHARGING", "level": 50}))
        self.assertEqual(state, HeadsetState(connected=True, battery=50, charging=True))

    def test_charging_without_a_level_keeps_the_level_unknown(self):
        state = parse_status(report({"status": "BATTERY_CHARGING", "level": -1}))
        self.assertEqual(state, HeadsetState(connected=True, battery=None, charging=True))

    def test_headset_switched_off(self):
        state = parse_status(report({"status": "BATTERY_UNAVAILABLE", "level": -1}))
        self.assertFalse(state.connected)
        self.assertEqual(state.error, "Headset is off or out of range")

    def test_headset_not_answering(self):
        for status in ("BATTERY_ERROR", "BATTERY_TIMEOUT"):
            with self.subTest(status=status):
                state = parse_status(report({"status": status, "level": -1}))
                self.assertFalse(state.connected)
                self.assertEqual(state.error, "Headset did not answer")

    def test_no_dongle_found(self):
        state = parse_status(report(devices=False))
        self.assertFalse(state.connected)
        self.assertEqual(state.error, "Dongle not found (check the udev rule)")

    def test_device_error_message_is_passed_on(self):
        state = parse_status(report(errors={"battery": "Failed to open device"}))
        self.assertFalse(state.connected)
        self.assertEqual(state.error, "Failed to open device")

    def test_garbage_output(self):
        state = parse_status("Segmentation fault")
        self.assertFalse(state.connected)
        self.assertEqual(state.error, "Unexpected output from HeadsetControl")


class FakeRunner:
    def __init__(self, stdout="", returncode=0, raises=None):
        self.stdout = stdout
        self.returncode = returncode
        self.raises = raises
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(args, self.returncode, self.stdout, "")


class HeadsetControlTest(unittest.TestCase):
    def test_read_asks_for_the_battery_as_json(self):
        runner = FakeRunner(report({"status": "BATTERY_AVAILABLE", "level": 100}))
        state = HeadsetControl("/bin/hc", runner=runner).read()
        self.assertEqual(runner.calls, [["/bin/hc", "-b", "-o", "json"]])
        self.assertEqual(state.battery, 100)

    def test_read_parses_output_even_on_a_failing_exit_code(self):
        runner = FakeRunner(report(devices=False), returncode=1)
        state = HeadsetControl("/bin/hc", runner=runner).read()
        self.assertEqual(state.error, "Dongle not found (check the udev rule)")

    def test_read_without_the_program_installed(self):
        state = HeadsetControl(None).read()
        self.assertFalse(state.connected)
        self.assertEqual(state.error, "HeadsetControl is not installed")

    def test_read_survives_a_hung_program(self):
        runner = FakeRunner(raises=subprocess.TimeoutExpired("hc", 10))
        state = HeadsetControl("/bin/hc", runner=runner).read()
        self.assertEqual(state.error, "HeadsetControl did not respond")

    def test_set_auto_off_passes_the_minutes(self):
        runner = FakeRunner()
        self.assertTrue(HeadsetControl("/bin/hc", runner=runner).set_auto_off(0))
        self.assertEqual(runner.calls, [["/bin/hc", "-i", "0"]])

    def test_set_auto_off_reports_failure(self):
        runner = FakeRunner(returncode=1)
        self.assertFalse(HeadsetControl("/bin/hc", runner=runner).set_auto_off(30))
        self.assertFalse(HeadsetControl(None).set_auto_off(30))
        hung = FakeRunner(raises=OSError("gone"))
        self.assertFalse(HeadsetControl("/bin/hc", runner=hung).set_auto_off(30))


if __name__ == "__main__":
    unittest.main()
