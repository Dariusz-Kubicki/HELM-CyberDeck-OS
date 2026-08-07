from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileStage5CloseoutTests(unittest.TestCase):
    def test_stage5_manifest_contract(self) -> None:
        payload = json.loads(
            (
                ROOT / "mobile" / "stage5" / "stage5.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            payload.get("stage"),
            "5d-stage5-closeout",
        )
        self.assertEqual(payload.get("status"), "complete")

        telemetry = payload["telemetry"]
        self.assertTrue(telemetry["single_collector"])
        self.assertTrue(telemetry["sampling_is_read_only"])
        self.assertTrue(
            telemetry["power_sample_in_system_snapshot"]
        )

        policy = payload["mode_policy"]
        self.assertEqual(
            policy["unknown_power_source_fallback"],
            "balanced",
        )
        self.assertEqual(
            policy["unavailable_profile_fallback"],
            "balanced",
        )
        self.assertTrue(policy["apply_failure_non_fatal"])

        surface = payload["surface"]
        self.assertEqual(surface["panel"], "MobilePowerPanel")
        self.assertFalse(surface["second_collector"])

        self.assertFalse(any(payload["safety"].values()))

    def test_stage5_documentation_is_closed(self) -> None:
        source = (
            ROOT / "docs" / "mobile-stage5-telemetry-modes.md"
        ).read_text(encoding="utf-8")

        for marker in (
            "## Stage 5D — Final validation and milestone closeout",
            "Stage 5 status: **COMPLETE**",
            "Stage 5A",
            "Stage 5B",
            "Stage 5C",
            "scripts/mobile/audit-stage5-telemetry-modes.sh",
        ):
            self.assertIn(marker, source)

    def test_stage5_audit_has_no_mutating_operations(self) -> None:
        source = (
            ROOT
            / "scripts"
            / "mobile"
            / "audit-stage5-telemetry-modes.sh"
        ).read_text(encoding="utf-8")

        forbidden = (
            "save_active_mode(",
            "launch_mode(",
            "apply_power_profile(",
            "RuntimeJsonStore(",
            "systemctl enable",
            "systemctl disable",
            "systemctl start",
            "systemctl stop",
            "mkinitcpio -P",
            "git commit",
            "git push",
        )

        for marker in forbidden:
            self.assertNotIn(marker, source)

        self.assertNotRegex(
            source,
            r"(?m)^\s*(?:sudo\s+)?(?:reboot|shutdown)\b",
        )
        self.assertIn("powerprofilesctl get", source)
        self.assertNotIn("powerprofilesctl set", source)

    def test_mobile_doctor_contains_stage5_closeout_checks(self) -> None:
        source = (
            ROOT / "scripts" / "mobile" / "doctor.sh"
        ).read_text(encoding="utf-8")

        for marker in (
            "HELM Mobile Stage 5 milestone manifest",
            "Stage 5 telemetry read-only contract",
            "Stage 5 adaptive mode policy contract",
            "Stage 5 telemetry surface contract",
            "Stage 5 reusable read-only audit",
        ):
            self.assertIn(marker, source)

    def test_changelog_records_stage5_closeout(self) -> None:
        source = (ROOT / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "HELM Mobile Stage 5D milestone closeout",
            source,
        )


if __name__ == "__main__":
    unittest.main()
