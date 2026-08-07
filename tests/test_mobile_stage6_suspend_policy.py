from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileStage6SuspendPolicyTests(unittest.TestCase):
    def test_manifest_contract(self) -> None:
        payload = json.loads(
            (ROOT / "mobile/power/suspend-policy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["stage"], "6a-mobile-suspend-policy")
        self.assertEqual(payload["ownership"]["lid_and_power_events"], "KDE PowerDevil")
        self.assertEqual(payload["lid"]["battery"], "suspend")
        self.assertEqual(payload["lid"]["ac"], "suspend")
        self.assertEqual(payload["sleep"]["backend"], "s2idle")
        self.assertTrue(payload["sleep"]["allow_suspend"])
        self.assertFalse(payload["sleep"]["allow_hibernation"])
        self.assertFalse(payload["sleep"]["allow_suspend_then_hibernate"])
        self.assertFalse(payload["sleep"]["allow_hybrid_sleep"])
        self.assertTrue(payload["security"]["lock_on_resume"])

    def test_systemd_sleep_template_is_suspend_only(self) -> None:
        text = (ROOT / "mobile/systemd/90-helm-mobile-sleep.conf").read_text(encoding="utf-8")
        for marker in (
            "AllowSuspend=yes",
            "AllowHibernation=no",
            "AllowSuspendThenHibernate=no",
            "AllowHybridSleep=no",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("MemorySleepMode=deep", text)

    def test_apply_tool_does_not_trigger_sleep_or_restart_services(self) -> None:
        text = (ROOT / "scripts/mobile/apply-stage6a-suspend-policy.sh").read_text(encoding="utf-8")
        forbidden = (
            "systemctl suspend",
            "systemctl hibernate",
            "systemctl hybrid-sleep",
            "systemctl suspend-then-hibernate",
            "restart plasma-powerdevil",
            "restart systemd-logind",
            "powerprofilesctl set",
        )
        for marker in forbidden:
            self.assertNotIn(marker, text)

    def test_documentation_defers_real_sleep_test_to_stage6b(self) -> None:
        text = (ROOT / "docs/mobile-stage6-power-suspend.md").read_text(encoding="utf-8")
        self.assertIn("Stage 6B", text)
        self.assertIn("does **not** trigger suspend", text)
        self.assertIn("zram-only", text)

    def test_mobile_doctor_contains_stage6a_contracts(self) -> None:
        text = (ROOT / "scripts/mobile/doctor.sh").read_text(encoding="utf-8")
        for marker in (
            "HELM Mobile Stage 6A suspend policy",
            "Stage 6A installed sleep policy",
            "Stage 6A PowerDevil lid ownership",
            "Stage 6A lid-close suspend configuration",
            "Stage 6A lock-on-resume",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
