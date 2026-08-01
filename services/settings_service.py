from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from services.runtime_data import (
    RuntimeJsonStore,
    runtime_data_path,
)


@dataclass(frozen=True, slots=True)
class HelmSettings:
    telemetry_interval: float = 1.0
    start_screen: str = "system"
    navigation_logging: bool = True
    log_rows: int = 200

    ai_model: str = "qwen3:8b"
    ai_context_window: int = 4096
    ai_keep_alive: str = "10m"


@dataclass(frozen=True, slots=True)
class SettingsDiagnostics:
    config_path: str
    config_exists: bool
    config_valid: bool
    config_size: int
    backup_count: int
    latest_backup: str | None
    export_count: int


class SettingsService:
    """Validates, stores, backs up and exports HELM settings."""

    SCHEMA_VERSION = 2
    MAX_BACKUPS = 10

    ALLOWED_INTERVALS = (
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
    )

    ALLOWED_START_SCREENS = (
        "system",
        "network",
        "storage",
        "devices",
        "modes",
        "projects",
        "logs",
        "ai",
        "settings",
    )

    ALLOWED_LOG_ROWS = (
        50,
        100,
        200,
        500,
        1000,
    )

    ALLOWED_AI_CONTEXTS = (
        2048,
        4096,
        8192,
        16384,
    )

    ALLOWED_AI_KEEP_ALIVE = (
        "0",
        "5m",
        "10m",
        "30m",
        "1h",
    )

    def __init__(
        self,
        path: Path | None = None,
        *,
        legacy_path: Path | None = None,
        example_path: Path | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        repository_config = project_root / "config"
        using_default_path = path is None

        self.path = (
            Path(path)
            if path is not None
            else runtime_data_path("settings.json")
        )

        resolved_legacy_path = (
            Path(legacy_path)
            if legacy_path is not None
            else (
                repository_config / "settings.json"
                if using_default_path
                else None
            )
        )

        resolved_example_path = (
            Path(example_path)
            if example_path is not None
            else repository_config / "settings.example.json"
        )

        self._store = RuntimeJsonStore(
            filename="settings.json",
            target_path=self.path,
            legacy_path=resolved_legacy_path,
            example_path=resolved_example_path,
            default_factory=lambda: asdict(
                self.defaults()
            ),
        )

        self.backup_directory = (
            self.path.parent / "backups"
        )

        self.export_directory = (
            self.path.parent / "exports"
        )

    @staticmethod
    def defaults() -> HelmSettings:
        return HelmSettings()

    def _validate_runtime_payload(
        self,
        payload: dict[str, Any],
    ) -> None:
        self._payload_to_settings(payload)

    def load(self) -> HelmSettings:
        payload = self._store.read(
            self._validate_runtime_payload
        )

        return self._payload_to_settings(payload)

    def validate(
        self,
        settings: HelmSettings,
    ) -> HelmSettings:
        return self._payload_to_settings(
            asdict(settings)
        )

    def save(
        self,
        settings: HelmSettings,
    ) -> None:
        validated = self.validate(settings)

        self._store.write(
            asdict(validated),
            self._validate_runtime_payload,
        )

    def create_backup(self) -> Path:
        if not self.path.exists():
            self.save(self.defaults())

        self.backup_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S-%f"
        )

        destination = (
            self.backup_directory
            / f"settings-{timestamp}.json"
        )

        shutil.copy2(
            self.path,
            destination,
        )

        self._prune_backups()
        return destination

    def latest_backup_path(self) -> Path:
        """Return the newest existing settings backup."""
        backups = self._backup_paths()

        if not backups:
            raise FileNotFoundError(
                "No settings backup is available."
            )

        return backups[0]

    def restore_backup(
        self,
        source: Path,
    ) -> HelmSettings:
        """Restore one explicitly selected backup."""
        source_path = Path(source).resolve()
        backup_root = self.backup_directory.resolve()

        try:
            source_path.relative_to(backup_root)
        except ValueError as error:
            raise ValueError(
                "Backup must be located inside "
                "the settings backup directory."
            ) from error

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Backup does not exist: {source_path}"
            )

        payload = self._read_json(source_path)
        settings = self._payload_to_settings(payload)

        self.save(settings)
        return settings

    def restore_latest_backup(
        self,
    ) -> tuple[HelmSettings, Path]:
        source = self.latest_backup_path()
        settings = self.restore_backup(source)

        return settings, source

    def export_profile(
        self,
        settings: HelmSettings,
    ) -> Path:
        validated = self.validate(settings)

        self.export_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        destination = (
            self.export_directory
            / f"helm-settings-{timestamp}.json"
        )

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "exported_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "settings": asdict(validated),
        }

        self._atomic_write_json(
            destination,
            payload,
        )

        return destination

    def diagnostics(self) -> SettingsDiagnostics:
        config_exists = self.path.exists()
        config_valid = False
        config_size = 0

        if config_exists:
            try:
                payload = self._read_json(self.path)
                self._payload_to_settings(payload)

                config_valid = True
                config_size = self.path.stat().st_size
            except (
                OSError,
                json.JSONDecodeError,
                ValueError,
            ):
                config_valid = False

        backups = self._backup_paths()

        exports = tuple(
            sorted(
                self.export_directory.glob(
                    "helm-settings-*.json"
                )
            )
        ) if self.export_directory.exists() else ()

        return SettingsDiagnostics(
            config_path=str(self.path),
            config_exists=config_exists,
            config_valid=config_valid,
            config_size=config_size,
            backup_count=len(backups),
            latest_backup=(
                str(backups[0])
                if backups
                else None
            ),
            export_count=len(exports),
        )

    def _payload_to_settings(
        self,
        payload: dict[str, Any],
    ) -> HelmSettings:
        if not isinstance(payload, dict):
            raise ValueError(
                "Settings root must be a JSON object."
            )

        if (
            "settings" in payload
            and isinstance(
                payload.get("settings"),
                dict,
            )
        ):
            payload = payload["settings"]

        defaults = self.defaults()

        interval = self._validated_float(
            payload.get(
                "telemetry_interval"
            ),
            self.ALLOWED_INTERVALS,
            defaults.telemetry_interval,
        )

        start_screen = str(
            payload.get(
                "start_screen",
                defaults.start_screen,
            )
        ).strip().lower()

        if (
            start_screen
            not in self.ALLOWED_START_SCREENS
        ):
            start_screen = defaults.start_screen

        navigation_logging = payload.get(
            "navigation_logging",
            defaults.navigation_logging,
        )

        if not isinstance(
            navigation_logging,
            bool,
        ):
            navigation_logging = (
                defaults.navigation_logging
            )

        log_rows = self._validated_int(
            payload.get("log_rows"),
            self.ALLOWED_LOG_ROWS,
            defaults.log_rows,
        )

        ai_model = self._validated_model(
            payload.get(
                "ai_model",
                defaults.ai_model,
            ),
            defaults.ai_model,
        )

        ai_context_window = self._validated_int(
            payload.get(
                "ai_context_window"
            ),
            self.ALLOWED_AI_CONTEXTS,
            defaults.ai_context_window,
        )

        ai_keep_alive = str(
            payload.get(
                "ai_keep_alive",
                defaults.ai_keep_alive,
            )
        ).strip().lower()

        if (
            ai_keep_alive
            not in self.ALLOWED_AI_KEEP_ALIVE
        ):
            ai_keep_alive = defaults.ai_keep_alive

        return HelmSettings(
            telemetry_interval=interval,
            start_screen=start_screen,
            navigation_logging=navigation_logging,
            log_rows=log_rows,
            ai_model=ai_model,
            ai_context_window=ai_context_window,
            ai_keep_alive=ai_keep_alive,
        )

    @staticmethod
    def _read_json(
        path: Path,
    ) -> dict[str, Any]:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, dict):
            raise ValueError(
                f"{path.name} does not contain a JSON object."
            )

        return payload

    @staticmethod
    def _atomic_write_json(
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = path.with_name(
            f".{path.name}.tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temporary_path,
                path,
            )

        finally:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

    def _backup_paths(self) -> tuple[Path, ...]:
        if not self.backup_directory.exists():
            return ()

        return tuple(
            sorted(
                self.backup_directory.glob(
                    "settings-*.json"
                ),
                reverse=True,
            )
        )

    def _prune_backups(self) -> None:
        for path in self._backup_paths()[
            self.MAX_BACKUPS:
        ]:
            try:
                path.unlink()
            except OSError:
                continue

    @staticmethod
    def _validated_model(
        value: object,
        default: str,
    ) -> str:
        model = str(value).strip()

        if (
            not model
            or len(model) > 128
            or any(
                character.isspace()
                for character in model
            )
            or any(
                character in "\r\n\t"
                for character in model
            )
        ):
            return default

        return model

    @staticmethod
    def _validated_float(
        value: object,
        allowed: tuple[float, ...],
        default: float,
    ) -> float:
        try:
            converted = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return default

        return (
            converted
            if converted in allowed
            else default
        )

    @staticmethod
    def _validated_int(
        value: object,
        allowed: tuple[int, ...],
        default: int,
    ) -> int:
        try:
            converted = int(value)
        except (
            TypeError,
            ValueError,
        ):
            return default

        return (
            converted
            if converted in allowed
            else default
        )
