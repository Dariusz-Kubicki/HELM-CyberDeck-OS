from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from services.runtime_data import (
    RuntimeJsonStore,
    runtime_data_path,
)


@dataclass(frozen=True, slots=True)
class ProjectMutationResult:
    action: str
    status: str
    project_id: str | None
    detail: str


class ProjectService:
    """Safely creates, edits and removes HELM projects."""

    STATUS_ORDER = (
        "CONCEPT",
        "PLANNING",
        "ACTIVE",
        "BUILDING",
        "TESTING",
        "BLOCKED",
        "PAUSED",
        "STABLE",
        "DONE",
    )

    def __init__(
        self,
        config_path: Path | None = None,
        *,
        legacy_path: Path | None = None,
        example_path: Path | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        repository_config = project_root / "config"
        using_default_path = config_path is None

        self.config_path = (
            Path(config_path)
            if config_path is not None
            else runtime_data_path("projects.json")
        )

        resolved_legacy_path = (
            Path(legacy_path)
            if legacy_path is not None
            else (
                repository_config / "projects.json"
                if using_default_path
                else None
            )
        )

        resolved_example_path = (
            Path(example_path)
            if example_path is not None
            else repository_config / "projects.example.json"
        )

        self._store = RuntimeJsonStore(
            filename="projects.json",
            target_path=self.config_path,
            legacy_path=resolved_legacy_path,
            example_path=resolved_example_path,
            default_factory=self._default_payload,
        )

    @staticmethod
    def _default_payload() -> dict[str, Any]:
        return {
            "projects": [],
        }

    @staticmethod
    def _validate_payload(
        payload: dict[str, Any],
    ) -> None:
        projects = payload.get("projects")

        if not isinstance(projects, list):
            raise ValueError(
                "'projects' must be a list."
            )

    def create_project(
        self,
        fields: dict[str, Any],
    ) -> ProjectMutationResult:
        try:
            payload = self._read_payload()
            projects = payload["projects"]

            name = str(
                fields.get("name", "")
            ).strip()

            if not name:
                return self._failed(
                    "CREATE",
                    "Project name cannot be empty.",
                )

            existing_ids = {
                str(project.get("id", ""))
                for project in projects
                if isinstance(project, dict)
            }

            project_id = self._unique_id(
                self._slugify(name),
                existing_ids,
            )

            project = self._normalise_project(
                {
                    **fields,
                    "id": project_id,
                }
            )

            projects.append(project)
            self._write_payload(payload)

            return ProjectMutationResult(
                action="CREATE",
                status="CREATED",
                project_id=project_id,
                detail=f"Created {project['name']}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            return self._failed(
                "CREATE",
                f"{type(error).__name__}: {error}",
            )

    def update_project(
        self,
        project_id: str,
        fields: dict[str, Any],
    ) -> ProjectMutationResult:
        try:
            payload = self._read_payload()
            projects = payload["projects"]

            for index, project in enumerate(projects):
                if not isinstance(project, dict):
                    continue

                if str(project.get("id")) != project_id:
                    continue

                updated_project = self._normalise_project(
                    {
                        **project,
                        **fields,
                        "id": project_id,
                    }
                )

                projects[index] = updated_project
                self._write_payload(payload)

                return ProjectMutationResult(
                    action="UPDATE",
                    status="SAVED",
                    project_id=project_id,
                    detail=(
                        f"Updated "
                        f"{updated_project['name']}"
                    ),
                )

            return ProjectMutationResult(
                action="UPDATE",
                status="NOT FOUND",
                project_id=project_id,
                detail="Project does not exist.",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            return self._failed(
                "UPDATE",
                f"{type(error).__name__}: {error}",
                project_id,
            )

    def delete_project(
        self,
        project_id: str,
    ) -> ProjectMutationResult:
        try:
            payload = self._read_payload()
            projects = payload["projects"]

            remaining_projects: list[dict] = []
            deleted_name: str | None = None

            for project in projects:
                if not isinstance(project, dict):
                    continue

                if str(project.get("id")) == project_id:
                    deleted_name = str(
                        project.get(
                            "name",
                            project_id,
                        )
                    )
                    continue

                remaining_projects.append(project)

            if deleted_name is None:
                return ProjectMutationResult(
                    action="DELETE",
                    status="NOT FOUND",
                    project_id=project_id,
                    detail="Project does not exist.",
                )

            payload["projects"] = remaining_projects
            self._write_payload(payload)

            return ProjectMutationResult(
                action="DELETE",
                status="DELETED",
                project_id=project_id,
                detail=f"Deleted {deleted_name}",
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            return self._failed(
                "DELETE",
                f"{type(error).__name__}: {error}",
                project_id,
            )

    def cycle_status(
        self,
        project_id: str,
        direction: int,
    ) -> ProjectMutationResult:
        project = self._find_project(project_id)

        if project is None:
            return ProjectMutationResult(
                action="STATUS",
                status="NOT FOUND",
                project_id=project_id,
                detail="Project does not exist.",
            )

        current_status = str(
            project.get("status", "CONCEPT")
        ).upper()

        try:
            index = self.STATUS_ORDER.index(
                current_status
            )
        except ValueError:
            index = 0

        new_status = self.STATUS_ORDER[
            (index + direction)
            % len(self.STATUS_ORDER)
        ]

        result = self.update_project(
            project_id,
            {
                "status": new_status,
            },
        )

        if result.status == "SAVED":
            return ProjectMutationResult(
                action="STATUS",
                status="SAVED",
                project_id=project_id,
                detail=f"Status changed to {new_status}",
            )

        return result

    def adjust_progress(
        self,
        project_id: str,
        delta: int,
    ) -> ProjectMutationResult:
        project = self._find_project(project_id)

        if project is None:
            return ProjectMutationResult(
                action="PROGRESS",
                status="NOT FOUND",
                project_id=project_id,
                detail="Project does not exist.",
            )

        try:
            current_progress = int(
                project.get("progress", 0)
            )
        except (TypeError, ValueError):
            current_progress = 0

        new_progress = max(
            0,
            min(current_progress + delta, 100),
        )

        result = self.update_project(
            project_id,
            {
                "progress": new_progress,
            },
        )

        if result.status == "SAVED":
            return ProjectMutationResult(
                action="PROGRESS",
                status="SAVED",
                project_id=project_id,
                detail=(
                    f"Progress changed to "
                    f"{new_progress}%"
                ),
            )

        return result

    def _find_project(
        self,
        project_id: str,
    ) -> dict[str, Any] | None:
        try:
            payload = self._read_payload()
        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None

        for project in payload["projects"]:
            if (
                isinstance(project, dict)
                and str(project.get("id")) == project_id
            ):
                return project

        return None

    def _read_payload(self) -> dict[str, Any]:
        return self._store.read(
            self._validate_payload
        )

    def _write_payload(
        self,
        payload: dict[str, Any],
    ) -> None:
        self._store.write(
            payload,
            self._validate_payload,
        )

    def _normalise_project(
        self,
        project: dict[str, Any],
    ) -> dict[str, Any]:
        name = str(
            project.get("name", "")
        ).strip()

        if not name:
            raise ValueError(
                "Project name cannot be empty."
            )

        status = str(
            project.get("status", "CONCEPT")
        ).upper()

        if status not in self.STATUS_ORDER:
            status = "CONCEPT"

        priority = self._clamp_integer(
            project.get("priority", 1),
            minimum=1,
            maximum=5,
            default=1,
        )

        progress = self._clamp_integer(
            project.get("progress", 0),
            minimum=0,
            maximum=100,
            default=0,
        )

        raw_tech = project.get("tech", [])

        if isinstance(raw_tech, str):
            tech = [
                item.strip()
                for item in raw_tech.split(",")
                if item.strip()
            ]

        elif isinstance(raw_tech, list):
            tech = [
                str(item).strip()
                for item in raw_tech
                if str(item).strip()
            ]

        else:
            tech = []

        return {
            "id": str(project.get("id", "")).strip(),
            "name": name,
            "category": str(
                project.get(
                    "category",
                    "GENERAL",
                )
            ).strip().upper() or "GENERAL",
            "status": status,
            "priority": priority,
            "progress": progress,
            "tech": tech,
            "next_action": str(
                project.get(
                    "next_action",
                    "Not defined",
                )
            ).strip() or "Not defined",
            "description": str(
                project.get("description", "")
            ).strip(),
            "path": str(
                project.get("path", "")
            ).strip(),
            "github_url": self._normalise_github_url(
                project.get("github_url", "")
            ),
            "updated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

    @staticmethod
    def _normalise_github_url(value: Any) -> str:
        url = str(value or "").strip()

        if not url:
            return ""

        lowered = url.lower()

        if lowered.startswith("github.com/"):
            url = f"https://{url}"

        elif lowered.startswith("www.github.com/"):
            url = f"https://{url}"

        elif lowered.startswith("http://"):
            url = f"https://{url[7:]}"

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        if (
            parsed.scheme != "https"
            or host not in {
                "github.com",
                "www.github.com",
            }
            or parsed.path in {"", "/"}
        ):
            raise ValueError(
                "GitHub URL must point to a repository "
                "on https://github.com/."
            )

        return url

    @staticmethod
    def _clamp_integer(
        value: Any,
        *,
        minimum: int,
        maximum: int,
        default: int,
    ) -> int:
        try:
            integer = int(value)
        except (TypeError, ValueError):
            integer = default

        return max(
            minimum,
            min(integer, maximum),
        )

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            value.lower(),
        ).strip("-")

        return slug or "project"

    @staticmethod
    def _unique_id(
        base_id: str,
        existing_ids: set[str],
    ) -> str:
        if base_id not in existing_ids:
            return base_id

        index = 2

        while f"{base_id}-{index}" in existing_ids:
            index += 1

        return f"{base_id}-{index}"

    @staticmethod
    def _failed(
        action: str,
        detail: str,
        project_id: str | None = None,
    ) -> ProjectMutationResult:
        return ProjectMutationResult(
            action=action,
            status="FAILED",
            project_id=project_id,
            detail=detail,
        )
