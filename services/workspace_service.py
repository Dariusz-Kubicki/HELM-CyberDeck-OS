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
    """Launches complete desktop workspaces configured in HELM."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.home = Path.home()

    def launch_mode(
        self,
        mode: WorkMode,
    ) -> tuple[LaunchResult, ...]:
        results = tuple(
            self.launch_application(application)
            for application in mode.applications
        )

        self._send_notification(mode, results)
        return results

    def launch_application(
        self,
        application: ApplicationSpec,
    ) -> LaunchResult:
        if not application.enabled:
            return LaunchResult(
                application=application.name,
                status="DISABLED",
                detail="Disabled in the workspace manifest",
            )

        return self._launch_item(application)

    def _launch_item(
        self,
        application: ApplicationSpec,
    ) -> LaunchResult:
        if application.kind == "browser":
            return self._launch_browser(application)

        return self._launch_application(application)

    def _launch_browser(
        self,
        application: ApplicationSpec,
    ) -> LaunchResult:
        if not application.urls:
            return LaunchResult(
                application=application.name,
                status="SKIPPED",
                detail="No URLs configured",
            )

        browsers = (
            "firefox",
            "brave",
            "brave-browser",
            "chromium",
            "google-chrome-stable",
            "google-chrome",
        )

        selected_browser = next(
            (
                browser
                for browser in browsers
                if shutil.which(browser) is not None
            ),
            None,
        )

        if selected_browser is not None:
            command = (
                selected_browser,
                "--new-window",
                *application.urls,
            )

            try:
                self._spawn(
                    command,
                    working_directory=str(self.home),
                )
            except OSError as error:
                return LaunchResult(
                    application=application.name,
                    status="FAILED",
                    detail=f"{type(error).__name__}: {error}",
                )

            return LaunchResult(
                application=application.name,
                status="LAUNCHED",
                detail=(
                    f"{selected_browser}: "
                    f"{len(application.urls)} tab(s)"
                ),
            )

        if shutil.which("xdg-open") is not None:
            launched = 0

            for url in application.urls:
                try:
                    self._spawn(
                        ("xdg-open", url),
                        working_directory=str(self.home),
                    )
                    launched += 1
                except OSError:
                    continue

            if launched:
                return LaunchResult(
                    application=application.name,
                    status="LAUNCHED",
                    detail=f"xdg-open: {launched} URL(s)",
                )

        return LaunchResult(
            application=application.name,
            status="NOT INSTALLED",
            detail="No supported browser detected",
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
            self._spawn(
                resolved_command,
                working_directory=working_directory,
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
                ["flatpak", "info", application_id],
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

        try:
            process_directories = Path("/proc").iterdir()
        except OSError:
            return False

        for process_directory in process_directories:
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

    @staticmethod
    def _spawn(
        command: tuple[str, ...],
        *,
        working_directory: str,
    ) -> None:
        subprocess.Popen(
            command,
            cwd=working_directory,
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

    def _expand_value(self, value: str) -> str:
        return (
            os.path.expandvars(str(value))
            .replace(
                "{project_root}",
                str(self.project_root),
            )
            .replace(
                "{home}",
                str(self.home),
            )
        )

    @staticmethod
    def _send_notification(
        mode: WorkMode,
        results: tuple[LaunchResult, ...],
    ) -> None:
        if shutil.which("notify-send") is None:
            return

        launched = sum(
            result.status == "LAUNCHED"
            for result in results
        )
        unavailable = sum(
            result.status in {"FAILED", "NOT INSTALLED"}
            for result in results
        )

        message = (
            f"Workspace activated\n"
            f"Applications launched: {launched}\n"
            f"Unavailable: {unavailable}"
        )

        try:
            subprocess.Popen(
                [
                    "notify-send",
                    "-a",
                    "HELM",
                    f"HELM // {mode.name}",
                    message,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            pass
