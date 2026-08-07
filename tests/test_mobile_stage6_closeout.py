from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileStage6CloseoutTests(unittest.TestCase):
    def test_wake_policy_is_no_change(self) -> None:
        p = json.loads(
            (ROOT / "mobile/power/wake-policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(p["stage"], "6c-wake-source-closeout")
        self.assertEqual(p["status"], "complete-no-policy-change")
        self.assertTrue(
            p["observed_behavior"]["wake_and_resuspend_confirmed"]
        )
        self.assertEqual(p["decision"]["action"], "no-policy-change")
        self.assertFalse(p["decision"]["disable_wake_sources"])
        self.assertTrue(p["decision"]["preserve_lid_open_wake"])
        self.assertTrue(p["decision"]["preserve_normal_input_wake"])

    def test_ambiguous_sources_are_not_promoted_to_causal(self) -> None:
        p = json.loads(
            (ROOT / "mobile/power/wake-policy.json").read_text(
                encoding="utf-8"
            )
        )
        e = p["evidence"]
        self.assertEqual(e["last_observed_pm_wakeup_irq"], 9)
        self.assertFalse(e["keyboard_irq1_causality_proven"])
        self.assertFalse(e["wifi_network_causality_proven"])
        self.assertFalse(e["usb_xhci_causality_proven"])
        self.assertFalse(e["rtc_alarm_causality_proven"])

    def test_stage6_milestone_is_complete(self) -> None:
        p = json.loads(
            (ROOT / "mobile/stage6/stage6.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(p["stage"], "6c-stage6-closeout")
        self.assertEqual(p["status"], "complete")
        self.assertEqual(
            p["stages"]["6b"]["status"],
            "real-hardware-verified",
        )
        self.assertEqual(
            p["stages"]["6c"]["status"],
            "complete-no-policy-change",
        )
        self.assertFalse(p["final_policy"]["allow_hibernation"])
        self.assertEqual(
            p["final_policy"]["wake_source_action"],
            "no-policy-change",
        )

    def test_reusable_wake_audit_is_read_only(self) -> None:
        text = (
            ROOT / "scripts/mobile/audit-stage6-wake-sources.sh"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "systemctl suspend",
            "systemctl hibernate",
            "powerprofilesctl set",
            "systemctl restart",
            "kwriteconfig6",
            "tee /proc/acpi/wakeup",
            "> /proc/acpi/wakeup",
            "power/wakeup\" >",
            "sudo ",
        ):
            self.assertNotIn(forbidden, text)

        self.assertIn("pm_wakeup_irq", text)
        self.assertIn("/proc/acpi/wakeup", text)
        self.assertIn("No wake policy was modified", text)

    def test_documentation_and_doctor_close_stage6(self) -> None:
        docs = (
            ROOT / "docs/mobile-stage6-power-suspend.md"
        ).read_text(encoding="utf-8")
        doctor = (ROOT / "scripts/mobile/doctor.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("NO POLICY CHANGE", docs)
        self.assertIn("Stage 6 status: **COMPLETE**", docs)

        for marker in (
            "HELM Mobile Stage 6C wake decision",
            "Stage 6C no-policy-change contract",
            "Stage 6 reusable wake audit",
            "HELM Mobile Stage 6 milestone manifest",
            "Stage 6 suspend-only final contract",
        ):
            self.assertIn(marker, doctor)


if __name__ == "__main__":
    unittest.main()
