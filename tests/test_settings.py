import json
import tempfile
import unittest
from pathlib import Path

from headset_tray.settings import AUTO_OFF_PRESETS, REMINDER_STARTS, Settings, SettingsStore


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
                charge_reminder_start=21 * 60,
            ),
        )

    def test_round_trip(self):
        saved = Settings(
            auto_off_minutes=0,
            low_battery_alert=False,
            charge_reminder=False,
            charge_reminder_start=23 * 60 + 30,
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
                    "charge_reminder_start": 21 * 60 + 15,
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
        self.assertEqual(loaded.charge_reminder_start, 21 * 60)

    def test_reminder_starts_every_half_hour_from_eight_to_half_past_eleven(self):
        self.assertEqual(
            REMINDER_STARTS,
            (1200, 1230, 1260, 1290, 1320, 1350, 1380, 1410),
        )

    def test_an_hour_saved_by_the_first_version_is_carried_over(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"charge_reminder_hour": 22}))
        self.assertEqual(self.store.load().charge_reminder_start, 22 * 60)


if __name__ == "__main__":
    unittest.main()
