import json
import tempfile
import unittest
from pathlib import Path

from headset_tray.settings import AUTO_OFF_PRESETS, Settings, SettingsStore


class SettingsStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "nested" / "settings.json"
        self.store = SettingsStore(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_defaults_when_nothing_saved(self):
        self.assertEqual(self.store.load(), Settings(auto_off_minutes=30, low_battery_alert=True))

    def test_round_trip(self):
        saved = Settings(auto_off_minutes=0, low_battery_alert=False)
        self.store.save(saved)
        self.assertEqual(self.store.load(), saved)

    def test_invalid_values_fall_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"auto_off_minutes": 500, "low_battery_alert": "yes"}))
        self.assertEqual(self.store.load(), Settings())

    def test_unreadable_file_falls_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json")
        self.assertEqual(self.store.load(), Settings())

    def test_presets_include_never_and_fit_headsetcontrol_range(self):
        self.assertEqual(AUTO_OFF_PRESETS[0], 0)
        self.assertTrue(all(0 <= minutes <= 90 for minutes in AUTO_OFF_PRESETS))


if __name__ == "__main__":
    unittest.main()
