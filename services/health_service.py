from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from services.log_service import LogEntry, LogService
from services.mode_service import ModeService
from services.settings_service import (
    HelmSettings,
    SettingsService,
)


@dataclass(frozen=True, slots=True)
class HealthCheck:
    code: str
    category: str
    title: str
    status: str
    detail: str

    @property
    def is_problem(self) -> bool:
        return self.status in {
            "WARNING",
            "CRITICAL",
        }


@dataclass(frozen=True, slots=True)
class HealthReport:
    generated_at: str
    duration_ms: float
    state: str
    checks: tuple[HealthCheck, ...]

    @property
    def passed_count(self) -> int:
        return sum(
            check.status == "PASS"
            for check in self.checks
        )

    @property
    def info_count(self) -> int:
        return sum(
            check.status == "INFO"
            for check in self.checks
        )

    @property
    def warning_count(self) -> int:
        return sum(
            check.status == "WARNING"
            for check in self.checks
        )

    @property
    def critical_count(self) -> int:
        return sum(
            check.status == "CRITICAL"
            for check in self.checks
        )

    @property
    def problem_checks(
        self,
    ) -> tuple[HealthCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if check.is_problem
        )

    def to_text(self) -> str:
        lines = [
            "HELM CORE HEALTH REPORT",
            "",
            f"GENERATED     {self.generated_at}",
            f"STATE         {self.state}",
            f"DURATION      {self.duration_ms:.1f} ms",
            (
                "CHECKS        "
                f"{len(self.checks)} total"
                f"  //  {self.passed_count} passed"
                f"  //  {self.info_count} info"
                f"  //  {self.warning_count} warning"
                f"  //  {self.critical_count} critical"
            ),
            "",
        ]

        current_category: str | None = None

        for check in self.checks:
            if check.category != current_category:
                current_category = check.category

                lines.extend(
                    [
                        current_category,
                        "-" * len(current_category),
                    ]
                )

            lines.append(
                f"[{check.status:<8}] "
                f"{check.title}"
            )
            lines.append(
                f"           {check.detail}"
            )

        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = [
            "# HELM Core Health Report",
            "",
            f"- Generated: {self.generated_at}",
            f"- State: **{self.state}**",
            f"- Duration: {self.duration_ms:.1f} ms",
            f"- Passed: {self.passed_count}",
            f"- Informational: {self.info_count}",
            f"- Warnings: {self.warning_count}",
            f"- Critical: {self.critical_count}",
            "",
        ]

        current_category: str | None = None

        for check in self.checks:
            if check.category != current_category:
                current_category = check.category

                lines.extend(
                    [
                        f"## {current_category}",
                        "",
                    ]
                )

            lines.extend(
                [
                    (
                        f"### {check.status} — "
                        f"{check.title}"
                    ),
                    "",
                    check.detail,
                    "",
                ]
            )

        return "\n".join(lines)


