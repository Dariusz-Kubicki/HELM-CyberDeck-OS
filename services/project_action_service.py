from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class ProjectActionResult:
    action_id: str
    title: str
    status: str
    detail: str


class ProjectActionService:
    """Launches approved tools for a project directory."""

    def __init__(self) -> None:
        self.project_root = Path(
            __file__
        ).resolve().parents[1]

    def launch(
        self,
        action_id: str,
        project_path: str,
        github_url: str = "",
    ) -> ProjectActionResult:
        if action_id == "github":
            return self._open_github(github_url)

        resolved_path = self._resolve_path(
            project_path
        )

        if resolved_path is None:
            return ProjectActionResult(
                action_id=action_id,
                title=self._title(action_id),
                status="UNAVAILABLE",
                detail=(
                    "Project directory is not configured "
                    "or does not exist."
                ),
            )

        command = self._resolve_command(
            action_id,
            resolved_path,
        )

        if command is None:
            return ProjectActionResult(
                action_id=action_id,
                title=self._title(action_id),
                status="UNAVAILABLE",
                detail="Required application was not detected.",
            )

        try:
            subprocess.Popen(
                command,
                cwd=str(resolved_path),
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

        except (OSError, ValueError) as error:
            return ProjectActionResult(
                action_id=action_id,
                title=self._title(action_id),
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return ProjectActionResult(
            action_id=action_id,
            title=self._title(action_id),
            status="LAUNCHED",
            detail=str(resolved_path),
        )

    def _open_github(
        self,
        github_url: str,
    ) -> ProjectActionResult:
        url = github_url.strip()

        if not url:
            return ProjectActionResult(
                action_id="github",
                title="OPEN GITHUB REPOSITORY",
                status="UNAVAILABLE",
                detail="GitHub repository is not configured.",
            )

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
            return ProjectActionResult(
                action_id="github",
                title="OPEN GITHUB REPOSITORY",
                status="UNAVAILABLE",
                detail="Configured GitHub URL is invalid.",
            )

        if shutil.which("xdg-open"):
            command = (
                "xdg-open",
                url,
            )
        else:
            browser = next(
                (
                    name
                    for name in (
                        "firefox",
                        "brave",
                        "brave-browser",
                        "chromium",
                        "google-chrome-stable",
                    )
                    if shutil.which(name)
                ),
                None,
            )

            if browser is None:
                return ProjectActionResult(
                    action_id="github",
                    title="OPEN GITHUB REPOSITORY",
                    status="UNAVAILABLE",
                    detail="No supported browser was detected.",
                )

            command = (
                browser,
                url,
            )

        try:
            subprocess.Popen(
                command,
                cwd=str(self.project_root),
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

        except OSError as error:
            return ProjectActionResult(
                action_id="github",
                title="OPEN GITHUB REPOSITORY",
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return ProjectActionResult(
            action_id="github",
            title="OPEN GITHUB REPOSITORY",
            status="LAUNCHED",
            detail=url,
        )

    def _resolve_path(
        self,
        value: str,
    ) -> Path | None:
        if not value.strip():
            return None

        expanded = (
            os.path.expandvars(value)
            .replace(
                "{project_root}",
                str(self.project_root),
            )
        )

        path = Path(expanded).expanduser()

        try:
            path = path.resolve()
        except OSError:
            pass

        if not path.is_dir():
            return None

        return path

    @staticmethod
    def _resolve_command(
        action_id: str,
        path: Path,
    ) -> tuple[str, ...] | None:
        path_text = str(path)

        if action_id == "folder":
            if shutil.which("dolphin"):
                return (
                    "dolphin",
                    path_text,
                )

            if shutil.which("xdg-open"):
                return (
                    "xdg-open",
                    path_text,
                )

        if action_id == "terminal":
            if shutil.which("konsole"):
                return (
                    "konsole",
                    "--workdir",
                    path_text,
                )

            if shutil.which("kitty"):
                return (
                    "kitty",
                    "--directory",
                    path_text,
                )

            if shutil.which("alacritty"):
                return (
                    "alacritty",
                    "--working-directory",
                    path_text,
                )

        if action_id == "editor":
            if shutil.which("code"):
                return (
                    "code",
                    "--new-window",
                    path_text,
                )

            if shutil.which("codium"):
                return (
                    "codium",
                    "--new-window",
                    path_text,
                )

            if shutil.which("kate"):
                return (
                    "kate",
                    path_text,
                )

        return None

    @staticmethod
    def _title(action_id: str) -> str:
        return {
            "folder": "OPEN PROJECT FOLDER",
            "terminal": "OPEN PROJECT TERMINAL",
            "editor": "OPEN PROJECT EDITOR",
            "github": "OPEN GITHUB REPOSITORY",
        }.get(
            action_id,
            action_id.upper(),
        )
