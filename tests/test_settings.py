import json
import tempfile
import unittest
from pathlib import Path

from headset_tray.settings import AUTO_OFF_PRESETS, REMINDER_HOURS, Settings, SettingsStore


class SettingsStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "nested" / "settings.json"
        self.store = SettingsStore(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_defaults_when_nothing_saved(self):
        self.assertEqual(
            self.store.load(),
            Settings(
                auto_off_minutes=30,
                low_battery_alert=True,
                charge_reminder=True,
                charge_reminder_hour=21,
            ),
        )

    def test_round_trip(self):
        saved = Settings(
            auto_off_minutes=0,
            low_battery_alert=False,
            charge_reminder=False,
            charge_reminder_hour=23,
        )
        self.store.save(saved)
        self.assertEqual(self.store.load(), saved)

    def test_invalid_values_fall_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps(
                {
                    "auto_off_minutes": 500,
                    "low_battery_alert": "yes",
                    "charge_reminder": 1,
                    "charge_reminder_hour": 3,
                }
            )
        )
        self.assertEqual(self.store.load(), Settings())

    def test_unreadable_file_falls_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json")
        self.assertEqual(self.store.load(), Settings())

    def test_presets_include_never_and_fit_headsetcontrol_range(self):
        self.assertEqual(AUTO_OFF_PRESETS[0], 0)
        self.assertTrue(all(0 <= minutes <= 90 for minutes in AUTO_OFF_PRESETS))

    def test_settings_saved_before_the_reminder_existed_still_load(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"auto_off_minutes": 0, "low_battery_alert": False}))
        loaded = self.store.load()
        self.assertEqual(loaded.auto_off_minutes, 0)
        self.assertTrue(loaded.charge_reminder)
        self.assertEqual(loaded.charge_reminder_hour, 21)

    def test_reminder_hours_are_evening_hours(self):
        self.assertEqual(REMINDER_HOURS, (20, 21, 22, 23))


if __name__ == "__main__":
    unittest.main()
