from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from services.mode_service import ApplicationSpec, WorkMode


@dataclass(frozen=True, slots=True)
class LaunchResult:
    application: str
    status: str
    detail: str


class WorkspaceService:
    """Launches applications configured for HELM work modes."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.home = Path.home()

    def launch_mode(
        self,
        mode: WorkMode,
    ) -> tuple[LaunchResult, ...]:
        return tuple(
            self._launch_application(application)
            for application in mode.applications
        )

    def _launch_application(
        self,
        application: ApplicationSpec,
    ) -> LaunchResult:
        if (
            application.skip_if_running
            and self._is_process_running(
                application.process_names
            )
        ):
            return LaunchResult(
                application=application.name,
                status="ALREADY RUNNING",
                detail="Existing process detected",
            )

        command = self._select_command(
            application.alternatives
        )

        if command is None:
            return LaunchResult(
                application=application.name,
                status="NOT INSTALLED",
                detail="No configured executable was found",
            )

        resolved_command = tuple(
            self._expand_value(argument)
            for argument in command
        )

        working_directory = (
            self._expand_value(application.working_directory)
            if application.working_directory
            else str(self.home)
        )

        try:
            subprocess.Popen(
                resolved_command,
                cwd=working_directory,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

        except (OSError, ValueError) as error:
            return LaunchResult(
                application=application.name,
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return LaunchResult(
            application=application.name,
            status="LAUNCHED",
            detail=" ".join(resolved_command),
        )

    def _select_command(
        self,
        alternatives: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...] | None:
        for command in alternatives:
            if not command:
                continue

            executable = command[0]

            if shutil.which(executable) is None:
                continue

            if (
                executable == "flatpak"
                and len(command) >= 3
                and command[1] == "run"
                and not self._flatpak_app_exists(command[2])
            ):
                continue

            return command

        return None

    @staticmethod
    def _flatpak_app_exists(application_id: str) -> bool:
        try:
            result = subprocess.run(
                [
                    "flatpak",
                    "info",
                    application_id,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        return result.returncode == 0

    @staticmethod
    def _is_process_running(
        process_names: tuple[str, ...],
    ) -> bool:
        if not process_names:
            return False

        expected_names = {
            name.lower()
            for name in process_names
        }

        proc_root = Path("/proc")

        for process_directory in proc_root.iterdir():
            if not process_directory.name.isdigit():
                continue

            try:
                process_name = (
                    process_directory / "comm"
                ).read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip().lower()

            except OSError:
                continue

            if process_name in expected_names:
                return True

        return False

    def _expand_value(self, value: str) -> str:
        return (
            os.path.expandvars(value)
            .replace(
                "{project_root}",
                str(self.project_root),
            )
            .replace(
                "{home}",
                str(self.home),
            )
        )
