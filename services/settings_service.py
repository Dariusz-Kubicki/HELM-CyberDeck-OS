from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HelmSettings:
    telemetry_interval: float = 1.0
    start_screen: str = "system"
    navigation_logging: bool = True
    log_rows: int = 200


class SettingsService:
    """Loads, validates and saves HELM runtime settings."""

    ALLOWED_INTERVALS = (0.5, 1.0, 2.0, 5.0)

    ALLOWED_START_SCREENS = (
        "system",
        "network",
        "storage",
        "devices",
        "projects",
        "logs",
        "ai",
        "settings",
    )

    ALLOWED_LOG_ROWS = (50, 100, 200, 500)

    def __init__(self, path: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[1]

        self.path = path or project_root / "config" / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def defaults() -> HelmSettings:
        return HelmSettings()

    def load(self) -> HelmSettings:
        if not self.path.exists():
            settings = self.defaults()
            self.save(settings)
            return settings

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self.defaults()

        if not isinstance(payload, dict):
            return self.defaults()

        defaults = self.defaults()

        interval = self._validated_float(
            payload.get("telemetry_interval"),
            self.ALLOWED_INTERVALS,
            defaults.telemetry_interval,
        )

        start_screen = str(
            payload.get("start_screen", defaults.start_screen)
        ).lower()

        if start_screen not in self.ALLOWED_START_SCREENS:
            start_screen = defaults.start_screen

        navigation_logging = payload.get(
            "navigation_logging",
            defaults.navigation_logging,
        )

        if not isinstance(navigation_logging, bool):
            navigation_logging = defaults.navigation_logging

        log_rows = self._validated_int(
            payload.get("log_rows"),
            self.ALLOWED_LOG_ROWS,
            defaults.log_rows,
        )

        return HelmSettings(
            telemetry_interval=interval,
            start_screen=start_screen,
            navigation_logging=navigation_logging,
            log_rows=log_rows,
        )

    def save(self, settings: HelmSettings) -> None:
        temporary_path = self.path.with_suffix(".json.tmp")

        temporary_path.write_text(
            json.dumps(
                asdict(settings),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(self.path)

    @staticmethod
    def _validated_float(
        value: object,
        allowed: tuple[float, ...],
        default: float,
    ) -> float:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return default

        return converted if converted in allowed else default

    @staticmethod
    def _validated_int(
        value: object,
        allowed: tuple[int, ...],
        default: int,
    ) -> int:
        try:
            converted = int(value)
        except (TypeError, ValueError):
            return default

        return converted if converted in allowed else default
