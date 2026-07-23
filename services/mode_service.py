from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ApplicationSpec:
    name: str
    kind: str
    alternatives: tuple[tuple[str, ...], ...]
    process_names: tuple[str, ...]
    skip_if_running: bool
    working_directory: str | None
    urls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkMode:
    mode_id: str
    name: str
    description: str
    telemetry_interval: float
    target_screen: str
    navigation_logging: bool
    workload_profile: str
    power_profile: str
    objective: str
    features: tuple[str, ...]
    applications: tuple[ApplicationSpec, ...]


class ModeService:
    """Loads, validates and stores HELM workspace modes."""

    ALLOWED_SCREENS = {
        "system",
        "network",
        "storage",
        "devices",
        "modes",
        "projects",
        "logs",
        "ai",
        "settings",
    }

    ALLOWED_POWER_PROFILES = {
        "balanced",
        "performance",
        "power-saver",
        "unchanged",
    }

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[1]

        self.config_path = project_root / "config" / "modes.json"
        self.state_path = project_root / "config" / "mode_state.json"
        self._modes: tuple[WorkMode, ...] = ()

    def load_modes(self) -> tuple[WorkMode, ...]:
        try:
            payload = json.loads(
                self.config_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Cannot load workspaces: {error}"
            ) from error

        raw_modes = payload.get("modes", [])

        if not isinstance(raw_modes, list):
            raise RuntimeError("'modes' must be a list")

        modes = tuple(
            self._parse_mode(item)
            for item in raw_modes
            if isinstance(item, dict)
        )

        if not modes:
            raise RuntimeError("No valid workspaces configured")

        mode_ids = [mode.mode_id for mode in modes]

        if len(mode_ids) != len(set(mode_ids)):
            raise RuntimeError("Workspace IDs must be unique")

        self._modes = modes
        return modes

    def get_mode(self, mode_id: str) -> WorkMode | None:
        if not self._modes:
            self.load_modes()

        return next(
            (
                mode
                for mode in self._modes
                if mode.mode_id == mode_id
            ),
            None,
        )

    def load_active_mode(self) -> str:
        try:
            payload = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )
            return str(payload.get("active_mode", "command"))

        except (OSError, json.JSONDecodeError):
            return "command"

    def save_active_mode(self, mode_id: str) -> None:
        temporary_path = self.state_path.with_suffix(".json.tmp")

        temporary_path.write_text(
            json.dumps(
                {"active_mode": mode_id},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(self.state_path)

    def get_current_power_profile(self) -> str:
        if shutil.which("powerprofilesctl") is None:
            return "NOT MANAGED"

        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "NOT MANAGED"

        if result.returncode != 0:
            return "NOT MANAGED"

        return result.stdout.strip().upper() or "NOT MANAGED"

    def apply_power_profile(self, profile: str) -> str:
        normalized = profile.lower().strip()

        if normalized == "unchanged":
            return "UNCHANGED"

        if normalized not in self.ALLOWED_POWER_PROFILES:
            return "INVALID"

        if shutil.which("powerprofilesctl") is None:
            return "NOT MANAGED"

        try:
            result = subprocess.run(
                ["powerprofilesctl", "set", normalized],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "NOT MANAGED"

        if result.returncode != 0:
            return "NOT MANAGED"

        return self.get_current_power_profile()

    def _parse_mode(self, item: dict) -> WorkMode:
        mode_id = str(item.get("id", "")).strip().lower()

        if not mode_id:
            raise RuntimeError("Workspace without an ID detected")

        target_screen = str(
            item.get("target_screen", "system")
        ).lower()

        if target_screen not in self.ALLOWED_SCREENS:
            target_screen = "system"

        power_profile = str(
            item.get("power_profile", "unchanged")
        ).lower()

        if power_profile not in self.ALLOWED_POWER_PROFILES:
            power_profile = "unchanged"

        try:
            telemetry_interval = float(
                item.get("telemetry_interval", 1.0)
            )
        except (TypeError, ValueError):
            telemetry_interval = 1.0

        telemetry_interval = max(
            0.5,
            min(telemetry_interval, 10.0),
        )

        raw_features = item.get("features", [])
        raw_applications = item.get("applications", [])

        if not isinstance(raw_features, list):
            raw_features = []

        if not isinstance(raw_applications, list):
            raw_applications = []

        applications = tuple(
            self._parse_application(application)
            for application in raw_applications
            if isinstance(application, dict)
        )

        return WorkMode(
            mode_id=mode_id,
            name=str(item.get("name", mode_id)).upper(),
            description=str(item.get("description", "")),
            telemetry_interval=telemetry_interval,
            target_screen=target_screen,
            navigation_logging=bool(
                item.get("navigation_logging", True)
            ),
            workload_profile=str(
                item.get("workload_profile", "BALANCED")
            ).upper(),
            power_profile=power_profile,
            objective=str(item.get("objective", "")),
            features=tuple(
                str(feature)
                for feature in raw_features
            ),
            applications=applications,
        )

    @staticmethod
    def _parse_application(item: dict) -> ApplicationSpec:
        kind = str(
            item.get("kind", "application")
        ).strip().lower()

        if kind not in {"application", "browser"}:
            kind = "application"

        raw_alternatives = item.get("alternatives", [])
        alternatives: list[tuple[str, ...]] = []

        if isinstance(raw_alternatives, list):
            for command in raw_alternatives:
                if (
                    isinstance(command, list)
                    and command
                    and all(
                        isinstance(argument, str)
                        for argument in command
                    )
                ):
                    alternatives.append(tuple(command))

        raw_process_names = item.get("process_names", [])

        if not isinstance(raw_process_names, list):
            raw_process_names = []

        raw_urls = item.get("urls", [])

        if not isinstance(raw_urls, list):
            raw_urls = []

        working_directory = item.get("working_directory")

        if working_directory is not None:
            working_directory = str(working_directory)

        return ApplicationSpec(
            name=str(item.get("name", "Application")),
            kind=kind,
            alternatives=tuple(alternatives),
            process_names=tuple(
                str(name)
                for name in raw_process_names
            ),
            skip_if_running=bool(
                item.get("skip_if_running", True)
            ),
            working_directory=working_directory,
            urls=tuple(
                str(url)
                for url in raw_urls
                if str(url).strip()
            ),
        )
