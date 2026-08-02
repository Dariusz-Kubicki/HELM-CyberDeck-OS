from __future__ import annotations

import copy
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


JsonObject = dict[str, Any]
Validator = Callable[[JsonObject], None]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_data_root() -> Path:
    explicit = os.environ.get("HELM_DATA_DIR", "").strip()

    if explicit:
        return Path(explicit).expanduser()

    xdg_data_home = os.environ.get(
        "XDG_DATA_HOME",
        "",
    ).strip()

    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "helm"

    return Path.home() / ".local" / "share" / "helm"


def runtime_data_path(filename: str) -> Path:
    return runtime_data_root() / filename


class RuntimeJsonStore:
    """Resilient JSON storage outside the Git working tree."""

    def __init__(
        self,
        *,
        filename: str,
        target_path: Path | None = None,
        legacy_path: Path | None = None,
        example_path: Path | None = None,
        default_factory: Callable[[], JsonObject] | None = None,
    ) -> None:
        self.path = (
            Path(target_path)
            if target_path is not None
            else runtime_data_path(filename)
        )

        self.legacy_path = (
            Path(legacy_path)
            if legacy_path is not None
            else None
        )

        self.example_path = (
            Path(example_path)
            if example_path is not None
            else None
        )

        self.default_factory = default_factory

        self.recovery_directory = (
            self.path.parent / "recovery"
        )

        self.last_good_path = (
            self.recovery_directory
            / f"{self.path.stem}.last-good.json"
        )

    def ensure(
        self,
        validator: Validator | None = None,
    ) -> Path:
        if not self.path.exists():
            self.read(validator)

        return self.path

    def read(
        self,
        validator: Validator | None = None,
    ) -> JsonObject:
        payload = self._load_or_recover(validator)

        self._atomic_write(
            self.last_good_path,
            payload,
        )

        return copy.deepcopy(payload)

    def write(
        self,
        payload: JsonObject,
        validator: Validator | None = None,
    ) -> None:
        validated = self._validate_payload(
            payload,
            validator,
        )

        self._atomic_write(
            self.path,
            validated,
        )

        self._atomic_write(
            self.last_good_path,
            validated,
        )

    def _load_or_recover(
        self,
        validator: Validator | None,
    ) -> JsonObject:
        if self.path.exists():
            try:
                return self._read_valid(
                    self.path,
                    validator,
                )
            except (
                OSError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ):
                self._quarantine_broken_file()

        for candidate in (
            self.last_good_path,
            self.legacy_path,
            self.example_path,
        ):
            if (
                candidate is None
                or candidate == self.path
                or not candidate.is_file()
            ):
                continue

            try:
                payload = self._read_valid(
                    candidate,
                    validator,
                )
            except (
                OSError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ):
                continue

            self._atomic_write(
                self.path,
                payload,
            )

            return payload

        if self.default_factory is None:
            raise RuntimeError(
                "No valid runtime JSON source is available "
                f"for {self.path.name}."
            )

        payload = self._validate_payload(
            self.default_factory(),
            validator,
        )

        self._atomic_write(
            self.path,
            payload,
        )

        return payload

    def _quarantine_broken_file(self) -> None:
        if not self.path.exists():
            return

        self.recovery_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S-%f"
        )

        destination = (
            self.recovery_directory
            / (
                f"{self.path.stem}-{timestamp}"
                ".broken.json"
            )
        )

        shutil.copy2(
            self.path,
            destination,
        )

        self.path.unlink(missing_ok=True)

    @staticmethod
    def _validate_payload(
        payload: JsonObject,
        validator: Validator | None,
    ) -> JsonObject:
        if not isinstance(payload, dict):
            raise ValueError(
                "Runtime JSON root must be an object."
            )

        cloned = copy.deepcopy(payload)

        if validator is not None:
            validator(cloned)

        return cloned

    def _read_valid(
        self,
        path: Path,
        validator: Validator | None,
    ) -> JsonObject:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        return self._validate_payload(
            payload,
            validator,
        )

    @staticmethod
    def _atomic_write(
        path: Path,
        payload: JsonObject,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = path.with_name(
            f".{path.name}.{os.getpid()}.tmp"
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
            temporary_path.unlink(
                missing_ok=True
            )

