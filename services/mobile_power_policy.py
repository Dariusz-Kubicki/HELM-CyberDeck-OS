from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from modules.power import PowerMonitor, PowerSample


_MANAGED_PROFILES = {
    "balanced",
    "performance",
    "power-saver",
}
_ALLOWED_MODE_PROFILES = _MANAGED_PROFILES | {"unchanged"}


class ModePowerController(Protocol):
    def apply_power_profile(self, profile: str) -> str: ...

    def get_current_power_profile(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ModePowerDecision:
    mode_id: str
    power_source: str
    policy_profile: str
    resolved_profile: str
    fallback_reason: str


@dataclass(frozen=True, slots=True)
class ModePowerApplyResult:
    mode_id: str
    power_source: str
    policy_profile: str
    resolved_profile: str
    applied_profile: str
    fallback_reason: str
    status: str


class MobilePowerPolicyService:
    """Resolve and safely apply Mobile Node workspace power policy."""

    def __init__(
        self,
        policy_path: Path | None = None,
        *,
        power_monitor: PowerMonitor | None = None,
        available_profile_reader: Callable[[], set[str] | None] | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.policy_path = (
            Path(policy_path)
            if policy_path is not None
            else project_root / "mobile" / "modes" / "power-policy.json"
        )
        self.power_monitor = power_monitor or PowerMonitor()
        self._available_profile_reader = (
            available_profile_reader
            if available_profile_reader is not None
            else self._read_available_profiles
        )
        self._policy, self.load_error = self._load_policy()

    def resolve(
        self,
        mode_id: str,
        explicit_profile: str,
    ) -> ModePowerDecision:
        mode_key = str(mode_id).strip().lower()
        explicit = self._normalise_profile(explicit_profile)
        reasons: list[str] = []

        try:
            sample = self.power_monitor.sample()
        except Exception:
            sample = PowerSample.unavailable()
            reasons.append("power-sample-unavailable")

        if explicit != "unchanged":
            policy_profile = explicit
            power_source = "EXPLICIT"
        else:
            mode_policy = self._mode_policy(mode_key)

            if mode_policy is None:
                policy_profile = "unchanged"
                power_source = "UNMANAGED"
            elif sample.external_power_online is True:
                policy_profile = mode_policy["ac"]
                power_source = "AC"
            elif sample.external_power_online is False:
                policy_profile = mode_policy["battery"]
                power_source = "BATTERY"
            else:
                policy_profile = self._fallback_profile(
                    "unknown_power_source"
                )
                power_source = "UNKNOWN"
                reasons.append("power-source-unavailable")

        resolved_profile = policy_profile

        if resolved_profile in _MANAGED_PROFILES:
            available = self._safe_available_profiles()
            if available and resolved_profile not in available:
                resolved_profile = self._fallback_profile(
                    "unavailable_profile"
                )
                reasons.append("requested-profile-unavailable")

        return ModePowerDecision(
            mode_id=mode_key,
            power_source=power_source,
            policy_profile=policy_profile,
            resolved_profile=resolved_profile,
            fallback_reason=",".join(reasons),
        )

    def policy_target_for_source(
        self,
        mode_id: str,
        explicit_profile: str,
        external_power_online: bool | None,
    ) -> str:
        # Resolve configured mode target without sampling or applying power.
        mode_key = str(mode_id).strip().lower()
        explicit = self._normalise_profile(explicit_profile)

        if explicit != "unchanged":
            return explicit

        mode_policy = self._mode_policy(mode_key)
        if mode_policy is None:
            return "unchanged"

        if external_power_online is True:
            return mode_policy["ac"]

        if external_power_online is False:
            return mode_policy["battery"]

        return self._fallback_profile(
            "unknown_power_source"
        )

    def apply(
        self,
        controller: ModePowerController,
        mode_id: str,
        explicit_profile: str,
    ) -> ModePowerApplyResult:
        decision = self.resolve(
            mode_id,
            explicit_profile,
        )
        reasons = [
            reason
            for reason in decision.fallback_reason.split(",")
            if reason
        ]

        if decision.resolved_profile == "unchanged":
            return ModePowerApplyResult(
                mode_id=decision.mode_id,
                power_source=decision.power_source,
                policy_profile=decision.policy_profile,
                resolved_profile=decision.resolved_profile,
                applied_profile=self._safe_current_profile(controller),
                fallback_reason=",".join(reasons),
                status="UNCHANGED",
            )

        target = decision.resolved_profile
        applied = self._safe_apply(controller, target)

        if self._normalise_runtime_profile(applied) == target:
            status = "APPLIED"
        else:
            status = "NOT MANAGED"
            reasons.append("profile-apply-failed")

            if target != "balanced":
                fallback = self._fallback_profile("unavailable_profile")
                if fallback == "balanced":
                    balanced_result = self._safe_apply(
                        controller,
                        "balanced",
                    )
                    if (
                        self._normalise_runtime_profile(balanced_result)
                        == "balanced"
                    ):
                        target = "balanced"
                        applied = balanced_result
                        status = "FALLBACK"
                        reasons.append("balanced-fallback-applied")

        return ModePowerApplyResult(
            mode_id=decision.mode_id,
            power_source=decision.power_source,
            policy_profile=decision.policy_profile,
            resolved_profile=target,
            applied_profile=(
                str(applied).strip().upper()
                or "NOT MANAGED"
            ),
            fallback_reason=",".join(dict.fromkeys(reasons)),
            status=status,
        )

    def _load_policy(self) -> tuple[dict, str]:
        try:
            payload = json.loads(
                self.policy_path.read_text(
                    encoding="utf-8"
                )
            )
            self._validate_policy(payload)
            return payload, ""
        except Exception as error:
            return {}, f"{type(error).__name__}: {error}"

    @staticmethod
    def _validate_policy(payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("policy must be a JSON object")

        if payload.get("stage") != "5b-mobile-mode-policy":
            raise ValueError("unexpected policy stage")

        modes = payload.get("modes")
        if not isinstance(modes, dict):
            raise ValueError("modes must be an object")

        for mode_id, mapping in modes.items():
            if not isinstance(mode_id, str) or not mode_id.strip():
                raise ValueError("invalid mode id")
            if not isinstance(mapping, dict):
                raise ValueError(f"invalid policy for {mode_id}")

            for source in ("battery", "ac"):
                profile = str(mapping.get(source, "")).strip().lower()
                if profile not in _MANAGED_PROFILES:
                    raise ValueError(
                        f"invalid {source} profile for {mode_id}"
                    )

        fallbacks = payload.get("fallbacks")
        if not isinstance(fallbacks, dict):
            raise ValueError("fallbacks must be an object")

        for key in (
            "unknown_power_source",
            "unavailable_profile",
        ):
            profile = str(fallbacks.get(key, "")).strip().lower()
            if profile not in _MANAGED_PROFILES:
                raise ValueError(f"invalid fallback: {key}")

        if (
            fallbacks.get("apply_failure")
            != "continue-workspace-activation"
        ):
            raise ValueError("invalid apply-failure policy")

    def _mode_policy(
        self,
        mode_id: str,
    ) -> dict[str, str] | None:
        modes = self._policy.get("modes")
        if not isinstance(modes, dict):
            return None

        raw = modes.get(mode_id)
        if not isinstance(raw, dict):
            return None

        battery = self._normalise_profile(raw.get("battery"))
        ac = self._normalise_profile(raw.get("ac"))

        if battery not in _MANAGED_PROFILES or ac not in _MANAGED_PROFILES:
            return None

        return {
            "battery": battery,
            "ac": ac,
        }

    def _fallback_profile(self, key: str) -> str:
        fallbacks = self._policy.get("fallbacks")
        if not isinstance(fallbacks, dict):
            return "balanced"

        profile = self._normalise_profile(
            fallbacks.get(key)
        )
        if profile not in _MANAGED_PROFILES:
            return "balanced"
        return profile

    def _safe_available_profiles(self) -> set[str] | None:
        try:
            profiles = self._available_profile_reader()
        except Exception:
            return None

        if profiles is None:
            return None

        return {
            profile
            for profile in (
                self._normalise_profile(item)
                for item in profiles
            )
            if profile in _MANAGED_PROFILES
        }

    @staticmethod
    def _normalise_profile(value: object) -> str:
        profile = str(value or "unchanged").strip().lower()
        if profile not in _ALLOWED_MODE_PROFILES:
            return "unchanged"
        return profile

    @staticmethod
    def _normalise_runtime_profile(value: object) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _safe_current_profile(controller: ModePowerController) -> str:
        try:
            value = controller.get_current_power_profile()
        except Exception:
            return "NOT MANAGED"
        return str(value).strip().upper() or "NOT MANAGED"

    @staticmethod
    def _safe_apply(
        controller: ModePowerController,
        profile: str,
    ) -> str:
        try:
            return controller.apply_power_profile(profile)
        except Exception:
            return "NOT MANAGED"

    @staticmethod
    def _read_available_profiles() -> set[str] | None:
        if shutil.which("powerprofilesctl") is None:
            return None

        try:
            result = subprocess.run(
                ["powerprofilesctl", "list"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0:
            return None

        profiles: set[str] = set()
        for line in result.stdout.splitlines():
            match = re.match(
                r"^\s*\*?\s*(performance|balanced|power-saver):\s*$",
                line,
            )
            if match:
                profiles.add(match.group(1))

        return profiles or None
