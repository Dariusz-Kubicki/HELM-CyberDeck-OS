from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import monotonic


@dataclass(frozen=True, slots=True)
class Project:
    project_id: str
    name: str
    category: str
    status: str
    priority: int
    progress: int
    tech: tuple[str, ...]
    next_action: str
    description: str
    path: str
    github_url: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProjectSample:
    projects: tuple[Project, ...]
    active_count: int
    completed_count: int
    blocked_count: int
    average_progress: float
    focus_project: Project | None
    error: str | None


class ProjectMonitor:
    """Loads and caches the HELM project database."""

    REFRESH_SECONDS = 0.25

    ACTIVE_STATUSES = {
        "ACTIVE",
        "IN PROGRESS",
        "BUILDING",
        "TESTING",
    }

    COMPLETED_STATUSES = {
        "STABLE",
        "DONE",
        "COMPLETED",
    }

    def __init__(
        self,
        config_path: Path | None = None,
    ) -> None:
        self.config_path = config_path or (
            Path(__file__).resolve().parents[1]
            / "config"
            / "projects.json"
        )

        self._cached_sample = ProjectSample(
            projects=(),
            active_count=0,
            completed_count=0,
            blocked_count=0,
            average_progress=0.0,
            focus_project=None,
            error=None,
        )

        self._next_refresh = 0.0
        self._last_modified_ns: int | None = None

    def sample(self) -> ProjectSample:
        now = monotonic()

        if now < self._next_refresh:
            return self._cached_sample

        self._next_refresh = now + self.REFRESH_SECONDS

        try:
            modified_ns = self.config_path.stat().st_mtime_ns
        except OSError as error:
            self._cached_sample = self._error_sample(
                f"Cannot access project database: {error}"
            )
            return self._cached_sample

        if modified_ns == self._last_modified_ns:
            return self._cached_sample

        try:
            payload = json.loads(
                self.config_path.read_text(
                    encoding="utf-8"
                )
            )

            raw_projects = payload.get("projects", [])

            if not isinstance(raw_projects, list):
                raise ValueError(
                    "'projects' must be a list"
                )

            projects = tuple(
                self._parse_project(item)
                for item in raw_projects
                if isinstance(item, dict)
            )

            active_count = sum(
                project.status in self.ACTIVE_STATUSES
                for project in projects
            )

            completed_count = sum(
                project.status in self.COMPLETED_STATUSES
                for project in projects
            )

            blocked_count = sum(
                project.status == "BLOCKED"
                for project in projects
            )

            average_progress = (
                sum(
                    project.progress
                    for project in projects
                )
                / len(projects)
                if projects
                else 0.0
            )

            focus_candidates = tuple(
                project
                for project in projects
                if project.status in self.ACTIVE_STATUSES
            )

            unfinished_projects = tuple(
                project
                for project in projects
                if project.status
                not in self.COMPLETED_STATUSES
            )

            focus_project = max(
                (
                    focus_candidates
                    or unfinished_projects
                    or projects
                ),
                key=lambda project: (
                    project.priority,
                    -project.progress,
                ),
                default=None,
            )

            self._cached_sample = ProjectSample(
                projects=projects,
                active_count=active_count,
                completed_count=completed_count,
                blocked_count=blocked_count,
                average_progress=average_progress,
                focus_project=focus_project,
                error=None,
            )

            self._last_modified_ns = modified_ns

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            self._cached_sample = self._error_sample(
                f"Invalid project database: {error}"
            )

        return self._cached_sample

    @staticmethod
    def _parse_project(item: dict) -> Project:
        raw_tech = item.get("tech", [])

        if not isinstance(raw_tech, list):
            raw_tech = []

        try:
            priority = int(item.get("priority", 1))
        except (TypeError, ValueError):
            priority = 1

        try:
            progress = int(item.get("progress", 0))
        except (TypeError, ValueError):
            progress = 0

        return Project(
            project_id=str(
                item.get("id", "unknown")
            ),
            name=str(
                item.get("name", "Unnamed project")
            ),
            category=str(
                item.get("category", "GENERAL")
            ).upper(),
            status=str(
                item.get("status", "CONCEPT")
            ).upper(),
            priority=max(
                1,
                min(priority, 5),
            ),
            progress=max(
                0,
                min(progress, 100),
            ),
            tech=tuple(
                str(value)
                for value in raw_tech
            ),
            next_action=str(
                item.get(
                    "next_action",
                    "Not defined",
                )
            ),
            description=str(
                item.get("description", "")
            ),
            path=str(
                item.get("path", "")
            ),
            github_url=str(
                item.get("github_url", "")
            ),
            updated_at=str(
                item.get("updated_at", "")
            ),
        )

    def _error_sample(
        self,
        message: str,
    ) -> ProjectSample:
        return ProjectSample(
            projects=self._cached_sample.projects,
            active_count=self._cached_sample.active_count,
            completed_count=(
                self._cached_sample.completed_count
            ),
            blocked_count=(
                self._cached_sample.blocked_count
            ),
            average_progress=(
                self._cached_sample.average_progress
            ),
            focus_project=(
                self._cached_sample.focus_project
            ),
            error=message,
        )
