from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import get_type_hints

from modules.power import PowerMonitor, PowerSample
from services.data_service import SystemSnapshot


class MobilePowerTelemetryTests(unittest.TestCase):
    @staticmethod
    def _write(path: Path, value: object) -> None:
        path.write_text(f"{value}\n", encoding="utf-8")

    def test_energy_based_battery_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            battery = root / "BAT0"
            ac = root / "AC"
            battery.mkdir()
            ac.mkdir()

            values = {
                "type": "Battery",
                "present": 1,
                "capacity": 51,
                "status": "Discharging",
                "energy_now": 23_870_000,
                "energy_full": 46_350_000,
                "energy_full_design": 50_450_000,
                "power_now": 7_210_000,
            }

            for name, value in values.items():
                self._write(battery / name, value)

            self._write(ac / "type", "Mains")
            self._write(ac / "online", 0)

            sample = PowerMonitor(
                root,
                profile_reader=lambda: "balanced",
            ).sample()

            self.assertTrue(sample.battery_present)
            self.assertEqual(sample.battery_percent, 51.0)
            self.assertEqual(sample.battery_state, "DISCHARGING")
            self.assertAlmostEqual(sample.battery_power_w or 0.0, 7.21)
            self.assertAlmostEqual(sample.battery_energy_wh or 0.0, 23.87)
            self.assertAlmostEqual(sample.battery_health_percent or 0.0, 91.9)
            self.assertFalse(sample.external_power_online)
            self.assertEqual(sample.power_profile, "balanced")
            self.assertIsNotNone(sample.battery_time_remaining_s)

    def test_charge_and_voltage_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            battery = root / "BAT0"
            battery.mkdir()

            values = {
                "type": "Battery",
                "capacity": 50,
                "status": "Charging",
                "charge_now": 2_000_000,
                "charge_full": 4_000_000,
                "charge_full_design": 5_000_000,
                "voltage_now": 12_000_000,
                "current_now": 1_000_000,
            }

            for name, value in values.items():
                self._write(battery / name, value)

            sample = PowerMonitor(
                root,
                profile_reader=lambda: "power-saver",
            ).sample()

            self.assertAlmostEqual(sample.battery_energy_wh or 0.0, 24.0)
            self.assertAlmostEqual(sample.battery_energy_full_wh or 0.0, 48.0)
            self.assertAlmostEqual(sample.battery_power_w or 0.0, 12.0)
            self.assertEqual(sample.battery_health_percent, 80.0)
            self.assertEqual(sample.power_profile, "power-saver")

    def test_missing_battery_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sample = PowerMonitor(
                Path(temporary),
                profile_reader=lambda: "balanced",
            ).sample()

            self.assertFalse(sample.battery_present)
            self.assertEqual(sample.battery_state, "NOT PRESENT")
            self.assertIsNone(sample.battery_percent)
            self.assertEqual(sample.power_profile, "balanced")

    def test_system_snapshot_contract_contains_power(self) -> None:
        self.assertIs(
            get_type_hints(SystemSnapshot)["power"],
            PowerSample,
        )


if __name__ == "__main__":
    unittest.main()
