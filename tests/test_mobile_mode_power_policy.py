from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from modules.power import PowerSample
from services.mobile_power_policy import MobilePowerPolicyService


REPOSITORY = Path(__file__).resolve().parents[1]
POLICY = REPOSITORY / "mobile" / "modes" / "power-policy.json"
MAIN = REPOSITORY / "app" / "main.py"


class FakePowerMonitor:
    def __init__(self, external_power_online: bool | None) -> None:
        self.external_power_online = external_power_online

    def sample(self) -> PowerSample:
        return replace(
            PowerSample.unavailable(),
            battery_present=True,
            external_power_online=self.external_power_online,
            power_profile="balanced",
        )


class FakeController:
    def __init__(
        self,
        *,
        current: str = "BALANCED",
        fail_profiles: set[str] | None = None,
    ) -> None:
        self.current = current
        self.fail_profiles = fail_profiles or set()
        self.calls: list[str] = []

    def apply_power_profile(self, profile: str) -> str:
        self.calls.append(profile)
        if profile in self.fail_profiles:
            raise RuntimeError("simulated profile failure")
        self.current = profile.upper()
        return self.current

    def get_current_power_profile(self) -> str:
        return self.current


class MobileModePowerPolicyTests(unittest.TestCase):
    def service(
        self,
        external_power_online: bool | None,
        *,
        available: set[str] | None = None,
    ) -> MobilePowerPolicyService:
        if available is None:
            available = {
                "balanced",
                "performance",
                "power-saver",
            }
        return MobilePowerPolicyService(
            POLICY,
            power_monitor=FakePowerMonitor(external_power_online),
            available_profile_reader=lambda: set(available),
        )

    def test_manifest_matches_approved_policy(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(payload["stage"], "5b-mobile-mode-policy")
        self.assertEqual(
            payload["modes"],
            {
                "chill": {"battery": "power-saver", "ac": "balanced"},
                "focus": {"battery": "power-saver", "ac": "balanced"},
                "maker": {"battery": "balanced", "ac": "balanced"},
                "development": {"battery": "balanced", "ac": "performance"},
                "command": {"battery": "balanced", "ac": "balanced"},
            },
        )
        self.assertEqual(
            payload["fallbacks"]["apply_failure"],
            "continue-workspace-activation",
        )

    def test_chill_and_focus_save_power_on_battery(self) -> None:
        service = self.service(False)
        for mode_id in ("chill", "focus"):
            decision = service.resolve(mode_id, "unchanged")
            self.assertEqual(decision.power_source, "BATTERY")
            self.assertEqual(decision.resolved_profile, "power-saver")

    def test_development_uses_performance_only_on_ac(self) -> None:
        battery = self.service(False).resolve("development", "unchanged")
        ac = self.service(True).resolve("development", "unchanged")
        self.assertEqual(battery.resolved_profile, "balanced")
        self.assertEqual(ac.resolved_profile, "performance")

    def test_command_and_maker_are_balanced(self) -> None:
        for external in (False, True):
            service = self.service(external)
            for mode_id in ("command", "maker"):
                self.assertEqual(
                    service.resolve(mode_id, "unchanged").resolved_profile,
                    "balanced",
                )

    def test_unknown_power_source_falls_back_to_balanced(self) -> None:
        decision = self.service(None).resolve("chill", "unchanged")
        self.assertEqual(decision.power_source, "UNKNOWN")
        self.assertEqual(decision.resolved_profile, "balanced")
        self.assertIn("power-source-unavailable", decision.fallback_reason)

    def test_explicit_mode_override_has_precedence(self) -> None:
        decision = self.service(False).resolve("chill", "performance")
        self.assertEqual(decision.power_source, "EXPLICIT")
        self.assertEqual(decision.resolved_profile, "performance")

    def test_unavailable_performance_falls_back_to_balanced(self) -> None:
        service = self.service(
            True,
            available={"balanced", "power-saver"},
        )
        decision = service.resolve("development", "unchanged")
        self.assertEqual(decision.policy_profile, "performance")
        self.assertEqual(decision.resolved_profile, "balanced")
        self.assertIn("requested-profile-unavailable", decision.fallback_reason)

    def test_apply_failure_does_not_raise_or_abort_policy(self) -> None:
        service = self.service(True)
        controller = FakeController(
            fail_profiles={"performance", "balanced"}
        )
        result = service.apply(
            controller,
            "development",
            "unchanged",
        )
        self.assertEqual(result.status, "NOT MANAGED")
        self.assertEqual(result.applied_profile, "NOT MANAGED")
        self.assertIn("profile-apply-failed", result.fallback_reason)

    def test_apply_can_recover_to_balanced(self) -> None:
        service = self.service(True)
        controller = FakeController(fail_profiles={"performance"})
        result = service.apply(
            controller,
            "development",
            "unchanged",
        )
        self.assertEqual(controller.calls, ["performance", "balanced"])
        self.assertEqual(result.status, "FALLBACK")
        self.assertEqual(result.resolved_profile, "balanced")
        self.assertEqual(result.applied_profile, "BALANCED")

    def test_custom_mode_keeps_legacy_unchanged_behavior(self) -> None:
        service = self.service(False)
        controller = FakeController(current="POWER-SAVER")
        result = service.apply(controller, "custom-lab", "unchanged")
        self.assertEqual(result.status, "UNCHANGED")
        self.assertEqual(result.applied_profile, "POWER-SAVER")
        self.assertEqual(controller.calls, [])

    def test_main_integrates_policy_for_restore_and_activation(self) -> None:
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn(
            "from services.mobile_power_policy import MobilePowerPolicyService",
            text,
        )
        self.assertEqual(
            text.count("self.mobile_power_policy.apply("),
            2,
        )
        self.assertNotIn(
            "power_profile = self.mode_service.apply_power_profile(\n"
            "                mode.power_profile",
            text,
        )


if __name__ == "__main__":
    unittest.main()
