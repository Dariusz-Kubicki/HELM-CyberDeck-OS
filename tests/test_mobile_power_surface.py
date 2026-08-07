from __future__ import annotations

import unittest
from pathlib import Path

from app.mobile_power_panel import MobilePowerPanel
from modules.power import PowerSample
from services.mobile_power_policy import MobilePowerPolicyService


ROOT = Path(__file__).resolve().parents[1]


class MobilePowerSurfaceTests(unittest.TestCase):
    def test_panel_formats_live_power_contract(self) -> None:
        sample = PowerSample(
            battery_present=True,
            battery_percent=46.0,
            battery_state="DISCHARGING",
            battery_power_w=7.5,
            battery_energy_wh=21.3,
            battery_energy_full_wh=46.35,
            battery_energy_full_design_wh=50.45,
            battery_health_percent=91.9,
            battery_time_remaining_s=10920,
            external_power_online=False,
            power_profile="balanced",
        )

        markup = MobilePowerPanel.build_markup(
            sample,
            "command",
            "balanced",
        )

        for marker in (
            "MOBILE POWER // FIELD ENERGY STATUS",
            "46.0%",
            "DISCHARGING",
            "3h 02m",
            "7.5 W",
            "21.30 / 46.35 Wh",
            "91.9%",
            "SOURCE[/b] BATTERY",
            "PROFILE[/b] BALANCED",
            "COMMAND -> BALANCED",
        ):
            self.assertIn(marker, markup)

    def test_panel_handles_unavailable_power_data(self) -> None:
        markup = MobilePowerPanel.build_markup(
            PowerSample.unavailable(),
            "custom",
            "unchanged",
        )

        self.assertIn("BATTERY[/b] N/A UNKNOWN", markup)
        self.assertIn("SOURCE[/b] UNKNOWN", markup)
        self.assertIn("CUSTOM -> UNCHANGED", markup)

    def test_policy_target_helper_is_pure_source_mapping(self) -> None:
        service = MobilePowerPolicyService()

        self.assertEqual(
            service.policy_target_for_source(
                "development",
                "unchanged",
                True,
            ),
            "performance",
        )
        self.assertEqual(
            service.policy_target_for_source(
                "development",
                "unchanged",
                False,
            ),
            "balanced",
        )
        self.assertEqual(
            service.policy_target_for_source(
                "chill",
                "unchanged",
                False,
            ),
            "power-saver",
        )

    def test_policy_target_helper_preserves_safety_fallbacks(self) -> None:
        service = MobilePowerPolicyService()

        self.assertEqual(
            service.policy_target_for_source(
                "development",
                "power-saver",
                True,
            ),
            "power-saver",
        )
        self.assertEqual(
            service.policy_target_for_source(
                "development",
                "unchanged",
                None,
            ),
            "balanced",
        )
        self.assertEqual(
            service.policy_target_for_source(
                "custom",
                "unchanged",
                False,
            ),
            "unchanged",
        )

    def test_system_screen_integrates_dedicated_power_panel(self) -> None:
        source = (
            ROOT / "app" / "screens" / "system.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "from app.mobile_power_panel import MobilePowerPanel",
            source,
        )
        self.assertIn(
            'yield MobilePowerPanel(id="mobile-power-panel")',
            source,
        )
        self.assertIn(
            ").update_snapshot(\n            snapshot,\n            self._mode_id,",
            source,
        )

        dashboard = (
            ROOT / "app" / "dashboard.py"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            dashboard.count("yield MetricCard("),
            4,
        )

    def test_main_supplies_mode_context_without_new_collector(self) -> None:
        main_source = (
            ROOT / "app" / "main.py"
        ).read_text(encoding="utf-8")
        panel_source = (
            ROOT / "app" / "mobile_power_panel.py"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            main_source.count(".update_mode_context("),
            4,
        )

        for forbidden in (
            "subprocess",
            "powerprofilesctl",
            "apply_power_profile(",
            "RuntimeJsonStore",
            "set_interval(",
        ):
            self.assertNotIn(
                forbidden,
                panel_source,
            )


if __name__ == "__main__":
    unittest.main()