class HealthService:
    """Performs non-destructive HELM startup health checks."""

    REQUIRED_COMMANDS = (
        "python",
        "git",
        "ip",
        "ss",
    )

    FEATURE_COMMANDS = (
        "btop",
        "sensors",
        "nvidia-smi",
        "smartctl",
        "nmcli",
        "ollama",
    )

    def __init__(
        self,
        settings_service: SettingsService,
        mode_service: ModeService,
        log_service: LogService,
        project_root: Path | None = None,
    ) -> None:
        self.settings_service = settings_service
        self.mode_service = mode_service
        self.log_service = log_service

        self.project_root = (
            project_root
            or Path(__file__).resolve().parents[1]
        )

        self.export_directory = (
            self.project_root
            / "logs"
            / "exports"
        )

    def collect(
        self,
        *,
        settings: HelmSettings,
        active_mode_id: str,
        telemetry_state: str,
        telemetry_duration_ms: float,
        telemetry_skipped_cycles: int,
    ) -> HealthReport:
        started = perf_counter()
        checks: list[HealthCheck] = []

        checks.extend(
            self._check_telemetry(
                settings=settings,
                state=telemetry_state,
                duration_ms=telemetry_duration_ms,
                skipped_cycles=(
                    telemetry_skipped_cycles
                ),
            )
        )

        checks.extend(
            self._check_configuration(
                settings=settings,
                active_mode_id=active_mode_id,
            )
        )

        checks.extend(
            self._check_directories()
        )

        checks.extend(
            self._check_commands()
        )

        checks.extend(
            self._check_ollama(settings)
        )

        checks.extend(
            self._check_git()
        )

        checks.extend(
            self._check_previous_session()
        )

        state = self._overall_state(checks)

        return HealthReport(
            generated_at=datetime.now().isoformat(
                timespec="seconds"
            ),
            duration_ms=(
                perf_counter() - started
            ) * 1000.0,
            state=state,
            checks=tuple(checks),
        )

    def export_report(
        self,
        report: HealthReport,
    ) -> Path:
        self.export_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S-%f"
        )

        destination = (
            self.export_directory
            / f"helm-health-{timestamp}.md"
        )

        destination.write_text(
            report.to_markdown(),
            encoding="utf-8",
        )

        return destination

    def _check_telemetry(
        self,
        *,
        settings: HelmSettings,
        state: str,
        duration_ms: float,
        skipped_cycles: int,
    ) -> list[HealthCheck]:
        normalized_state = state.upper()

        if normalized_state == "FAILED":
            state_check = self._check(
                "telemetry-state",
                "TELEMETRY ENGINE",
                "Telemetry state",
                "CRITICAL",
                (
                    "The latest telemetry cycle did not "
                    "produce a usable snapshot."
                ),
            )

        elif normalized_state == "DEGRADED":
            state_check = self._check(
                "telemetry-state",
                "TELEMETRY ENGINE",
                "Telemetry state",
                "WARNING",
                (
                    "Telemetry is operating with at least "
                    "one fallback data source."
                ),
            )

        elif normalized_state == "NOMINAL":
            state_check = self._check(
                "telemetry-state",
                "TELEMETRY ENGINE",
                "Telemetry state",
                "PASS",
                "Latest snapshot completed successfully.",
            )

        else:
            state_check = self._check(
                "telemetry-state",
                "TELEMETRY ENGINE",
                "Telemetry state",
                "INFO",
                f"Current engine state: {normalized_state}.",
            )

        interval_ms = (
            settings.telemetry_interval
            * 1000.0
        )

        if (
            duration_ms > interval_ms
            and duration_ms > 0
        ):
            performance_status = "WARNING"
            performance_detail = (
                f"Collection took {duration_ms:.1f} ms, "
                f"longer than the configured "
                f"{interval_ms:.0f} ms interval."
            )
        else:
            performance_status = "PASS"
            performance_detail = (
                f"Latest collection took "
                f"{duration_ms:.1f} ms with a "
                f"{interval_ms:.0f} ms interval."
            )

        skipped_status = (
            "INFO"
            if skipped_cycles
            else "PASS"
        )

        return [
            state_check,
            self._check(
                "telemetry-performance",
                "TELEMETRY ENGINE",
                "Collection performance",
                performance_status,
                performance_detail,
            ),
            self._check(
                "telemetry-skipped",
                "TELEMETRY ENGINE",
                "Skipped cycles",
                skipped_status,
                (
                    f"{skipped_cycles} overlapping cycle(s) "
                    "were intentionally skipped."
                    if skipped_cycles
                    else "No telemetry cycles were skipped."
                ),
            ),
        ]

    def _check_configuration(
        self,
        *,
        settings: HelmSettings,
        active_mode_id: str,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        diagnostics = (
            self.settings_service.diagnostics()
        )

        checks.append(
            self._check(
                "settings-config",
                "CONFIGURATION",
                "Runtime settings",
                (
                    "PASS"
                    if diagnostics.config_valid
                    else "CRITICAL"
                ),
                (
                    f"{diagnostics.config_path}; "
                    f"size={diagnostics.config_size} B; "
                    f"backups={diagnostics.backup_count}; "
                    f"exports={diagnostics.export_count}"
                ),
            )
        )

        checks.append(
            self._check(
                "ai-config",
                "CONFIGURATION",
                "Local AI settings",
                "PASS",
                (
                    f"model={settings.ai_model}; "
                    f"context={settings.ai_context_window}; "
                    f"keep_alive={settings.ai_keep_alive}"
                ),
            )
        )

        modes_path = self.mode_service.config_path

        try:
            modes_payload = self._read_json(
                modes_path
            )

            raw_modes = modes_payload.get(
                "modes",
                []
            )

            if not isinstance(raw_modes, list):
                raise ValueError(
                    "'modes' must be a list."
                )

            mode_ids = [
                str(mode.get("id", "")).strip()
                for mode in raw_modes
                if isinstance(mode, dict)
            ]

            if (
                not mode_ids
                or any(not mode_id for mode_id in mode_ids)
                or len(mode_ids) != len(set(mode_ids))
            ):
                raise ValueError(
                    "Workspace IDs are missing or duplicated."
                )

            checks.append(
                self._check(
                    "modes-config",
                    "CONFIGURATION",
                    "Workspace database",
                    "PASS",
                    (
                        f"{len(mode_ids)} valid workspace(s) "
                        f"loaded from {modes_path}."
                    ),
                )
            )

            if active_mode_id == "custom":
                active_status = "INFO"
                active_detail = (
                    "Custom runtime configuration is active."
                )

            elif active_mode_id in mode_ids:
                active_status = "PASS"
                active_detail = (
                    f"Active workspace '{active_mode_id}' "
                    "exists in the database."
                )

            else:
                active_status = "CRITICAL"
                active_detail = (
                    f"Active workspace '{active_mode_id}' "
                    "does not exist."
                )

            checks.append(
                self._check(
                    "active-mode",
                    "CONFIGURATION",
                    "Active workspace",
                    active_status,
                    active_detail,
                )
            )

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            checks.append(
                self._check(
                    "modes-config",
                    "CONFIGURATION",
                    "Workspace database",
                    "CRITICAL",
                    (
                        f"{type(error).__name__}: "
                        f"{self._clean(error)}"
                    ),
                )
            )

        projects_path = (
            self.project_root
            / "config"
            / "projects.json"
        )

        try:
            project_payload = self._read_json(
                projects_path
            )

            raw_projects = project_payload.get(
                "projects",
                []
            )

            if not isinstance(raw_projects, list):
                raise ValueError(
                    "'projects' must be a list."
                )

            checks.append(
                self._check(
                    "projects-config",
                    "CONFIGURATION",
                    "Project database",
                    "PASS",
                    (
                        f"{len(raw_projects)} project(s) "
                        f"loaded from {projects_path}."
                    ),
                )
            )

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            checks.append(
                self._check(
                    "projects-config",
                    "CONFIGURATION",
                    "Project database",
                    "WARNING",
                    (
                        f"{type(error).__name__}: "
                        f"{self._clean(error)}"
                    ),
                )
            )

        return checks

    def _check_directories(
        self,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        directory_specs = (
            (
                "directory-config",
                "Configuration directory",
                self.project_root / "config",
            ),
            (
                "directory-logs",
                "Log directory",
                self.project_root / "logs",
            ),
            (
                "directory-scripts",
                "Scripts directory",
                self.project_root / "scripts",
            ),
        )

        for code, title, path in directory_specs:
            exists = path.is_dir()
            writable = (
                os.access(path, os.W_OK)
                if exists
                else False
            )

            if not exists:
                status = "CRITICAL"
                detail = f"Directory does not exist: {path}"
            elif title == "Scripts directory":
                status = "PASS"
                detail = f"Directory is readable: {path}"
            elif not writable:
                status = "CRITICAL"
                detail = f"Directory is not writable: {path}"
            else:
                status = "PASS"
                detail = f"Directory is writable: {path}"

            checks.append(
                self._check(
                    code,
                    "FILESYSTEM",
                    title,
                    status,
                    detail,
                )
            )

        diagnostic_script = (
            self.project_root
            / "scripts"
            / "helm-system-diagnostic.sh"
        )

        checks.append(
            self._check(
                "diagnostic-script",
                "FILESYSTEM",
                "System diagnostic script",
                (
                    "PASS"
                    if diagnostic_script.is_file()
                    else "WARNING"
                ),
                (
                    f"Available: {diagnostic_script}"
                    if diagnostic_script.is_file()
                    else f"Missing: {diagnostic_script}"
                ),
            )
        )

        return checks

    def _check_commands(
        self,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        for command in self.REQUIRED_COMMANDS:
            path = shutil.which(command)

            checks.append(
                self._check(
                    f"command-{command}",
                    "SYSTEM TOOLS",
                    command,
                    (
                        "PASS"
                        if path is not None
                        else "CRITICAL"
                    ),
                    (
                        path
                        if path is not None
                        else "Required command is not installed."
                    ),
                )
            )

        for command in self.FEATURE_COMMANDS:
            path = shutil.which(command)

            checks.append(
                self._check(
                    f"command-{command}",
                    "SYSTEM TOOLS",
                    command,
                    (
                        "PASS"
                        if path is not None
                        else "WARNING"
                    ),
                    (
                        path
                        if path is not None
                        else (
                            "Optional HELM feature will "
                            "be unavailable."
                        )
                    ),
                )
            )

        checks.append(
            self._check(
                "python-runtime",
                "SYSTEM TOOLS",
                "Python runtime",
                "PASS",
                (
                    f"{sys.version.split()[0]} "
                    f"// {sys.executable}"
                ),
            )
        )

        return checks

    def _check_ollama(
        self,
        settings: HelmSettings,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        ollama_path = shutil.which("ollama")

        if ollama_path is None:
            return [
                self._check(
                    "ollama-provider",
                    "LOCAL AI",
                    "Ollama provider",
                    "WARNING",
                    "Ollama executable was not found.",
                )
            ]

        active_code, active_output = self._run(
            (
                "systemctl",
                "is-active",
                "ollama.service",
            ),
            timeout=3.0,
        )

        checks.append(
            self._check(
                "ollama-service",
                "LOCAL AI",
                "Ollama service",
                (
                    "PASS"
                    if (
                        active_code == 0
                        and active_output == "active"
                    )
                    else "WARNING"
                ),
                (
                    "ollama.service is active."
                    if (
                        active_code == 0
                        and active_output == "active"
                    )
                    else (
                        "ollama.service state: "
                        f"{active_output or 'unknown'}"
                    )
                ),
            )
        )

        enabled_code, enabled_output = self._run(
            (
                "systemctl",
                "is-enabled",
                "ollama.service",
            ),
            timeout=3.0,
        )

        checks.append(
            self._check(
                "ollama-autostart",
                "LOCAL AI",
                "Ollama autostart",
                (
                    "PASS"
                    if enabled_code == 0
                    else "WARNING"
                ),
                (
                    "ollama.service is enabled."
                    if enabled_code == 0
                    else (
                        "ollama.service is not enabled: "
                        f"{enabled_output or 'unknown'}"
                    )
                ),
            )
        )

        try:
            version_payload = self._http_json(
                "http://127.0.0.1:11434/api/version"
            )

            version = str(
                version_payload.get(
                    "version",
                    "UNKNOWN",
                )
            )

            checks.append(
                self._check(
                    "ollama-api",
                    "LOCAL AI",
                    "Ollama API",
                    "PASS",
                    f"Local API online; version={version}.",
                )
            )

            tags_payload = self._http_json(
                "http://127.0.0.1:11434/api/tags"
            )

            models = self._model_names(
                tags_payload.get(
                    "models",
                    [],
                )
            )

            installed = self._model_matches(
                settings.ai_model,
                models,
            )

            checks.append(
                self._check(
                    "ollama-model",
                    "LOCAL AI",
                    "Configured model",
                    (
                        "PASS"
                        if installed
                        else "WARNING"
                    ),
                    (
                        f"{settings.ai_model} is installed."
                        if installed
                        else (
                            f"{settings.ai_model} is not "
                            "present in the local model library."
                        )
                    ),
                )
            )

        except (
            OSError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
            urllib.error.HTTPError,
        ) as error:
            checks.append(
                self._check(
                    "ollama-api",
                    "LOCAL AI",
                    "Ollama API",
                    "WARNING",
                    (
                        f"{type(error).__name__}: "
                        f"{self._clean(error)}"
                    ),
                )
            )

        return checks

    def _check_git(
        self,
    ) -> list[HealthCheck]:
        repo_code, repo_output = self._run(
            (
                "git",
                "-C",
                str(self.project_root),
                "rev-parse",
                "--is-inside-work-tree",
            ),
            timeout=3.0,
        )

        if (
            repo_code != 0
            or repo_output != "true"
        ):
            return [
                self._check(
                    "git-repository",
                    "PROJECT STATE",
                    "Git repository",
                    "WARNING",
                    (
                        repo_output
                        or "Project is not inside a Git repository."
                    ),
                )
            ]

        _, branch = self._run(
            (
                "git",
                "-C",
                str(self.project_root),
                "branch",
                "--show-current",
            ),
            timeout=3.0,
        )

        _, status_output = self._run(
            (
                "git",
                "-C",
                str(self.project_root),
                "status",
                "--porcelain",
            ),
            timeout=3.0,
        )

        dirty_count = len(
            [
                line
                for line in status_output.splitlines()
                if line.strip()
            ]
        )

        return [
            self._check(
                "git-repository",
                "PROJECT STATE",
                "Git repository",
                "PASS",
                (
                    f"Repository detected; "
                    f"branch={branch or 'DETACHED'}."
                ),
            ),
            self._check(
                "git-working-tree",
                "PROJECT STATE",
                "Git working tree",
                (
                    "INFO"
                    if dirty_count
                    else "PASS"
                ),
                (
                    f"{dirty_count} uncommitted path(s)."
                    if dirty_count
                    else "Working tree is clean."
                ),
            ),
        ]

    def _check_previous_session(
        self,
    ) -> list[HealthCheck]:
        entries = self.log_service.tail(
            limit=1000
        )

        previous_entries = (
            self._previous_session_entries(entries)
        )

        error_count = sum(
            entry.level == "ERROR"
            for entry in previous_entries
        )

        critical_count = sum(
            entry.level == "CRITICAL"
            for entry in previous_entries
        )

        if critical_count:
            status = "WARNING"
        elif error_count:
            status = "INFO"
        else:
            status = "PASS"

        return [
            self._check(
                "previous-session-errors",
                "EVENT HISTORY",
                "Previous session",
                status,
                (
                    f"{error_count} error(s); "
                    f"{critical_count} critical event(s); "
                    f"{len(previous_entries)} total event(s)."
                ),
            )
        ]

    @staticmethod
    def _previous_session_entries(
        entries: tuple[LogEntry, ...],
    ) -> tuple[LogEntry, ...]:
        start_indices = [
            index
            for index, entry in enumerate(entries)
            if (
                entry.source == "HELM"
                and entry.message
                == "CyberDeck control interface started"
            )
        ]

        if len(start_indices) >= 2:
            start = start_indices[-2] + 1
            end = start_indices[-1]
            return entries[start:end]

        if len(start_indices) == 1:
            return entries[:start_indices[0]]

        return entries

    @staticmethod
    def _overall_state(
        checks: list[HealthCheck],
    ) -> str:
        statuses = {
            check.status
            for check in checks
        }

        if "CRITICAL" in statuses:
            return "CRITICAL"

        if "WARNING" in statuses:
            return "DEGRADED"

        return "NOMINAL"

    @staticmethod
    def _check(
        code: str,
        category: str,
        title: str,
        status: str,
        detail: str,
    ) -> HealthCheck:
        return HealthCheck(
            code=code,
            category=category,
            title=title,
            status=status,
            detail=" ".join(
                str(detail).split()
            ),
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
                f"{path.name} must contain a JSON object."
            )

        return payload

    @staticmethod
    def _run(
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> tuple[int, str]:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

        except (
            OSError,
            subprocess.TimeoutExpired,
        ) as error:
            return 1, (
                f"{type(error).__name__}: "
                f"{HealthService._clean(error)}"
            )

        output = (
            completed.stdout.strip()
            or completed.stderr.strip()
        )

        return completed.returncode, output

    @staticmethod
    def _http_json(
        url: str,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=3.0,
        ) as response:
            payload = json.load(response)

        if not isinstance(payload, dict):
            raise ValueError(
                "HTTP response is not a JSON object."
            )

        return payload

    @staticmethod
    def _model_names(
        raw_models: object,
    ) -> tuple[str, ...]:
        if not isinstance(raw_models, list):
            return ()

        names: list[str] = []

        for item in raw_models:
            if not isinstance(item, dict):
                continue

            name = str(
                item.get(
                    "name",
                    item.get(
                        "model",
                        "",
                    ),
                )
            ).strip()

            if name:
                names.append(name)

        return tuple(names)

    @staticmethod
    def _model_matches(
        expected: str,
        available: tuple[str, ...],
    ) -> bool:
        if expected in available:
            return True

        expected_base = expected.split(
            ":",
            1,
        )[0]

        return any(
            candidate.split(
                ":",
                1,
            )[0] == expected_base
            for candidate in available
        )

    @staticmethod
    def _clean(
        value: object,
    ) -> str:
        cleaned = " ".join(
            str(value).split()
        )

        return (
            cleaned[:300]
            or "No detail available."
        )
