from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileStage6SuspendValidationTests(unittest.TestCase):
    def test_validation_manifest_contract(self) -> None:
        payload = json.loads(
            (ROOT / "mobile/power/suspend-validation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["stage"], "6b-real-suspend-validation")
        self.assertEqual(payload["status"], "real-hardware-verified")
        self.assertEqual(payload["sleep_backend"], "s2idle")
        validation = payload["validation"]
        for key in (
            "manual_suspend_resume",
            "lid_close_suspend_resume",
            "powerdevil_lid_request",
            "kscreenlocker_locked_hint",
            "native_password_unlock_user_verified",
            "amdgpu_resume",
            "power_profile_preserved",
            "boot_identity_preserved",
        ):
            self.assertTrue(validation[key], key)
        self.assertFalse(validation["failed_services_after_resume"])
        for key in ("hibernate", "hybrid_sleep", "suspend_then_hibernate"):
            self.assertTrue(payload["not_validated"][key])

    def test_stage6a_policy_remains_suspend_only(self) -> None:
        payload = json.loads(
            (ROOT / "mobile/power/suspend-policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(payload["sleep"]["allow_suspend"])
        self.assertFalse(payload["sleep"]["allow_hibernation"])
        self.assertFalse(payload["sleep"]["allow_hybrid_sleep"])
        self.assertTrue(payload["security"]["lock_on_resume"])

    def test_documentation_records_real_hardware_verification(self) -> None:
        text = (
            ROOT / "docs/mobile-stage6-power-suspend.md"
        ).read_text(encoding="utf-8")
        self.assertIn("REAL-HARDWARE VERIFIED", text)
        self.assertIn("native password", text)
        self.assertIn("amdgpu", text)

    def test_mobile_doctor_contains_stage6b_contracts(self) -> None:
        text = (ROOT / "scripts/mobile/doctor.sh").read_text(
            encoding="utf-8"
        )
        for marker in (
            "HELM Mobile Stage 6B real suspend validation",
            "Stage 6B real-hardware evidence",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
