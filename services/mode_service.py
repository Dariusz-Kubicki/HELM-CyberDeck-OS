from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from services.runtime_data import (
    RuntimeJsonStore,
    runtime_data_path,
)


@dataclass(frozen=True, slots=True)
class ApplicationSpec:
    name: str
    kind: str
    enabled: bool
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


@dataclass(frozen=True, slots=True)
class ModeMutationResult:
    action: str
    status: str
    mode_id: str | None
    detail: str


class ModeService:
    """Loads, validates and safely edits HELM workspaces."""

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

    def __init__(
        self,
        config_path: Path | None = None,
        state_path: Path | None = None,
        *,
        legacy_config_path: Path | None = None,
        example_config_path: Path | None = None,
        legacy_state_path: Path | None = None,
        example_state_path: Path | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        repository_config = project_root / "config"

        using_default_config = config_path is None
        using_default_state = state_path is None

        self.config_path = (
            Path(config_path)
            if config_path is not None
            else runtime_data_path("modes.json")
        )

        self.state_path = (
            Path(state_path)
            if state_path is not None
            else runtime_data_path("mode_state.json")
        )

        resolved_legacy_config = (
            Path(legacy_config_path)
            if legacy_config_path is not None
            else (
                repository_config / "modes.json"
                if using_default_config
                else None
            )
        )

        resolved_example_config = (
            Path(example_config_path)
            if example_config_path is not None
            else repository_config / "modes.example.json"
        )

        resolved_legacy_state = (
            Path(legacy_state_path)
            if legacy_state_path is not None
            else (
                repository_config / "mode_state.json"
                if using_default_state
                else None
            )
        )

        resolved_example_state = (
            Path(example_state_path)
            if example_state_path is not None
            else repository_config / "mode_state.example.json"
        )

        self._mode_store = RuntimeJsonStore(
            filename="modes.json",
            target_path=self.config_path,
            legacy_path=resolved_legacy_config,
            example_path=resolved_example_config,
            default_factory=self._default_modes_payload,
        )

        self._state_store = RuntimeJsonStore(
            filename="mode_state.json",
            target_path=self.state_path,
            legacy_path=resolved_legacy_state,
            example_path=resolved_example_state,
            default_factory=self._default_state_payload,
        )

        self._modes: tuple[WorkMode, ...] = ()

    def load_modes(self) -> tuple[WorkMode, ...]:
        payload = self._read_payload()
        raw_modes = payload["modes"]

        modes = tuple(
            self._parse_mode(item)
            for item in raw_modes
            if isinstance(item, dict)
        )

        if not modes:
            raise RuntimeError(
                "No valid workspaces configured"
            )

        mode_ids = [
            mode.mode_id
            for mode in modes
        ]

        if len(mode_ids) != len(set(mode_ids)):
            raise RuntimeError(
                "Workspace IDs must be unique"
            )

        self._modes = modes
        return modes

    def get_mode(
        self,
        mode_id: str,
    ) -> WorkMode | None:
        # Always reload so edits made from MODES work immediately.
        self.load_modes()

        return next(
            (
                mode
                for mode in self._modes
                if mode.mode_id == mode_id
            ),
            None,
        )

    def create_mode(
        self,
        fields: dict[str, Any],
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_modes = payload["modes"]

            name = str(
                fields.get("name", "")
            ).strip()

            if not name:
                return self._failed(
                    "CREATE",
                    "Workspace name cannot be empty.",
                )

            existing_ids = {
                str(mode.get("id", ""))
                for mode in raw_modes
                if isinstance(mode, dict)
            }

            mode_id = self._unique_id(
                self._slugify(name),
                existing_ids,
            )

            raw_mode = self._normalise_mode(
                {
                    **fields,
                    "id": mode_id,
                    "applications": [],
                },
                forced_id=mode_id,
            )

            raw_modes.append(raw_mode)
            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="CREATE",
                status="CREATED",
                mode_id=mode_id,
                detail=f"Created {raw_mode['name']}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "CREATE",
                f"{type(error).__name__}: {error}",
            )

    def update_mode(
        self,
        mode_id: str,
        fields: dict[str, Any],
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_modes = payload["modes"]

            for index, raw_mode in enumerate(raw_modes):
                if not isinstance(raw_mode, dict):
                    continue

                if str(raw_mode.get("id")) != mode_id:
                    continue

                updated = self._normalise_mode(
                    {
                        **raw_mode,
                        **fields,
                    },
                    forced_id=mode_id,
                )

                raw_modes[index] = updated
                self._write_payload(payload)
                self.load_modes()

                return ModeMutationResult(
                    action="UPDATE",
                    status="SAVED",
                    mode_id=mode_id,
                    detail=f"Updated {updated['name']}",
                )

            return ModeMutationResult(
                action="UPDATE",
                status="NOT FOUND",
                mode_id=mode_id,
                detail="Workspace does not exist.",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "UPDATE",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def clone_mode(
        self,
        mode_id: str,
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_modes = payload["modes"]

            source = next(
                (
                    mode
                    for mode in raw_modes
                    if (
                        isinstance(mode, dict)
                        and str(mode.get("id")) == mode_id
                    )
                ),
                None,
            )

            if source is None:
                return ModeMutationResult(
                    action="CLONE",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Workspace does not exist.",
                )

            existing_ids = {
                str(mode.get("id", ""))
                for mode in raw_modes
                if isinstance(mode, dict)
            }

            source_name = str(
                source.get("name", mode_id)
            )

            cloned_id = self._unique_id(
                self._slugify(
                    f"{source_name}-copy"
                ),
                existing_ids,
            )

            cloned = copy.deepcopy(source)
            cloned["id"] = cloned_id
            cloned["name"] = f"{source_name} COPY"

            cloned = self._normalise_mode(
                cloned,
                forced_id=cloned_id,
            )

            raw_modes.append(cloned)
            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="CLONE",
                status="CREATED",
                mode_id=cloned_id,
                detail=f"Cloned {source_name}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "CLONE",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def delete_mode(
        self,
        mode_id: str,
        *,
        protected_mode_id: str | None = None,
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_modes = payload["modes"]

            if mode_id == protected_mode_id:
                return ModeMutationResult(
                    action="DELETE",
                    status="BLOCKED",
                    mode_id=mode_id,
                    detail=(
                        "The active workspace cannot be deleted. "
                        "Activate another workspace first."
                    ),
                )

            valid_modes = [
                mode
                for mode in raw_modes
                if isinstance(mode, dict)
            ]

            if len(valid_modes) <= 1:
                return ModeMutationResult(
                    action="DELETE",
                    status="BLOCKED",
                    mode_id=mode_id,
                    detail=(
                        "At least one workspace must remain."
                    ),
                )

            remaining: list[dict] = []
            deleted_name: str | None = None

            for raw_mode in valid_modes:
                if str(raw_mode.get("id")) == mode_id:
                    deleted_name = str(
                        raw_mode.get("name", mode_id)
                    )
                    continue

                remaining.append(raw_mode)

            if deleted_name is None:
                return ModeMutationResult(
                    action="DELETE",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Workspace does not exist.",
                )

            payload["modes"] = remaining
            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="DELETE",
                status="DELETED",
                mode_id=mode_id,
                detail=f"Deleted {deleted_name}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "DELETE",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def toggle_application(
        self,
        mode_id: str,
        application_index: int,
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_mode = self._find_raw_mode(
                payload,
                mode_id,
            )

            if raw_mode is None:
                return ModeMutationResult(
                    action="APPLICATION",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Workspace does not exist.",
                )

            applications = raw_mode.get(
                "applications",
                [],
            )

            if (
                not isinstance(applications, list)
                or not 0 <= application_index < len(applications)
            ):
                return ModeMutationResult(
                    action="APPLICATION",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Application does not exist.",
                )

            application = applications[
                application_index
            ]

            if not isinstance(application, dict):
                return ModeMutationResult(
                    action="APPLICATION",
                    status="FAILED",
                    mode_id=mode_id,
                    detail="Invalid application entry.",
                )

            enabled = not bool(
                application.get("enabled", True)
            )

            application["enabled"] = enabled

            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="APPLICATION",
                status="SAVED",
                mode_id=mode_id,
                detail=(
                    f"{application.get('name', 'Application')} "
                    f"{'enabled' if enabled else 'disabled'}"
                ),
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "APPLICATION",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def add_browser_application(
        self,
        mode_id: str,
        name: str,
        urls: str | list[str],
    ) -> ModeMutationResult:
        try:
            application_name = name.strip()

            if not application_name:
                return self._failed(
                    "ADD APPLICATION",
                    "Application name cannot be empty.",
                    mode_id,
                )

            if isinstance(urls, str):
                raw_urls = re.split(
                    r"[\n,]+",
                    urls,
                )
            else:
                raw_urls = list(urls)

            normalised_urls = tuple(
                self._normalise_url(url)
                for url in raw_urls
                if str(url).strip()
            )

            if not normalised_urls:
                return self._failed(
                    "ADD APPLICATION",
                    "At least one valid URL is required.",
                    mode_id,
                )

            payload = self._read_payload()
            raw_mode = self._find_raw_mode(
                payload,
                mode_id,
            )

            if raw_mode is None:
                return ModeMutationResult(
                    action="ADD APPLICATION",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Workspace does not exist.",
                )

            applications = raw_mode.setdefault(
                "applications",
                [],
            )

            if not isinstance(applications, list):
                raise ValueError(
                    "'applications' must be a list."
                )

            applications.append(
                {
                    "name": application_name,
                    "kind": "browser",
                    "enabled": True,
                    "urls": list(normalised_urls),
                }
            )

            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="ADD APPLICATION",
                status="CREATED",
                mode_id=mode_id,
                detail=f"Added {application_name}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "ADD APPLICATION",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def remove_application(
        self,
        mode_id: str,
        application_index: int,
    ) -> ModeMutationResult:
        try:
            payload = self._read_payload()
            raw_mode = self._find_raw_mode(
                payload,
                mode_id,
            )

            if raw_mode is None:
                return ModeMutationResult(
                    action="REMOVE APPLICATION",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Workspace does not exist.",
                )

            applications = raw_mode.get(
                "applications",
                [],
            )

            if (
                not isinstance(applications, list)
                or not 0 <= application_index < len(applications)
            ):
                return ModeMutationResult(
                    action="REMOVE APPLICATION",
                    status="NOT FOUND",
                    mode_id=mode_id,
                    detail="Application does not exist.",
                )

            removed = applications.pop(
                application_index
            )

            removed_name = (
                str(removed.get("name", "Application"))
                if isinstance(removed, dict)
                else "Application"
            )

            self._write_payload(payload)
            self.load_modes()

            return ModeMutationResult(
                action="REMOVE APPLICATION",
                status="DELETED",
                mode_id=mode_id,
                detail=f"Removed {removed_name}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            return self._failed(
                "REMOVE APPLICATION",
                f"{type(error).__name__}: {error}",
                mode_id,
            )

    def load_active_mode(self) -> str:
        try:
            payload = self._state_store.read(
                self._validate_state_payload
            )

            return str(
                payload.get(
                    "active_mode",
                    "command",
                )
            )

        except (
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            json.JSONDecodeError,
        ):
            return "command"

    def save_active_mode(
        self,
        mode_id: str,
    ) -> None:
        self._state_store.write(
            {
                "active_mode": mode_id,
            },
            self._validate_state_payload,
        )

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
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return "NOT MANAGED"

        if result.returncode != 0:
            return "NOT MANAGED"

        return (
            result.stdout.strip().upper()
            or "NOT MANAGED"
        )

    def apply_power_profile(
        self,
        profile: str,
    ) -> str:
        normalised = profile.lower().strip()

        if normalised == "unchanged":
            return "UNCHANGED"

        if normalised not in self.ALLOWED_POWER_PROFILES:
            return "INVALID"

        if shutil.which("powerprofilesctl") is None:
            return "NOT MANAGED"

        try:
            result = subprocess.run(
                [
                    "powerprofilesctl",
                    "set",
                    normalised,
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return "NOT MANAGED"

        if result.returncode != 0:
            return "NOT MANAGED"

        return self.get_current_power_profile()

    def _parse_mode(
        self,
        item: dict,
    ) -> WorkMode:
        mode_id = str(
            item.get("id", "")
        ).strip().lower()

        if not mode_id:
            raise RuntimeError(
                "Workspace without an ID detected"
            )

        target_screen = str(
            item.get(
                "target_screen",
                "system",
            )
        ).lower()

        if target_screen not in self.ALLOWED_SCREENS:
            target_screen = "system"

        power_profile = str(
            item.get(
                "power_profile",
                "unchanged",
            )
        ).lower()

        if (
            power_profile
            not in self.ALLOWED_POWER_PROFILES
        ):
            power_profile = "unchanged"

        try:
            telemetry_interval = float(
                item.get(
                    "telemetry_interval",
                    1.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            telemetry_interval = 1.0

        telemetry_interval = max(
            0.5,
            min(telemetry_interval, 10.0),
        )

        raw_features = item.get(
            "features",
            [],
        )

        raw_applications = item.get(
            "applications",
            [],
        )

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
            name=str(
                item.get("name", mode_id)
            ).upper(),
            description=str(
                item.get("description", "")
            ),
            telemetry_interval=telemetry_interval,
            target_screen=target_screen,
            navigation_logging=bool(
                item.get(
                    "navigation_logging",
                    True,
                )
            ),
            workload_profile=str(
                item.get(
                    "workload_profile",
                    "BALANCED",
                )
            ).upper(),
            power_profile=power_profile,
            objective=str(
                item.get("objective", "")
            ),
            features=tuple(
                str(feature)
                for feature in raw_features
            ),
            applications=applications,
        )

    @staticmethod
    def _parse_application(
        item: dict,
    ) -> ApplicationSpec:
        kind = str(
            item.get(
                "kind",
                "application",
            )
        ).strip().lower()

        if kind not in {
            "application",
            "browser",
        }:
            kind = "application"

        raw_alternatives = item.get(
            "alternatives",
            [],
        )

        alternatives: list[
            tuple[str, ...]
        ] = []

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
                    alternatives.append(
                        tuple(command)
                    )

        raw_process_names = item.get(
            "process_names",
            [],
        )

        if not isinstance(
            raw_process_names,
            list,
        ):
            raw_process_names = []

        raw_urls = item.get(
            "urls",
            [],
        )

        if not isinstance(raw_urls, list):
            raw_urls = []

        working_directory = item.get(
            "working_directory"
        )

        if working_directory is not None:
            working_directory = str(
                working_directory
            )

        return ApplicationSpec(
            name=str(
                item.get(
                    "name",
                    "Application",
                )
            ),
            kind=kind,
            enabled=bool(
                item.get("enabled", True)
            ),
            alternatives=tuple(alternatives),
            process_names=tuple(
                str(name)
                for name in raw_process_names
            ),
            skip_if_running=bool(
                item.get(
                    "skip_if_running",
                    True,
                )
            ),
            working_directory=working_directory,
            urls=tuple(
                str(url)
                for url in raw_urls
                if str(url).strip()
            ),
        )

    def _normalise_mode(
        self,
        item: dict[str, Any],
        *,
        forced_id: str,
    ) -> dict[str, Any]:
        name = str(
            item.get("name", "")
        ).strip()

        if not name:
            raise ValueError(
                "Workspace name cannot be empty."
            )

        target_screen = str(
            item.get(
                "target_screen",
                "system",
            )
        ).strip().lower()

        if target_screen not in self.ALLOWED_SCREENS:
            target_screen = "system"

        power_profile = str(
            item.get(
                "power_profile",
                "unchanged",
            )
        ).strip().lower()

        if (
            power_profile
            not in self.ALLOWED_POWER_PROFILES
        ):
            power_profile = "unchanged"

        try:
            telemetry = float(
                item.get(
                    "telemetry_interval",
                    1.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            telemetry = 1.0

        telemetry = max(
            0.5,
            min(telemetry, 10.0),
        )

        raw_features = item.get(
            "features",
            [],
        )

        if isinstance(raw_features, str):
            features = [
                line.strip()
                for line in raw_features.splitlines()
                if line.strip()
            ]

        elif isinstance(raw_features, list):
            features = [
                str(feature).strip()
                for feature in raw_features
                if str(feature).strip()
            ]

        else:
            features = []

        raw_applications = item.get(
            "applications",
            [],
        )

        applications: list[dict] = []

        if isinstance(raw_applications, list):
            for application in raw_applications:
                if not isinstance(
                    application,
                    dict,
                ):
                    continue

                cleaned = copy.deepcopy(
                    application
                )

                cleaned["name"] = str(
                    cleaned.get(
                        "name",
                        "Application",
                    )
                ).strip() or "Application"

                kind = str(
                    cleaned.get(
                        "kind",
                        "application",
                    )
                ).strip().lower()

                cleaned["kind"] = (
                    kind
                    if kind in {
                        "application",
                        "browser",
                    }
                    else "application"
                )

                cleaned["enabled"] = bool(
                    cleaned.get(
                        "enabled",
                        True,
                    )
                )

                applications.append(cleaned)

        return {
            "id": forced_id,
            "name": name.upper(),
            "description": str(
                item.get("description", "")
            ).strip(),
            "telemetry_interval": telemetry,
            "target_screen": target_screen,
            "navigation_logging": bool(
                item.get(
                    "navigation_logging",
                    True,
                )
            ),
            "workload_profile": str(
                item.get(
                    "workload_profile",
                    "BALANCED",
                )
            ).strip().upper() or "BALANCED",
            "power_profile": power_profile,
            "objective": str(
                item.get("objective", "")
            ).strip(),
            "features": features,
            "applications": applications,
        }

    @staticmethod
    def _default_modes_payload() -> dict[str, Any]:
        return {
            "modes": [
                {
                    "id": "command",
                    "name": "COMMAND",
                    "description": (
                        "Recovered default HELM workspace."
                    ),
                    "telemetry_interval": 1.0,
                    "target_screen": "system",
                    "navigation_logging": True,
                    "workload_profile": "BALANCED",
                    "power_profile": "unchanged",
                    "objective": (
                        "Keep HELM operational after "
                        "runtime data recovery."
                    ),
                    "features": [],
                    "applications": [],
                }
            ]
        }

    @staticmethod
    def _default_state_payload() -> dict[str, Any]:
        return {
            "active_mode": "command",
        }

    @staticmethod
    def _validate_modes_payload(
        payload: dict[str, Any],
    ) -> None:
        modes = payload.get("modes")

        if not isinstance(modes, list):
            raise ValueError(
                "'modes' must be a list."
            )

        valid_modes = [
            mode
            for mode in modes
            if isinstance(mode, dict)
        ]

        if not valid_modes:
            raise ValueError(
                "At least one workspace is required."
            )

        mode_ids = [
            str(mode.get("id", "")).strip()
            for mode in valid_modes
        ]

        if (
            any(not mode_id for mode_id in mode_ids)
            or len(mode_ids) != len(set(mode_ids))
        ):
            raise ValueError(
                "Workspace IDs must be present and unique."
            )

    @staticmethod
    def _validate_state_payload(
        payload: dict[str, Any],
    ) -> None:
        active_mode = payload.get("active_mode")

        if (
            not isinstance(active_mode, str)
            or not active_mode.strip()
        ):
            raise ValueError(
                "'active_mode' must be a non-empty string."
            )

    def _read_payload(
        self,
    ) -> dict[str, Any]:
        try:
            return self._mode_store.read(
                self._validate_modes_payload
            )

        except (
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            json.JSONDecodeError,
        ) as error:
            raise RuntimeError(
                f"Cannot load workspaces: {error}"
            ) from error

    def _write_payload(
        self,
        payload: dict[str, Any],
    ) -> None:
        self._mode_store.write(
            payload,
            self._validate_modes_payload,
        )

    @staticmethod
    def _find_raw_mode(
        payload: dict[str, Any],
        mode_id: str,
    ) -> dict[str, Any] | None:
        for raw_mode in payload["modes"]:
            if (
                isinstance(raw_mode, dict)
                and str(raw_mode.get("id")) == mode_id
            ):
                return raw_mode

        return None

    @staticmethod
    def _normalise_url(
        value: Any,
    ) -> str:
        url = str(value).strip()

        if not url:
            raise ValueError(
                "URL cannot be empty."
            )

        if "://" not in url:
            url = f"https://{url}"

        parsed = urlparse(url)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
        ):
            raise ValueError(
                f"Invalid URL: {value}"
            )

        return url

    @staticmethod
    def _slugify(
        value: str,
    ) -> str:
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            value.lower(),
        ).strip("-")

        return slug or "workspace"

    @staticmethod
    def _unique_id(
        base_id: str,
        existing_ids: set[str],
    ) -> str:
        if base_id not in existing_ids:
            return base_id

        index = 2

        while (
            f"{base_id}-{index}"
            in existing_ids
        ):
            index += 1

        return f"{base_id}-{index}"

    @staticmethod
    def _failed(
        action: str,
        detail: str,
        mode_id: str | None = None,
    ) -> ModeMutationResult:
        return ModeMutationResult(
            action=action,
            status="FAILED",
            mode_id=mode_id,
            detail=detail,
        )
